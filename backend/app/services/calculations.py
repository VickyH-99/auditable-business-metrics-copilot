from __future__ import annotations

import math
from statistics import mean, pstdev


def safe_change(current_value: float | int | None, previous_value: float | int | None) -> float | None:
    if current_value is None or previous_value in (None, 0):
        return None
    return (float(current_value) - float(previous_value)) / float(previous_value)


def round_metric(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    if abs(value - round(value)) < 1e-9:
        return int(round(value))
    return round(float(value), 2)


def compute_z_score(current_value: float | int | None, history: list[float]) -> dict | None:
    clean_history = [float(item) for item in history if item is not None]
    if current_value is None or len(clean_history) < 5:
        return None
    baseline = mean(clean_history)
    deviation = pstdev(clean_history)
    if deviation == 0:
        return {
            "baseline": round(baseline, 2),
            "z_score": 0.0,
            "is_anomaly": False,
        }
    z_score = (float(current_value) - baseline) / deviation
    return {
        "baseline": round(baseline, 2),
        "z_score": round(z_score, 3),
        "is_anomaly": math.fabs(z_score) >= 2,
    }

