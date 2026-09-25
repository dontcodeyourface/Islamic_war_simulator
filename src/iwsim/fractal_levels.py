from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

FRACTAL_LEVEL_ORDER = (
    "L0_SYSTEM",
    "L1_COUNTRY",
    "L2_REGION",
    "L3_METRO_OR_LOGISTICS_AREA",
    "L4_ACTOR_NETWORK",
    "L5_EVENT_CLUSTER",
)


def level_index(level: str) -> int:
    logger.info("level_index level=%s", level)
    try:
        return FRACTAL_LEVEL_ORDER.index(str(level))
    except ValueError as exc:
        raise ValueError(f"Unknown fractal level: {level}") from exc


def validate_adjacent_expansion(
    *,
    from_level: str,
    to_level: str,
    materialization_config: dict[str, Any],
) -> None:
    logger.info(
        "validate_adjacent_expansion from=%s to=%s",
        from_level,
        to_level,
    )
    recursive = materialization_config.get("recursive")
    if not isinstance(recursive, dict):
        raise ValueError("Fractal materialization requires recursive policy")
    if recursive.get("enabled") is not True:
        raise ValueError("Recursive fractal materialization is disabled")
    if recursive.get("adjacent_levels_only") is not True:
        raise ValueError("Recursive fractal materialization must be adjacent-only")

    if level_index(to_level) != level_index(from_level) + 1:
        raise ValueError(
            f"Fractal materialization requires adjacent expansion: "
            f"{from_level} -> {to_level}"
        )

    allowed = recursive.get("allowed_expansions")
    if not isinstance(allowed, dict):
        raise ValueError("Recursive fractal allowed_expansions must be a mapping")
    configured = allowed.get(from_level)
    if configured != to_level:
        raise ValueError(
            f"Fractal expansion {from_level} -> {to_level} is not enabled"
        )


def validate_topology_level(level: str) -> None:
    logger.info("validate_topology_level level=%s", level)
    index = level_index(level)
    if index < level_index("L2_REGION"):
        raise ValueError(
            f"Materialized fractal topology node cannot use level {level}"
        )
