from enum import Enum
from typing import Any, Final, Mapping

from ragdoll.core.config import get_settings


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    INTERNAL = "internal"


FeatureFlags = dict[str, bool]

FLAG_UNIFIED_SEARCH: Final[str] = "unified_search"
FLAG_SEARCH_GRAPH_MODE: Final[str] = "search_graph_mode"
FLAG_SEARCH_CHAT_IN_COMBINED: Final[str] = "search_chat_in_combined"
FLAG_KNOWLEDGE_GRAPH_VISUALIZER: Final[str] = "knowledge_graph_visualizer"
FLAG_DOCUMENT_VERSION_HISTORY: Final[str] = "document_version_history"

ALL_FEATURE_FLAG_KEYS: Final[tuple[str, ...]] = (
    FLAG_UNIFIED_SEARCH,
    FLAG_SEARCH_GRAPH_MODE,
    FLAG_SEARCH_CHAT_IN_COMBINED,
    FLAG_KNOWLEDGE_GRAPH_VISUALIZER,
    FLAG_DOCUMENT_VERSION_HISTORY,
)


def _flags_for_plan_tier(plan_tier: str) -> FeatureFlags:
    if plan_tier == PlanTier.INTERNAL.value:
        return {key: True for key in ALL_FEATURE_FLAG_KEYS}
    if plan_tier == PlanTier.PRO.value:
        return {
            FLAG_UNIFIED_SEARCH: True,
            FLAG_SEARCH_GRAPH_MODE: True,
            FLAG_SEARCH_CHAT_IN_COMBINED: True,
            FLAG_KNOWLEDGE_GRAPH_VISUALIZER: True,
            FLAG_DOCUMENT_VERSION_HISTORY: False,
        }
    return {
        FLAG_UNIFIED_SEARCH: True,
        FLAG_SEARCH_GRAPH_MODE: False,
        FLAG_SEARCH_CHAT_IN_COMBINED: False,
        FLAG_KNOWLEDGE_GRAPH_VISUALIZER: False,
        FLAG_DOCUMENT_VERSION_HISTORY: False,
    }


def resolve_feature_flags(
    plan_tier: PlanTier | str = PlanTier.FREE,
    overrides: Mapping[str, Any] | None = None,
    *,
    global_unified_search_enabled: bool | None = None,
) -> FeatureFlags:
    tier_value = plan_tier.value if isinstance(plan_tier, PlanTier) else str(plan_tier).strip().lower()

    if tier_value not in {PlanTier.FREE.value, PlanTier.PRO.value, PlanTier.INTERNAL.value}:
        tier_value = PlanTier.FREE.value

    flags = _flags_for_plan_tier(tier_value)

    if overrides:
        for key, value in overrides.items():
            if key in flags and isinstance(value, bool):
                flags[key] = value

    settings = get_settings()
    unified_search_enabled = (
        settings.feature_flag_unified_search
        if global_unified_search_enabled is None
        else global_unified_search_enabled
    )
    if not unified_search_enabled:
        flags[FLAG_UNIFIED_SEARCH] = False

    return flags
