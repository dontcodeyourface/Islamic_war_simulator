from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .effects import DeltaProposal
from .extremism import propose_extremist_network_dynamics
from .fractal_child_state import FractalChildStateStore
from .fractal_runtime import FractalRuntimePlan
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
    recovery_proposals: tuple[DeltaProposal, ...]
    network_proposals: tuple[DeltaProposal, ...]
    reciprocal_proposals: tuple[DeltaProposal, ...]
    security_chain_proposals: tuple[DeltaProposal, ...]
    resolutions: tuple[ResolutionRecord, ...]
    state_hashes_before: tuple[tuple[str, str], ...]
    state_hashes_after: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalChildDynamicsResult.to_dict states=%s proposals=%s resolutions=%s",
            len(self.store.states),
            len(self.proposals),
            len(self.resolutions),
        )
        return {
            "store": self.store.to_dict(),
            "proposals": [item.to_dict() for item in self.proposals],
            "recovery_proposals": [
                item.to_dict() for item in self.recovery_proposals
            ],
            "network_proposals": [
                item.to_dict() for item in self.network_proposals
            ],
            "reciprocal_proposals": [
                item.to_dict() for item in self.reciprocal_proposals
            ],
            "security_chain_proposals": [
                item.to_dict() for item in self.security_chain_proposals
            ],
            "resolutions": [item.to_dict() for item in self.resolutions],
            "state_hashes_before": dict(self.state_hashes_before),
            "state_hashes_after": dict(self.state_hashes_after),
        }


def _validate_config(config: dict[str, Any]) -> dict[str, bool]:
    logger.info("_validate_config")
    mode = config.get("mode")
    if not isinstance(mode, dict):
        raise ValueError("Fractal child dynamics config requires mode")
    if mode.get("autonomous_l2_dynamics_allowed") is not True:
        raise ValueError("Autonomous L2 dynamics are disabled by config")
    if mode.get("child_clock_advance_deferred_to_child_state_commit") is not True:
        raise ValueError(
            "v0.26 requires child clock advance to remain deferred "
            "to child-state commit"
        )
    if mode.get("one_owner_resolution_pass_per_l2_runtime") is not True:
        raise ValueError(
            "v0.26 requires one owner-resolution pass for L2 proposals"
        )

    supported = config.get("supported_modules")
    if not isinstance(supported, dict):
        raise ValueError("Fractal child dynamics requires supported_modules")
    required = {
        "bounded_recovery",
        "extremist_network_dynamics",
        "reciprocal_radicalization",
        "security_chain_dynamics",
    }
    if set(supported) != required:
        raise ValueError(
            "Fractal child dynamics supported_modules mismatch: "
            f"expected={sorted(required)} actual={sorted(supported)}"
        )
    return {
        key: bool(supported[key])
        for key in sorted(supported)
    }


def _active_child_states(
    *,
    child_store: FractalChildStateStore,
    runtime_plan: FractalRuntimePlan,
) -> dict[str, EngineState]:
    logger.info(
        "_active_child_states store=%s active_plan=%s",
        len(child_store.states),
        len(runtime_plan.active_regional_node_ids),
    )
    if child_store.last_initialized_day != runtime_plan.day:
        raise ValueError(
            "Fractal child dynamics store/runtime day mismatch: "
            f"{child_store.last_initialized_day} != {runtime_plan.day}"
        )
    state_map = child_store.state_map()
    active_ids = set(runtime_plan.active_regional_node_ids)
    if set(state_map) != active_ids:
        raise ValueError(
            "Fractal child dynamics requires exact active child store: "
            f"missing={sorted(active_ids - set(state_map))} "
            f"extra={sorted(set(state_map) - active_ids)}"
        )
    return {
        node_id: state_map[node_id]
        for node_id in sorted(active_ids)
    }


def _validate_proposals(
    *,
    proposals: tuple[DeltaProposal, ...],
    runtime_plan: FractalRuntimePlan,
) -> None:
    logger.info(
        "_validate_proposals proposals=%s active_l2=%s",
        len(proposals),
        len(runtime_plan.active_regional_node_ids),
    )
    active_ids = set(runtime_plan.active_regional_node_ids)
    regionalizable = set(runtime_plan.regionalizable_latents)
    national_only = set(runtime_plan.national_only_latents)

    for proposal in proposals:
        if proposal.target_node not in active_ids:
            raise ValueError(
                f"L2 proposal {proposal.proposal_id} targets non-active node "
                f"{proposal.target_node}"
            )
        if proposal.variable in national_only:
            raise ValueError(
                f"L2 proposal {proposal.proposal_id} targets national-only "
                f"latent {proposal.variable}"
            )
        if proposal.variable not in regionalizable:
            raise ValueError(
                f"L2 proposal {proposal.proposal_id} targets latent without "
                f"regional authority: {proposal.variable}"
            )


