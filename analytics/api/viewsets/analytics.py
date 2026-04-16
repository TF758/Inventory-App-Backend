from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import json
from django.db.models import Q
from django.shortcuts import get_object_or_404


from analytics.utils.analytics_helpers import parse_range_to_days
from analytics.utils.department_analytic_helpers import get_department_overview
from analytics.utils.system_overview_helpers.overview import get_system_overview
from core.redis import redis_reports_client
from inventory.sites.models.sites import Department


class SystemOverviewAnalytics(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        range_param = request.GET.get("range", "30d")
        days = parse_range_to_days(range_param)

        granularity = request.GET.get("granularity", "daily")

        raw_sections = request.GET.get("sections", "")
        sections = [s for s in raw_sections.split(",") if s]

        sections = sorted(set(sections))

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

        return Response(payload)

class DepartmentOverviewAnalytics(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, department_id):
        range_param = request.GET.get("range", "30d")
        days = parse_range_to_days(range_param)
        granularity = request.GET.get("granularity", "daily")

        raw_sections = request.GET.get("sections", "")
        sections = [s for s in raw_sections.split(",") if s]

        department = get_object_or_404(
            Department,
            public_id=department_id,
        )

        cache_key = (
            f"analytics:department:overview:"
            f"{department.id}:{days}:{granularity}:{','.join(sections)}"
        )

        cached = redis_reports_client.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        overview = get_department_overview(
            department=department,
            days=days,
            granularity=granularity,
            sections=sections,
        )

        payload = {
            "meta": {
                "department": {
                    "id": department.public_id,
                    "name": department.name,
                },
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