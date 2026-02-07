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