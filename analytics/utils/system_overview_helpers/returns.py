from django.db.models import Max, OuterRef, Subquery, Avg, Sum

from analytics.models.metrics import DailyReturnMetrics
from analytics.utils.analytics_helpers import truncate_date
from analytics.utils.utils.viewset_helpers import get_snapshot_range_start



def build_return_flow_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailyReturnMetrics,
        days=days,
    )

    if not start:
        return []

    qs = (
        DailyReturnMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
        .values("period")
        .annotate(
            requests_created=Sum("requests_created_last_24h"),
            requests_processed=Sum("requests_processed_last_24h"),
        )
        .order_by("period")
    )

    return [
        {
            "date": row["period"].isoformat(),
            "requests_created": row["requests_created"],
            "requests_processed": row["requests_processed"],
        }
        for row in qs
    ]

def build_return_state_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailyReturnMetrics,
        days=days,
    )

    if not start:
        return []

    base = (
        DailyReturnMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
    )

    latest_per_period = (
        base
        .values("period")
        .annotate(latest_date=Max("date"))
    )

    qs = (
        base
        .filter(
            date=Subquery(
                latest_per_period
                .filter(period=OuterRef("period"))
                .values("latest_date")[:1]
            )
        )
        .order_by("period")
    )

    return [
        {
            "date": row.period.isoformat(),
            "pending_requests": row.pending_requests,
            "approved_requests": row.approved_requests,
            "denied_requests": row.denied_requests,
            "partial_requests": row.partial_requests,
        }
        for row in qs
    ]
def build_return_performance_trends(*, days: int, granularity: str):
    start = get_snapshot_range_start(
        model=DailyReturnMetrics,
        days=days,
    )

    if not start:
        return []

    qs = (
        DailyReturnMetrics.objects
        .filter(date__gte=start)
        .annotate(period=truncate_date("date", granularity))
        .values("period")
        .annotate(
            avg_processing_time=Avg("avg_processing_time_seconds"),
            max_processing_time=Max("max_processing_time_seconds"),
        )
        .order_by("period")
    )

    return [
        {
            "date": row["period"].isoformat(),
            "avg_processing_time_seconds": int(row["avg_processing_time"] or 0),
            "max_processing_time_seconds": int(row["max_processing_time"] or 0),
        }
        for row in qs
    ]