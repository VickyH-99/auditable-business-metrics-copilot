from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.api import (
    AnswerResponse,
    AttributionRequest,
    ChatRequest,
    ClarificationResponse,
    ExplainRequest,
    HealthResponse,
    MetricsQueryRequest,
    RankingRequest,
    TrendRequest,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    catalog = request.app.state.catalog
    data_source = request.app.state.data_source
    return HealthResponse(
        status="ok",
        data_source=data_source.data_source,
        database_available=data_source.database_available,
        metrics_loaded=len(catalog.definitions),
        data_updated_at=data_source.data_updated_at,
    )


@router.get("/metrics/catalog")
def metrics_catalog(request: Request):
    return request.app.state.catalog.to_response().model_dump()


@router.get("/metrics/definition/{metric_id}")
def metric_definition(metric_id: str, request: Request):
    try:
        return request.app.state.catalog.get(metric_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/chat", response_model=ClarificationResponse | AnswerResponse)
def chat(request_body: ChatRequest, request: Request):
    try:
        return request.app.state.agent.handle_chat(request_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/metrics/query")
def metrics_query(request_body: MetricsQueryRequest, request: Request):
    try:
        return request.app.state.agent.execute_query(request_body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/metrics/explain")
def metrics_explain(request_body: ExplainRequest, request: Request):
    return request.app.state.agent.explain(request_body)


@router.post("/metrics/attribution")
def metrics_attribution(request_body: AttributionRequest, request: Request):
    return request.app.state.agent.attribution(request_body)


@router.post("/metrics/trend")
def metrics_trend(request_body: TrendRequest, request: Request):
    return request.app.state.agent.trend(request_body)


@router.post("/metrics/ranking")
def metrics_ranking(request_body: RankingRequest, request: Request):
    return request.app.state.agent.ranking(request_body)
