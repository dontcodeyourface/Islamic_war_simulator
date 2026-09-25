from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_child_state import FractalChildStateStore
from .fractal_runtime import FractalRuntimePlan
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalParentChildCouplingAudit:
    audit_id: str
    day: int
    parent_node_id: str
    child_node_ids: tuple[str, ...]
    parent_context_hash: str
    aggregate_view_hash: str
    divergent_regimes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalParentChildCouplingAudit.to_dict parent=%s day=%s",
            self.parent_node_id,
            self.day,
        )
        return {
            "audit_id": self.audit_id,
            "day": self.day,
            "parent_node_id": self.parent_node_id,
            "child_node_ids": list(self.child_node_ids),
            "parent_context_hash": self.parent_context_hash,
            "aggregate_view_hash": self.aggregate_view_hash,
            "divergent_regimes": list(self.divergent_regimes),
        }


@dataclass(frozen=True)
class FractalParentChildCouplingResult:
    parent_states: dict[str, EngineState]
    child_store: FractalChildStateStore
    audits: tuple[FractalParentChildCouplingAudit, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalParentChildCouplingResult.to_dict parents=%s audits=%s",
            len(self.parent_states),
            len(self.audits),
        )
        return {
            "parent_states": {
                node_id: state.to_dict()
                for node_id, state in sorted(self.parent_states.items())
            },
            "child_store": self.child_store.to_dict(),
            "audits": [item.to_dict() for item in self.audits],
        }


def _physical_policy(
    reaggregation_config: dict[str, Any],
) -> tuple[set[str], set[str]]:
    logger.info("_physical_policy")
    policies = reaggregation_config.get("physical_stock_policies", {})
    additive = set(policies.get("additive_integer_sum", ()))
    intensive = set(
        policies.get("intensive_initialization_weighted_mean", ())
    )
    if additive & intensive:
        raise ValueError("Coupling physical policies overlap")
    return additive, intensive


def _weights(children: tuple[EngineState, ...]) -> dict[str, float]:
    logger.info("_weights children=%s", len(children))
    result: dict[str, float] = {}
    for child in children:
        raw = child.metadata.get("fractal_initialization_weight")
        if raw is None:
            raise ValueError(
                f"Child {child.node_id} lacks fractal initialization weight"
            )
        value = float(raw)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"Child {child.node_id} has invalid weight")
        result[child.node_id] = value
    if not math.isclose(math.fsum(result.values()), 1.0, abs_tol=1e-9):
        raise ValueError("Active child coupling weights must sum to 1.0")
    return result


def _parent_context(
    *,
    parent: EngineState,
    runtime_plan: FractalRuntimePlan,
) -> dict[str, Any]:
    logger.info("_parent_context parent=%s", parent.node_id)
    return {
        "policy_id": "FRACTAL_PARENT_CONTEXT_V1",
        "day": parent.day,
        "parent_node_id": parent.node_id,
        "physical_stocks": {
            variable: parent.physical_stocks[variable]
            for variable in runtime_plan.national_only_physical_stocks
        },
        "latents": {
            variable: parent.latents[variable]
            for variable in runtime_plan.national_only_latents
        },
        "regimes": {
            variable: parent.regimes[variable]
            for variable in runtime_plan.national_only_regimes
        },
    }


