from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal import (
    FractalRefinementActionProposal,
    FractalRefinementPersistenceState,
)
from .manifest import RunManifest
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalTopologyNode:
    node_id: str
    label: str
    parent_node_id: str
    level: str
    created_day: int
    refinement_action_id: str
    refinement_reason: str
    source_variables: tuple[str, ...]
    initialization_weight: float
    initialization_weight_policy_id: str
    inherited_uncertainty_policy_id: str
    aggregation_rule_id: str
    catalog_source_id: str
    de_refinement_day: int | None = None
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalTopologyNode.to_dict node=%s parent=%s active=%s",
            self.node_id,
            self.parent_node_id,
            self.active,
        )
        return {
            "node_id": self.node_id,
            "label": self.label,
            "parent_node_id": self.parent_node_id,
            "level": self.level,
            "created_day": self.created_day,
            "refinement_action_id": self.refinement_action_id,
            "refinement_reason": self.refinement_reason,
            "source_variables": list(self.source_variables),
            "initialization_weight": self.initialization_weight,
            "initialization_weight_policy_id": (
                self.initialization_weight_policy_id
            ),
            "inherited_uncertainty_policy_id": (
                self.inherited_uncertainty_policy_id
            ),
            "aggregation_rule_id": self.aggregation_rule_id,
            "catalog_source_id": self.catalog_source_id,
            "de_refinement_day": self.de_refinement_day,
            "active": self.active,
        }


@dataclass(frozen=True)
class FractalTopologyState:
    last_committed_day: int
    nodes: tuple[FractalTopologyNode, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalTopologyState.to_dict day=%s nodes=%s",
            self.last_committed_day,
            len(self.nodes),
        )
        return {
            "last_committed_day": self.last_committed_day,
            "nodes": [
                item.to_dict()
                for item in sorted(self.nodes, key=lambda node: node.node_id)
            ],
        }

    def topology_hash(self) -> str:
        logger.info(
            "FractalTopologyState.topology_hash day=%s nodes=%s",
            self.last_committed_day,
            len(self.nodes),
        )
        return canonical_hash(self.to_dict())

    def active_children(
        self,
        parent_node_id: str,
    ) -> tuple[FractalTopologyNode, ...]:
        logger.info(
            "FractalTopologyState.active_children parent=%s",
            parent_node_id,
        )
        return tuple(
            sorted(
                (
                    item
                    for item in self.nodes
                    if item.parent_node_id == parent_node_id
                    and item.active
                ),
                key=lambda item: item.node_id,
            )
        )


@dataclass(frozen=True)
class FractalMaterializationCommitRecord:
    commit_id: str
    parent_node_id: str
    day: int
    action_id: str
    from_level: str
    to_level: str
    child_node_ids: tuple[str, ...]
    catalog_hash: str
    topology_hash_before: str
    topology_hash_after: str
    persistence_before: dict[str, Any]
    persistence_after: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalMaterializationCommitRecord.to_dict commit_id=%s parent=%s",
            self.commit_id,
            self.parent_node_id,
        )
        return {
            "commit_id": self.commit_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "action_id": self.action_id,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "child_node_ids": list(self.child_node_ids),
            "catalog_hash": self.catalog_hash,
            "topology_hash_before": self.topology_hash_before,
            "topology_hash_after": self.topology_hash_after,
            "persistence_before": self.persistence_before,
            "persistence_after": self.persistence_after,
        }


def empty_fractal_topology(day: int = 0) -> FractalTopologyState:
    logger.info("empty_fractal_topology day=%s", day)
    return FractalTopologyState(last_committed_day=day, nodes=())


def _validate_materialization_config(config: dict[str, Any]) -> dict[str, Any]:
    logger.info("_validate_materialization_config")
    mode = config.get("mode", {})
    if mode.get("expansion_commit_allowed") is not True:
        raise ValueError("v0.20 requires expansion_commit_allowed=true")
    if mode.get("collapse_commit_allowed") is not False:
        raise ValueError("v0.20 collapse commit must remain disabled")
    if mode.get("engine_state_child_activation") is not False:
        raise ValueError(
            "v0.20 must not activate child EngineState dynamics"
        )
    if mode.get("country_graph_child_activation") is not False:
        raise ValueError(
            "v0.20 must not insert children into CountryGraph"
        )
    if mode.get("explicit_catalog_required") is not True:
        raise ValueError("v0.20 requires an explicit region catalog")

    min_children = int(config["catalog_constraints"]["min_children"])
    max_children = int(config["catalog_constraints"]["max_children"])
    if min_children < 2 or max_children < min_children:
        raise ValueError("Invalid fractal child-count constraints")

    return {
        "min_children": min_children,
        "max_children": max_children,
    }


