from __future__ import annotations

import logging
import math
from dataclasses import dataclass, replace
from typing import Any

from .config import canonical_hash
from .fractal import (
    FractalRefinementActionProposal,
    FractalRefinementPersistenceState,
)
from .fractal_child_state import FractalChildStateStore
from .fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from .manifest import RunManifest
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalReaggregationAuditRecord:
    audit_id: str
    parent_node_id: str
    day: int
    child_node_ids: tuple[str, ...]
    additive_child_sums: tuple[tuple[str, int | None], ...]
    intensive_weighted_child_values: tuple[
        tuple[str, float | None], ...
    ]
    parent_only_retained_values: tuple[
        tuple[str, int | float | None], ...
    ]
    latent_weighted_child_values: tuple[tuple[str, float], ...]
    regime_consensus: tuple[tuple[str, str], ...]
    max_abs_latent_error: float
    tolerance: float
    conserved: bool

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalReaggregationAuditRecord.to_dict audit_id=%s parent=%s",
            self.audit_id,
            self.parent_node_id,
        )
        return {
            "audit_id": self.audit_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "child_node_ids": list(self.child_node_ids),
            "additive_child_sums": dict(self.additive_child_sums),
            "intensive_weighted_child_values": dict(
                self.intensive_weighted_child_values
            ),
            "parent_only_retained_values": dict(
                self.parent_only_retained_values
            ),
            "latent_weighted_child_values": dict(
                self.latent_weighted_child_values
            ),
            "regime_consensus": dict(self.regime_consensus),
            "max_abs_latent_error": self.max_abs_latent_error,
            "tolerance": self.tolerance,
            "conserved": self.conserved,
        }


@dataclass(frozen=True)
class FractalCollapseCommitRecord:
    commit_id: str
    action_id: str
    parent_node_id: str
    day: int
    from_level: str
    to_level: str
    child_node_ids: tuple[str, ...]
    aggregation_rule_id: str
    audit_id: str
    parent_state_hash_before: str
    parent_state_hash_after: str
    topology_hash_before: str
    topology_hash_after: str
    child_store_hash_before: str
    child_store_hash_after: str
    persistence_before: dict[str, Any]
    persistence_after: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalCollapseCommitRecord.to_dict commit_id=%s parent=%s",
            self.commit_id,
            self.parent_node_id,
        )
        return {
            "commit_id": self.commit_id,
            "action_id": self.action_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "child_node_ids": list(self.child_node_ids),
            "aggregation_rule_id": self.aggregation_rule_id,
            "audit_id": self.audit_id,
            "parent_state_hash_before": self.parent_state_hash_before,
            "parent_state_hash_after": self.parent_state_hash_after,
            "topology_hash_before": self.topology_hash_before,
            "topology_hash_after": self.topology_hash_after,
            "child_store_hash_before": self.child_store_hash_before,
            "child_store_hash_after": self.child_store_hash_after,
            "persistence_before": self.persistence_before,
            "persistence_after": self.persistence_after,
        }


@dataclass(frozen=True)
class FractalCollapseResult:
    states: dict[str, EngineState]
    topology: FractalTopologyState
    child_store: FractalChildStateStore
    persistence: dict[str, FractalRefinementPersistenceState]
    commits: tuple[FractalCollapseCommitRecord, ...]
    audits: tuple[FractalReaggregationAuditRecord, ...]


def _physical_stock_ids(
    engine_state_registry: dict[str, Any],
) -> tuple[str, ...]:
    logger.info("_physical_stock_ids")
    return tuple(
        str(item["id"])
        for item in engine_state_registry["physical_stocks"]
    )


