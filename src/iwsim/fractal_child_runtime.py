from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .effects import DeltaProposal
from .extremism import propose_extremist_network_dynamics
from .fractal_child_state import FractalChildStateStore
from .fractal_runtime import (
    FractalRuntimePlan,
    build_runtime_resolver_context,
)
from .reciprocal import propose_reciprocal_radicalization_effects
from .recovery import propose_recovery_effects
from .resolver import ResolutionRecord, resolve_delta_proposals
from .security import propose_security_chain_dynamics
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalChildDynamicsResult:
    store: FractalChildStateStore
    proposals: tuple[DeltaProposal, ...]
    resolutions: tuple[ResolutionRecord, ...]
    executed_node_ids: tuple[str, ...]
    enabled_modules: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalChildDynamicsResult.to_dict nodes=%s proposals=%s resolutions=%s",
            len(self.executed_node_ids),
            len(self.proposals),
            len(self.resolutions),
        )
        return {
            "store": self.store.to_dict(),
            "proposals": [item.to_dict() for item in self.proposals],
            "resolutions": [item.to_dict() for item in self.resolutions],
            "executed_node_ids": list(self.executed_node_ids),
            "enabled_modules": list(self.enabled_modules),
        }


def _clone_with_runtime_metadata(
    *,
    state: EngineState,
    plan: FractalRuntimePlan,
) -> EngineState:
    logger.info(
        "_clone_with_runtime_metadata node=%s day=%s",
        state.node_id,
        state.day,
    )
    metadata = dict(state.metadata)
    metadata.update(
        {
            "fractal_child_dynamics_active": True,
            "fractal_child_runtime_policy_id": plan.policy_id,
            "fractal_child_runtime_plan_hash": plan.plan_hash(),
            "fractal_child_dynamics_applied_from_day": state.day,
            "fractal_child_dynamics_applied_to_day": state.day + 1,
        }
    )
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes=dict(state.regimes),
        metadata=metadata,
    )


def _validate_child_runtime_inputs(
    *,
    child_store: FractalChildStateStore,
    runtime_plan: FractalRuntimePlan,
) -> dict[str, EngineState]:
    logger.info(
        "_validate_child_runtime_inputs day=%s active_l2=%s",
        runtime_plan.day,
        len(runtime_plan.active_regional_node_ids),
    )
    if not runtime_plan.autonomous_child_dynamics_allowed:
        raise RuntimeError(
            "Fractal runtime plan does not allow autonomous child dynamics"
        )
    if child_store.last_initialized_day != runtime_plan.day:
        raise ValueError(
            "Fractal child runtime day mismatch: "
            f"plan={runtime_plan.day} store={child_store.last_initialized_day}"
        )

    state_map = child_store.state_map()
    expected_ids = set(runtime_plan.active_regional_node_ids)
    actual_ids = set(state_map)
    if actual_ids != expected_ids:
        raise ValueError(
            "Fractal child runtime state coverage mismatch: "
            f"missing={sorted(expected_ids - actual_ids)} "
            f"unexpected={sorted(actual_ids - expected_ids)}"
        )

    authority = {
        item.runtime_node_id: item
        for item in runtime_plan.nodes
        if item.level == "L2_REGION"
    }
    if set(authority) != expected_ids:
        raise ValueError(
            "Fractal child runtime authority coverage mismatch"
        )

    for node_id in sorted(expected_ids):
        state = state_map[node_id]
        item = authority[node_id]
        if state.day != runtime_plan.day:
            raise ValueError(
                f"Fractal child {node_id} day mismatch: "
                f"{state.day} != {runtime_plan.day}"
            )
        if not item.owns_regionalizable_state:
            raise ValueError(
                f"Fractal child {node_id} lacks regionalizable authority"
            )
        if item.owns_national_only_state:
            raise ValueError(
                f"Fractal child {node_id} may not own national-only state"
            )
    return state_map


def _validate_proposal_authority(
    *,
    proposals: tuple[DeltaProposal, ...],
    runtime_plan: FractalRuntimePlan,
) -> None:
    logger.info(
        "_validate_proposal_authority proposals=%s",
        len(proposals),
    )
    active_ids = set(runtime_plan.active_regional_node_ids)
    regionalizable = set(runtime_plan.regionalizable_latents)
    national_only = set(runtime_plan.national_only_latents)

    for proposal in proposals:
        if proposal.target_node not in active_ids:
            raise ValueError(
                f"L2 proposal {proposal.proposal_id} targets non-active child "
                f"{proposal.target_node}"
            )
        if proposal.variable in national_only:
            raise ValueError(
                f"L2 proposal {proposal.proposal_id} attempts to mutate "
                f"national-only latent {proposal.variable}"
            )
        if proposal.variable not in regionalizable:
            raise ValueError(
                f"L2 proposal {proposal.proposal_id} targets latent without "
                f"regional authority: {proposal.variable}"
            )


