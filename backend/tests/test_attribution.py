from __future__ import annotations

import pytest

from app.services.attribution import calculate_attribution_contributions


def test_calculate_attribution_contributions_for_overall_drop():
    payload = calculate_attribution_contributions(
        rows=[
            {"dimension": "city", "dimension_label": "城市", "member": "深圳", "current_value": 20, "compare_value": 30, "delta": -10},
            {"dimension": "city", "dimension_label": "城市", "member": "广州", "current_value": 15, "compare_value": 20, "delta": -5},
            {"dimension": "city", "dimension_label": "城市", "member": "杭州", "current_value": 10, "compare_value": 15, "delta": -5},
            {"dimension": "city", "dimension_label": "城市", "member": "北京", "current_value": 13, "compare_value": 10, "delta": 3},
            {"dimension": "city", "dimension_label": "城市", "member": "上海", "current_value": 12, "compare_value": 10, "delta": 2},
        ],
        current_total=80,
        compare_total=100,
    )

    assert payload["total_delta"] == -20
    assert len(payload["negative_drivers"]) == 3
    assert len(payload["positive_offsets"]) == 2
    assert sum(row["negative_contribution_pct"] or 0 for row in payload["negative_drivers"]) == pytest.approx(1.0)
    assert sum(row["positive_offset_pct"] or 0 for row in payload["positive_offsets"]) == pytest.approx(1.0)


def test_calculate_attribution_contributions_for_overall_growth():
    payload = calculate_attribution_contributions(
        rows=[
            {"dimension": "channel", "dimension_label": "渠道", "member": "线上直营", "current_value": 18, "compare_value": 10, "delta": 8},
            {"dimension": "channel", "dimension_label": "渠道", "member": "经销商合作", "current_value": 14, "compare_value": 10, "delta": 4},
            {"dimension": "channel", "dimension_label": "渠道", "member": "门店自然到访", "current_value": 9, "compare_value": 12, "delta": -3},
        ],
        current_total=120,
        compare_total=111,
    )

    assert payload["total_delta"] == 9
    assert [row["direction"] for row in payload["positive_offsets"]] == ["positive_offset", "positive_offset"]
    assert [row["direction"] for row in payload["negative_drivers"]] == ["negative_driver"]
    assert payload["positive_offsets"][0]["positive_offset_pct"] == pytest.approx(8 / 12, rel=1e-3)
    assert payload["negative_drivers"][0]["negative_contribution_pct"] == pytest.approx(1.0)


def test_calculate_attribution_contributions_handles_zero_denominators():
    payload = calculate_attribution_contributions(
        rows=[
            {"dimension": "city", "dimension_label": "城市", "member": "深圳", "current_value": 10, "compare_value": 10, "delta": 0},
            {"dimension": "city", "dimension_label": "城市", "member": "北京", "current_value": 10, "compare_value": 10, "delta": 0},
        ],
        current_total=20,
        compare_total=20,
    )

    assert payload["total_delta"] == 0
    assert all(row["net_contribution_pct"] is None for row in payload["all_rows"])
    assert all(row["negative_contribution_pct"] is None for row in payload["all_rows"])
    assert all(row["positive_offset_pct"] is None for row in payload["all_rows"])


def test_calculate_attribution_contributions_marks_all_zero_rows_neutral():
    payload = calculate_attribution_contributions(
        rows=[
            {"dimension": "region_group", "dimension_label": "大区", "member": "华南大区", "current_value": 5, "compare_value": 5, "delta": 0},
            {"dimension": "region_group", "dimension_label": "大区", "member": "华东大区", "current_value": 8, "compare_value": 8, "delta": 0},
        ],
        current_total=13,
        compare_total=13,
    )

    assert payload["negative_drivers"] == []
    assert payload["positive_offsets"] == []
    assert all(row["direction"] == "neutral" for row in payload["neutral_items"])
