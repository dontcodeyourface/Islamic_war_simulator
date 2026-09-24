from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .fractal_materialization import FractalTopologyState

logger = logging.getLogger(__name__)

_GENERATION_SUFFIX_RE = re.compile(r"::g([1-9][0-9]*)$")


@dataclass(frozen=True)
class FractalLineageAllocation:
    catalog_child_id: str
    runtime_node_id: str
    lineage_generation: int
    lineage_policy_id: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalLineageAllocation.to_dict catalog_child=%s runtime=%s gen=%s",
            self.catalog_child_id,
            self.runtime_node_id,
            self.lineage_generation,
        )
        return {
            "catalog_child_id": self.catalog_child_id,
            "runtime_node_id": self.runtime_node_id,
            "lineage_generation": self.lineage_generation,
            "lineage_policy_id": self.lineage_policy_id,
        }


def validate_lifecycle_config(
    materialization_config: dict[str, Any],
) -> dict[str, Any]:
    logger.info("validate_lifecycle_config")
    lifecycle = materialization_config.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise ValueError("Fractal materialization lifecycle must be a mapping")

    policy_id = str(lifecycle.get("policy_id", ""))
    if policy_id != "FRACTAL_TOPOLOGY_GENERATION_V1":
        raise ValueError("Unsupported fractal topology lifecycle policy")

    required_true = (
        "preserve_closed_lineage",
        "never_reactivate_closed_runtime_node",
        "first_generation_uses_catalog_child_id",
        "generation_advances_by_one",
        "current_catalog_child_set_must_match_history",
        "complete_sibling_generation_history_required",
        "reserved_catalog_generation_suffix_forbidden",
    )
    for key in required_true:
        if lifecycle.get(key) is not True:
            raise ValueError(
                f"Fractal lifecycle requires {key}=true"
            )

    generation_starts_at = int(lifecycle.get("generation_starts_at", 0))
    if generation_starts_at != 1:
        raise ValueError("Fractal lifecycle generation must start at 1")

    suffix_template = str(
        lifecycle.get("subsequent_generation_suffix", "")
    )
    if suffix_template != "::g{generation}":
        raise ValueError(
            "Fractal lifecycle suffix must remain ::g{generation}"
        )

    return {
        "policy_id": policy_id,
        "generation_starts_at": generation_starts_at,
        "suffix_template": suffix_template,
    }


def _catalog_identity(node: Any) -> str:
    logger.info(
        "_catalog_identity node=%s generation=%s",
        node.node_id,
        node.lineage_generation,
    )
    explicit = getattr(node, "catalog_child_id", None)
    generation = int(getattr(node, "lineage_generation", 1))
    if explicit:
        return str(explicit)
    if generation != 1:
        raise ValueError(
            f"Topology node {node.node_id} generation {generation} "
            "requires explicit catalog_child_id"
        )
    return str(node.node_id)


def _expected_runtime_id(
    *,
    catalog_child_id: str,
    generation: int,
) -> str:
    logger.info(
        "_expected_runtime_id catalog_child=%s generation=%s",
        catalog_child_id,
        generation,
    )
    if generation == 1:
        return catalog_child_id
    return f"{catalog_child_id}::g{generation}"


def _validate_catalog_child_ids(
    *,
    parent_node_id: str,
    catalog_child_ids: tuple[str, ...],
) -> tuple[str, ...]:
    logger.info(
        "_validate_catalog_child_ids parent=%s count=%s",
        parent_node_id,
        len(catalog_child_ids),
    )
    normalized = tuple(sorted(str(item) for item in catalog_child_ids))
    if not normalized:
        raise ValueError("Fractal lifecycle requires catalog children")
    if len(normalized) != len(set(normalized)):
        raise ValueError("Duplicate catalog child IDs in fractal lifecycle")
    for child_id in normalized:
        if not child_id.startswith(f"{parent_node_id}::"):
            raise ValueError(
                f"Catalog child {child_id} is not namespaced by "
                f"{parent_node_id}::"
            )
        if _GENERATION_SUFFIX_RE.search(child_id):
            raise ValueError(
                f"Catalog child {child_id} uses reserved generation suffix"
            )
    return normalized


