# registry.py


from .security import build_security_trends, build_session_trends
from .assets import build_asset_trends, build_user_trends
from .returns import (
    build_return_flow_trends,
    build_return_state_trends,
    build_return_performance_trends,
)

SECTION_BUILDERS = {
    "users": build_user_trends,
    "sessions": build_session_trends,
    "security": build_security_trends,
    "assets": build_asset_trends,
    "return_flow": build_return_flow_trends,
    "return_state": build_return_state_trends,
    "return_performance": build_return_performance_trends,
}