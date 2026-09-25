from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_levels import level_index
from .fractal_materialization import FractalTopologyNode, FractalTopologyState
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalChildStateStore:
    last_initialized_day: int
    states: tuple[EngineState, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalChildStateStore.to_dict day=%s states=%s",
            self.last_initialized_day,
            len(self.states),
        )
        return {
            "last_initialized_day": self.last_initialized_day,
            "states": [
                item.to_dict()
                for item in sorted(self.states, key=lambda state: state.node_id)
            ],
        }

    def store_hash(self) -> str:
        logger.info(
            "FractalChildStateStore.store_hash day=%s states=%s",
            self.last_initialized_day,
            len(self.states),
        )
        return canonical_hash(self.to_dict())

    def state_map(self) -> dict[str, EngineState]:
        logger.info(
            "FractalChildStateStore.state_map states=%s",
            len(self.states),
        )
        return {
            state.node_id: state
            for state in sorted(self.states, key=lambda item: item.node_id)
        }


@dataclass(frozen=True)
class FractalChildStateInitializationRecord:
    initialization_id: str
    parent_node_id: str
    child_node_id: str
    day: int
    initialization_weight: float
    parent_state_hash: str
    child_state_hash: str
    refinement_action_id: str
    catalog_source_id: str
    catalog_child_id: str
    lineage_generation: int
    lineage_policy_id: str | None
    additive_integer_variables: tuple[str, ...]
    inherited_intensive_variables: tuple[str, ...]
    parent_only_variables: tuple[str, ...]
    latent_policy_id: str
    regime_policy_id: str
    metadata_policy_id: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalChildStateInitializationRecord.to_dict "
            "initialization_id=%s child=%s",
            self.initialization_id,
            self.child_node_id,
        )
        return {
            "initialization_id": self.initialization_id,
            "parent_node_id": self.parent_node_id,
            "child_node_id": self.child_node_id,
            "day": self.day,
            "initialization_weight": self.initialization_weight,
            "parent_state_hash": self.parent_state_hash,
            "child_state_hash": self.child_state_hash,
            "refinement_action_id": self.refinement_action_id,
            "catalog_source_id": self.catalog_source_id,
            "catalog_child_id": self.catalog_child_id,
            "lineage_generation": self.lineage_generation,
            "lineage_policy_id": self.lineage_policy_id,
            "additive_integer_variables": list(
                self.additive_integer_variables
            ),
            "inherited_intensive_variables": list(
                self.inherited_intensive_variables
            ),
            "parent_only_variables": list(self.parent_only_variables),
            "latent_policy_id": self.latent_policy_id,
            "regime_policy_id": self.regime_policy_id,
            "metadata_policy_id": self.metadata_policy_id,
        }


@dataclass(frozen=True)
class FractalConservationAuditRecord:
    audit_id: str
    parent_node_id: str
    day: int
    child_node_ids: tuple[str, ...]
    additive_parent_values: tuple[tuple[str, int | None], ...]
    additive_child_sums: tuple[tuple[str, int | None], ...]
    conserved: bool

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalConservationAuditRecord.to_dict audit_id=%s parent=%s",
            self.audit_id,
            self.parent_node_id,
        )
        return {
            "audit_id": self.audit_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "child_node_ids": list(self.child_node_ids),
            "additive_parent_values": dict(self.additive_parent_values),
            "additive_child_sums": dict(self.additive_child_sums),
            "conserved": self.conserved,
        }


@dataclass(frozen=True)
class FractalChildInitializationResult:
    store: FractalChildStateStore
    initialization_records: tuple[FractalChildStateInitializationRecord, ...]
    conservation_audits: tuple[FractalConservationAuditRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalChildInitializationResult.to_dict records=%s audits=%s",
            len(self.initialization_records),
            len(self.conservation_audits),
        )
        return {
            "store": self.store.to_dict(),
            "initialization_records": [
                item.to_dict() for item in self.initialization_records
            ],
            "conservation_audits": [
                item.to_dict() for item in self.conservation_audits
            ],
        }