def execute_autonomous_l2_dynamics(
    *,
    child_store: FractalChildStateStore,
    runtime_plan: FractalRuntimePlan,
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
    enable_recovery: bool = False,
    recovery_config: dict[str, Any] | None = None,
    enable_extremist_network_dynamics: bool = False,
    extremist_network_config: dict[str, Any] | None = None,
    enable_reciprocal_radicalization: bool = False,
    reciprocal_radicalization_config: dict[str, Any] | None = None,
    enable_security_chain_dynamics: bool = False,
    security_chain_config: dict[str, Any] | None = None,
) -> FractalChildDynamicsResult:
    """Resolve the v0.26 safe endogenous modules on active L2 children.

    The returned child states intentionally remain on the beginning-of-day clock.
    The existing child-state lifecycle advances them exactly once later in the
    atomic day transaction. This prevents double clock advancement while allowing
    the resolved L2 state to flow into uncertainty/reaggregation/lifecycle code.
    """
    logger.info(
        "execute_autonomous_l2_dynamics day=%s children=%s profile=%s",
        runtime_plan.day,
        len(runtime_plan.active_regional_node_ids),
        profile,
    )
    states = _validate_child_runtime_inputs(
        child_store=child_store,
        runtime_plan=runtime_plan,
    )

    if not states:
        return FractalChildDynamicsResult(
            store=child_store,
            proposals=(),
            resolutions=(),
            executed_node_ids=(),
            enabled_modules=(),
        )

    proposals: list[DeltaProposal] = []
    enabled_modules: list[str] = []

    if enable_recovery:
        if recovery_config is None:
            raise ValueError("L2 recovery requires recovery_config")
        enabled_modules.append("bounded_recovery")
        proposals.extend(
            propose_recovery_effects(
                states=states,
                recovery_config=recovery_config,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                trace=trace,
            )
        )

    if enable_extremist_network_dynamics:
        if extremist_network_config is None:
            raise ValueError(
                "L2 extremist-network dynamics require extremist_network_config"
            )
        enabled_modules.append("extremist_network_dynamics")
        proposals.extend(
            propose_extremist_network_dynamics(
                states=states,
                network_config=extremist_network_config,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                trace=trace,
            )
        )

    if enable_reciprocal_radicalization:
        if reciprocal_radicalization_config is None:
            raise ValueError(
                "L2 reciprocal radicalization requires "
                "reciprocal_radicalization_config"
            )
        enabled_modules.append("reciprocal_radicalization")
        proposals.extend(
            propose_reciprocal_radicalization_effects(
                states=states,
                feedback_config=reciprocal_radicalization_config,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                trace=trace,
            )
        )

    if enable_security_chain_dynamics:
        if security_chain_config is None:
            raise ValueError(
                "L2 security-chain dynamics require security_chain_config"
            )
        enabled_modules.append("security_chain_dynamics")
        proposals.extend(
            propose_security_chain_dynamics(
                states=states,
                security_config=security_chain_config,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                trace=trace,
            )
        )

    proposal_tuple = tuple(
        sorted(proposals, key=lambda item: item.proposal_id)
    )
    proposal_ids = [item.proposal_id for item in proposal_tuple]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate autonomous L2 proposal IDs")

    _validate_proposal_authority(
        proposals=proposal_tuple,
        runtime_plan=runtime_plan,
    )

    runtime_context = build_runtime_resolver_context(
        plan=runtime_plan,
        node_ids=set(states),
    )
    resolution = resolve_delta_proposals(
        states=states,
        proposals=proposal_tuple,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=trace,
        runtime_context_by_node=runtime_context,
    )

    resolved_states = tuple(
        _clone_with_runtime_metadata(
            state=resolution.states[node_id],
            plan=runtime_plan,
        )
        for node_id in sorted(resolution.states)
    )
    store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=resolved_states,
    )

    trace.append(
        "fractal_child_dynamics_committed",
        day_from=runtime_plan.day,
        day_to=runtime_plan.day + 1,
        runtime_plan_hash=runtime_plan.plan_hash(),
        runtime_policy_id=runtime_plan.policy_id,
        executed_node_ids=list(sorted(states)),
        enabled_modules=list(sorted(enabled_modules)),
        proposal_ids=[item.proposal_id for item in proposal_tuple],
        resolution_ids=[item.resolution_id for item in resolution.records],
        child_store_hash_before=child_store.store_hash(),
        child_store_hash_after=store.store_hash(),
    )

    return FractalChildDynamicsResult(
        store=store,
        proposals=proposal_tuple,
        resolutions=resolution.records,
        executed_node_ids=tuple(sorted(states)),
        enabled_modules=tuple(sorted(enabled_modules)),
    )
