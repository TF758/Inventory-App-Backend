import secrets
import uuid

from django.conf import settings
from django.http import HttpResponseNotFound

from core.request_context import clear_request_id, set_request_id


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # REQ + 10 hex digits
        request_id = f"DBG-{uuid.uuid4().hex[:10]}"

        request.request_id = request_id
        set_request_id(request_id)

        try:
            response = self.get_response(request)
        finally:
            clear_request_id()

        return response


class OperationalEndpointSecurityMiddleware:
    """Require an explicit bearer token for Prometheus metrics."""

    metrics_paths = {"/metrics", "/metrics/"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in self.metrics_paths and not self._metrics_allowed(
            request
        ):
            # Hide the endpoint instead of advertising an auth boundary.
            return HttpResponseNotFound()

        return self.get_response(request)

    @staticmethod
    def _metrics_allowed(request) -> bool:
        if settings.METRICS_ALLOW_PUBLIC:
            return True

        expected_token = settings.METRICS_BEARER_TOKEN.strip()
        if not expected_token:
            return False

        authorization = request.headers.get("Authorization", "")
        scheme, separator, supplied_token = authorization.partition(" ")

        if separator != " " or scheme.lower() != "bearer":
            return False

        supplied_token = supplied_token.strip()
        if not supplied_token:
            return False

        return secrets.compare_digest(supplied_token, expected_token)