def empty_fractal_child_state_store(
    day: int = 0,
) -> FractalChildStateStore:
    logger.info("empty_fractal_child_state_store day=%s", day)
    return FractalChildStateStore(
        last_initialized_day=day,
        states=(),
    )


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
    initialization_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_validate_config")
    mode = initialization_config.get("mode", {})
    if mode.get("child_state_initialization_allowed") is not True:
        raise ValueError(
            "v0.21 requires child_state_initialization_allowed=true"
        )
    if mode.get("child_dynamics_allowed") is not False:
        raise ValueError("v0.21 child dynamics must remain disabled")
    if mode.get("country_graph_child_activation") is not False:
        raise ValueError(
            "v0.21 child CountryGraph activation must remain disabled"
        )
    if mode.get("random_perturbation_allowed") is not False:
        raise ValueError(
            "v0.21 random perturbation must remain disabled until v0.22"
        )

    policies = initialization_config.get("physical_stock_policies")
    if not isinstance(policies, dict):
        raise ValueError("physical_stock_policies must be a mapping")

    required_groups = (
        "additive_integer_conserved",
        "intensive_inherit_parent",
        "parent_only_null",
    )
    normalized: dict[str, tuple[str, ...]] = {}
    seen: set[str] = set()
    for group in required_groups:
        raw = policies.get(group)
        if not isinstance(raw, list):
            raise ValueError(
                f"Physical stock policy {group} must be a list"
            )
        values = tuple(sorted(str(item) for item in raw))
        if len(values) != len(set(values)):
            raise ValueError(
                f"Duplicate physical stock in policy {group}"
            )
        overlap = seen.intersection(values)
        if overlap:
            raise ValueError(
                f"Physical stocks classified multiple times: {sorted(overlap)}"
            )
        seen.update(values)
        normalized[group] = values

    expected = set(_physical_stock_ids(engine_state_registry))
    if seen != expected:
        raise ValueError(
            "Physical stock policy coverage mismatch "
            f"missing={sorted(expected-seen)} extra={sorted(seen-expected)}"
        )

    latent_policy = initialization_config.get("latent_policy", {})
    if latent_policy.get("mode") != "inherit_parent_exact":
        raise ValueError("v0.21 latents must inherit parent exactly")
    if not str(latent_policy.get("policy_id", "")):
        raise ValueError("latent_policy requires policy_id")

    regime_policy = initialization_config.get("regime_policy", {})
    if regime_policy.get("mode") != "inherit_parent_exact":
        raise ValueError("v0.21 regimes must inherit parent exactly")
    if not str(regime_policy.get("policy_id", "")):
        raise ValueError("regime_policy requires policy_id")

    metadata_policy = initialization_config.get("metadata_policy", {})
    if metadata_policy.get("mode") != "copy_parent_and_append_fractal_lineage":
        raise ValueError(
            "v0.21 metadata policy must copy parent and append lineage"
        )
    if not str(metadata_policy.get("policy_id", "")):
        raise ValueError("metadata_policy requires policy_id")

    return {
        **normalized,
        "latent_policy_id": str(latent_policy["policy_id"]),
        "regime_policy_id": str(regime_policy["policy_id"]),
        "metadata_policy_id": str(metadata_policy["policy_id"]),
    }


