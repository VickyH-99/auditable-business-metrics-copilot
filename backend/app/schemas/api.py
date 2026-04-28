from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class AggregationDefinition(BaseModel):
    type: Literal["count_distinct", "sum", "average_order_value"]
    field: str


class MetricDefinition(BaseModel):
    metric_id: str
    name_zh: str
    name_en: str
    description: str
    table: str
    time_field: str
    aggregation: AggregationDefinition
    default_filters: dict[str, Any]
    allowed_dimensions: list[str]
    formula: str
    owner: str
    update_frequency: str
    aliases: list[str] = Field(default_factory=list)


class MetricCatalogResponse(BaseModel):
    metrics: list[MetricDefinition]


class TimeRangeModel(BaseModel):
    mode: str
    start_date: date
    end_date: date
    label: str


class QueryPlan(BaseModel):
    intent: Literal["summary", "trend", "ranking", "breakdown", "attribution"]
    metric: str
    time_range: TimeRangeModel
    comparison: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = 10


class ClarificationState(BaseModel):
    intent: str
    time_range: str | None = None
    comparison: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    original_message: str
    metric: str | None = None
    limit: int = 10


class ConversationStatePayload(BaseModel):
    unresolved_query: ClarificationState | None = None
    last_query_plan: QueryPlan | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class MetricsQueryRequest(BaseModel):
    session_id: str | None = None
    message: str | None = None
    query_plan: QueryPlan | None = None


class ExplainRequest(BaseModel):
    query_plan: QueryPlan
    question: str | None = None


class TrendRequest(BaseModel):
    metric_id: str
    time_range_mode: str = "last_7_days"
    filters: dict[str, Any] = Field(default_factory=dict)


class RankingRequest(BaseModel):
    metric_id: str
    dimension: str
    time_range_mode: str = "today"
    limit: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)


class AttributionRequest(BaseModel):
    metric_id: str
    compare_with: Literal["yesterday", "last_week"] = "yesterday"
    filters: dict[str, Any] = Field(default_factory=dict)


class ClarificationResponse(BaseModel):
    type: Literal["clarification"] = "clarification"
    message: str
    options: list[str]
    conversation_state: ConversationStatePayload


class HealthResponse(BaseModel):
    status: str
    data_source: str
    database_available: bool
    metrics_loaded: int
    data_updated_at: str | None = None


class AttributionRow(BaseModel):
    dimension: str
    dimension_label: str
    member: str
    current_value: float | int | None = None
    compare_value: float | int | None = None
    delta: float | int | None = None
    absolute_delta: float | int | None = None
    negative_contribution_pct: float | None = None
    positive_offset_pct: float | None = None
    net_contribution_pct: float | None = None
    direction: Literal["negative_driver", "positive_offset", "neutral"]


class AttributionPayload(BaseModel):
    current_total: float | int | None = None
    compare_total: float | int | None = None
    total_delta: float | int | None = None
    drivers: list[AttributionRow] = Field(default_factory=list)
    offsets: list[AttributionRow] = Field(default_factory=list)
    dimension_impact: list[AttributionRow] = Field(default_factory=list)
    negative_drivers: list[AttributionRow] = Field(default_factory=list)
    positive_offsets: list[AttributionRow] = Field(default_factory=list)
    neutral_items: list[AttributionRow] = Field(default_factory=list)
    all_rows: list[AttributionRow] = Field(default_factory=list)


class AnswerResponse(BaseModel):
    type: Literal["answer"] = "answer"
    question: str
    summary: str
    metric: str
    metric_name: str
    current_value: float | int | None = None
    yesterday_value: float | int | None = None
    last_year_value: float | int | None = None
    last_month_value: float | int | None = None
    yoy: float | None = None
    mom: float | None = None
    dod: float | None = None
    mtd_value: float | int | None = None
    anomaly: dict[str, Any] | None = None
    insights: list[str] = Field(default_factory=list)
    query_plan: dict[str, Any]
    sql_used: str
    metric_definition: dict[str, Any]
    chart_data: list[dict[str, Any]]
    table_data: list[dict[str, Any]]
    raw_data: list[dict[str, Any]]
    raw_data_sql: str | None = None
    attribution: AttributionPayload | None = None
    data_updated_at: str
    data_source: str
    conversation_state: ConversationStatePayload | None = None
