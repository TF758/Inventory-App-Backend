import logging
import os
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
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",

        # Added by our logging filter / formatter
        "request_id",
        "service_name",
    }

    def format(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"

        if not hasattr(record, "service_name"):
            record.service_name = os.getenv("SERVICE_NAME", "app")

        message = super().format(record)

        extra = {
            key: str(value) if isinstance(value, uuid.UUID) else value
            for key, value in record.__dict__.items()
            if key not in self.STANDARD_ATTRS
        }

        if extra:
            if record.exc_info:
                parts = message.split("\n", 1)

                if len(parts) == 2:
                    return f"{parts[0]} | extra={extra}\n{parts[1]}"

                return f"{message} | extra={extra}"

            return f"{message} | extra={extra}"

        return message


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or "-"
        record.service_name = os.getenv("SERVICE_NAME", "app")
        return True