def _validate_topology_children(
    *,
    parent_state: EngineState,
    children: tuple[FractalTopologyNode, ...],
) -> None:
    logger.info(
        "_validate_topology_children parent=%s children=%s",
        parent_state.node_id,
        len(children),
    )
    if not children:
        raise ValueError(
            f"Parent {parent_state.node_id} has no active fractal children"
        )
    weights = [float(item.initialization_weight) for item in children]
    if any(
        not math.isfinite(value) or value <= 0.0
        for value in weights
    ):
        raise ValueError(
            f"Parent {parent_state.node_id} has invalid child weights"
        )
    if not math.isclose(
        math.fsum(weights),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            f"Parent {parent_state.node_id} child weights must sum to 1.0"
        )
    parent_level = str(
        parent_state.metadata.get("fractal_level", "L1_COUNTRY")
    )
    expected_child_index = level_index(parent_level) + 1
    for child in children:
        if child.parent_node_id != parent_state.node_id:
            raise ValueError(
                f"Child {child.node_id} parent mismatch"
            )
        if level_index(child.level) != expected_child_index:
            raise ValueError(
                f"Child {child.node_id} level {child.level} is not adjacent "
                f"to parent level {parent_level}"
            )
        if not child.active:
            raise ValueError(
                f"Child {child.node_id} must be active for initialization"
            )


def _integer_parent_value(
    *,
    variable: str,
    value: int | float | None,
) -> int | None:
    logger.info(
        "_integer_parent_value variable=%s value=%s",
        variable,
        value,
    )
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError(
            f"Additive physical stock {variable} must be finite/non-negative"
        )
    rounded = round(numeric)
    if not math.isclose(
        numeric,
        float(rounded),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            f"Additive integer physical stock {variable}={numeric} "
            "is not integer-valued"
        )
    return int(rounded)


def _largest_remainder_allocate(
    *,
    total: int,
    children: tuple[FractalTopologyNode, ...],
) -> dict[str, int]:
    logger.info(
        "_largest_remainder_allocate total=%s children=%s",
        total,
        len(children),
    )
    raw = {
        child.node_id: total * float(child.initialization_weight)
        for child in children
    }
    base = {
        child_id: math.floor(value)
        for child_id, value in raw.items()
    }
    remaining = total - sum(base.values())
    ranked = sorted(
        raw,
        key=lambda child_id: (
            -(raw[child_id] - base[child_id]),
            child_id,
        ),
    )
    result = dict(base)
    for child_id in ranked[:remaining]:
        result[child_id] += 1

    if sum(result.values()) != total:
        raise RuntimeError(
            "Largest-remainder allocation failed exact conservation"
        )
    return result


def _allocate_physical_stocks(
    *,
    parent_state: EngineState,
    children: tuple[FractalTopologyNode, ...],
    policy: dict[str, Any],
) -> tuple[
    dict[str, dict[str, int | float | None]],
    dict[str, int | None],
    dict[str, int | None],
]:
    logger.info(
        "_allocate_physical_stocks parent=%s children=%s",
        parent_state.node_id,
        len(children),
    )
    child_values = {
        child.node_id: {}
        for child in children
    }
    parent_additive: dict[str, int | None] = {}
    child_sums: dict[str, int | None] = {}

    for variable in policy["additive_integer_conserved"]:
        if variable not in parent_state.physical_stocks:
            raise KeyError(
                f"Parent {parent_state.node_id} missing physical stock {variable}"
            )
        total = _integer_parent_value(
            variable=variable,
            value=parent_state.physical_stocks[variable],
        )
        parent_additive[variable] = total
        if total is None:
            child_sums[variable] = None
            for child in children:
                child_values[child.node_id][variable] = None
            continue

        allocation = _largest_remainder_allocate(
            total=total,
            children=children,
        )
        child_sums[variable] = sum(allocation.values())
        for child in children:
            child_values[child.node_id][variable] = allocation[child.node_id]

    for variable in policy["intensive_inherit_parent"]:
        if variable not in parent_state.physical_stocks:
            raise KeyError(
                f"Parent {parent_state.node_id} missing physical stock {variable}"
            )
        value = parent_state.physical_stocks[variable]
        for child in children:
            child_values[child.node_id][variable] = value

    for variable in policy["parent_only_null"]:
        if variable not in parent_state.physical_stocks:
            raise KeyError(
                f"Parent {parent_state.node_id} missing physical stock {variable}"
            )
        for child in children:
            child_values[child.node_id][variable] = None

    return child_values, parent_additive, child_sums