def _validate_config(
    *,
    reaggregation_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_validate_config")
    mode = reaggregation_config.get("mode", {})
    required_true = (
        "enabled",
        "collapse_commit_allowed",
        "l2_to_l1_only",
        "complete_active_sibling_set_required",
        "remove_collapsed_children_from_store",
        "mark_topology_children_inactive",
        "de_refinement_day_required",
        "preserve_original_parent_object",
    )
    for key in required_true:
        if mode.get(key) is not True:
            raise ValueError(f"v0.23 requires {key}=true")
    if mode.get("child_dynamics_allowed") is not False:
        raise ValueError("v0.23 child dynamics must remain disabled")
    if mode.get("country_graph_child_activation") is not False:
        raise ValueError(
            "v0.23 must not activate L2 children in CountryGraph"
        )

    aggregation_rule_id = str(
        reaggregation_config.get("aggregation_rule_id", "")
    )
    if aggregation_rule_id != "FRACTAL_PARENT_REAGGREGATION_V1":
        raise ValueError("Unsupported fractal reaggregation rule")

    policies = reaggregation_config.get("physical_stock_policies")
    if not isinstance(policies, dict):
        raise ValueError(
            "Fractal reaggregation physical_stock_policies must be a mapping"
        )
    groups = (
        "additive_integer_sum",
        "intensive_initialization_weighted_mean",
        "parent_only_retain_current",
    )
    normalized: dict[str, tuple[str, ...]] = {}
    seen: set[str] = set()
    for group in groups:
        raw = policies.get(group)
        if not isinstance(raw, list):
            raise ValueError(
                f"Fractal reaggregation physical policy {group} must be a list"
            )
        values = tuple(sorted(str(item) for item in raw))
        if len(values) != len(set(values)):
            raise ValueError(
                f"Duplicate physical stock in reaggregation group {group}"
            )
        overlap = seen.intersection(values)
        if overlap:
            raise ValueError(
                "Fractal reaggregation physical stocks classified multiple "
                f"times: {sorted(overlap)}"
            )
        seen.update(values)
        normalized[group] = values

    expected = set(_physical_stock_ids(engine_state_registry))
    if seen != expected:
        raise ValueError(
            "Fractal reaggregation physical stock coverage mismatch "
            f"missing={sorted(expected-seen)} extra={sorted(seen-expected)}"
        )

    latent_policy = reaggregation_config.get("latent_policy", {})
    if latent_policy.get("mode") != "initialization_weighted_mean":
        raise ValueError(
            "v0.23 latents must use initialization_weighted_mean"
        )
    tolerance = float(latent_policy.get("tolerance", 0.0))
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("Fractal reaggregation tolerance must be positive")

    regime_policy = reaggregation_config.get("regime_policy", {})
    if regime_policy.get("mode") != "all_children_consensus_required":
        raise ValueError(
            "v0.23 categorical regimes require all-children consensus"
        )

    metadata_policy = reaggregation_config.get("metadata_policy", {})
    if (
        metadata_policy.get("mode")
        != "retain_parent_append_collapse_lineage"
    ):
        raise ValueError("Unsupported fractal collapse metadata policy")
    metadata_policy_id = str(metadata_policy.get("policy_id", ""))
    if not metadata_policy_id:
        raise ValueError("Fractal collapse metadata policy_id is required")

    safety = reaggregation_config.get("safety", {})
    if (
        safety.get("collapse_is_resolution_change_not_political_outcome")
        is not True
    ):
        raise ValueError(
            "Fractal collapse must remain a resolution operation"
        )
    forbidden = (
        "civilian_identity_direct_aggregation_input",
        "religion_direct_aggregation_input",
        "ethnicity_direct_aggregation_input",
        "political_identity_direct_aggregation_input",
        "tactical_target_selection",
        "route_planning",
        "weapon_selection",
        "operational_execution",
    )
    if any(safety.get(key) is not False for key in forbidden):
        raise ValueError("Fractal reaggregation safety contract violated")

    return {
        **normalized,
        "aggregation_rule_id": aggregation_rule_id,
        "tolerance": tolerance,
        "metadata_policy_id": metadata_policy_id,
    }


def _validate_action(
    *,
    action: FractalRefinementActionProposal,
    persistence: FractalRefinementPersistenceState,
    policy: dict[str, Any],
) -> None:
    logger.info(
        "_validate_action parent=%s action_id=%s",
        action.node_id,
        action.action_id,
    )
    if action.apply_status != "PROPOSED_NOT_APPLIED":
        raise ValueError(
            f"Fractal collapse action {action.action_id} is not commit-eligible"
        )
    if action.action != "COLLAPSE":
        raise ValueError("v0.23 reaggregation accepts COLLAPSE actions only")
    if action.from_level != "L2_REGION" or action.to_level != "L1_COUNTRY":
        raise ValueError("v0.23 supports only L2_REGION -> L1_COUNTRY")
    if action.aggregation_rule_id != policy["aggregation_rule_id"]:
        raise ValueError("Fractal collapse aggregation rule mismatch")
    if persistence.node_id != action.node_id:
        raise ValueError("Fractal collapse action/persistence node mismatch")
    if persistence.current_level != "L2_REGION":
        raise ValueError(
            f"Fractal collapse parent {action.node_id} is not at L2_REGION"
        )
    if persistence.last_evaluated_day != action.day:
        raise ValueError(
            "Fractal collapse persistence day must equal action day"
        )
    if action.persistence_observed < action.persistence_required:
        raise ValueError(
            "Fractal collapse action has not satisfied persistence"
        )
    if persistence.collapse_streak < action.persistence_required:
        raise ValueError(
            "Fractal collapse persistence streak is not satisfied"
        )


def _validate_children(
    *,
    parent_state: EngineState,
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    policy: dict[str, Any],
) -> tuple[
    tuple[FractalTopologyNode, ...],
    dict[str, EngineState],
]:
    logger.info(
        "_validate_children parent=%s day=%s",
        parent_state.node_id,
        parent_state.day,
    )
    if topology.last_committed_day != parent_state.day:
        raise ValueError(
            "Fractal collapse topology must be committed through action day"
        )
    if child_store.last_initialized_day != parent_state.day:
        raise ValueError(
            "Fractal collapse child store must be committed through action day"
        )

    children = topology.active_children(parent_state.node_id)
    if not children:
        raise ValueError(
            f"Fractal collapse parent {parent_state.node_id} has no active children"
        )
    child_map = child_store.state_map()
    missing = {
        item.node_id for item in children
    } - set(child_map)
    if missing:
        raise ValueError(
            "Fractal collapse child store is incomplete for parent "
            f"{parent_state.node_id}: {sorted(missing)}"
        )

    weight_sum = math.fsum(
        float(item.initialization_weight) for item in children
    )
    if not math.isclose(
        weight_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=policy["tolerance"],
    ):
        raise ValueError(
            f"Fractal collapse child weights for {parent_state.node_id} "
            f"must sum to 1.0"
        )

    selected: dict[str, EngineState] = {}
    for topology_node in children:
        if topology_node.level != "L2_REGION":
            raise ValueError(
                f"Fractal collapse child {topology_node.node_id} "
                "must be L2_REGION"
            )
        if not topology_node.active:
            raise ValueError(
                f"Fractal collapse child {topology_node.node_id} must be active"
            )
        if topology_node.de_refinement_day is not None:
            raise ValueError(
                f"Active child {topology_node.node_id} already has "
                "de_refinement_day"
            )
        if (
            topology_node.aggregation_rule_id
            != policy["aggregation_rule_id"]
        ):
            raise ValueError(
                f"Child {topology_node.node_id} aggregation rule mismatch"
            )

        child = child_map[topology_node.node_id]
        if child.day != parent_state.day:
            raise ValueError(
                f"Fractal collapse child {child.node_id} day mismatch"
            )
        if (
            child.metadata.get("fractal_parent_node_id")
            != parent_state.node_id
        ):
            raise ValueError(
                f"Fractal collapse child {child.node_id} parent lineage mismatch"
            )
        if (
            child.metadata.get("fractal_aggregation_rule_id")
            != policy["aggregation_rule_id"]
        ):
            raise ValueError(
                f"Fractal collapse child {child.node_id} metadata "
                "aggregation rule mismatch"
            )
        if child.metadata.get("fractal_child_dynamics_active") is not False:
            raise ValueError(
                f"Fractal collapse child {child.node_id} dynamics must "
                "remain disabled in v0.23"
            )
        selected[child.node_id] = child

    return children, selected


def _integer_or_none(
    *,
    variable: str,
    value: int | float | None,
) -> int | None:
    logger.info("_integer_or_none variable=%s value=%s", variable, value)
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(
            f"Fractal additive child stock {variable} must be "
            "finite/non-negative"
        )
    rounded = round(numeric)
    if not math.isclose(
        numeric,
        float(rounded),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            f"Fractal additive child stock {variable}={numeric} "
            "is not integer-valued"
        )
    return int(rounded)


def _aggregate_additive(
    *,
    variable: str,
    children: tuple[FractalTopologyNode, ...],
    child_states: dict[str, EngineState],
) -> int | None:
    logger.info("_aggregate_additive variable=%s", variable)
    for item in children:
        if variable not in child_states[item.node_id].physical_stocks:
            raise KeyError(
                f"Fractal collapse child {item.node_id} missing physical "
                f"stock {variable}"
            )
    values = [
        _integer_or_none(
            variable=variable,
            value=child_states[item.node_id].physical_stocks[variable],
        )
        for item in children
    ]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError(
            f"Fractal additive stock {variable} has mixed null/numeric children"
        )
    return sum(int(value) for value in values if value is not None)


def _aggregate_intensive(
    *,
    variable: str,
    children: tuple[FractalTopologyNode, ...],
    child_states: dict[str, EngineState],
) -> float | None:
    logger.info("_aggregate_intensive variable=%s", variable)
    for item in children:
        if variable not in child_states[item.node_id].physical_stocks:
            raise KeyError(
                f"Fractal collapse child {item.node_id} missing physical "
                f"stock {variable}"
            )
    values = [
        child_states[item.node_id].physical_stocks[variable]
        for item in children
    ]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError(
            f"Fractal intensive stock {variable} has mixed null/numeric children"
        )
    weighted_terms: list[float] = []
    for topology_node, raw in zip(children, values, strict=True):
        numeric = float(raw)
        if not math.isfinite(numeric):
            raise ValueError(
                f"Fractal intensive child stock {variable} must be finite"
            )
        weighted_terms.append(
            float(topology_node.initialization_weight) * numeric
        )
    return math.fsum(weighted_terms)


def _aggregate_physical_stocks(
    *,
    parent_state: EngineState,
    children: tuple[FractalTopologyNode, ...],
    child_states: dict[str, EngineState],
    policy: dict[str, Any],
) -> tuple[
    dict[str, int | float | None],
    dict[str, int | None],
    dict[str, float | None],
    dict[str, int | float | None],
]:
    logger.info(
        "_aggregate_physical_stocks parent=%s children=%s",
        parent_state.node_id,
        len(children),
    )
    aggregated: dict[str, int | float | None] = {}
    additive: dict[str, int | None] = {}
    intensive: dict[str, float | None] = {}
    retained: dict[str, int | float | None] = {}

    for variable in policy["additive_integer_sum"]:
        value = _aggregate_additive(
            variable=variable,
            children=children,
            child_states=child_states,
        )
        additive[variable] = value
        aggregated[variable] = value

    for variable in policy["intensive_initialization_weighted_mean"]:
        value = _aggregate_intensive(
            variable=variable,
            children=children,
            child_states=child_states,
        )
        intensive[variable] = value
        aggregated[variable] = value

    for variable in policy["parent_only_retain_current"]:
        if variable not in parent_state.physical_stocks:
            raise KeyError(
                f"Parent {parent_state.node_id} missing parent-only stock "
                f"{variable}"
            )
        value = parent_state.physical_stocks[variable]
        retained[variable] = value
        aggregated[variable] = value

    return aggregated, additive, intensive, retained


def _validate_aggregated_physical_stocks(
    *,
    physical_stocks: dict[str, int | float | None],
    engine_state_registry: dict[str, Any],
) -> None:
    logger.info("_validate_aggregated_physical_stocks")
    definitions = {
        str(item["id"]): item
        for item in engine_state_registry["physical_stocks"]
    }
    observed = set(physical_stocks)
    expected = set(definitions)
    if observed != expected:
        raise ValueError(
            "Reaggregated physical-stock coverage mismatch "
            f"missing={sorted(expected-observed)} "
            f"extra={sorted(observed-expected)}"
        )
    for variable, definition in sorted(definitions.items()):
        value = physical_stocks[variable]
        nullable = bool(definition.get("nullable", False))
        if value is None:
            if not nullable:
                raise ValueError(
                    f"Reaggregated non-null physical stock {variable} is null"
                )
            continue
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(
                f"Reaggregated physical stock {variable} must be finite"
            )
        if numeric < 0.0:
            raise ValueError(
                f"Reaggregated physical stock {variable} must be non-negative"
            )


def _aggregate_latents(
    *,
    children: tuple[FractalTopologyNode, ...],
    child_states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
) -> dict[str, float]:
    logger.info("_aggregate_latents children=%s", len(children))
    latent_registry = extract_latent_registry(engine_state_registry)
    result: dict[str, float] = {}
    for variable in sorted(latent_registry):
        value = math.fsum(
            float(item.initialization_weight)
            * float(child_states[item.node_id].latents[variable])
            for item in children
        )
        low, high = latent_registry[variable]
        if value < low - 1e-12 or value > high + 1e-12:
            raise ValueError(
                f"Reaggregated latent {variable}={value} outside [{low}, {high}]"
            )
        if value < low:
            value = low
        if value > high:
            value = high
        result[variable] = value
    return result


def _aggregate_regimes(
    *,
    children: tuple[FractalTopologyNode, ...],
    child_states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
) -> dict[str, str]:
    logger.info("_aggregate_regimes children=%s", len(children))
    regime_definitions = engine_state_registry["regimes"]
    regime_ids = tuple(sorted(regime_definitions))
    result: dict[str, str] = {}
    for regime_id in regime_ids:
        for item in children:
            if regime_id not in child_states[item.node_id].regimes:
                raise KeyError(
                    f"Fractal collapse child {item.node_id} missing regime "
                    f"{regime_id}"
                )
        observed = {
            str(child_states[item.node_id].regimes[regime_id])
            for item in children
        }
        if len(observed) != 1:
            raise ValueError(
                f"Fractal collapse regime {regime_id} requires unanimous "
                f"sibling consensus, got {sorted(observed)}"
            )
        consensus = next(iter(observed))
        allowed = {
            str(value)
            for value in regime_definitions[regime_id]["values"]
        }
        if consensus not in allowed:
            raise ValueError(
                f"Fractal collapse regime {regime_id} has invalid value "
                f"{consensus}"
            )
        result[regime_id] = consensus
    return result


def _audit(
    *,
    parent_state: EngineState,
    children: tuple[FractalTopologyNode, ...],
    child_states: dict[str, EngineState],
    additive: dict[str, int | None],
    intensive: dict[str, float | None],
    retained: dict[str, int | float | None],
    latents: dict[str, float],
    regimes: dict[str, str],
    tolerance: float,
    aggregation_rule_id: str,
) -> FractalReaggregationAuditRecord:
    logger.info(
        "_audit parent=%s children=%s",
        parent_state.node_id,
        len(children),
    )
    recomputed_latents = {
        variable: math.fsum(
            float(item.initialization_weight)
            * float(child_states[item.node_id].latents[variable])
            for item in children
        )
        for variable in sorted(latents)
    }
    errors = [
        abs(recomputed_latents[variable] - latents[variable])
        for variable in latents
    ]
    max_error = max(errors, default=0.0)

    payload = {
        "parent_node_id": parent_state.node_id,
        "day": parent_state.day,
        "child_node_ids": [item.node_id for item in children],
        "child_state_hashes": {
            item.node_id: child_states[item.node_id].state_hash()
            for item in children
        },
        "additive_child_sums": dict(sorted(additive.items())),
        "intensive_weighted_child_values": dict(sorted(intensive.items())),
        "parent_only_retained_values": dict(sorted(retained.items())),
        "latent_weighted_child_values": dict(sorted(latents.items())),
        "regime_consensus": dict(sorted(regimes.items())),
        "aggregation_rule_id": aggregation_rule_id,
        "tolerance": tolerance,
        "contract": "FRACTAL_L2_TO_L1_REAGGREGATION_AUDIT_V1",
    }
    audit_id = f"fractal-reaggregation-audit-{canonical_hash(payload)[:24]}"
    conserved = max_error <= tolerance
    return FractalReaggregationAuditRecord(
        audit_id=audit_id,
        parent_node_id=parent_state.node_id,
        day=parent_state.day,
        child_node_ids=tuple(item.node_id for item in children),
        additive_child_sums=tuple(sorted(additive.items())),
        intensive_weighted_child_values=tuple(sorted(intensive.items())),
        parent_only_retained_values=tuple(sorted(retained.items())),
        latent_weighted_child_values=tuple(sorted(latents.items())),
        regime_consensus=tuple(sorted(regimes.items())),
        max_abs_latent_error=max_error,
        tolerance=tolerance,
        conserved=conserved,
    )


def _collapsed_parent_metadata(
    *,
    parent_state: EngineState,
    action: FractalRefinementActionProposal,
    child_node_ids: tuple[str, ...],
    audit_id: str,
    policy: dict[str, Any],
) -> dict[str, Any]:
    logger.info(
        "_collapsed_parent_metadata parent=%s action_id=%s",
        parent_state.node_id,
        action.action_id,
    )
    metadata = dict(parent_state.metadata)
    metadata.update(
        {
            "fractal_last_collapse_day": action.day,
            "fractal_last_collapse_action_id": action.action_id,
            "fractal_last_collapsed_child_ids": list(child_node_ids),
            "fractal_last_aggregation_rule_id": policy[
                "aggregation_rule_id"
            ],
            "fractal_last_reaggregation_audit_id": audit_id,
            "fractal_collapse_metadata_policy_id": policy[
                "metadata_policy_id"
            ],
        }
    )
    return metadata


def _deactivate_topology_children(
    *,
    topology: FractalTopologyState,
    parent_node_id: str,
    day: int,
) -> FractalTopologyState:
    logger.info(
        "_deactivate_topology_children parent=%s day=%s",
        parent_node_id,
        day,
    )
    nodes: list[FractalTopologyNode] = []
    changed = 0
    for node in topology.nodes:
        if node.parent_node_id == parent_node_id and node.active:
            nodes.append(
                replace(
                    node,
                    de_refinement_day=day,
                    active=False,
                )
            )
            changed += 1
        else:
            nodes.append(node)
    if changed == 0:
        raise ValueError(
            f"No active topology children to collapse for {parent_node_id}"
        )
    result = FractalTopologyState(
        last_committed_day=day,
        nodes=tuple(sorted(nodes, key=lambda item: item.node_id)),
    )
    if result.active_children(parent_node_id):
        raise RuntimeError(
            f"Fractal topology collapse left active children for {parent_node_id}"
        )
    return result


def _remove_child_states(
    *,
    child_store: FractalChildStateStore,
    child_node_ids: tuple[str, ...],
    day: int,
) -> FractalChildStateStore:
    logger.info(
        "_remove_child_states day=%s children=%s",
        day,
        len(child_node_ids),
    )
    remove = set(child_node_ids)
    present = set(child_store.state_map())
    missing = remove - present
    if missing:
        raise ValueError(
            f"Fractal collapse child states missing: {sorted(missing)}"
        )
    result = FractalChildStateStore(
        last_initialized_day=day,
        states=tuple(
            state
            for state in child_store.states
            if state.node_id not in remove
        ),
    )
    if remove.intersection(result.state_map()):
        raise RuntimeError("Collapsed child states remain in child store")
    return result


def collapse_l2_to_l1(
    *,
    parent_state: EngineState,
    action: FractalRefinementActionProposal,
    persistence: FractalRefinementPersistenceState,
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    reaggregation_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    EngineState,
    FractalTopologyState,
    FractalChildStateStore,
    FractalRefinementPersistenceState,
    FractalCollapseCommitRecord,
    FractalReaggregationAuditRecord,
]:
    """Commit one conservative L2->L1 collapse for a single parent."""
    logger.info(
        "collapse_l2_to_l1 parent=%s day=%s action_id=%s",
        parent_state.node_id,
        parent_state.day,
        action.action_id,
    )
    policy = _validate_config(
        reaggregation_config=reaggregation_config,
        engine_state_registry=engine_state_registry,
    )
    _validate_action(
        action=action,
        persistence=persistence,
        policy=policy,
    )
    if parent_state.node_id != action.node_id:
        raise ValueError("Fractal collapse action does not target parent state")
    if parent_state.day != action.day:
        raise ValueError("Fractal collapse parent/action day mismatch")

    parent_hash_before = parent_state.state_hash()
    topology_hash_before = topology.topology_hash()
    child_store_hash_before = child_store.store_hash()

    children, child_states = _validate_children(
        parent_state=parent_state,
        topology=topology,
        child_store=child_store,
        policy=policy,
    )
    child_node_ids = tuple(item.node_id for item in children)

    (
        physical_stocks,
        additive,
        intensive,
        retained,
    ) = _aggregate_physical_stocks(
        parent_state=parent_state,
        children=children,
        child_states=child_states,
        policy=policy,
    )
    latents = _aggregate_latents(
        children=children,
        child_states=child_states,
        engine_state_registry=engine_state_registry,
    )
    _validate_aggregated_physical_stocks(
        physical_stocks=physical_stocks,
        engine_state_registry=engine_state_registry,
    )
    regimes = _aggregate_regimes(
        children=children,
        child_states=child_states,
        engine_state_registry=engine_state_registry,
    )
    audit = _audit(
        parent_state=parent_state,
        children=children,
        child_states=child_states,
        additive=additive,
        intensive=intensive,
        retained=retained,
        latents=latents,
        regimes=regimes,
        tolerance=policy["tolerance"],
        aggregation_rule_id=policy["aggregation_rule_id"],
    )
    if not audit.conserved:
        raise RuntimeError(
            f"Fractal reaggregation failed for {parent_state.node_id}: "
            f"max_error={audit.max_abs_latent_error}"
        )

    parent_after = EngineState(
        node_id=parent_state.node_id,
        day=parent_state.day,
        physical_stocks=dict(sorted(physical_stocks.items())),
        latents=dict(sorted(latents.items())),
        regimes=dict(sorted(regimes.items())),
        metadata=_collapsed_parent_metadata(
            parent_state=parent_state,
            action=action,
            child_node_ids=child_node_ids,
            audit_id=audit.audit_id,
            policy=policy,
        ),
    )
    parent_after.validate(extract_latent_registry(engine_state_registry))
    if parent_state.state_hash() != parent_hash_before:
        raise RuntimeError("Fractal collapse mutated original parent EngineState")

    topology_after = _deactivate_topology_children(
        topology=topology,
        parent_node_id=parent_state.node_id,
        day=action.day,
    )
    child_store_after = _remove_child_states(
        child_store=child_store,
        child_node_ids=child_node_ids,
        day=action.day,
    )
    persistence_after = FractalRefinementPersistenceState(
        node_id=persistence.node_id,
        current_level="L1_COUNTRY",
        last_evaluated_day=persistence.last_evaluated_day,
        expand_streak=0,
        collapse_streak=0,
    )

    payload = {
        "replay_key": manifest.replay_key,
        "action_id": action.action_id,
        "parent_node_id": parent_state.node_id,
        "day": action.day,
        "child_node_ids": list(child_node_ids),
        "aggregation_rule_id": policy["aggregation_rule_id"],
        "audit_id": audit.audit_id,
        "parent_state_hash_before": parent_hash_before,
        "parent_state_hash_after": parent_after.state_hash(),
        "topology_hash_before": topology_hash_before,
        "topology_hash_after": topology_after.topology_hash(),
        "child_store_hash_before": child_store_hash_before,
        "child_store_hash_after": child_store_after.store_hash(),
        "contract": "FRACTAL_L2_TO_L1_COLLAPSE_V1",
    }
    commit_id = f"fractal-collapse-{canonical_hash(payload)[:24]}"
    record = FractalCollapseCommitRecord(
        commit_id=commit_id,
        action_id=action.action_id,
        parent_node_id=parent_state.node_id,
        day=action.day,
        from_level=action.from_level,
        to_level=action.to_level,
        child_node_ids=child_node_ids,
        aggregation_rule_id=policy["aggregation_rule_id"],
        audit_id=audit.audit_id,
        parent_state_hash_before=parent_hash_before,
        parent_state_hash_after=parent_after.state_hash(),
        topology_hash_before=topology_hash_before,
        topology_hash_after=topology_after.topology_hash(),
        child_store_hash_before=child_store_hash_before,
        child_store_hash_after=child_store_after.store_hash(),
        persistence_before=persistence.to_dict(),
        persistence_after=persistence_after.to_dict(),
    )

    trace.append("fractal_reaggregation_audit", **audit.to_dict())
    trace.append("fractal_collapse_committed", **record.to_dict())
    closed_by_id = {
        item.node_id: item
        for item in topology_after.nodes
        if item.parent_node_id == parent_state.node_id
        and item.node_id in set(child_node_ids)
    }
    for child_node_id in child_node_ids:
        node = closed_by_id[child_node_id]
        trace.append(
            "fractal_lineage_closed",
            parent_node_id=parent_state.node_id,
            child_node_id=child_node_id,
            day=action.day,
            de_refinement_day=node.de_refinement_day,
            commit_id=record.commit_id,
            aggregation_rule_id=record.aggregation_rule_id,
        )

    return (
        parent_after,
        topology_after,
        child_store_after,
        persistence_after,
        record,
        audit,
    )


def commit_fractal_collapses(
    *,
    parent_states: dict[str, EngineState],
    actions: tuple[FractalRefinementActionProposal, ...],
    persistence: dict[str, FractalRefinementPersistenceState],
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    reaggregation_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> FractalCollapseResult:
    """Commit zero or more independent parent collapses deterministically."""
    logger.info(
        "commit_fractal_collapses day=%s actions=%s",
        topology.last_committed_day,
        len(actions),
    )
    states_out = dict(parent_states)
    persistence_out = dict(persistence)
    topology_out = topology
    child_store_out = child_store
    commits: list[FractalCollapseCommitRecord] = []
    audits: list[FractalReaggregationAuditRecord] = []
    seen_parents: set[str] = set()

    for action in sorted(actions, key=lambda item: item.action_id):
        if action.node_id in seen_parents:
            raise ValueError(
                f"Multiple fractal collapse actions for {action.node_id}"
            )
        seen_parents.add(action.node_id)
        if action.node_id not in states_out:
            raise ValueError(
                f"Fractal collapse targets unknown parent {action.node_id}"
            )
        if action.node_id not in persistence_out:
            raise ValueError(
                f"Fractal collapse targets unknown persistence {action.node_id}"
            )

        (
            parent_after,
            topology_out,
            child_store_out,
            persistence_after,
            commit_record,
            audit,
        ) = collapse_l2_to_l1(
            parent_state=states_out[action.node_id],
            action=action,
            persistence=persistence_out[action.node_id],
            topology=topology_out,
            child_store=child_store_out,
            reaggregation_config=reaggregation_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=trace,
        )
        states_out[action.node_id] = parent_after
        persistence_out[action.node_id] = persistence_after
        commits.append(commit_record)
        audits.append(audit)

    return FractalCollapseResult(
        states=states_out,
        topology=topology_out,
        child_store=child_store_out,
        persistence=persistence_out,
        commits=tuple(sorted(commits, key=lambda item: item.commit_id)),
        audits=tuple(sorted(audits, key=lambda item: item.audit_id)),
    )
