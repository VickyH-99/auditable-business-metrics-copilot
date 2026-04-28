from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data_source"] in {"mock_database", "fallback_mock"}


def test_chat_clarification(client):
    response = client.post(
        "/api/chat",
        json={"session_id": "session-a", "message": "最近7天趋势如何？"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "clarification"
    assert "指标" in payload["message"]


def test_chat_answer(client):
    response = client.post(
        "/api/chat",
        json={"session_id": "session-b", "message": "今天卖车同比多少？"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "answer"
    assert payload["metric"] == "car_sales_count"
    assert "sql_used" in payload
    assert "metric_definition" in payload


def test_chat_attribution_answer(client):
    response = client.post(
        "/api/chat",
        json={"session_id": "session-d", "message": "为什么今天卖车下降？"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "answer"
    assert payload["query_plan"]["intent"] == "attribution"
    assert payload["attribution"]["drivers"] is not None
    assert payload["attribution"]["offsets"] is not None
    assert payload["attribution"]["dimension_impact"] is not None
    assert payload["attribution"]["negative_drivers"] is not None
    assert payload["attribution"]["positive_offsets"] is not None
    assert payload["attribution"]["drivers"] == payload["attribution"]["positive_offsets"]
    assert payload["attribution"]["offsets"] == payload["attribution"]["negative_drivers"]
    assert payload["attribution"]["dimension_impact"] == payload["attribution"]["all_rows"]


def test_chat_multi_turn_clarification(client):
    first = client.post(
        "/api/chat",
        json={"session_id": "session-c", "message": "最近7天趋势如何？"},
    )
    assert first.status_code == 200
    assert first.json()["type"] == "clarification"

    second = client.post(
        "/api/chat",
        json={"session_id": "session-c", "message": "卖车销量"},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["type"] == "answer"
    assert payload["metric"] == "car_sales_count"
    assert payload["query_plan"]["time_range"]["mode"] == "last_7_days"
