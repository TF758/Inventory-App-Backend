"""Shared dashboard behavior."""

from __future__ import annotations


class PeriodDashboardMixin:
    """Parse and clamp the dashboard ``period`` query parameter."""

    DEFAULT_PERIOD_DAYS = 7
    MIN_PERIOD_DAYS = 1
    MAX_PERIOD_DAYS = 30

    def get_rooms(self, public_id):
        """Return rooms in scope; concrete views must implement this method."""
        raise NotImplementedError

    def get_period(self, request):
        raw_period = request.query_params.get(
            "period",
            self.DEFAULT_PERIOD_DAYS,
        )

        try:
            period = int(raw_period)
        except (TypeError, ValueError):
            period = self.DEFAULT_PERIOD_DAYS

        return max(
            self.MIN_PERIOD_DAYS,
            min(period, self.MAX_PERIOD_DAYS),
        )
