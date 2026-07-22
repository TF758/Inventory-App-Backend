from .prod import *

# Staging is production-like:
# - DEBUG remains False
# - production authentication boundaries remain enforced
# - values differ through .env.staging

APP_ENV = "staging"

# Staff-only API documentation can remain available in staging for
# release verification. It is disabled by default in production.
API_DOCS_ENABLED = env.bool(
    "API_DOCS_ENABLED",
    default=True,
)
API_DOCS_PUBLIC = False

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
