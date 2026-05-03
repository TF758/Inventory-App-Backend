# core/request_context.py
import threading

_request_local = threading.local()

def set_request_id(request_id: str):
    _request_local.request_id = request_id

def get_request_id():
    return getattr(_request_local, "request_id", None)

def clear_request_id():
    if hasattr(_request_local, "request_id"):
        del _request_local.request_id