def _aggregate_parent_view(
    *,
    parent: EngineState,
    children: tuple[EngineState, ...],
    weights: dict[str, float],
    runtime_plan: FractalRuntimePlan,
    engine_state_registry: dict[str, Any],
    reaggregation_config: dict[str, Any],
) -> tuple[EngineState, tuple[str, ...], str]:
    logger.info(
        "_aggregate_parent_view parent=%s children=%s",
        parent.node_id,
        len(children),
    )
    additive, intensive = _physical_policy(reaggregation_config)
    regional_physical = set(runtime_plan.regionalizable_physical_stocks)
    unsupported = regional_physical - additive - intensive
    if unsupported:
        raise ValueError(
            f"Coupling lacks physical aggregation policy for {sorted(unsupported)}"
        )

    physical = dict(parent.physical_stocks)
    for variable in sorted(regional_physical):
        values = [child.physical_stocks[variable] for child in children]
        if all(value is None for value in values):
            physical[variable] = None
        elif any(value is None for value in values):
            raise ValueError(
                f"Coupling physical stock {variable} mixes null and numeric values"
            )
        elif variable in additive:
            physical[variable] = sum(int(value) for value in values)
        else:
            physical[variable] = math.fsum(
                weights[child.node_id]
                * float(child.physical_stocks[variable])
                for child in children
            )

    latent_bounds = extract_latent_registry(engine_state_registry)
    latents = dict(parent.latents)
    for variable in runtime_plan.regionalizable_latents:
        value = math.fsum(
            weights[child.node_id] * float(child.latents[variable])
            for child in children
        )
        low, high = latent_bounds[variable]
        latents[variable] = min(high, max(low, value))

    regimes = dict(parent.regimes)
    divergent: list[str] = []
    for variable in runtime_plan.regionalizable_regimes:
        observed = {str(child.regimes[variable]) for child in children}
        if len(observed) == 1:
            regimes[variable] = next(iter(observed))
        else:
            divergent.append(variable)

    aggregate_view = {
        "policy_id": "FRACTAL_CHILD_PARENT_AGGREGATE_VIEW_V1",
        "day": parent.day,
        "parent_node_id": parent.node_id,
        "child_node_ids": [child.node_id for child in children],
        "physical_stocks": {
            key: physical[key] for key in sorted(regional_physical)
        },
        "latents": {
            key: latents[key]
            for key in sorted(runtime_plan.regionalizable_latents)
        },
        "consensus_regimes": {
            key: regimes[key]
            for key in sorted(runtime_plan.regionalizable_regimes)
            if key not in divergent
        },
        "divergent_regimes": sorted(divergent),
    }
    view_hash = canonical_hash(aggregate_view)
    metadata = dict(parent.metadata)
    metadata.update(
        {
            "fractal_parent_aggregate_view": aggregate_view,
            "fractal_parent_aggregate_view_hash": view_hash,
            "fractal_parent_child_coupling_day": parent.day,
            "fractal_parent_child_coupling_policy_id": (
                "FRACTAL_PARENT_CHILD_COUPLING_V1"
            ),
        }
    )
    return (
        EngineState(
            node_id=parent.node_id,
            day=parent.day,
            physical_stocks=physical,
            latents=latents,
            regimes=regimes,
            metadata=metadata,
        ),
        tuple(sorted(divergent)),
        view_hash,
    )


def _runtime_depths(
    runtime_plan: FractalRuntimePlan,
) -> dict[str, int]:
    logger.info("_runtime_depths nodes=%s", len(runtime_plan.nodes))
    by_id = {
        item.runtime_node_id: item
        for item in runtime_plan.nodes
    }
    result: dict[str, int] = {}
    for node_id in sorted(by_id):
        depth = 0
        current = by_id[node_id]
        seen: set[str] = set()
        while current.parent_node_id is not None:
            if current.runtime_node_id in seen:
                raise ValueError(
                    f"Fractal coupling runtime ancestry cycle at {node_id}"
                )
            seen.add(current.runtime_node_id)
            parent_id = current.parent_node_id
            if parent_id not in by_id:
                raise ValueError(
                    f"Fractal coupling runtime parent missing: {parent_id}"
                )
            current = by_id[parent_id]
            depth += 1
        result[node_id] = depth
    return result


