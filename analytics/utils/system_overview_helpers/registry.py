from analytics.utils.utils.cache import (
    AUTH_METRICS,
    RETURN_METRICS,
    SYSTEM_METRICS,
)

from .assets import build_asset_trends, build_user_trends
from .returns import (
    build_return_flow_trends,
    build_return_performance_trends,
    build_return_state_trends,
)
from .security import build_security_trends, build_session_trends
from .valuation import build_asset_value_trends


SECTION_BUILDERS = {
    "users": build_user_trends,
    "sessions": build_session_trends,
    "security": build_security_trends,
    "assets": build_asset_trends,
    "return_flow": build_return_flow_trends,
    "return_state": build_return_state_trends,
    "return_performance": build_return_performance_trends,
    "asset_value": build_asset_value_trends,
}

# A section is invalidated only when the snapshot dataset it reads changes.
SECTION_DEPENDENCIES = {
    "users": (SYSTEM_METRICS,),
    "sessions": (SYSTEM_METRICS,),
    "security": (AUTH_METRICS,),
    "assets": (SYSTEM_METRICS,),
    "return_flow": (RETURN_METRICS,),
    "return_state": (RETURN_METRICS,),
    "return_performance": (RETURN_METRICS,),
    "asset_value": (SYSTEM_METRICS,),
}
