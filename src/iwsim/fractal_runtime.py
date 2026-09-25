from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_child_state import FractalChildStateStore
from .fractal_materialization import FractalTopologyState
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalRuntimeAuthorityNode:
    runtime_node_id: str
    parent_node_id: str | None
    level: str
    catalog_node_id: str
    lineage_generation: int | None
    authority_scope: str
    owns_regionalizable_state: bool
    owns_national_only_state: bool
    execution_status: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRuntimeAuthorityNode.to_dict node=%s scope=%s",
            self.runtime_node_id,
            self.authority_scope,
        )
        return {
            "runtime_node_id": self.runtime_node_id,
            "parent_node_id": self.parent_node_id,
            "level": self.level,
            "catalog_node_id": self.catalog_node_id,
            "lineage_generation": self.lineage_generation,
            "authority_scope": self.authority_scope,
            "owns_regionalizable_state": self.owns_regionalizable_state,
            "owns_national_only_state": self.owns_national_only_state,
            "execution_status": self.execution_status,
        }


@dataclass(frozen=True)
class FractalRuntimePlan:
    day: int
    policy_id: str
    config_hash: str
    topology_hash: str
    child_store_hash: str
    autonomous_child_dynamics_allowed: bool
    nodes: tuple[FractalRuntimeAuthorityNode, ...]
    refined_parent_ids: tuple[str, ...]
    active_regional_node_ids: tuple[str, ...]
    inactive_lineage_node_ids: tuple[str, ...]
    regionalizable_physical_stocks: tuple[str, ...]
    national_only_physical_stocks: tuple[str, ...]
    regionalizable_latents: tuple[str, ...]
    national_only_latents: tuple[str, ...]
    regionalizable_regimes: tuple[str, ...]
    national_only_regimes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRuntimePlan.to_dict day=%s refined=%s active_l2=%s",
            self.day,
            len(self.refined_parent_ids),
            len(self.active_regional_node_ids),
        )
        return {
            "day": self.day,
            "policy_id": self.policy_id,
            "config_hash": self.config_hash,
            "topology_hash": self.topology_hash,
            "child_store_hash": self.child_store_hash,
            "autonomous_child_dynamics_allowed": (
                self.autonomous_child_dynamics_allowed
            ),
            "nodes": [
                item.to_dict()
                for item in sorted(
                    self.nodes,
                    key=lambda node: node.runtime_node_id,
                )
            ],
            "refined_parent_ids": list(self.refined_parent_ids),
            "active_regional_node_ids": list(self.active_regional_node_ids),
            "inactive_lineage_node_ids": list(self.inactive_lineage_node_ids),
            "authority": {
                "physical_stocks": {
                    "regionalizable": list(
                        self.regionalizable_physical_stocks
                    ),
                    "national_only": list(
                        self.national_only_physical_stocks
                    ),
                },
                "latents": {
                    "regionalizable": list(self.regionalizable_latents),
                    "national_only": list(self.national_only_latents),
                },
                "regimes": {
                    "regionalizable": list(self.regionalizable_regimes),
                    "national_only": list(self.national_only_regimes),
                },
            },
        }

    def plan_hash(self) -> str:
        logger.info(
            "FractalRuntimePlan.plan_hash day=%s policy=%s",
            self.day,
            self.policy_id,
        )
        return canonical_hash(self.to_dict())