def allocate_lineage_generation(
    *,
    parent_node_id: str,
    catalog_child_ids: tuple[str, ...],
    topology: "FractalTopologyState",
    materialization_config: dict[str, Any],
) -> tuple[FractalLineageAllocation, ...]:
    """Allocate immutable runtime IDs for the next sibling lineage generation."""
    logger.info(
        "allocate_lineage_generation parent=%s catalog_children=%s "
        "topology_nodes=%s",
        parent_node_id,
        len(catalog_child_ids),
        len(topology.nodes),
    )
    policy = validate_lifecycle_config(materialization_config)
    current_catalog_ids = _validate_catalog_child_ids(
        parent_node_id=parent_node_id,
        catalog_child_ids=catalog_child_ids,
    )

    parent_history = tuple(
        item
        for item in topology.nodes
        if item.parent_node_id == parent_node_id
    )
    if any(item.active for item in parent_history):
        raise ValueError(
            f"Fractal lifecycle parent {parent_node_id} already has "
            "active topology lineage"
        )

    history_by_catalog: dict[str, list[Any]] = {}
    runtime_ids = {str(item.node_id) for item in topology.nodes}
    for node in parent_history:
        catalog_id = _catalog_identity(node)
        if catalog_id not in history_by_catalog:
            history_by_catalog[catalog_id] = []
        history_by_catalog[catalog_id].append(node)

        generation = int(getattr(node, "lineage_generation", 1))
        if generation < 1:
            raise ValueError(
                f"Topology node {node.node_id} has invalid lineage generation"
            )
        expected_runtime = _expected_runtime_id(
            catalog_child_id=catalog_id,
            generation=generation,
        )
        if node.node_id != expected_runtime:
            raise ValueError(
                f"Topology node {node.node_id} runtime ID does not match "
                f"catalog={catalog_id} generation={generation}"
            )
        if node.de_refinement_day is None:
            raise ValueError(
                f"Inactive topology node {node.node_id} requires "
                "de_refinement_day before a new generation"
            )
        lineage_policy_id = getattr(node, "lineage_policy_id", None)
        if generation > 1 and lineage_policy_id != policy["policy_id"]:
            raise ValueError(
                f"Topology node {node.node_id} generation {generation} "
                "has invalid lineage policy ID"
            )
        if (
            generation == 1
            and lineage_policy_id is not None
            and lineage_policy_id != policy["policy_id"]
        ):
            raise ValueError(
                f"Topology node {node.node_id} has incompatible lineage "
                "policy ID"
            )

    historical_catalog_ids = tuple(sorted(history_by_catalog))
    if historical_catalog_ids and historical_catalog_ids != current_catalog_ids:
        raise ValueError(
            "Fractal lifecycle catalog child set changed across generations: "
            f"history={list(historical_catalog_ids)} "
            f"current={list(current_catalog_ids)}"
        )

    generation_sets: dict[str, tuple[int, ...]] = {}
    for catalog_id, nodes in sorted(history_by_catalog.items()):
        generations = tuple(
            sorted(int(getattr(node, "lineage_generation", 1)) for node in nodes)
        )
        if len(generations) != len(set(generations)):
            raise ValueError(
                f"Duplicate lineage generation for catalog child {catalog_id}"
            )
        expected = tuple(range(1, max(generations) + 1))
        if generations != expected:
            raise ValueError(
                f"Non-contiguous lineage history for {catalog_id}: "
                f"{list(generations)}"
            )
        generation_sets[catalog_id] = generations

    if generation_sets:
        observed_sets = set(generation_sets.values())
        if len(observed_sets) != 1:
            raise ValueError(
                "Fractal sibling lineage generation history is inconsistent"
            )
        next_generation = max(next(iter(observed_sets))) + 1
    else:
        next_generation = policy["generation_starts_at"]

    allocations: list[FractalLineageAllocation] = []
    for catalog_id in current_catalog_ids:
        runtime_id = _expected_runtime_id(
            catalog_child_id=catalog_id,
            generation=next_generation,
        )
        if runtime_id in runtime_ids:
            raise ValueError(
                f"Fractal lifecycle runtime node ID already exists: {runtime_id}"
            )
        allocations.append(
            FractalLineageAllocation(
                catalog_child_id=catalog_id,
                runtime_node_id=runtime_id,
                lineage_generation=next_generation,
                lineage_policy_id=policy["policy_id"],
            )
        )

    return tuple(
        sorted(allocations, key=lambda item: item.catalog_child_id)
    )