def _validate_topology(topology: FractalTopologyState) -> None:
    logger.info(
        "_validate_topology day=%s nodes=%s",
        topology.last_committed_day,
        len(topology.nodes),
    )
    node_ids = [item.node_id for item in topology.nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("Duplicate node IDs in fractal topology")
    for item in topology.nodes:
        if item.level != "L2_REGION":
            raise ValueError(
                f"v0.20 topology node {item.node_id} must be L2_REGION"
            )
        if item.initialization_weight <= 0.0:
            raise ValueError(
                f"Fractal node {item.node_id} must have positive weight"
            )
        if not math.isfinite(item.initialization_weight):
            raise ValueError(
                f"Fractal node {item.node_id} has non-finite weight"
            )


def _catalog_children(
    *,
    parent_node_id: str,
    region_catalog: dict[str, Any],
    constraints: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    logger.info("_catalog_children parent=%s", parent_node_id)
    parents = region_catalog.get("parents")
    if not isinstance(parents, dict):
        raise ValueError("Fractal region catalog parents must be a mapping")
    parent = parents.get(parent_node_id)
    if not isinstance(parent, dict):
        raise ValueError(
            f"No explicit regional catalog for parent {parent_node_id}"
        )
    source_id = str(parent.get("source_id", ""))
    if not source_id:
        raise ValueError(
            f"Regional catalog parent {parent_node_id} requires source_id"
        )
    children_raw = parent.get("children")
    if not isinstance(children_raw, list):
        raise ValueError(
            f"Regional catalog parent {parent_node_id} children must be a list"
        )
    count = len(children_raw)
    if not constraints["min_children"] <= count <= constraints["max_children"]:
        raise ValueError(
            f"Regional catalog parent {parent_node_id} child count {count} "
            "outside configured bounds"
        )

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    weight_sum = 0.0
    for item in children_raw:
        if not isinstance(item, dict):
            raise ValueError("Regional catalog child must be a mapping")
        child_id = str(item.get("child_id", ""))
        label = str(item.get("label", ""))
        weight = float(item.get("initialization_weight", -1.0))
        if not child_id or not label:
            raise ValueError(
                f"Invalid regional catalog child for {parent_node_id}: {item}"
            )
        if not child_id.startswith(f"{parent_node_id}::"):
            raise ValueError(
                f"Fractal child {child_id} must be namespaced by parent "
                f"{parent_node_id}::"
            )
        if child_id in seen:
            raise ValueError(f"Duplicate regional child ID {child_id}")
        seen.add(child_id)
        if not math.isfinite(weight) or weight <= 0.0:
            raise ValueError(
                f"Regional child {child_id} weight must be finite and positive"
            )
        weight_sum += weight
        normalized.append(
            {
                "child_id": child_id,
                "label": label,
                "initialization_weight": weight,
                "source_id": source_id,
            }
        )

    if not math.isclose(
        weight_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            f"Regional child initialization weights for {parent_node_id} "
            f"must sum to 1.0, got {weight_sum}"
        )
    return tuple(sorted(normalized, key=lambda item: item["child_id"]))


def _commit_id(
    *,
    manifest: RunManifest,
    action: FractalRefinementActionProposal,
    catalog_hash: str,
    topology_hash_before: str,
    child_node_ids: tuple[str, ...],
) -> str:
    logger.info(
        "_commit_id parent=%s action_id=%s children=%s",
        action.node_id,
        action.action_id,
        len(child_node_ids),
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "parent_node_id": action.node_id,
            "day": action.day,
            "action_id": action.action_id,
            "catalog_hash": catalog_hash,
            "topology_hash_before": topology_hash_before,
            "child_node_ids": list(child_node_ids),
            "commit_contract": "FRACTAL_L2_MATERIALIZATION_V1",
        }
    )
    return f"fractal-commit-{digest[:24]}"


def materialize_l1_to_l2(
    *,
    action: FractalRefinementActionProposal,
    persistence: FractalRefinementPersistenceState,
    topology: FractalTopologyState,
    region_catalog: dict[str, Any],
    materialization_config: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    FractalTopologyState,
    FractalRefinementPersistenceState,
    FractalMaterializationCommitRecord,
]:
    """Commit one matured L1->L2 topology expansion without child EngineState."""
    logger.info(
        "materialize_l1_to_l2 parent=%s day=%s action=%s",
        action.node_id,
        action.day,
        action.action,
    )
    constraints = _validate_materialization_config(materialization_config)
    _validate_topology(topology)

    if action.apply_status != "PROPOSED_NOT_APPLIED":
        raise ValueError(
            f"Fractal action {action.action_id} is not commit-eligible"
        )
    if action.action != "EXPAND":
        raise ValueError("v0.20 materializer supports EXPAND only")
    if action.from_level != "L1_COUNTRY" or action.to_level != "L2_REGION":
        raise ValueError("v0.20 supports only L1_COUNTRY -> L2_REGION")
    if persistence.node_id != action.node_id:
        raise ValueError("Fractal action/persistence node mismatch")
    if persistence.current_level != "L1_COUNTRY":
        raise ValueError(
            f"Fractal parent {action.node_id} is not at L1_COUNTRY"
        )
    if persistence.last_evaluated_day != action.day:
        raise ValueError(
            "Fractal persistence day must equal matured action day"
        )
    if persistence.expand_streak < action.persistence_required:
        raise ValueError(
            "Fractal action persistence requirement is not satisfied"
        )
    if topology.last_committed_day != action.day - 1:
        raise ValueError(
            "Fractal topology must be committed through the prior day"
        )
    if topology.active_children(action.node_id):
        raise ValueError(
            f"Fractal parent {action.node_id} already has active children"
        )

    children = _catalog_children(
        parent_node_id=action.node_id,
        region_catalog=region_catalog,
        constraints=constraints,
    )
    catalog_hash = canonical_hash(region_catalog)
    topology_hash_before = topology.topology_hash()

    new_nodes = list(topology.nodes)
    for child in children:
        new_nodes.append(
            FractalTopologyNode(
                node_id=child["child_id"],
                label=child["label"],
                parent_node_id=action.node_id,
                level="L2_REGION",
                created_day=action.day,
                refinement_action_id=action.action_id,
                refinement_reason=action.refinement_reason,
                source_variables=action.source_variables,
                initialization_weight=child["initialization_weight"],
                initialization_weight_policy_id=(
                    action.initialization_weight_policy_id
                ),
                inherited_uncertainty_policy_id=(
                    action.inherited_uncertainty_policy_id
                ),
                aggregation_rule_id=action.aggregation_rule_id,
                catalog_source_id=child["source_id"],
            )
        )

    topology_after = FractalTopologyState(
        last_committed_day=action.day,
        nodes=tuple(sorted(new_nodes, key=lambda item: item.node_id)),
    )
    _validate_topology(topology_after)

    persistence_after = FractalRefinementPersistenceState(
        node_id=persistence.node_id,
        current_level="L2_REGION",
        last_evaluated_day=persistence.last_evaluated_day,
        expand_streak=0,
        collapse_streak=0,
    )
    child_node_ids = tuple(
        item["child_id"] for item in children
    )
    commit_id = _commit_id(
        manifest=manifest,
        action=action,
        catalog_hash=catalog_hash,
        topology_hash_before=topology_hash_before,
        child_node_ids=child_node_ids,
    )
    record = FractalMaterializationCommitRecord(
        commit_id=commit_id,
        parent_node_id=action.node_id,
        day=action.day,
        action_id=action.action_id,
        from_level=action.from_level,
        to_level=action.to_level,
        child_node_ids=child_node_ids,
        catalog_hash=catalog_hash,
        topology_hash_before=topology_hash_before,
        topology_hash_after=topology_after.topology_hash(),
        persistence_before=persistence.to_dict(),
        persistence_after=persistence_after.to_dict(),
    )
    trace.append(
        "fractal_materialization_committed",
        **record.to_dict(),
    )
    for node in topology_after.active_children(action.node_id):
        trace.append(
            "fractal_lineage_created",
            **node.to_dict(),
        )
    return topology_after, persistence_after, record


def advance_fractal_topology_without_materialization(
    *,
    topology: FractalTopologyState,
    day: int,
    trace: TraceLedger,
) -> FractalTopologyState:
    logger.info(
        "advance_fractal_topology_without_materialization "
        "from_day=%s to_day=%s",
        topology.last_committed_day,
        day,
    )
    _validate_topology(topology)
    if topology.last_committed_day != day - 1:
        raise ValueError(
            "Fractal topology must advance exactly one committed day"
        )
    advanced = FractalTopologyState(
        last_committed_day=day,
        nodes=topology.nodes,
    )
    trace.append(
        "fractal_topology_retained",
        day=day,
        topology_hash=advanced.topology_hash(),
        active_node_ids=[
            item.node_id
            for item in advanced.nodes
            if item.active
        ],
    )
    return advanced
