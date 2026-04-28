from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.db.models import FactDeliveryOrder
from app.schemas.api import MetricDefinition
from app.services.mock_data import generate_mock_orders, seed_database_if_needed
from app.services.sql_builder import DETAIL_COLUMNS, build_aggregate_sql, build_detail_sql


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class DataSourceManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: Engine | None = None
        self.database_available = False
        self.data_source = "fallback_mock"
        self._fallback_records: list[dict] = []
        self._data_updated_at: datetime | None = None

    def initialize(self) -> None:
        for _ in range(self.settings.database_connect_retries):
            try:
                engine = create_engine(self.settings.database_url, future=True, pool_pre_ping=True)
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                seed_database_if_needed(engine, self.settings.today)
                self.engine = engine
                self.database_available = True
                self.data_source = self.settings.default_data_source_label
                self._refresh_data_updated_at()
                return
            except Exception:
                time.sleep(self.settings.database_connect_retry_seconds)

        self._fallback_records = generate_mock_orders(
            start_date=self.settings.today - timedelta(days=790),
            end_date=self.settings.today,
        )
        self.database_available = False
        self.data_source = "fallback_mock"
        self._data_updated_at = max(item["updated_at"] for item in self._fallback_records)

    def _refresh_data_updated_at(self) -> None:
        if not self.engine:
            return
        with self.engine.connect() as connection:
            updated_at = connection.execute(text("SELECT MAX(updated_at) FROM fact_delivery_orders")).scalar_one_or_none()
        if isinstance(updated_at, datetime):
            self._data_updated_at = updated_at

    @property
    def data_updated_at(self) -> str:
        if not self._data_updated_at:
            return datetime.utcnow().isoformat()
        return self._data_updated_at.isoformat()

    def aggregate(
        self,
        metric: MetricDefinition,
        start_date: date,
        end_date: date,
        filters: dict,
        dimensions: list[str] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        title: str | None = None,
    ) -> tuple[list[dict], str]:
        sql = build_aggregate_sql(
            metric=metric,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            dimensions=dimensions or [],
            order_by=order_by,
            limit=limit,
            title=title,
        )
        if self.database_available and self.engine:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql))
                rows = [{key: _normalize_scalar(value) for key, value in row._mapping.items()} for row in result]
            return rows, sql
        return self._aggregate_fallback(metric, start_date, end_date, filters, dimensions or [], order_by, limit), sql

    def detail_rows(
        self,
        metric: MetricDefinition,
        start_date: date,
        end_date: date,
        filters: dict,
        limit: int,
    ) -> tuple[list[dict], str]:
        sql = build_detail_sql(metric, start_date, end_date, filters, limit)
        if self.database_available and self.engine:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql))
                rows = [{key: _normalize_scalar(value) for key, value in row._mapping.items()} for row in result]
            return rows, sql
        return self._detail_rows_fallback(metric, start_date, end_date, filters, limit), sql

    def _matching_records(self, start_date: date, end_date: date, filters: dict) -> list[dict]:
        records = []
        for row in self._fallback_records:
            statistics_date = row["statistics_date"]
            if not (start_date <= statistics_date <= end_date):
                continue
            matched = True
            for field, expected in filters.items():
                actual = row.get(field)
                if isinstance(expected, list):
                    if actual not in expected:
                        matched = False
                        break
                elif actual != expected:
                    matched = False
                    break
            if matched:
                records.append(row)
        return records

    def _aggregate_fallback(
        self,
        metric: MetricDefinition,
        start_date: date,
        end_date: date,
        filters: dict,
        dimensions: list[str],
        order_by: str | None,
        limit: int | None,
    ) -> list[dict]:
        merged_filters = dict(metric.default_filters)
        merged_filters.update(filters)
        records = self._matching_records(start_date, end_date, merged_filters)
        buckets: dict[tuple, dict] = defaultdict(dict)

        for row in records:
            key = tuple(row[dimension] for dimension in dimensions)
            bucket = buckets.setdefault(key, {"__order_ids": set(), "__sales_sum": 0.0, "__metric_sum": 0.0})
            if metric.aggregation.type == "count_distinct":
                bucket["__order_ids"].add(row["order_id"])
            elif metric.aggregation.type == "sum":
                bucket["__metric_sum"] += float(row[metric.aggregation.field])
            elif metric.aggregation.type == "average_order_value":
                bucket["__sales_sum"] += float(row["sales_amount"])
                bucket["__order_ids"].add(row["order_id"])

        rows: list[dict] = []
        for key, bucket in buckets.items():
            item = {dimension: key[index] for index, dimension in enumerate(dimensions)}
            if metric.aggregation.type == "count_distinct":
                item["metric_value"] = len(bucket["__order_ids"])
            elif metric.aggregation.type == "sum":
                item["metric_value"] = round(bucket["__metric_sum"], 2)
            else:
                denominator = len(bucket["__order_ids"])
                item["metric_value"] = round(bucket["__sales_sum"] / denominator, 2) if denominator else 0.0
            rows.append(item)

        if not dimensions and not rows:
            rows = [{"metric_value": 0}]

        if order_by:
            reverse = order_by.endswith("DESC")
            field_name = order_by.split()[0]
            rows = sorted(rows, key=lambda item: item.get(field_name, 0), reverse=reverse)
        if limit:
            rows = rows[:limit]
        return rows

    def _detail_rows_fallback(
        self,
        metric: MetricDefinition,
        start_date: date,
        end_date: date,
        filters: dict,
        limit: int,
    ) -> list[dict]:
        merged_filters = dict(metric.default_filters)
        merged_filters.update(filters)
        records = self._matching_records(start_date, end_date, merged_filters)
        records = sorted(records, key=lambda item: (item["statistics_date"], item["delivery_time"]), reverse=True)
        results = []
        for row in records[:limit]:
            results.append({column: _normalize_scalar(row[column]) for column in DETAIL_COLUMNS})
        return results