def _descendant_active_ids(
    *,
    root_id: str,
    child_map: dict[str, EngineState],
    active_ids: set[str],
) -> tuple[str, ...]:
    logger.info(
        "_descendant_active_ids root=%s active=%s",
        root_id,
        len(active_ids),
    )
    by_parent: dict[str, list[str]] = {}
    for node_id, state in child_map.items():
        parent_id = state.metadata.get("fractal_parent_node_id")
        if parent_id is not None:
            by_parent.setdefault(str(parent_id), []).append(node_id)

    found: set[str] = set()
    stack = [root_id]
    seen: set[str] = set()
    while stack:
        parent_id = stack.pop()
        if parent_id in seen:
            raise ValueError(
                f"Fractal coupling child ancestry cycle at {parent_id}"
            )
        seen.add(parent_id)
        for child_id in sorted(by_parent.get(parent_id, ())):
            if child_id in active_ids:
                found.add(child_id)
            else:
                stack.append(child_id)
    return tuple(sorted(found))


def _coupling_audit(
    *,
    parent: EngineState,
    children: tuple[EngineState, ...],
    context_hash: str,
    view_hash: str,
    divergent: tuple[str, ...],
) -> FractalParentChildCouplingAudit:
    logger.info(
        "_coupling_audit parent=%s children=%s",
        parent.node_id,
        len(children),
    )
    payload = {
        "day": parent.day,
        "parent_node_id": parent.node_id,
        "child_node_ids": [child.node_id for child in children],
        "parent_context_hash": context_hash,
        "aggregate_view_hash": view_hash,
        "divergent_regimes": list(divergent),
        "policy_id": "FRACTAL_PARENT_CHILD_COUPLING_V2",
    }
    return FractalParentChildCouplingAudit(
        audit_id=f"fractal-coupling-{canonical_hash(payload)[:24]}",
        day=parent.day,
        parent_node_id=parent.node_id,
        child_node_ids=tuple(child.node_id for child in children),
        parent_context_hash=context_hash,
        aggregate_view_hash=view_hash,
        divergent_regimes=divergent,
    )


