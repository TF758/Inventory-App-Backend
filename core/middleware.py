# core/middleware.py
import uuid
from core.request_context import set_request_id, clear_request_id

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