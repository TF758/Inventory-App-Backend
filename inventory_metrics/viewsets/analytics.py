from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import json

from inventory_metrics.utils.analytics_helpers import parse_range_to_days
from inventory_metrics.utils.system_overview_helpers import build_asset_trends, build_security_trends, build_session_trends, build_system_kpis, build_user_trends, get_system_overview
from inventory_metrics.redis import redis_reports_client


class SystemOverviewAnalytics(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        range_param = request.GET.get("range", "30d")
        days = parse_range_to_days(range_param)

        granularity = request.GET.get("granularity", "daily")

        raw_sections = request.GET.get("sections", "")
        sections = [s for s in raw_sections.split(",") if s]

        cache_key = f"analytics:system:overview:{days}:{granularity}:{','.join(sections)}"

        cached = redis_reports_client.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        overview = get_system_overview(
            days=days,
            granularity=granularity,
            sections=sections,
        )

        payload = {
            "meta": {
                "range": range_param,
                "days": days,
                "granularity": granularity,
                "sections": sections,
                "generated_at": timezone.now().isoformat(),
            },
            "data": overview,
        }

        redis_reports_client.setex(
            cache_key,
            600,
            json.dumps(payload, default=str),
        )

        return Response(payload)