def run_fractal_child_dynamics(
    *,
    child_store: FractalChildStateStore,
    runtime_plan: FractalRuntimePlan,
    child_dynamics_config: dict[str, Any],
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
    logger.info(
        "run_fractal_child_dynamics day=%s active_l2=%s profile=%s",
        runtime_plan.day,
        len(runtime_plan.active_regional_node_ids),
        profile,
    )
    supported = _validate_config(child_dynamics_config)
    states = _active_child_states(
        child_store=child_store,
        runtime_plan=runtime_plan,
    )
    hashes_before = tuple(
        (node_id, state.state_hash())
        for node_id, state in sorted(states.items())
    )

    if enable_recovery and not supported["bounded_recovery"]:
        raise ValueError("L2 bounded recovery is disabled by child dynamics config")
    if (
        enable_extremist_network_dynamics
        and not supported["extremist_network_dynamics"]
    ):
        raise ValueError(
            "L2 extremist-network dynamics are disabled by child dynamics config"
        )
    if (
        enable_reciprocal_radicalization
        and not supported["reciprocal_radicalization"]
    ):
        raise ValueError(
            "L2 reciprocal radicalization is disabled by child dynamics config"
        )
    if (
        enable_security_chain_dynamics
        and not supported["security_chain_dynamics"]
    ):
        raise ValueError(
            "L2 security-chain dynamics are disabled by child dynamics config"
        )

    recovery_proposals: tuple[DeltaProposal, ...] = ()
    if enable_recovery:
        if recovery_config is None:
            raise ValueError("L2 recovery requires recovery_config")
        recovery_proposals = propose_recovery_effects(
            states=states,
            recovery_config=recovery_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=trace,
        )

    network_proposals: tuple[DeltaProposal, ...] = ()
    if enable_extremist_network_dynamics:
        if extremist_network_config is None:
            raise ValueError(
                "L2 extremist-network dynamics require extremist_network_config"
            )
        network_proposals = propose_extremist_network_dynamics(
            states=states,
            network_config=extremist_network_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=trace,
        )

    reciprocal_proposals: tuple[DeltaProposal, ...] = ()
    if enable_reciprocal_radicalization:
        if reciprocal_radicalization_config is None:
            raise ValueError(
                "L2 reciprocal radicalization requires "
                "reciprocal_radicalization_config"
            )
        reciprocal_proposals = propose_reciprocal_radicalization_effects(
            states=states,
            feedback_config=reciprocal_radicalization_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=trace,
        )

    security_chain_proposals: tuple[DeltaProposal, ...] = ()
    if enable_security_chain_dynamics:
        if security_chain_config is None:
            raise ValueError(
                "L2 security-chain dynamics require security_chain_config"
            )
        security_chain_proposals = propose_security_chain_dynamics(
            states=states,
            security_config=security_chain_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=trace,
        )

    proposals = tuple(
        sorted(
            (
                *recovery_proposals,
                *network_proposals,
                *reciprocal_proposals,
                *security_chain_proposals,
            ),
            key=lambda item: item.proposal_id,
        )
    )
    _validate_proposals(
        proposals=proposals,
        runtime_plan=runtime_plan,
    )

    for proposal in proposals:
        trace.append(
            "fractal_l2_proposal",
            runtime_plan_hash=runtime_plan.plan_hash(),
            **proposal.to_dict(),
        )

    resolution = resolve_delta_proposals(
        states=states,
        proposals=proposals,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=trace,
    )

    for node_id, state in resolution.states.items():
        if state.day != runtime_plan.day:
            raise RuntimeError(
                f"v0.26 child dynamics advanced clock for {node_id}; "
                "clock advance belongs to child-state commit"
            )

    for record in resolution.records:
        trace.append(
            "fractal_l2_resolution",
            runtime_plan_hash=runtime_plan.plan_hash(),
            **record.to_dict(),
        )

    store_out = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(
            resolution.states[node_id]
            for node_id in sorted(resolution.states)
        ),
    )
    hashes_after = tuple(
        (node_id, state.state_hash())
        for node_id, state in sorted(resolution.states.items())
    )

    trace.append(
        "fractal_l2_dynamics_committed",
        day=runtime_plan.day,
        runtime_plan_hash=runtime_plan.plan_hash(),
        active_regional_node_ids=list(runtime_plan.active_regional_node_ids),
        proposal_ids=[item.proposal_id for item in proposals],
        resolution_ids=[item.resolution_id for item in resolution.records],
        state_hashes_before=dict(hashes_before),
        state_hashes_after=dict(hashes_after),
    )

    return FractalChildDynamicsResult(
        store=store_out,
        proposals=proposals,
        recovery_proposals=recovery_proposals,
        network_proposals=network_proposals,
        reciprocal_proposals=reciprocal_proposals,
        security_chain_proposals=security_chain_proposals,
        resolutions=resolution.records,
        state_hashes_before=hashes_before,
        state_hashes_after=hashes_after,
    )


def coarse_l1_regional_state_view(
    *,
    parent_states: dict[str, EngineState],
    runtime_plan: FractalRuntimePlan,
) -> dict[str, EngineState]:
    logger.info(
        "coarse_l1_regional_state_view parents=%s refined=%s",
        len(parent_states),
        len(runtime_plan.refined_parent_ids),
    )
    refined = set(runtime_plan.refined_parent_ids)
    return {
        node_id: state
        for node_id, state in sorted(parent_states.items())
        if node_id not in refined
    }


def assert_l1_proposals_respect_runtime_authority(
    *,
    proposals: tuple[DeltaProposal, ...] | list[DeltaProposal],
    runtime_plan: FractalRuntimePlan,
    source: str,
) -> None:
    logger.info(
        "assert_l1_proposals_respect_runtime_authority source=%s proposals=%s",
        source,
        len(proposals),
    )
    refined = set(runtime_plan.refined_parent_ids)
    regionalizable = set(runtime_plan.regionalizable_latents)
    for proposal in proposals:
        if (
            proposal.target_node in refined
            and proposal.variable in regionalizable
        ):
            raise RuntimeError(
                f"{source} produced regionalizable L1 delta for refined parent "
                f"{proposal.target_node}.{proposal.variable}. Cross-scale "
                "projection is not implemented in v0.26; refusing duplicate "
                "or stale parent execution."
            )
