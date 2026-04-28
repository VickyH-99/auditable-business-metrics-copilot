from __future__ import annotations

from app.core.time_utils import resolve_time_range
from app.schemas.api import QueryPlan, TimeRangeModel


def test_metric_catalog_and_query_execution(client):
    catalog_response = client.get("/api/metrics/catalog")
    assert catalog_response.status_code == 200
    metrics = catalog_response.json()["metrics"]
    assert any(metric["metric_id"] == "sales_amount" for metric in metrics)


def test_structured_query(client):
    plan = QueryPlan(
        intent="ranking",
        metric="car_sales_count",
        time_range=TimeRangeModel.model_validate(resolve_time_range("today", client.app.state.metric_service.settings.today).to_dict()),
        dimensions=["city"],
        filters={},
        limit=5,
    )
    response = client.post(
        "/api/metrics/query",
        json={"query_plan": plan.model_dump(mode="json"), "message": "今天各城市卖车排名"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "answer"
    assert payload["table_data"]
    assert payload["query_plan"]["dimensions"] == ["city"]


def test_attribution_endpoint(client):
    response = client.post(
        "/api/metrics/attribution",
        json={"metric_id": "car_sales_count", "compare_with": "yesterday", "filters": {}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "answer"
    assert payload["metric"] == "car_sales_count"
    assert payload["table_data"]
    assert payload["attribution"]["all_rows"]
    assert "negative_drivers" in payload["attribution"]
    assert "positive_offsets" in payload["attribution"]
    assert payload["table_data"] == payload["attribution"]["all_rows"]
