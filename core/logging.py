import logging
import uuid
from core.request_context import get_request_id


def get_logger(name: str) -> logging.Logger:
    """
    Return an application-scoped operational logger.

    Example:
        logger = get_logger("data_import")
        logger.info("import_started", extra={"job_id": job.public_id})
    """
    return logging.getLogger(f"arms.{name}")


class SafeExtraFormatter(logging.Formatter):
    STANDARD_ATTRS = {
        'name', 'msg', 'args', 'levelname', 'levelno',
        'pathname', 'filename', 'module', 'exc_info',
        'exc_text', 'stack_info', 'lineno', 'funcName',
        'created', 'msecs', 'relativeCreated', 'thread',
        'threadName', 'processName', 'process',
        'message', 'asctime', 'taskName'
    }

    def format(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = None

        message = super().format(record)

        extra = {
            key: str(value) if isinstance(value, uuid.UUID) else value
            for key, value in record.__dict__.items()
            if key not in self.STANDARD_ATTRS
            and key != "request_id"
        }

        if extra:
            if record.exc_info:
                parts = message.split("\n", 1)
                return f"{parts[0]} | extra={extra}\n{parts[1]}"
            else:
                return f"{message} | extra={extra}"

        return message
    

class RequestIDFilter:
    def filter(self, record):
        record.request_id = get_request_id()
        return True