def _child_metadata(
    *,
    parent_state: EngineState,
    topology_node: FractalTopologyNode,
    policy: dict[str, Any],
) -> dict[str, Any]:
    logger.info(
        "_child_metadata parent=%s child=%s",
        parent_state.node_id,
        topology_node.node_id,
    )
    metadata = dict(parent_state.metadata)
    metadata.update(
        {
            "fractal_level": topology_node.level,
            "fractal_parent_node_id": parent_state.node_id,
            "fractal_label": topology_node.label,
            "fractal_created_day": topology_node.created_day,
            "fractal_refinement_action_id": (
                topology_node.refinement_action_id
            ),
            "fractal_refinement_reason": topology_node.refinement_reason,
            "fractal_initialization_weight": (
                topology_node.initialization_weight
            ),
            "fractal_catalog_source_id": topology_node.catalog_source_id,
            "fractal_catalog_child_id": (
                topology_node.catalog_child_id
                if topology_node.catalog_child_id is not None
                else topology_node.node_id
            ),
            "fractal_lineage_generation": topology_node.lineage_generation,
            "fractal_lineage_policy_id": topology_node.lineage_policy_id,
            "fractal_runtime_node_id": topology_node.node_id,
            "fractal_initialization_weight_policy_id": (
                topology_node.initialization_weight_policy_id
            ),
            "fractal_inherited_uncertainty_policy_id": (
                topology_node.inherited_uncertainty_policy_id
            ),
            "fractal_aggregation_rule_id": (
                topology_node.aggregation_rule_id
            ),
            "fractal_parent_state_hash_at_initialization": (
                parent_state.state_hash()
            ),
            "fractal_latent_policy_id": policy["latent_policy_id"],
            "fractal_regime_policy_id": policy["regime_policy_id"],
            "fractal_metadata_policy_id": policy["metadata_policy_id"],
            "fractal_child_dynamics_active": False,
        }
    )
    return metadata


def _initialization_id(
    *,
    parent_state: EngineState,
    child_state: EngineState,
    topology_node: FractalTopologyNode,
    policy: dict[str, Any],
) -> str:
    logger.info(
        "_initialization_id parent=%s child=%s",
        parent_state.node_id,
        child_state.node_id,
    )
    digest = canonical_hash(
        {
            "parent_node_id": parent_state.node_id,
            "child_node_id": child_state.node_id,
            "day": child_state.day,
            "parent_state_hash": parent_state.state_hash(),
            "child_state_hash": child_state.state_hash(),
            "initialization_weight": topology_node.initialization_weight,
            "refinement_action_id": topology_node.refinement_action_id,
            "catalog_child_id": (
                topology_node.catalog_child_id
                if topology_node.catalog_child_id is not None
                else topology_node.node_id
            ),
            "lineage_generation": topology_node.lineage_generation,
            "lineage_policy_id": topology_node.lineage_policy_id,
            "latent_policy_id": policy["latent_policy_id"],
            "regime_policy_id": policy["regime_policy_id"],
            "metadata_policy_id": policy["metadata_policy_id"],
            "contract": "FRACTAL_CHILD_STATE_INIT_V1",
        }
    )
    return f"fractal-child-init-{digest[:24]}"


def _conservation_audit(
    *,
    parent_state: EngineState,
    children: tuple[EngineState, ...],
    parent_values: dict[str, int | None],
    child_sums: dict[str, int | None],
) -> FractalConservationAuditRecord:
    logger.info(
        "_conservation_audit parent=%s children=%s",
        parent_state.node_id,
        len(children),
    )
    conserved = parent_values == child_sums
    payload = {
        "parent_node_id": parent_state.node_id,
        "day": parent_state.day,
        "child_node_ids": sorted(item.node_id for item in children),
        "additive_parent_values": dict(sorted(parent_values.items())),
        "additive_child_sums": dict(sorted(child_sums.items())),
        "conserved": conserved,
        "contract": "FRACTAL_ADDITIVE_CONSERVATION_V1",
    }
    audit_id = f"fractal-audit-{canonical_hash(payload)[:24]}"
    return FractalConservationAuditRecord(
        audit_id=audit_id,
        parent_node_id=parent_state.node_id,
        day=parent_state.day,
        child_node_ids=tuple(payload["child_node_ids"]),
        additive_parent_values=tuple(sorted(parent_values.items())),
        additive_child_sums=tuple(sorted(child_sums.items())),
        conserved=conserved,
    )


