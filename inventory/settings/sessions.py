# inventory/settings/sessions.py

from datetime import timedelta

from .base import env

# -------------------------------------------------
# Session lifetime configuration
# -------------------------------------------------

SESSION_IDLE_MINUTES = env.int(
    "SESSION_IDLE_MINUTES",
    default=30,
)

SESSION_ABSOLUTE_HOURS = env.int(
    "SESSION_ABSOLUTE_HOURS",
    default=12,
)

SESSION_IDLE_TIMEOUT = timedelta(
    minutes=SESSION_IDLE_MINUTES,
)

SESSION_ABSOLUTE_LIFETIME = timedelta(
    hours=SESSION_ABSOLUTE_HOURS,
)

# -------------------------------------------------
# Session record retention
# -------------------------------------------------

SESSION_EXPIRED_RETENTION_DAYS = env.int(
    "SESSION_EXPIRED_RETENTION_DAYS",
    default=5,
)

SESSION_REVOKED_RETENTION_DAYS = env.int(
    "SESSION_REVOKED_RETENTION_DAYS",
    default=20,
)