def _partition(
    *,
    section_name: str,
    section: dict[str, Any],
    expected_ids: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    logger.info(
        "_partition section=%s expected=%s",
        section_name,
        len(expected_ids),
    )
    regional_raw = section.get("regionalizable")
    national_raw = section.get("national_only")
    if not isinstance(regional_raw, list) or not isinstance(national_raw, list):
        raise ValueError(
            f"Fractal runtime {section_name} authority must define "
            "regionalizable and national_only lists"
        )

    regional = tuple(str(item) for item in regional_raw)
    national = tuple(str(item) for item in national_raw)
    regional_set = set(regional)
    national_set = set(national)

    if len(regional) != len(regional_set):
        raise ValueError(
            f"Duplicate regionalizable authority ID in {section_name}"
        )
    if len(national) != len(national_set):
        raise ValueError(
            f"Duplicate national-only authority ID in {section_name}"
        )
    overlap = regional_set & national_set
    if overlap:
        raise ValueError(
            f"Duplicate scale authority in {section_name}: {sorted(overlap)}"
        )
    actual = regional_set | national_set
    if actual != expected_ids:
        raise ValueError(
            f"Fractal runtime {section_name} authority coverage mismatch: "
            f"missing={sorted(expected_ids - actual)} "
            f"extra={sorted(actual - expected_ids)}"
        )
    return tuple(sorted(regional)), tuple(sorted(national))


def _validate_runtime_config(
    *,
    runtime_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_validate_runtime_config")
    mode = runtime_config.get("mode")
    if not isinstance(mode, dict):
        raise ValueError("Fractal runtime config requires mode")
    if mode.get("runtime_plan_generation_allowed") is not True:
        raise ValueError(
            "Fractal runtime plan generation is disabled by runtime config"
        )
    if mode.get("topology_changes_take_effect_next_day") is not True:
        raise ValueError(
            "v0.25 requires topology changes to take effect next day"
        )

    authority = runtime_config.get("authority")
    if not isinstance(authority, dict):
        raise ValueError("Fractal runtime config requires authority")
    policy_id = str(authority.get("policy_id", "")).strip()
    if not policy_id:
        raise ValueError("Fractal runtime authority policy_id is required")

    physical_ids = {
        str(item["id"])
        for item in engine_state_registry["physical_stocks"]
    }
    latent_ids = set(extract_latent_registry(engine_state_registry))
    regime_ids = {
        str(item)
        for item in engine_state_registry["regimes"]
    }

    physical_regional, physical_national = _partition(
        section_name="physical_stocks",
        section=authority.get("physical_stocks", {}),
        expected_ids=physical_ids,
    )
    latent_regional, latent_national = _partition(
        section_name="latents",
        section=authority.get("latents", {}),
        expected_ids=latent_ids,
    )
    regime_regional, regime_national = _partition(
        section_name="regimes",
        section=authority.get("regimes", {}),
        expected_ids=regime_ids,
    )

    statuses = runtime_config.get("execution_status")
    if not isinstance(statuses, dict):
        raise ValueError("Fractal runtime config requires execution_status")
    required_statuses = {
        "coarse_l1",
        "refined_l1_parent",
        "active_l2",
        "inactive_lineage",
    }
    if set(statuses) != required_statuses:
        raise ValueError(
            "Fractal runtime execution_status keys mismatch: "
            f"expected={sorted(required_statuses)} "
            f"actual={sorted(statuses)}"
        )

    return {
        "policy_id": policy_id,
        "autonomous_child_dynamics_allowed": bool(
            mode.get("autonomous_child_dynamics_allowed", False)
        ),
        "refined_beginning_of_day_requires_autonomous_runtime": bool(
            mode.get(
                "refined_beginning_of_day_requires_autonomous_runtime",
                True,
            )
        ),
        "physical_regional": physical_regional,
        "physical_national": physical_national,
        "latent_regional": latent_regional,
        "latent_national": latent_national,
        "regime_regional": regime_regional,
        "regime_national": regime_national,
        "statuses": {
            key: str(statuses[key])
            for key in sorted(statuses)
        },
    }


def _validate_active_child_state(
    *,
    state: EngineState,
    topology_node: Any,
) -> None:
    logger.info(
        "_validate_active_child_state child=%s parent=%s",
        state.node_id,
        topology_node.parent_node_id,
    )
    if state.node_id != topology_node.node_id:
        raise ValueError(
            f"Fractal child state/topology node mismatch: "
            f"{state.node_id} != {topology_node.node_id}"
        )
    if state.metadata.get("fractal_parent_node_id") != (
        topology_node.parent_node_id
    ):
        raise ValueError(
            f"Fractal child {state.node_id} parent metadata mismatch"
        )
    if state.metadata.get("fractal_level") != "L2_REGION":
        raise ValueError(
            f"Fractal child {state.node_id} requires L2_REGION metadata"
        )

    runtime_id = state.metadata.get("fractal_runtime_node_id")
    if runtime_id is not None and runtime_id != state.node_id:
        raise ValueError(
            f"Fractal child {state.node_id} runtime identity mismatch"
        )

    catalog_id = (
        topology_node.catalog_child_id
        if topology_node.catalog_child_id is not None
        else topology_node.node_id
    )
    metadata_catalog = state.metadata.get("fractal_catalog_child_id")
    if metadata_catalog is not None and metadata_catalog != catalog_id:
        raise ValueError(
            f"Fractal child {state.node_id} catalog identity mismatch"
        )

    metadata_generation = state.metadata.get(
        "fractal_lineage_generation"
    )
    if (
        metadata_generation is not None
        and int(metadata_generation) != topology_node.lineage_generation
    ):
        raise ValueError(
            f"Fractal child {state.node_id} lineage generation mismatch"
        )


def build_fractal_runtime_plan(
    *,
    day: int,
    parent_states: dict[str, EngineState],
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    runtime_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
) -> FractalRuntimePlan:
    logger.info(
        "build_fractal_runtime_plan day=%s parents=%s topology_nodes=%s "
        "child_states=%s",
        day,
        len(parent_states),
        len(topology.nodes),
        len(child_store.states),
    )
    policy = _validate_runtime_config(
        runtime_config=runtime_config,
        engine_state_registry=engine_state_registry,
    )

    if topology.last_committed_day != day:
        raise ValueError(
            f"Fractal runtime topology day mismatch: "
            f"expected {day}, got {topology.last_committed_day}"
        )
    if child_store.last_initialized_day != day:
        raise ValueError(
            f"Fractal runtime child-store day mismatch: "
            f"expected {day}, got {child_store.last_initialized_day}"
        )

    parent_ids = set(parent_states)
    topology_parent_ids = {
        item.parent_node_id
        for item in topology.nodes
    }
    unknown_parents = topology_parent_ids - parent_ids
    if unknown_parents:
        raise ValueError(
            "Fractal runtime topology contains unknown parents: "
            f"{sorted(unknown_parents)}"
        )

    active_topology = {
        item.node_id: item
        for item in topology.nodes
        if item.active
    }
    inactive_lineage_ids = tuple(
        sorted(
            item.node_id
            for item in topology.nodes
            if not item.active
        )
    )
    child_states = child_store.state_map()

    active_ids = set(active_topology)
    child_ids = set(child_states)
    if child_ids != active_ids:
        raise ValueError(
            "Fractal runtime active child-state coverage mismatch: "
            f"missing_states={sorted(active_ids - child_ids)} "
            f"unexpected_states={sorted(child_ids - active_ids)}"
        )
    inactive_with_state = set(inactive_lineage_ids) & child_ids
    if inactive_with_state:
        raise ValueError(
            "Inactive fractal lineage must not remain in child-state store: "
            f"{sorted(inactive_with_state)}"
        )

    for child_id in sorted(active_ids):
        node = active_topology[child_id]
        if node.level != "L2_REGION":
            raise ValueError(
                f"v0.25 active child {child_id} must be L2_REGION"
            )
        _validate_active_child_state(
            state=child_states[child_id],
            topology_node=node,
        )

    nodes: list[FractalRuntimeAuthorityNode] = []
    refined_parents: list[str] = []
    active_regional_ids: list[str] = []

    for parent_id in sorted(parent_states):
        children = topology.active_children(parent_id)
        if not children:
            nodes.append(
                FractalRuntimeAuthorityNode(
                    runtime_node_id=parent_id,
                    parent_node_id=None,
                    level="L1_COUNTRY",
                    catalog_node_id=parent_id,
                    lineage_generation=None,
                    authority_scope="FULL",
                    owns_regionalizable_state=True,
                    owns_national_only_state=True,
                    execution_status=policy["statuses"]["coarse_l1"],
                )
            )
            continue

        refined_parents.append(parent_id)
        nodes.append(
            FractalRuntimeAuthorityNode(
                runtime_node_id=parent_id,
                parent_node_id=None,
                level="L1_COUNTRY",
                catalog_node_id=parent_id,
                lineage_generation=None,
                authority_scope="NATIONAL_ONLY",
                owns_regionalizable_state=False,
                owns_national_only_state=True,
                execution_status=(
                    policy["statuses"]["refined_l1_parent"]
                ),
            )
        )
        for child in children:
            active_regional_ids.append(child.node_id)
            catalog_id = (
                child.catalog_child_id
                if child.catalog_child_id is not None
                else child.node_id
            )
            nodes.append(
                FractalRuntimeAuthorityNode(
                    runtime_node_id=child.node_id,
                    parent_node_id=parent_id,
                    level="L2_REGION",
                    catalog_node_id=catalog_id,
                    lineage_generation=child.lineage_generation,
                    authority_scope="REGIONALIZABLE",
                    owns_regionalizable_state=True,
                    owns_national_only_state=False,
                    execution_status=policy["statuses"]["active_l2"],
                )
            )

    plan = FractalRuntimePlan(
        day=day,
        policy_id=policy["policy_id"],
        config_hash=canonical_hash(runtime_config),
        topology_hash=topology.topology_hash(),
        child_store_hash=child_store.store_hash(),
        autonomous_child_dynamics_allowed=(
            policy["autonomous_child_dynamics_allowed"]
        ),
        nodes=tuple(
            sorted(nodes, key=lambda item: item.runtime_node_id)
        ),
        refined_parent_ids=tuple(sorted(refined_parents)),
        active_regional_node_ids=tuple(sorted(active_regional_ids)),
        inactive_lineage_node_ids=inactive_lineage_ids,
        regionalizable_physical_stocks=policy["physical_regional"],
        national_only_physical_stocks=policy["physical_national"],
        regionalizable_latents=policy["latent_regional"],
        national_only_latents=policy["latent_national"],
        regionalizable_regimes=policy["regime_regional"],
        national_only_regimes=policy["regime_national"],
    )
    logger.info(
        "build_fractal_runtime_plan complete day=%s plan_hash=%s "
        "refined=%s active_l2=%s",
        day,
        plan.plan_hash(),
        len(plan.refined_parent_ids),
        len(plan.active_regional_node_ids),
    )
    return plan


def assert_beginning_of_day_runtime_supported(
    *,
    plan: FractalRuntimePlan,
    runtime_config: dict[str, Any],
    autonomous_execution_enabled: bool = False,
) -> None:
    logger.info(
        "assert_beginning_of_day_runtime_supported day=%s refined=%s "
        "plan_child_dynamics=%s execution_enabled=%s",
        plan.day,
        len(plan.refined_parent_ids),
        plan.autonomous_child_dynamics_allowed,
        autonomous_execution_enabled,
    )
    mode = runtime_config.get("mode", {})
    require_autonomous = bool(
        mode.get(
            "refined_beginning_of_day_requires_autonomous_runtime",
            True,
        )
    )
    if not require_autonomous or not plan.refined_parent_ids:
        return
    if not plan.autonomous_child_dynamics_allowed:
        raise RuntimeError(
            "Active L2 authority detected at beginning of day for "
            f"{list(plan.refined_parent_ids)}, but the runtime contract "
            "does not allow autonomous child dynamics."
        )
    if not autonomous_execution_enabled:
        raise RuntimeError(
            "Active L2 authority detected at beginning of day for "
            f"{list(plan.refined_parent_ids)}, but autonomous L2 execution "
            "was not enabled for this day transaction."
        )


def trace_fractal_runtime_plan(
    *,
    plan: FractalRuntimePlan,
    phase: str,
    trace: TraceLedger,
) -> None:
    logger.info(
        "trace_fractal_runtime_plan phase=%s day=%s plan_hash=%s",
        phase,
        plan.day,
        plan.plan_hash(),
    )
    trace.append(
        "fractal_runtime_plan",
        phase=phase,
        plan_hash=plan.plan_hash(),
        **plan.to_dict(),
    )
