from __future__ import annotations

from app.core.time_utils import resolve_time_range
from app.schemas.api import ConversationStatePayload
from app.services.nlu import QueryParser


def test_metric_mapping():
    parser = QueryParser(resolve_time_range("today", __import__("datetime").date(2026, 4, 27)).end_date)
    result = parser.parse("今天卖车多少？", ConversationStatePayload())
    assert result.plan is not None
    assert result.plan.metric == "car_sales_count"


def test_clarification_logic():
    parser = QueryParser(__import__("datetime").date(2026, 4, 27))
    result = parser.parse("各城市排名？", ConversationStatePayload())
    assert result.clarification is not None
    assert result.clarification["state"].missing_fields == ["metric"]


def test_query_plan_generation():
    parser = QueryParser(__import__("datetime").date(2026, 4, 27))
    result = parser.parse("按业务类型拆解今天交车量", ConversationStatePayload())
    assert result.plan is not None
    assert result.plan.intent == "breakdown"
    assert result.plan.dimensions == ["business_type"]

