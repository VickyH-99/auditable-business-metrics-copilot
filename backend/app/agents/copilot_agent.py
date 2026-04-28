from __future__ import annotations

from app.schemas.api import (
    AttributionRequest,
    ChatRequest,
    ExplainRequest,
    MetricsQueryRequest,
    RankingRequest,
    TrendRequest,
)
from app.services.chat_service import ChatService
from app.services.metric_service import MetricService


class CopilotAgent:
    def __init__(self, chat_service: ChatService, metric_service: MetricService) -> None:
        self.chat_service = chat_service
        self.metric_service = metric_service

    def handle_chat(self, request: ChatRequest) -> dict:
        return self.chat_service.handle_message(request.session_id, request.message)

    def execute_query(self, request: MetricsQueryRequest) -> dict:
        return self.metric_service.handle_query_request(request)

    def explain(self, request: ExplainRequest) -> dict:
        return self.metric_service.explain_query(request)

    def trend(self, request: TrendRequest) -> dict:
        return self.metric_service.run_trend_request(request)

    def ranking(self, request: RankingRequest) -> dict:
        return self.metric_service.run_ranking_request(request)

    def attribution(self, request: AttributionRequest) -> dict:
        return self.metric_service.run_attribution_request(request)

