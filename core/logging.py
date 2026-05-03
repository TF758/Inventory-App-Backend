import logging


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
        'message', 'asctime'
    }

    def format(self, record):
        message = super().format(record)

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.STANDARD_ATTRS
        }

        if extra:
            return f"{message} | extra={extra}"

        return message