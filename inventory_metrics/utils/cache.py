# analytics/services/cache.py

import json
from core.redis import redis_reports_client
from analytics.utils.system_overview_helpers.registry import SECTION_BUILDERS

def get_cached_section(*, section: str, days: int, granularity: str):
    cache_key = f"analytics:system:section:{section}:{days}:{granularity}"

    cached = redis_reports_client.get(cache_key)
    if cached:
        return json.loads(cached)


    builder = SECTION_BUILDERS.get(section)
    if not builder:
        return None

    data = builder(days=days, granularity=granularity)

    redis_reports_client.setex(
        cache_key,
        600,
        json.dumps(data, default=str),
    )

    return data