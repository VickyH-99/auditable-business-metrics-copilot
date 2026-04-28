from __future__ import annotations

from dataclasses import dataclass

from app.core.time_utils import resolve_time_range
from app.schemas.api import ClarificationState, ConversationStatePayload, QueryPlan, TimeRangeModel

METRIC_OPTIONS = [
    ("总交车量", "total_delivery_count"),
    ("卖车销量", "car_sales_count"),
    ("租车销量", "rental_count"),
    ("二手车销量", "used_car_count"),
    ("续租量", "renewal_count"),
    ("销售金额", "sales_amount"),
    ("毛利", "gross_profit"),
]

DIMENSION_OPTIONS = [
    ("渠道", "channel"),
    ("大区", "region_group"),
    ("区域", "region"),
    ("城市", "city"),
    ("门店", "store_name"),
    ("销售人员", "sales_person_name"),
    ("业务类型", "business_type"),
]


@dataclass
class ParseResult:
    plan: QueryPlan | None = None
    clarification: dict | None = None
    question: str | None = None


class QueryParser:
    def __init__(self, today) -> None:
        self.today = today

    def parse(self, message: str, conversation_state: ConversationStatePayload) -> ParseResult:
        unresolved = conversation_state.unresolved_query
        if unresolved:
            return self._resolve_clarification(message, conversation_state)

        intent = self._detect_intent(message)
        metric = self._detect_metric(message)
        dimension = self._detect_dimension(message)
        comparison = self._detect_comparison(message)
        time_range_mode = self._detect_time_range(message, intent)
        filters: dict = {}

        previous_plan = conversation_state.last_query_plan
        if not metric and previous_plan and any(token in message for token in ("同期", "呢", "那", "继续", "排名", "拆解")):
            metric = previous_plan.metric
        if not time_range_mode and previous_plan and any(token in message for token in ("同期", "呢", "那", "继续")):
            time_range_mode = previous_plan.time_range.mode

        missing_fields: list[str] = []
        if not metric:
            missing_fields.append("metric")
        if intent in {"ranking", "breakdown"} and not dimension:
            missing_fields.append("dimension")
        if intent == "trend" and not time_range_mode:
            missing_fields.append("time_range")

        if missing_fields:
            clarification_state = ClarificationState(
                intent=intent,
                metric=metric,
                time_range=time_range_mode,
                comparison=comparison,
                dimensions=[dimension] if dimension else [],
                filters=filters,
                missing_fields=missing_fields,
                original_message=message,
            )
            return ParseResult(
                clarification={
                    "message": self._clarification_message(missing_fields[0], intent),
                    "options": self._clarification_options(missing_fields[0]),
                    "state": clarification_state,
                }
            )

        resolved_time_range = resolve_time_range(time_range_mode or "today", self.today)
        dimensions = []
        if intent in {"trend"}:
            dimensions = ["statistics_date"]
        elif dimension:
            dimensions = [dimension]

        plan = QueryPlan(
            intent=intent,
            metric=metric,
            time_range=TimeRangeModel.model_validate(resolved_time_range.to_dict()),
            comparison=comparison,
            dimensions=dimensions,
            filters=filters,
        )
        return ParseResult(plan=plan, question=self._rewrite_question(message, plan))

    def _resolve_clarification(self, message: str, conversation_state: ConversationStatePayload) -> ParseResult:
        unresolved = conversation_state.unresolved_query
        if not unresolved:
            return self.parse(message, conversation_state)

        metric = unresolved.metric or self._detect_metric(message)
        dimension = unresolved.dimensions[0] if unresolved.dimensions else self._detect_dimension(message)
        time_range_mode = unresolved.time_range or self._detect_time_range(message, unresolved.intent)
        missing_fields = []
        if not metric:
            missing_fields.append("metric")
        if unresolved.intent in {"ranking", "breakdown"} and not dimension:
            missing_fields.append("dimension")
        if unresolved.intent == "trend" and not time_range_mode:
            missing_fields.append("time_range")

        if missing_fields:
            clarification_state = unresolved.model_copy(
                update={
                    "metric": metric,
                    "dimensions": [dimension] if dimension else unresolved.dimensions,
                    "time_range": time_range_mode,
                    "missing_fields": missing_fields,
                }
            )
            return ParseResult(
                clarification={
                    "message": self._clarification_message(missing_fields[0], unresolved.intent),
                    "options": self._clarification_options(missing_fields[0]),
                    "state": clarification_state,
                }
            )

        resolved_time_range = resolve_time_range(time_range_mode or "today", self.today)
        dimensions = ["statistics_date"] if unresolved.intent == "trend" else ([dimension] if dimension else [])
        plan = QueryPlan(
            intent=unresolved.intent,
            metric=metric,
            time_range=TimeRangeModel.model_validate(resolved_time_range.to_dict()),
            comparison=unresolved.comparison,
            dimensions=dimensions,
            filters=unresolved.filters,
            limit=unresolved.limit,
        )
        return ParseResult(plan=plan, question=self._rewrite_question(unresolved.original_message, plan))

    def _clarification_message(self, missing_field: str, intent: str) -> str:
        if missing_field == "metric":
            if intent == "trend":
                return "请问您想看哪个指标的趋势？"
            if intent == "ranking":
                return "请问您想看哪个指标的排名？"
            if intent == "breakdown":
                return "请问您想拆解哪个指标？"
            return "请问您想查询哪个指标？"
        if missing_field == "dimension":
            return "请问您希望按哪个维度查看？"
        return "请问您想看哪个时间范围？"

    def _clarification_options(self, missing_field: str) -> list[str]:
        if missing_field == "metric":
            return [item[0] for item in METRIC_OPTIONS]
        if missing_field == "dimension":
            return [item[0] for item in DIMENSION_OPTIONS]
        return ["今天", "最近7天", "最近30天", "本月累计"]

    def _detect_intent(self, message: str) -> str:
        if "为什么" in message or "原因" in message:
            return "attribution"
        if "趋势" in message:
            return "trend"
        if "排名" in message:
            return "ranking"
        if "拆解" in message or ("按" in message and self._detect_dimension(message)):
            return "breakdown"
        return "summary"

    def _detect_metric(self, message: str) -> str | None:
        checks = [
            ("销售金额", "sales_amount"),
            ("销售额", "sales_amount"),
            ("毛利", "gross_profit"),
            ("客单价", "average_order_value"),
            ("平均订单金额", "average_order_value"),
            ("二手车", "used_car_count"),
            ("续租", "renewal_count"),
            ("租车", "rental_count"),
            ("卖车", "car_sales_count"),
            ("交车", "total_delivery_count"),
            ("交付", "total_delivery_count"),
        ]
        for token, metric_id in checks:
            if token in message:
                return metric_id
        return None

    def _detect_dimension(self, message: str) -> str | None:
        checks = [
            ("销售人员", "sales_person_name"),
            ("销售顾问", "sales_person_name"),
            ("业务类型", "business_type"),
            ("门店", "store_name"),
            ("城市", "city"),
            ("大区", "region_group"),
            ("区域", "region"),
            ("渠道", "channel"),
        ]
        for token, dimension in checks:
            if token in message:
                return dimension
        return None

    def _detect_time_range(self, message: str, intent: str) -> str | None:
        if "最近30天" in message or "近30天" in message:
            return "last_30_days"
        if "最近7天" in message or "近7天" in message:
            return "last_7_days"
        if "本月累计" in message or "月累计" in message:
            return "mtd"
        if "昨天" in message or "昨日" in message:
            return "yesterday"
        if "今天" in message or "今日" in message:
            return "today"
        if intent == "trend":
            return None
        return "today"

    def _detect_comparison(self, message: str) -> str | None:
        if "同比" in message:
            return "yoy"
        if "环比" in message:
            return "mom"
        if "较昨日" in message or "对比昨天" in message:
            return "dod"
        if "去年同期" in message:
            return "last_year_same_period"
        if "上月同期" in message:
            return "last_month_same_period"
        return None

    def _rewrite_question(self, message: str, plan: QueryPlan) -> str:
        metric_names = dict(METRIC_OPTIONS)
        dimension_names = dict(DIMENSION_OPTIONS)
        metric_name = next((cn for cn, metric_id in METRIC_OPTIONS if metric_id == plan.metric), plan.metric)
        if plan.intent == "trend":
            return f"{plan.time_range.label}{metric_name}趋势如何？"
        if plan.intent == "ranking":
            dimension_name = next((cn for cn, dim in DIMENSION_OPTIONS if dim == plan.dimensions[0]), plan.dimensions[0])
            return f"{plan.time_range.label}{dimension_name}{metric_name}排名如何？"
        if plan.intent == "breakdown":
            dimension_name = next((cn for cn, dim in DIMENSION_OPTIONS if dim == plan.dimensions[0]), plan.dimensions[0])
            return f"按{dimension_name}拆解{plan.time_range.label}{metric_name}"
        if plan.intent == "attribution":
            return f"为什么{plan.time_range.label}{metric_name}变化了？"
        return message if message.endswith("？") else f"{message}？"

