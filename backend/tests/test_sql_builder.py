from __future__ import annotations

from datetime import date

from app.metrics.catalog_loader import load_metric_catalog
from app.services.sql_builder import build_aggregate_sql


def test_sql_builder_uses_statistics_date_and_completed():
    catalog = load_metric_catalog()
    metric = catalog.get("car_sales_count")
    sql = build_aggregate_sql(
        metric=metric,
        start_date=date(2026, 4, 21),
        end_date=date(2026, 4, 27),
        filters={},
        dimensions=["statistics_date"],
        order_by="statistics_date ASC",
    )
    assert "statistics_date BETWEEN '2026-04-21' AND '2026-04-27'" in sql
    assert "business_type = 'sale'" in sql
    assert "order_status = 'completed'" in sql