def execute_parent_child_coupling(
    *,
    parent_states: dict[str, EngineState],
    child_store: FractalChildStateStore,
    runtime_plan: FractalRuntimePlan,
    engine_state_registry: dict[str, Any],
    reaggregation_config: dict[str, Any],
    trace: TraceLedger,
) -> FractalParentChildCouplingResult:
    """Publish national context and aggregate active descendants bottom-up."""
    logger.info(
        "execute_parent_child_coupling day=%s refined_parents=%s",
        child_store.last_initialized_day,
        len(runtime_plan.refined_parent_ids),
    )
    if child_store.last_initialized_day != runtime_plan.day + 1:
        raise ValueError(
            "Parent-child coupling expects committed next-day child states"
        )

    child_map = child_store.state_map()
    active_ids = set(runtime_plan.active_regional_node_ids)
    missing_active = active_ids - set(child_map)
    if missing_active:
        raise ValueError(
            "Parent-child coupling missing active child states: "
            f"{sorted(missing_active)}"
        )

    authority_by_id = {
        item.runtime_node_id: item
        for item in runtime_plan.nodes
    }
    unknown_child_ids = set(child_map) - set(authority_by_id)
    if unknown_child_ids:
        raise ValueError(
            "Parent-child coupling child store contains nodes absent "
            f"from runtime plan: {sorted(unknown_child_ids)}"
        )

    updated_parents = dict(parent_states)
    updated_children = dict(child_map)
    audits: list[FractalParentChildCouplingAudit] = []

    # National-only context flows directly to every deepest active descendant,
    # regardless of the number of intermediate spatial levels.
    for parent_id in runtime_plan.refined_parent_ids:
        if parent_id not in parent_states:
            raise ValueError(
                f"Refined parent {parent_id} missing from parent states"
            )
        parent = parent_states[parent_id]
        context = _parent_context(
            parent=parent,
            runtime_plan=runtime_plan,
        )
        context_hash = canonical_hash(context)
        descendants = _descendant_active_ids(
            root_id=parent_id,
            child_map=updated_children,
            active_ids=active_ids,
        )
        if not descendants:
            raise ValueError(
                f"Refined parent {parent_id} has no active descendants"
            )
        for node_id in descendants:
            child = updated_children[node_id]
            metadata = dict(child.metadata)
            metadata.update(
                {
                    "fractal_parent_context": context,
                    "fractal_parent_context_hash": context_hash,
                    "fractal_parent_context_source_node_id": parent_id,
                }
            )
            updated_children[node_id] = EngineState(
                node_id=child.node_id,
                day=child.day,
                physical_stocks=dict(child.physical_stocks),
                latents=dict(child.latents),
                regimes=dict(child.regimes),
                metadata=metadata,
            )

    # Reconstruct refined intermediate nodes from their direct children before
    # they participate in the next coarser aggregation level.
    depths = _runtime_depths(runtime_plan)
    context_ids = [
        item.runtime_node_id
        for item in runtime_plan.nodes
        if item.authority_scope == "PARENT_CONTEXT"
    ]
    for context_id in sorted(
        context_ids,
        key=lambda node_id: (-depths[node_id], node_id),
    ):
        if context_id not in updated_children:
            raise ValueError(
                f"Fractal context node {context_id} missing child state"
            )
        parent = updated_children[context_id]
        children = tuple(
            updated_children[node_id]
            for node_id in sorted(updated_children)
            if (
                updated_children[node_id].metadata.get(
                    "fractal_parent_node_id"
                )
                == context_id
            )
        )
        if not children:
            raise ValueError(
                f"Fractal context parent {context_id} has no direct children"
            )
        weights = _weights(children)
        context_hash = canonical_hash(
            {
                "policy_id": "FRACTAL_INTERMEDIATE_CONTEXT_V1",
                "parent_node_id": context_id,
                "day": parent.day,
            }
        )
        projected, divergent, view_hash = _aggregate_parent_view(
            parent=parent,
            children=children,
            weights=weights,
            runtime_plan=runtime_plan,
            engine_state_registry=engine_state_registry,
            reaggregation_config=reaggregation_config,
        )
        updated_children[context_id] = projected
        audit = _coupling_audit(
            parent=parent,
            children=children,
            context_hash=context_hash,
            view_hash=view_hash,
            divergent=divergent,
        )
        audits.append(audit)
        trace.append(
            "fractal_parent_child_coupling",
            **audit.to_dict(),
        )

    # Reconstruct each refined L1 parent from its direct L2 children. Refined
    # L2 branches now contain the aggregate produced in the previous pass.
    for parent_id in runtime_plan.refined_parent_ids:
        parent = parent_states[parent_id]
        children = tuple(
            updated_children[node_id]
            for node_id in sorted(updated_children)
            if (
                updated_children[node_id].metadata.get(
                    "fractal_parent_node_id"
                )
                == parent_id
            )
        )
        if not children:
            raise ValueError(
                f"Refined parent {parent_id} has no direct child states"
            )
        weights = _weights(children)
        context = _parent_context(
            parent=parent,
            runtime_plan=runtime_plan,
        )
        context_hash = canonical_hash(context)
        projected, divergent, view_hash = _aggregate_parent_view(
            parent=parent,
            children=children,
            weights=weights,
            runtime_plan=runtime_plan,
            engine_state_registry=engine_state_registry,
            reaggregation_config=reaggregation_config,
        )
        updated_parents[parent_id] = projected
        audit = _coupling_audit(
            parent=parent,
            children=children,
            context_hash=context_hash,
            view_hash=view_hash,
            divergent=divergent,
        )
        audits.append(audit)
        trace.append(
            "fractal_parent_child_coupling",
            **audit.to_dict(),
        )

    return FractalParentChildCouplingResult(
        parent_states=updated_parents,
        child_store=FractalChildStateStore(
            last_initialized_day=child_store.last_initialized_day,
            states=tuple(
                updated_children[node_id]
                for node_id in sorted(updated_children)
            ),
        ),
        audits=tuple(sorted(audits, key=lambda item: item.audit_id)),
    )

