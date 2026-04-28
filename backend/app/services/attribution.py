from __future__ import annotations

from typing import Any

from app.services.calculations import round_metric

NEGATIVE_DRIVER = "negative_driver"
POSITIVE_OFFSET = "positive_offset"
NEUTRAL = "neutral"


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if abs(denominator) < 1e-12:
        return None
    return round(numerator / denominator, 4)


def calculate_attribution_contributions(
    rows: list[dict[str, Any]],
    current_total: float | int | None,
    compare_total: float | int | None,
) -> dict[str, Any]:
    current_total_value = _to_number(current_total)
    compare_total_value = _to_number(compare_total)
    total_delta = current_total_value - compare_total_value

    negative_total_delta = 0.0
    positive_total_delta = 0.0
    for row in rows:
        delta = _to_number(row.get("delta"))
        if delta < 0:
            negative_total_delta += abs(delta)
        elif delta > 0:
            positive_total_delta += delta

    all_rows: list[dict[str, Any]] = []
    for row in rows:
        current_value = _to_number(row.get("current_value"))
        compare_value = _to_number(row.get("compare_value"))
        delta = _to_number(row.get("delta", current_value - compare_value))
        absolute_delta = abs(delta)

        negative_contribution_pct: float | None = None
        positive_offset_pct: float | None = None
        if delta < 0:
            direction = NEGATIVE_DRIVER
            negative_contribution_pct = _safe_ratio(absolute_delta, negative_total_delta)
        elif delta > 0:
            direction = POSITIVE_OFFSET
            positive_offset_pct = _safe_ratio(delta, positive_total_delta)
        else:
            direction = NEUTRAL

        all_rows.append(
            {
                **row,
                "current_value": round_metric(current_value),
                "compare_value": round_metric(compare_value),
                "delta": round_metric(delta),
                "absolute_delta": round_metric(absolute_delta),
                "negative_contribution_pct": negative_contribution_pct,
                "positive_offset_pct": positive_offset_pct,
                "net_contribution_pct": _safe_ratio(delta, total_delta),
                "direction": direction,
            }
        )

    negative_drivers = sorted(
        (row for row in all_rows if row["direction"] == NEGATIVE_DRIVER),
        key=lambda item: float(item["absolute_delta"] or 0),
        reverse=True,
    )
    positive_offsets = sorted(
        (row for row in all_rows if row["direction"] == POSITIVE_OFFSET),
        key=lambda item: float(item["absolute_delta"] or 0),
        reverse=True,
    )
    neutral_items = sorted(
        (row for row in all_rows if row["direction"] == NEUTRAL),
        key=lambda item: (item["dimension_label"], item["member"]),
    )
    ordered_rows = sorted(
        all_rows,
        key=lambda item: (
            -float(item["absolute_delta"] or 0),
            item["dimension_label"],
            str(item["member"]),
        ),
    )

    return {
        "current_total": round_metric(current_total_value),
        "compare_total": round_metric(compare_total_value),
        "total_delta": round_metric(total_delta),
        "drivers": positive_offsets[:5],
        "offsets": negative_drivers[:5],
        "dimension_impact": ordered_rows,
        "negative_drivers": negative_drivers[:5],
        "positive_offsets": positive_offsets[:5],
        "neutral_items": neutral_items,
        "all_rows": ordered_rows,
    }
