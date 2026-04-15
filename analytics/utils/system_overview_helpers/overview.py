




from analytics.utils.system_overview_helpers.kpis import build_system_kpis
from analytics.utils.utils.cache import get_cached_section


def get_system_overview(*, days: int, granularity: str, sections: list[str]):
    charts = {}

    for section in sections:
        data = get_cached_section(
            section=section,
            days=days,
            granularity=granularity,
        )
        if data is not None:
            charts[section] = data

    return {
        "kpis": build_system_kpis(),
        "charts": charts,
    }