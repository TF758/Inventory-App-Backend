from typing import Optional
from datetime import date
from django.db.models.functions import (TruncDate, TruncWeek, TruncMonth)

def percentage_delta(current: int, previous: Optional[int]) -> Optional[float]:
    if previous in (None, 0):
        return None
    return round(((current - previous) / previous) * 100, 2)


def timeseries_point(d: date, **values):
    return {
        "date": d.isoformat(),
        **values,
    }

def truncate_date(field, granularity):
    if granularity == "daily":
        return TruncDate(field)
    if granularity == "weekly":
        return TruncWeek(field)
    if granularity == "monthly":
        return TruncMonth(field)
    raise ValueError("Invalid granularity")


RANGE_TO_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
}

def parse_range_to_days(range_param: str) -> int:
    try:
        return RANGE_TO_DAYS[range_param]
    except KeyError:
        raise ValueError(f"Invalid range parameter: {range_param}")