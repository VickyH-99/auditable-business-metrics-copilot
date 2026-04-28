from __future__ import annotations

from datetime import date

from app.core.time_utils import resolve_time_range
from app.services.calculations import round_metric, safe_change


def test_yoy_calculation():
    assert round(safe_change(120, 100), 3) == 0.2


def test_mom_calculation():
    assert round(safe_change(90, 120), 3) == -0.25


def test_mtd_range():
    result = resolve_time_range("mtd", date(2026, 4, 27))
    assert result.start_date.isoformat() == "2026-04-01"
    assert result.end_date.isoformat() == "2026-04-27"
    assert round_metric(12.0) == 12