def _advance_existing_child_state(
    *,
    state: EngineState,
    target_day: int,
) -> EngineState:
    logger.info(
        "_advance_existing_child_state child=%s from_day=%s to_day=%s",
        state.node_id,
        state.day,
        target_day,
    )
    if state.day != target_day - 1:
        raise ValueError(
            f"Child state {state.node_id} day mismatch "
            f"expected {target_day - 1}, got {state.day}"
        )
    return EngineState(
        node_id=state.node_id,
        day=target_day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes=dict(state.regimes),
        metadata=dict(state.metadata),
    )


def initialize_fractal_child_states(
    *,
    parent_states: dict[str, EngineState],
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    initialization_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    trace: TraceLedger,
) -> FractalChildInitializationResult:
    """Initialize newly materialized L2 child states with exact conservation."""
    logger.info(
        "initialize_fractal_child_states parents=%s topology_nodes=%s "
        "existing_children=%s day=%s",
        len(parent_states),
        len(topology.nodes),
        len(child_store.states),
        topology.last_committed_day,
    )
    target_day = topology.last_committed_day
    same_day_augmentation = (
        child_store.last_initialized_day == target_day
    )
    if child_store.last_initialized_day not in {
        target_day - 1,
        target_day,
    }:
        raise ValueError(
            "Fractal child-state store must be initialized through prior "
            "day or current day for same-day recursive augmentation"
        )

    policy = _validate_config(
        initialization_config=initialization_config,
        engine_state_registry=engine_state_registry,
    )
    latent_registry = extract_latent_registry(engine_state_registry)
    existing = child_store.state_map()
    active_topology = {
        item.node_id: item
        for item in topology.nodes
        if item.active
    }
    extra_existing = set(existing) - set(active_topology)
    if extra_existing:
        raise ValueError(
            f"Child-state store contains nodes absent from active topology: "
            f"{sorted(extra_existing)}"
        )

    next_states: dict[str, EngineState] = {}
    records: list[FractalChildStateInitializationRecord] = []
    audits: list[FractalConservationAuditRecord] = []

    for child_id, state in sorted(existing.items()):
        if same_day_augmentation:
            if state.day != target_day:
                raise ValueError(
                    f"Same-day child state {child_id} day mismatch: "
                    f"expected {target_day}, got {state.day}"
                )
            next_states[child_id] = state
        else:
            next_states[child_id] = _advance_existing_child_state(
                state=state,
                target_day=target_day,
            )
        trace.append(
            "fractal_child_state_retained",
            child_node_id=child_id,
            day=target_day,
            same_day_augmentation=same_day_augmentation,
            state_hash=next_states[child_id].state_hash(),
        )

    new_by_parent: dict[str, list[FractalTopologyNode]] = {}
    for child_id, topology_node in sorted(active_topology.items()):
        if child_id in existing:
            continue
        if topology_node.created_day != target_day:
            raise ValueError(
                f"Missing child state history for {child_id}: "
                f"created_day={topology_node.created_day} target_day={target_day}"
            )
        if (
            topology_node.parent_node_id not in parent_states
            and topology_node.parent_node_id not in next_states
        ):
            raise ValueError(
                f"Child {child_id} references unknown parent "
                f"{topology_node.parent_node_id}"
            )
        new_by_parent.setdefault(
            topology_node.parent_node_id,
            [],
        ).append(topology_node)

    for parent_node_id, raw_children in sorted(new_by_parent.items()):
        parent_state = (
            parent_states[parent_node_id]
            if parent_node_id in parent_states
            else next_states[parent_node_id]
        )
        if parent_state.day != target_day:
            raise ValueError(
                f"Parent {parent_node_id} day {parent_state.day} "
                f"does not match topology day {target_day}"
            )
        children = tuple(sorted(raw_children, key=lambda item: item.node_id))
        all_active_children = topology.active_children(parent_node_id)
        if tuple(item.node_id for item in children) != tuple(
            item.node_id for item in all_active_children
        ):
            raise ValueError(
                f"Parent {parent_node_id} must initialize its complete "
                "active child set atomically"
            )
        _validate_topology_children(
            parent_state=parent_state,
            children=children,
        )
        (
            physical_by_child,
            parent_additive,
            child_sums,
        ) = _allocate_physical_stocks(
            parent_state=parent_state,
            children=children,
            policy=policy,
        )

        initialized_children: list[EngineState] = []
        for topology_node in children:
            child_state = EngineState(
                node_id=topology_node.node_id,
                day=target_day,
                physical_stocks=dict(
                    sorted(
                        physical_by_child[topology_node.node_id].items()
                    )
                ),
                latents=dict(parent_state.latents),
                regimes=dict(parent_state.regimes),
                metadata=_child_metadata(
                    parent_state=parent_state,
                    topology_node=topology_node,
                    policy=policy,
                ),
            )
            child_state.validate(latent_registry)
            initialized_children.append(child_state)
            next_states[child_state.node_id] = child_state

            initialization_id = _initialization_id(
                parent_state=parent_state,
                child_state=child_state,
                topology_node=topology_node,
                policy=policy,
            )
            record = FractalChildStateInitializationRecord(
                initialization_id=initialization_id,
                parent_node_id=parent_node_id,
                child_node_id=child_state.node_id,
                day=target_day,
                initialization_weight=topology_node.initialization_weight,
                parent_state_hash=parent_state.state_hash(),
                child_state_hash=child_state.state_hash(),
                refinement_action_id=topology_node.refinement_action_id,
                catalog_source_id=topology_node.catalog_source_id,
                catalog_child_id=(
                    topology_node.catalog_child_id
                    if topology_node.catalog_child_id is not None
                    else topology_node.node_id
                ),
                lineage_generation=topology_node.lineage_generation,
                lineage_policy_id=topology_node.lineage_policy_id,
                additive_integer_variables=policy[
                    "additive_integer_conserved"
                ],
                inherited_intensive_variables=policy[
                    "intensive_inherit_parent"
                ],
                parent_only_variables=policy["parent_only_null"],
                latent_policy_id=policy["latent_policy_id"],
                regime_policy_id=policy["regime_policy_id"],
                metadata_policy_id=policy["metadata_policy_id"],
            )
            records.append(record)
            trace.append(
                "fractal_child_state_initialized",
                **record.to_dict(),
            )

        audit = _conservation_audit(
            parent_state=parent_state,
            children=tuple(initialized_children),
            parent_values=parent_additive,
            child_sums=child_sums,
        )
        if not audit.conserved:
            raise RuntimeError(
                f"Fractal additive conservation failed for {parent_node_id}"
            )
        audits.append(audit)
        trace.append(
            "fractal_conservation_audit",
            **audit.to_dict(),
        )

    expected_ids = set(active_topology)
    if set(next_states) != expected_ids:
        raise RuntimeError(
            "Child-state store does not match active fractal topology"
        )

    store = FractalChildStateStore(
        last_initialized_day=target_day,
        states=tuple(
            next_states[node_id]
            for node_id in sorted(next_states)
        ),
    )
    return FractalChildInitializationResult(
        store=store,
        initialization_records=tuple(
            sorted(records, key=lambda item: item.initialization_id)
        ),
        conservation_audits=tuple(
            sorted(audits, key=lambda item: item.audit_id)
        ),
    )
