from .prod import *

# Staging is production-like:
# - DEBUG remains False
# - production settings are used
# - values differ through .env.staging

APP_ENV = "staging"

# Safer default for staging unless explicitly enabled.
SECURE_HSTS_SECONDS = env.int(
    "SECURE_HSTS_SECONDS",
    default=0,
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)

SECURE_HSTS_PRELOAD = env.bool(
    "SECURE_HSTS_PRELOAD",
    default=False,
)