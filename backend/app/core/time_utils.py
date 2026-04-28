from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class TimeRange:
    mode: str
    start_date: date
    end_date: date
    label: str

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "label": self.label,
        }


def add_months(target: date, months: int) -> date:
    month_index = target.month - 1 + months
    year = target.year + month_index // 12
    month = month_index % 12 + 1
    day = min(target.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_years(target: date, years: int) -> date:
    try:
        return target.replace(year=target.year + years)
    except ValueError:
        return target.replace(month=2, day=28, year=target.year + years)


def rolling_days_range(anchor: date, days: int) -> TimeRange:
    return TimeRange(
        mode=f"last_{days}_days",
        start_date=anchor - timedelta(days=days - 1),
        end_date=anchor,
        label=f"最近{days}天",
    )


def month_to_date_range(anchor: date) -> TimeRange:
    return TimeRange(
        mode="mtd",
        start_date=anchor.replace(day=1),
        end_date=anchor,
        label="本月累计",
    )


def resolve_time_range(mode: str | None, today: date) -> TimeRange:
    normalized = mode or "today"
    if normalized == "today":
        return TimeRange("today", today, today, "今天")
    if normalized == "yesterday":
        day = today - timedelta(days=1)
        return TimeRange("yesterday", day, day, "昨天")
    if normalized == "last_7_days":
        return rolling_days_range(today, 7)
    if normalized == "last_30_days":
        return rolling_days_range(today, 30)
    if normalized == "mtd":
        return month_to_date_range(today)
    raise ValueError(f"Unsupported time range mode: {mode}")


def shift_range_by_days(time_range: TimeRange, days: int, mode: str) -> TimeRange:
    return TimeRange(
        mode=mode,
        start_date=time_range.start_date + timedelta(days=days),
        end_date=time_range.end_date + timedelta(days=days),
        label=time_range.label,
    )


def shift_range_by_months(time_range: TimeRange, months: int, mode: str) -> TimeRange:
    if time_range.mode == "mtd":
        shifted_end = add_months(time_range.end_date, months)
        return TimeRange(
            mode=mode,
            start_date=shifted_end.replace(day=1),
            end_date=shifted_end,
            label=time_range.label,
        )

    return TimeRange(
        mode=mode,
        start_date=add_months(time_range.start_date, months),
        end_date=add_months(time_range.end_date, months),
        label=time_range.label,
    )


def shift_range_by_years(time_range: TimeRange, years: int, mode: str) -> TimeRange:
    return TimeRange(
        mode=mode,
        start_date=add_years(time_range.start_date, years),
        end_date=add_years(time_range.end_date, years),
        label=time_range.label,
    )

