from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.time_utils import (
    TimeRange,
    resolve_time_range,
    rolling_days_range,
    shift_range_by_days,
    shift_range_by_months,
    shift_range_by_years,
)
from app.metrics.catalog_loader import MetricCatalog
from app.schemas.api import (
    AnswerResponse,
    AttributionRequest,
    ExplainRequest,
    MetricsQueryRequest,
    QueryPlan,
    RankingRequest,
    TrendRequest,
)
from app.services.attribution import calculate_attribution_contributions
from app.services.calculations import compute_z_score, round_metric, safe_change
from app.services.data_source import DataSourceManager
from app.services.sql_builder import build_attribution_sql, merge_filters

DIMENSION_LABELS = {
    "channel": "渠道",
    "region_group": "大区",
    "region": "区域",
    "city": "城市",
    "store_name": "门店",
    "sales_person_name": "销售人员",
    "business_type": "业务类型",
    "statistics_date": "日期",
}

ATTRIBUTION_DIMENSIONS = ["city", "region_group", "channel", "store_name", "business_type"]


class MetricService:
    def __init__(self, catalog: MetricCatalog, data_source: DataSourceManager, settings: Settings) -> None:
        self.catalog = catalog
        self.data_source = data_source
        self.settings = settings

    def handle_query_request(self, request: MetricsQueryRequest) -> dict:
        if request.query_plan:
            return self.execute_plan(request.query_plan, request.message or "结构化指标查询")
        raise ValueError("query_plan is required for /api/metrics/query")

    def explain_query(self, request: ExplainRequest) -> dict:
        response = self.execute_plan(request.query_plan, request.question or "指标解释")
        response["summary"] = (
            f"{response['metric_name']} 使用 {response['query_plan']['time_range']['label']} 作为时间范围，"
            f"默认按 {response['metric_definition']['time_field']} 统计，并自动套用 {response['query_plan']['filters']} 过滤条件。"
        )
        return response

    def run_trend_request(self, request: TrendRequest) -> dict:
        plan = QueryPlan(
            intent="trend",
            metric=request.metric_id,
            time_range=resolve_time_range(request.time_range_mode, self.settings.today).to_dict(),
            comparison=None,
            dimensions=["statistics_date"],
            filters=request.filters,
        )
        plan = QueryPlan.model_validate(plan)
        metric_name = self.catalog.get(request.metric_id).name_zh
        return self.execute_plan(plan, f"{plan.time_range.label}{metric_name}趋势如何？")

    def run_ranking_request(self, request: RankingRequest) -> dict:
        plan = QueryPlan(
            intent="ranking",
            metric=request.metric_id,
            time_range=resolve_time_range(request.time_range_mode, self.settings.today).to_dict(),
            comparison=None,
            dimensions=[request.dimension],
            filters=request.filters,
            limit=request.limit,
        )
        plan = QueryPlan.model_validate(plan)
        metric_name = self.catalog.get(request.metric_id).name_zh
        dimension_label = DIMENSION_LABELS.get(request.dimension, request.dimension)
        return self.execute_plan(plan, f"{plan.time_range.label}{dimension_label}{metric_name}排名如何？")

    def run_attribution_request(self, request: AttributionRequest) -> dict:
        time_range = resolve_time_range("today", self.settings.today)
        comparison = "dod" if request.compare_with == "yesterday" else "wow"
        plan = QueryPlan(
            intent="attribution",
            metric=request.metric_id,
            time_range=time_range.to_dict(),
            comparison=comparison,
            dimensions=[],
            filters=request.filters,
        )
        plan = QueryPlan.model_validate(plan)
        metric_name = self.catalog.get(request.metric_id).name_zh
        return self.execute_plan(plan, f"为什么今天{metric_name}变化了？")

    def execute_plan(self, plan: QueryPlan, question: str) -> dict:
        metric = self.catalog.get(plan.metric)
        self._validate_dimensions(metric, plan.dimensions)
        filters = merge_filters(metric, plan.filters)
        time_range = TimeRange(
            mode=plan.time_range.mode,
            start_date=plan.time_range.start_date,
            end_date=plan.time_range.end_date,
            label=plan.time_range.label,
        )

        current_rows, current_sql = self.data_source.aggregate(
            metric,
            time_range.start_date,
            time_range.end_date,
            filters,
            dimensions=[],
            title=f"{question} - 当前值",
        )
        current_value = self._single_metric_value(current_rows)

        previous_period = shift_range_by_days(time_range, -time_range.days, "previous_period")
        last_year_range = shift_range_by_years(time_range, -1, "last_year")
        last_month_range = shift_range_by_months(time_range, -1, "last_month")
        mtd_range = resolve_time_range("mtd", time_range.end_date)

        previous_rows, previous_sql = self.data_source.aggregate(
            metric,
            previous_period.start_date,
            previous_period.end_date,
            filters,
            dimensions=[],
            title=f"{question} - 对比周期",
        )
        last_year_rows, last_year_sql = self.data_source.aggregate(
            metric,
            last_year_range.start_date,
            last_year_range.end_date,
            filters,
            dimensions=[],
            title=f"{question} - 去年同期",
        )
        last_month_rows, last_month_sql = self.data_source.aggregate(
            metric,
            last_month_range.start_date,
            last_month_range.end_date,
            filters,
            dimensions=[],
            title=f"{question} - 上月同期",
        )
        mtd_rows, mtd_sql = self.data_source.aggregate(
            metric,
            mtd_range.start_date,
            mtd_range.end_date,
            filters,
            dimensions=[],
            title=f"{question} - 本月累计",
        )

        previous_value = self._single_metric_value(previous_rows)
        last_year_value = self._single_metric_value(last_year_rows)
        last_month_value = self._single_metric_value(last_month_rows)
        mtd_value = self._single_metric_value(mtd_rows)

        chart_range = time_range if plan.intent == "trend" else rolling_days_range(time_range.end_date, 7)
        chart_rows, chart_sql = self.data_source.aggregate(
            metric,
            chart_range.start_date,
            chart_range.end_date,
            filters,
            dimensions=["statistics_date"],
            order_by="statistics_date ASC",
            title=f"{question} - 趋势图",
        )
        chart_data = [self._normalize_row(row) for row in chart_rows]

        table_data: list[dict[str, Any]]
        table_sql = ""
        insights: list[str] = []
        attribution_payload: dict[str, Any] | None = None

        if plan.intent in {"ranking", "breakdown"}:
            dimension = plan.dimensions[0]
            table_rows, table_sql = self.data_source.aggregate(
                metric,
                time_range.start_date,
                time_range.end_date,
                filters,
                dimensions=[dimension],
                order_by="metric_value DESC",
                limit=plan.limit,
                title=f"{question} - 维度明细",
            )
            table_data = [self._normalize_row(row) for row in table_rows]
            insights = self._build_dimensional_insights(table_data, dimension)
        elif plan.intent == "trend":
            table_data = chart_data
            table_sql = chart_sql
            insights = self._build_trend_insights(chart_data)
        elif plan.intent == "attribution":
            attribution_payload, table_sql, insights = self._build_attribution(
                metric,
                time_range,
                filters,
                plan.comparison,
                current_value,
            )
            table_data = attribution_payload["all_rows"]
        else:
            table_data = [
                {"label": "当前区间", "value": round_metric(float(current_value or 0))},
                {"label": "对比周期", "value": round_metric(float(previous_value or 0))},
                {"label": "去年同期", "value": round_metric(float(last_year_value or 0))},
                {"label": "上月同期", "value": round_metric(float(last_month_value or 0))},
                {"label": "本月累计", "value": round_metric(float(mtd_value or 0))},
            ]
            table_sql = current_sql

        raw_data, raw_data_sql = self.data_source.detail_rows(
            metric,
            time_range.start_date,
            time_range.end_date,
            filters,
            self.settings.fallback_row_limit,
        )

        anomaly = self._detect_anomaly(metric, filters, time_range.end_date, current_value)

        response = AnswerResponse(
            question=question,
            summary=self._build_summary(
                metric,
                plan,
                current_value,
                last_year_value,
                last_month_value,
                previous_value,
                insights,
                anomaly,
                table_data,
                attribution_payload,
            ),
            metric=metric.metric_id,
            metric_name=metric.name_zh,
            current_value=round_metric(float(current_value or 0)),
            yesterday_value=round_metric(float(previous_value or 0)),
            last_year_value=round_metric(float(last_year_value or 0)),
            last_month_value=round_metric(float(last_month_value or 0)),
            yoy=safe_change(current_value, last_year_value),
            mom=safe_change(current_value, last_month_value),
            dod=safe_change(current_value, previous_value),
            mtd_value=round_metric(float(mtd_value or 0)),
            anomaly=anomaly,
            insights=insights,
            query_plan=self._query_plan_payload(plan, filters),
            sql_used="\n\n".join(
                [current_sql, previous_sql, last_year_sql, last_month_sql, mtd_sql, chart_sql, table_sql]
            ).strip(),
            metric_definition=metric.model_dump(),
            chart_data=chart_data,
            table_data=table_data,
            raw_data=raw_data,
            raw_data_sql=raw_data_sql,
            attribution=attribution_payload,
            data_updated_at=self.data_source.data_updated_at,
            data_source=self.data_source.data_source,
        )
        return response.model_dump()

    def _build_attribution(
        self,
        metric,
        time_range: TimeRange,
        filters: dict[str, Any],
        comparison: str | None,
        current_total,
    ) -> tuple[dict[str, Any], str, list[str]]:
        compare_range = self._resolve_attribution_compare_range(time_range, comparison)
        current_total_rows, current_total_sql = self.data_source.aggregate(
            metric,
            time_range.start_date,
            time_range.end_date,
            filters,
            dimensions=[],
            title="归因分析 - 当前周期总量",
        )
        compare_total_rows, compare_total_sql = self.data_source.aggregate(
            metric,
            compare_range.start_date,
            compare_range.end_date,
            filters,
            dimensions=[],
            title="归因分析 - 对比周期总量",
        )
        current_total_value = self._single_metric_value(current_total_rows) if current_total is None else float(current_total)
        compare_total_value = self._single_metric_value(compare_total_rows)

        rows: list[dict[str, Any]] = []
        sql_blocks = [current_total_sql, compare_total_sql]
        candidate_dimensions = [dimension for dimension in ATTRIBUTION_DIMENSIONS if dimension not in filters]

        for dimension in candidate_dimensions:
            current_rows, _ = self.data_source.aggregate(
                metric,
                time_range.start_date,
                time_range.end_date,
                filters,
                dimensions=[dimension],
                title=f"{dimension} - 当前周期归因",
            )
            compare_rows, _ = self.data_source.aggregate(
                metric,
                compare_range.start_date,
                compare_range.end_date,
                filters,
                dimensions=[dimension],
                title=f"{dimension} - 对比周期归因",
            )
            sql_blocks.append(
                build_attribution_sql(
                    metric,
                    time_range.start_date,
                    time_range.end_date,
                    compare_range.start_date,
                    compare_range.end_date,
                    filters,
                    dimension,
                    title=f"归因分析 - {DIMENSION_LABELS[dimension]}",
                )
            )
            current_map = {row[dimension]: float(row["metric_value"]) for row in current_rows}
            compare_map = {row[dimension]: float(row["metric_value"]) for row in compare_rows}
            all_members = sorted(set(current_map) | set(compare_map))
            if len(all_members) <= 1:
                continue
            for member in all_members:
                current_value = current_map.get(member, 0.0)
                compare_value = compare_map.get(member, 0.0)
                rows.append(
                    {
                        "dimension": dimension,
                        "dimension_label": DIMENSION_LABELS[dimension],
                        "member": member,
                        "current_value": current_value,
                        "compare_value": compare_value,
                        "delta": current_value - compare_value,
                    }
                )

        attribution = calculate_attribution_contributions(rows, current_total_value, compare_total_value)
        insights = self._build_attribution_insights(metric, attribution)
        return attribution, "\n\n".join(sql_blocks), insights

    def _resolve_attribution_compare_range(self, time_range: TimeRange, comparison: str | None) -> TimeRange:
        if comparison == "wow":
            return shift_range_by_days(time_range, -7, "last_week_same_period")
        if comparison == "dod" and time_range.days == 1:
            return shift_range_by_days(time_range, -1, "yesterday")
        return shift_range_by_days(time_range, -time_range.days, "previous_period")

    def _build_attribution_insights(self, metric, attribution: dict[str, Any]) -> list[str]:
        unit = self._metric_unit(metric)
        total_delta = float(attribution["total_delta"] or 0)
        if abs(total_delta) < 1e-12:
            return ["整体变化不明显，但不同维度之间存在结构性波动，建议关注结构性变化。"]

        if total_delta < 0:
            primary_rows = attribution["negative_drivers"]
            secondary_rows = attribution["positive_offsets"]
            primary_label = "下滑驱动"
            primary_pct_key = "negative_contribution_pct"
            primary_share_label = "负向变化"
            primary_verb = "下降"
            secondary_verb = "增长"
            secondary_label = "抵消"
        else:
            primary_rows = attribution["positive_offsets"]
            secondary_rows = attribution["negative_drivers"]
            primary_label = "增长驱动"
            primary_pct_key = "positive_offset_pct"
            primary_share_label = "正向变化"
            primary_verb = "增长"
            secondary_verb = "下降"
            secondary_label = "拖累"

        insights: list[str] = []
        for row in primary_rows[:3]:
            pct = self._format_ratio(row.get(primary_pct_key))
            insights.append(
                f"{primary_label}：{row['dimension_label']} {row['member']}{primary_verb}"
                f"{self._format_value_with_unit(abs(float(row['delta'] or 0)), unit)}，占{primary_share_label}{pct}。"
            )
        for row in secondary_rows[:2]:
            insights.append(
                f"{row['dimension_label']} {row['member']}{secondary_verb}"
                f"{self._format_value_with_unit(abs(float(row['delta'] or 0)), unit)}，对整体变化形成部分{secondary_label}。"
            )
        return insights

    def _detect_anomaly(self, metric, filters: dict, anchor_date, current_value) -> dict | None:
        trend_range = rolling_days_range(anchor_date, 30)
        history_rows, _ = self.data_source.aggregate(
            metric,
            trend_range.start_date,
            trend_range.end_date,
            filters,
            dimensions=["statistics_date"],
            order_by="statistics_date ASC",
            title="异常检测 - 近30天",
        )
        history = [float(row["metric_value"]) for row in history_rows[:-1]]
        anomaly = compute_z_score(float(current_value or 0), history)
        if not anomaly:
            return None
        if anomaly["is_anomaly"]:
            anomaly["message"] = f"当前值相较近30天均值出现异常波动，z-score={anomaly['z_score']}。"
        else:
            anomaly["message"] = "当前值在近30天正常波动范围内。"
        return anomaly

    def _build_dimensional_insights(self, rows: list[dict[str, Any]], dimension: str) -> list[str]:
        if not rows:
            return []
        leader = rows[0]
        return [f"{DIMENSION_LABELS[dimension]} {leader[dimension]} 当前贡献最高，指标值为 {leader['metric_value']}。"]

    def _build_trend_insights(self, rows: list[dict[str, Any]]) -> list[str]:
        if len(rows) < 2:
            return []
        first = float(rows[0]["metric_value"])
        last = float(rows[-1]["metric_value"])
        direction = "上升" if last >= first else "下降"
        return [f"最近区间整体呈{direction}趋势，期末值为 {round_metric(last)}。"]

    def _build_summary(
        self,
        metric,
        plan: QueryPlan,
        current_value,
        last_year_value,
        last_month_value,
        previous_value,
        insights: list[str],
        anomaly: dict | None,
        table_data: list[dict[str, Any]],
        attribution: dict[str, Any] | None = None,
    ) -> str:
        if plan.intent == "attribution" and attribution:
            return self._build_attribution_summary(metric, plan.time_range.label, attribution)

        summary = (
            f"{plan.time_range.label}{metric.name_zh}为 {round_metric(float(current_value or 0))}。"
            f" 同比 {self._format_change(safe_change(current_value, last_year_value))}，"
            f"环比 {self._format_change(safe_change(current_value, last_month_value))}，"
            f"较上个对比周期 {self._format_change(safe_change(current_value, previous_value))}。"
        )
        if plan.intent == "ranking" and table_data:
            summary += f" 排名第一的是 {table_data[0][plan.dimensions[0]]}，指标值 {table_data[0]['metric_value']}。"
        if plan.intent == "breakdown" and table_data:
            summary += f" 贡献最高的是 {table_data[0][plan.dimensions[0]]}。"
        if insights:
            summary += " " + " ".join(insights[:3])
        if anomaly:
            summary += " " + anomaly["message"]
        return summary.strip()

    def _build_attribution_summary(self, metric, time_label: str, attribution: dict[str, Any]) -> str:
        unit = self._metric_unit(metric)
        total_delta = float(attribution["total_delta"] or 0)
        if abs(total_delta) < 1e-12:
            return (
                f"{time_label}{metric.name_zh}整体变化不明显，但不同维度之间存在结构性波动。"
                "部分维度增长，部分维度下滑，建议关注结构性变化。"
            )

        if total_delta < 0:
            primary_rows = attribution["negative_drivers"]
            secondary_rows = attribution["positive_offsets"]
            summary = f"{time_label}{metric.name_zh}较对比周期下降 {self._format_value_with_unit(abs(total_delta), unit)}。"
            if primary_rows:
                summary += f" 主要下滑来自{self._join_members(primary_rows[:3])}。"
                summary += " " + self._build_primary_detail_sentence(primary_rows[:2], unit, "下降", "负向变化")
            if secondary_rows:
                summary += " 同时，" + self._build_secondary_sentence(secondary_rows[:2], unit, "增长", "对整体下滑形成一定抵消。")
            return summary.strip()

        primary_rows = attribution["positive_offsets"]
        secondary_rows = attribution["negative_drivers"]
        summary = f"{time_label}{metric.name_zh}较对比周期增长 {self._format_value_with_unit(abs(total_delta), unit)}。"
        if primary_rows:
            summary += f" 主要增长来自{self._join_members(primary_rows[:3])}。"
            summary += " " + self._build_primary_detail_sentence(primary_rows[:2], unit, "增长", "正向变化")
        if secondary_rows:
            summary += " 同时，" + self._build_secondary_sentence(secondary_rows[:2], unit, "下降", "对增长形成部分拖累。")
        return summary.strip()

    def _build_primary_detail_sentence(
        self,
        rows: list[dict[str, Any]],
        unit: str,
        verb: str,
        share_label: str,
    ) -> str:
        if not rows:
            return ""
        pct_key = "negative_contribution_pct" if verb == "下降" else "positive_offset_pct"
        detail_text = "；".join(
            f"{row['member']}{verb}{self._format_value_with_unit(abs(float(row['delta'] or 0)), unit)}，占{share_label}{self._format_ratio(row.get(pct_key))}"
            for row in rows
        )
        return f"其中{detail_text}。"

    def _build_secondary_sentence(
        self,
        rows: list[dict[str, Any]],
        unit: str,
        verb: str,
        closing: str,
    ) -> str:
        if not rows:
            return ""
        if len(rows) == 1:
            row = rows[0]
            return f"{row['member']}{verb}{self._format_value_with_unit(abs(float(row['delta'] or 0)), unit)}，{closing}"

        head = "、".join(str(row["member"]) for row in rows[:-1])
        tail = rows[-1]
        shared_value = None
        if all(float(row["delta"] or 0) == float(rows[0]["delta"] or 0) for row in rows):
            shared_value = abs(float(rows[0]["delta"] or 0))

        if shared_value is not None:
            return f"{head}和{tail['member']}分别{verb}{self._format_value_with_unit(shared_value, unit)}，{closing}"

        detail_text = "、".join(
            f"{row['member']}{verb}{self._format_value_with_unit(abs(float(row['delta'] or 0)), unit)}" for row in rows
        )
        return f"{detail_text}，{closing}"

    def _join_members(self, rows: list[dict[str, Any]]) -> str:
        members = [str(row["member"]) for row in rows]
        if len(members) <= 1:
            return "".join(members)
        if len(members) == 2:
            return f"{members[0]}和{members[1]}"
        return f"{'、'.join(members[:-1])}和{members[-1]}"

    def _metric_unit(self, metric) -> str:
        if metric.aggregation.type == "count_distinct":
            return "台"
        if metric.aggregation.type in {"sum", "average_order_value"}:
            return "元"
        return ""

    def _format_value_with_unit(self, value: float | int | None, unit: str) -> str:
        rounded = round_metric(float(value or 0))
        return f"{rounded}{unit}" if unit else str(rounded)

    def _format_ratio(self, value: float | None) -> str:
        if value is None:
            return "--"
        return f"{value * 100:.1f}%"

    def _format_change(self, change: float | None) -> str:
        if change is None:
            return "无法计算"
        direction = "增长" if change >= 0 else "下降"
        return f"{direction}{abs(change) * 100:.1f}%"

    def _query_plan_payload(self, plan: QueryPlan, filters: dict[str, Any]) -> dict[str, Any]:
        payload = plan.model_dump()
        payload["filters"] = filters
        return payload

    def _single_metric_value(self, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return float(rows[0].get("metric_value", 0.0))

    def _validate_dimensions(self, metric, dimensions: list[str]) -> None:
        invalid = [dimension for dimension in dimensions if dimension not in metric.allowed_dimensions]
        if invalid:
            raise ValueError(f"Invalid dimensions for metric {metric.metric_id}: {invalid}")

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                normalized[key] = value.isoformat()
            elif isinstance(value, (int, float)):
                normalized[key] = round_metric(float(value))
            else:
                normalized[key] = value
        return normalized
