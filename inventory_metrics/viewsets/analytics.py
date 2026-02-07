from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import json

from inventory_metrics.utils.system_overview_helpers import build_asset_trends, build_security_trends, build_session_trends, build_system_kpis, build_user_trends, get_system_overview
from inventory_metrics.redis import redis_reports_client


class SystemOverviewAnalytics(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # -----------------------------
        # Query params (with defaults)
        # -----------------------------
        range_param = request.GET.get("range", "30d")
        granularity = request.GET.get("granularity", "daily")
        sections = request.GET.getlist(
            "sections",
            ["kpis", "users", "sessions", "security", "assets"],
        )

        try:
            days = int(range_param.replace("d", ""))
        except ValueError:
            return Response(
                {"detail": "Invalid range. Use values like 7d, 30d, 90d, 365d."},
                status=400,
            )

        if granularity not in {"daily", "weekly", "monthly"}:
            return Response(
                {"detail": "Invalid granularity. Use daily, weekly, or monthly."},
                status=400,
            )

        # -----------------------------
        # Cache key (fully qualified)
        # -----------------------------
        sections_key = ",".join(sorted(sections))
        cache_key = (
            f"analytics:system:overview:"
            f"{days}:{granularity}:{sections_key}"
        )

        cached = redis_reports_client.get(cache_key)
        if cached:
            return Response(json.loads(cached))

        # -----------------------------
        # Build payload
        # -----------------------------
        data = {}

        if "kpis" in sections:
            data["kpis"] = build_system_kpis()

        if "users" in sections:
            data["users"] = build_user_trends(
                days=days,
                granularity=granularity,
            )

        if "sessions" in sections:
            data["sessions"] = build_session_trends(
                days=days,
                granularity=granularity,
            )

        if "security" in sections:
            data["security"] = build_security_trends(
                days=days,
                granularity=granularity,
            )

        if "assets" in sections:
            data["assets"] = build_asset_trends(
                days=days,
                granularity=granularity,
            )

        payload = {
            "meta": {
                "range": range_param,
                "days": days,
                "granularity": granularity,
                "sections": sections,
                "generated_at": timezone.now().isoformat(),
            },
            "data": data,
        }

        # -----------------------------
        # Cache response
        # -----------------------------
        redis_reports_client.setex(
            cache_key,
            600,  # 10 minutes
            json.dumps(payload, default=str),
        )

        return Response(payload)