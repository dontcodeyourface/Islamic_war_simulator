from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal, propose_event_effects
from .events import (
    EventCandidateResult,
    SimEvent,
    evaluate_interstate_incident,
    evaluate_mass_protest,
)
from .extremism import propose_extremist_network_dynamics
from .fractal import (
    FractalRefinementActionProposal,
    FractalRefinementEvaluationResult,
    FractalRefinementPersistenceState,
    evaluate_fractal_refinement,
)
from .fractal_materialization import (
    FractalMaterializationCommitRecord,
    FractalTopologyState,
    advance_fractal_topology_without_materialization,
    empty_fractal_topology,
    materialize_l1_to_l2,
    materialize_next_level,
)
from .fractal_child_state import (
    FractalChildStateInitializationRecord,
    FractalChildStateStore,
    FractalConservationAuditRecord,
    empty_fractal_child_state_store,
    initialize_fractal_child_states,
)
from .fractal_child_runtime import execute_autonomous_l2_dynamics
from .fractal_coupling import (
    FractalParentChildCouplingResult,
    execute_parent_child_coupling,
)
from .fractal_uncertainty import (
    FractalUncertaintyAuditRecord,
    FractalUncertaintyRecord,
    apply_fractal_uncertainty,
)
from .fractal_reaggregation import (
    FractalCollapseCommitRecord,
    FractalReaggregationAuditRecord,
    commit_fractal_collapses,
)
from .fractal_regional_regime import (
    FractalRegionalRegimeResult,
    FractalRegionalRegimeStore,
    bootstrap_or_validate_regional_regime_store,
    execute_regional_regime_runtime,
)
from .fractal_graph_projection import (
    FractalProjectedGraph,
    build_fractal_projected_graph,
    trace_fractal_projected_graph,
)
from .fractal_runtime import (
    FractalRuntimePlan,
    assert_beginning_of_day_runtime_supported,
    build_fractal_runtime_plan,
    build_runtime_resolver_context,
    trace_fractal_runtime_plan,
)
from .graph import CountryGraph
from .manifest import RunManifest
from .phases import PhaseEvaluationResult, PhasePersistenceState, evaluate_national_phase
from .phase_transition import (
    PhaseArbitrationRecord,
    PhaseCommitRecord,
    arbitrate_phase_proposals,
    commit_phase_transition,
    retain_phase_persistence,
)
from .recovery import propose_recovery_effects
from .reciprocal import propose_reciprocal_radicalization_effects
from .resolver import ResolutionRecord, resolve_delta_proposals
from .rng import RNGManager
from .security import propose_security_chain_dynamics
from .security_regime import (
    SecurityRegimeEvaluationResult,
    SecurityRegimePersistenceState,
    SecurityRegimeTransitionProposal,
    evaluate_security_regime,
)
from .security_regime_transition import (
    SecurityRegimeCommitRecord,
    commit_security_regime_transition,
    retain_security_regime_persistence,
)
from .security_regime_recovery import (
    SecurityRegimeRecoveryEvaluationResult,
    SecurityRegimeRecoveryPersistenceState,
    SecurityRegimeRecoveryProposal,
    evaluate_security_regime_recovery,
)
from .security_regime_recovery_transition import (
    SecurityRegimeRecoveryCommitRecord,
    commit_security_regime_recovery,
    retain_security_regime_recovery_persistence,
)
from .spillover import (
    GraphSpilloverRecord,
    SpilloverQueueState,
    empty_spillover_queue,
    evaluate_graph_spillovers,
    propose_matured_spillover_effects,
)
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyCandidate:
    candidate_key: str
    event_type: str
    actors: tuple[str, ...]
    result: EventCandidateResult

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "DailyCandidate.to_dict candidate_key=%s event_type=%s",
            self.candidate_key,
            self.event_type,
        )
        return {
            "candidate_key": self.candidate_key,
            "event_type": self.event_type,
            "actors": list(self.actors),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True)
class DayTransactionResult:
    transaction_id: str
    day_from: int
    day_to: int
    states: dict[str, EngineState]
    candidates: tuple[DailyCandidate, ...]
    events: tuple[SimEvent, ...]
    proposals: tuple[DeltaProposal, ...]
    resolutions: tuple[ResolutionRecord, ...]
    spillover_queue: SpilloverQueueState | None
    spillover_candidates: tuple[GraphSpilloverRecord, ...]
    matured_spillovers: tuple[GraphSpilloverRecord, ...]
    spillover_proposals: tuple[DeltaProposal, ...]
    network_proposals: tuple[DeltaProposal, ...]
    reciprocal_radicalization_proposals: tuple[DeltaProposal, ...]
    security_chain_proposals: tuple[DeltaProposal, ...]
    security_regime_persistence: dict[str, SecurityRegimePersistenceState]
    security_regime_evaluations: tuple[SecurityRegimeEvaluationResult, ...]
    security_regime_proposals: tuple[SecurityRegimeTransitionProposal, ...]
    security_regime_commits: tuple[SecurityRegimeCommitRecord, ...]
    security_regime_recovery_persistence: dict[
        str, SecurityRegimeRecoveryPersistenceState
    ]
    security_regime_recovery_evaluations: tuple[
        SecurityRegimeRecoveryEvaluationResult, ...
    ]
    security_regime_recovery_proposals: tuple[SecurityRegimeRecoveryProposal, ...]
    security_regime_recovery_commits: tuple[
        SecurityRegimeRecoveryCommitRecord, ...
    ]
    phase_persistence: dict[str, PhasePersistenceState]
    phase_evaluations: tuple[PhaseEvaluationResult, ...]
    phase_arbitrations: tuple[PhaseArbitrationRecord, ...]
    phase_commits: tuple[PhaseCommitRecord, ...]
    fractal_refinement_persistence: dict[
        str, FractalRefinementPersistenceState
    ]
    fractal_refinement_evaluations: tuple[
        FractalRefinementEvaluationResult, ...
    ]
    fractal_refinement_actions: tuple[
        FractalRefinementActionProposal, ...
    ]
    fractal_topology: FractalTopologyState | None
    fractal_materialization_commits: tuple[
        FractalMaterializationCommitRecord, ...
    ]
    fractal_child_state_store: FractalChildStateStore | None
    fractal_child_initialization_records: tuple[
        FractalChildStateInitializationRecord, ...
    ]
    fractal_conservation_audits: tuple[
        FractalConservationAuditRecord, ...
    ]
    fractal_uncertainty_records: tuple[
        FractalUncertaintyRecord, ...
    ]
    fractal_uncertainty_audits: tuple[
        FractalUncertaintyAuditRecord, ...
    ]
    fractal_collapse_commits: tuple[
        FractalCollapseCommitRecord, ...
    ]
    fractal_reaggregation_audits: tuple[
        FractalReaggregationAuditRecord, ...
    ]
    fractal_runtime_plan_before: FractalRuntimePlan | None
    fractal_runtime_plan_after: FractalRuntimePlan | None
    fractal_child_dynamics_proposals: tuple[DeltaProposal, ...]
    fractal_child_dynamics_resolutions: tuple[ResolutionRecord, ...]
    fractal_regional_regime_result: FractalRegionalRegimeResult | None
    fractal_projected_graph_before: FractalProjectedGraph | None
    fractal_projected_graph_after: FractalProjectedGraph | None
    fractal_parent_child_coupling_result: (
        FractalParentChildCouplingResult | None
    )

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "DayTransactionResult.to_dict transaction_id=%s day_to=%s",
            self.transaction_id,
            self.day_to,
        )
        return {
            "transaction_id": self.transaction_id,
            "day_from": self.day_from,
            "day_to": self.day_to,
            "states": {
                node_id: state.to_dict()
                for node_id, state in sorted(self.states.items())
            },
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "events": [event.to_dict() for event in self.events],
            "proposals": [proposal.to_dict() for proposal in self.proposals],
            "resolutions": [record.to_dict() for record in self.resolutions],
            "spillover_queue": (
                self.spillover_queue.to_dict()
                if self.spillover_queue is not None
                else None
            ),
            "spillover_candidates": [
                item.to_dict() for item in self.spillover_candidates
            ],
            "matured_spillovers": [
                item.to_dict() for item in self.matured_spillovers
            ],
            "spillover_proposals": [
                item.to_dict() for item in self.spillover_proposals
            ],
            "network_proposals": [
                item.to_dict() for item in self.network_proposals
            ],
            "reciprocal_radicalization_proposals": [
                item.to_dict()
                for item in self.reciprocal_radicalization_proposals
            ],
            "security_chain_proposals": [
                item.to_dict() for item in self.security_chain_proposals
            ],
            "security_regime_persistence": {
                node_id: persistence.to_dict()
                for node_id, persistence in sorted(
                    self.security_regime_persistence.items()
                )
            },
            "security_regime_evaluations": [
                item.to_dict() for item in self.security_regime_evaluations
            ],
            "security_regime_proposals": [
                item.to_dict() for item in self.security_regime_proposals
            ],
            "security_regime_commits": [
                item.to_dict() for item in self.security_regime_commits
            ],
            "security_regime_recovery_persistence": {
                node_id: item.to_dict()
                for node_id, item in sorted(
                    self.security_regime_recovery_persistence.items()
                )
            },
            "security_regime_recovery_evaluations": [
                item.to_dict()
                for item in self.security_regime_recovery_evaluations
            ],
            "security_regime_recovery_proposals": [
                item.to_dict()
                for item in self.security_regime_recovery_proposals
            ],
            "security_regime_recovery_commits": [
                item.to_dict()
                for item in self.security_regime_recovery_commits
            ],
            "phase_persistence": {
                node_id: persistence.to_dict()
                for node_id, persistence in sorted(self.phase_persistence.items())
            },
            "phase_evaluations": [
                item.to_dict() for item in self.phase_evaluations
            ],
            "phase_arbitrations": [
                item.to_dict() for item in self.phase_arbitrations
            ],
            "phase_commits": [item.to_dict() for item in self.phase_commits],
            "fractal_refinement_persistence": {
                node_id: item.to_dict()
                for node_id, item in sorted(
                    self.fractal_refinement_persistence.items()
                )
            },
            "fractal_refinement_evaluations": [
                item.to_dict()
                for item in self.fractal_refinement_evaluations
            ],
            "fractal_refinement_actions": [
                item.to_dict() for item in self.fractal_refinement_actions
            ],
            "fractal_topology": (
                self.fractal_topology.to_dict()
                if self.fractal_topology is not None
                else None
            ),
            "fractal_materialization_commits": [
                item.to_dict() for item in self.fractal_materialization_commits
            ],
            "fractal_child_state_store": (
                self.fractal_child_state_store.to_dict()
                if self.fractal_child_state_store is not None
                else None
            ),
            "fractal_child_initialization_records": [
                item.to_dict()
                for item in self.fractal_child_initialization_records
            ],
            "fractal_conservation_audits": [
                item.to_dict() for item in self.fractal_conservation_audits
            ],
            "fractal_uncertainty_records": [
                item.to_dict() for item in self.fractal_uncertainty_records
            ],
            "fractal_uncertainty_audits": [
                item.to_dict() for item in self.fractal_uncertainty_audits
            ],
            "fractal_collapse_commits": [
                item.to_dict() for item in self.fractal_collapse_commits
            ],
            "fractal_reaggregation_audits": [
                item.to_dict() for item in self.fractal_reaggregation_audits
            ],
            "fractal_runtime_plan_before": (
                self.fractal_runtime_plan_before.to_dict()
                if self.fractal_runtime_plan_before is not None
                else None
            ),
            "fractal_runtime_plan_after": (
                self.fractal_runtime_plan_after.to_dict()
                if self.fractal_runtime_plan_after is not None
                else None
            ),
            "fractal_child_dynamics_proposals": [
                item.to_dict()
                for item in self.fractal_child_dynamics_proposals
            ],
            "fractal_child_dynamics_resolutions": [
                item.to_dict()
                for item in self.fractal_child_dynamics_resolutions
            ],
            "fractal_regional_regime_result": (
                self.fractal_regional_regime_result.to_dict()
                if self.fractal_regional_regime_result is not None
                else None
            ),
            "fractal_projected_graph_before": (
                self.fractal_projected_graph_before.to_dict()
                if self.fractal_projected_graph_before is not None
                else None
            ),
            "fractal_projected_graph_after": (
                self.fractal_projected_graph_after.to_dict()
                if self.fractal_projected_graph_after is not None
                else None
            ),
            "fractal_parent_child_coupling_result": (
                self.fractal_parent_child_coupling_result.to_dict()
                if self.fractal_parent_child_coupling_result is not None
                else None
            ),
        }


def _validate_day_inputs(
    *,
    states: dict[str, EngineState],
    graph: CountryGraph,
    engine_state_registry: dict[str, Any],
) -> int:
    logger.info(
        "_validate_day_inputs states=%s graph_nodes=%s",
        len(states),
        len(graph.nodes),
    )
    graph.validate()
    graph_nodes = {node.iso3 for node in graph.nodes}
    state_nodes = set(states)
    if state_nodes != graph_nodes:
        raise ValueError(
            f"State/graph node mismatch state_nodes={sorted(state_nodes)} "
            f"graph_nodes={sorted(graph_nodes)}"
        )

    if not states:
        raise ValueError("At least one state is required")

    days = {state.day for state in states.values()}
    if len(days) != 1:
        raise ValueError(f"All states must share the same day, got {sorted(days)}")

    latent_registry = extract_latent_registry(engine_state_registry)
    for node_id, state in sorted(states.items()):
        if state.node_id != node_id:
            raise ValueError(
                f"State mapping key {node_id} does not match state.node_id={state.node_id}"
            )
        state.validate(latent_registry)

    return next(iter(days))


def _normalize_fractal_child_store_input(
    *,
    day_from: int,
    child_store: FractalChildStateStore | None,
) -> FractalChildStateStore:
    logger.info(
        "_normalize_fractal_child_store_input day_from=%s supplied=%s",
        day_from,
        child_store is not None,
    )
    if child_store is None:
        if day_from != 0:
            raise ValueError(
                "Fractal child-state store is required after day zero "
                "when child initialization is enabled"
            )
        return empty_fractal_child_state_store(day_from)
    if child_store.last_initialized_day != day_from:
        raise ValueError(
            "Fractal child-state store day mismatch: "
            f"expected {day_from}, got {child_store.last_initialized_day}"
        )
    for state in child_store.states:
        if state.day != day_from:
            raise ValueError(
                f"Fractal child state {state.node_id} day mismatch: "
                f"expected {day_from}, got {state.day}"
            )
    return child_store


def _fractal_child_state_inputs_fingerprint(
    *,
    child_store: FractalChildStateStore,
    initialization_config: dict[str, Any],
) -> dict[str, Any]:
    logger.info(
        "_fractal_child_state_inputs_fingerprint day=%s states=%s",
        child_store.last_initialized_day,
        len(child_store.states),
    )
    return {
        "child_store": child_store.to_dict(),
        "initialization_config_hash": canonical_hash(initialization_config),
    }


def _fractal_uncertainty_inputs_fingerprint(
    *,
    uncertainty_config: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_fractal_uncertainty_inputs_fingerprint")
    return {
        "uncertainty_config_hash": canonical_hash(uncertainty_config),
    }


def _fractal_reaggregation_inputs_fingerprint(
    *,
    reaggregation_config: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_fractal_reaggregation_inputs_fingerprint")
    return {
        "reaggregation_config_hash": canonical_hash(reaggregation_config),
    }


def _normalize_fractal_topology_input(
    *,
    day_from: int,
    topology: FractalTopologyState | None,
) -> FractalTopologyState:
    logger.info(
        "_normalize_fractal_topology_input day_from=%s supplied=%s",
        day_from,
        topology is not None,
    )
    if topology is None:
        if day_from != 0:
            raise ValueError(
                "Fractal topology is required after day zero when "
                "materialization is enabled"
            )
        return empty_fractal_topology(day_from)
    if topology.last_committed_day != day_from:
        raise ValueError(
            "Fractal topology day mismatch: "
            f"expected {day_from}, got {topology.last_committed_day}"
        )
    return topology


def _validate_fractal_topology_consistency(
    *,
    states: dict[str, EngineState],
    persistence: dict[str, FractalRefinementPersistenceState | None],
    topology: FractalTopologyState,
) -> None:
    logger.info(
        "_validate_fractal_topology_consistency states=%s topology_nodes=%s",
        len(states),
        len(topology.nodes),
    )
    topology_ids = {item.node_id for item in topology.nodes}
    known_parents = set(states) | topology_ids
    topology_parents = {item.parent_node_id for item in topology.nodes}
    unknown = topology_parents - known_parents
    if unknown:
        raise ValueError(
            f"Fractal topology contains unknown parents: {sorted(unknown)}"
        )

    active_l2 = {
        item.node_id: item
        for item in topology.nodes
        if item.active and item.level == "L2_REGION"
    }
    expected_persistence = set(states) | set(active_l2)
    unexpected = set(persistence) - expected_persistence
    if unexpected:
        raise ValueError(
            "Fractal refinement persistence contains inactive/unsupported "
            f"nodes: {sorted(unexpected)}"
        )

    for node_id in sorted(states):
        item = persistence.get(node_id)
        children = topology.active_children(node_id)
        if item is None:
            if children:
                raise ValueError(
                    f"Fractal topology has children for {node_id} without "
                    "refinement persistence"
                )
            continue
        if item.current_level == "L1_COUNTRY" and children:
            raise ValueError(
                f"Fractal L1 parent {node_id} cannot have active L2 children"
            )
        if item.current_level == "L2_REGION" and not children:
            raise ValueError(
                f"Fractal L1 parent {node_id} at L2 resolution requires "
                "active L2 children"
            )

    for node_id, topology_node in sorted(active_l2.items()):
        item = persistence.get(node_id)
        children = topology.active_children(node_id)
        if item is None:
            if children:
                raise ValueError(
                    f"Fractal L2 parent {node_id} has active L3 children "
                    "without refinement persistence"
                )
            if topology_node.created_day != topology.last_committed_day:
                raise ValueError(
                    f"Established L2 node {node_id} lacks refinement "
                    "persistence"
                )
            continue
        if item.current_level == "L2_REGION" and children:
            raise ValueError(
                f"Fractal L2 parent {node_id} at L2 resolution cannot "
                "have active L3 children"
            )
        if (
            item.current_level == "L3_METRO_OR_LOGISTICS_AREA"
            and not children
        ):
            raise ValueError(
                f"Fractal L2 parent {node_id} at L3 resolution requires "
                "active L3 children"
            )


def _fractal_materialization_inputs_fingerprint(
    *,
    topology: FractalTopologyState,
    materialization_config: dict[str, Any],
    region_catalog: dict[str, Any],
) -> dict[str, Any]:
    logger.info(
        "_fractal_materialization_inputs_fingerprint day=%s nodes=%s",
        topology.last_committed_day,
        len(topology.nodes),
    )
    return {
        "topology": topology.to_dict(),
        "materialization_config_hash": canonical_hash(materialization_config),
        "region_catalog_hash": canonical_hash(region_catalog),
    }


def _normalize_fractal_refinement_persistence_inputs(
    *,
    states: dict[str, EngineState],
    day_from: int,
    persistence: (
        dict[str, FractalRefinementPersistenceState | None] | None
    ),
    topology: FractalTopologyState | None = None,
) -> dict[str, FractalRefinementPersistenceState | None]:
    logger.info(
        "_normalize_fractal_refinement_persistence_inputs "
        "day_from=%s supplied=%s",
        day_from,
        persistence is not None,
    )
    active_l2 = {
        item.node_id: item
        for item in (topology.nodes if topology is not None else ())
        if item.active and item.level == "L2_REGION"
    }
    expected = set(states) | set(active_l2)

    if persistence is None:
        if day_from != 0:
            raise ValueError(
                "Fractal refinement persistence is required after day zero "
                "when fractal evaluation is enabled"
            )
        return {node_id: None for node_id in sorted(expected)}

    unexpected = set(persistence) - expected
    if unexpected:
        raise ValueError(
            "Fractal refinement persistence contains inactive/unsupported "
            f"nodes: {sorted(unexpected)}"
        )

    missing_l1 = set(states) - set(persistence)
    if missing_l1:
        raise ValueError(
            "Fractal refinement persistence missing L1 state nodes: "
            f"{sorted(missing_l1)}"
        )

    normalized: dict[str, FractalRefinementPersistenceState | None] = {}
    for node_id in sorted(expected):
        item = persistence.get(node_id)
        if item is None:
            if node_id in states:
                if day_from != 0:
                    raise ValueError(
                        f"Missing fractal refinement persistence for "
                        f"{node_id} after day zero"
                    )
            else:
                topology_node = active_l2[node_id]
                if topology_node.created_day != day_from:
                    raise ValueError(
                        f"Missing established L2 refinement persistence for "
                        f"{node_id}"
                    )
            normalized[node_id] = None
            continue
        if item.node_id != node_id:
            raise ValueError(
                f"Fractal refinement persistence node mismatch "
                f"key={node_id} value={item.node_id}"
            )
        if item.last_evaluated_day != day_from:
            raise ValueError(
                f"Fractal refinement persistence day mismatch for {node_id}: "
                f"expected {day_from}, got {item.last_evaluated_day}"
            )
        normalized[node_id] = item
    return normalized


def _fractal_refinement_inputs_fingerprint(
    *,
    persistence: dict[str, FractalRefinementPersistenceState | None],
    refinement_config: dict[str, Any],
) -> dict[str, Any]:
    logger.info(
        "_fractal_refinement_inputs_fingerprint nodes=%s",
        len(persistence),
    )
    return {
        "persistence": {
            node_id: item.to_dict() if item is not None else None
            for node_id, item in sorted(persistence.items())
        },
        "refinement_config_hash": canonical_hash(refinement_config),
    }


def _normalize_phase_persistence_inputs(
    *,
    states: dict[str, EngineState],
    day_from: int,
    phase_persistence: dict[str, PhasePersistenceState | None] | None,
) -> dict[str, PhasePersistenceState | None]:
    logger.info(
        "_normalize_phase_persistence_inputs day_from=%s supplied=%s",
        day_from,
        phase_persistence is not None,
    )
    if phase_persistence is None:
        if day_from != 0:
            raise ValueError(
                "Phase persistence is required after day zero when phase integration is enabled"
            )
        return {node_id: None for node_id in sorted(states)}

    if set(phase_persistence) != set(states):
        raise ValueError("Phase persistence nodes must equal state nodes")

    normalized: dict[str, PhasePersistenceState | None] = {}
    for node_id in sorted(states):
        persistence = phase_persistence[node_id]
        if persistence is None:
            if day_from != 0:
                raise ValueError(
                    f"Missing phase persistence for {node_id} after day zero"
                )
            normalized[node_id] = None
            continue
        if persistence.node_id != node_id:
            raise ValueError(
                f"Phase persistence node mismatch key={node_id} value={persistence.node_id}"
            )
        if persistence.last_evaluated_day != day_from:
            raise ValueError(
                f"Phase persistence day mismatch for {node_id}: "
                f"expected {day_from}, got {persistence.last_evaluated_day}"
            )
        if persistence.current_phase != states[node_id].regimes["national_phase"]:
            raise ValueError(
                f"Phase persistence phase mismatch for {node_id}: "
                f"{persistence.current_phase} != "
                f"{states[node_id].regimes['national_phase']}"
            )
        normalized[node_id] = persistence
    return normalized


def _normalize_security_regime_persistence_inputs(
    *,
    states: dict[str, EngineState],
    day_from: int,
    persistence: dict[str, SecurityRegimePersistenceState | None] | None,
) -> dict[str, SecurityRegimePersistenceState | None]:
    logger.info(
        "_normalize_security_regime_persistence_inputs day_from=%s supplied=%s",
        day_from,
        persistence is not None,
    )
    if persistence is None:
        if day_from != 0:
            raise ValueError(
                "Security regime persistence is required after day zero "
                "when the evaluator is enabled"
            )
        return {node_id: None for node_id in sorted(states)}

    if set(persistence) != set(states):
        raise ValueError("Security regime persistence nodes must equal state nodes")

    normalized: dict[str, SecurityRegimePersistenceState | None] = {}
    for node_id in sorted(states):
        item = persistence[node_id]
        if item is None:
            if day_from != 0:
                raise ValueError(
                    f"Missing security regime persistence for {node_id} after day zero"
                )
            normalized[node_id] = None
            continue
        if item.node_id != node_id:
            raise ValueError(
                f"Security regime persistence node mismatch key={node_id} "
                f"value={item.node_id}"
            )
        if item.last_evaluated_day != day_from:
            raise ValueError(
                f"Security regime persistence day mismatch for {node_id}: "
                f"expected {day_from}, got {item.last_evaluated_day}"
            )
        current = states[node_id].regimes["security_force_regime"]
        if item.current_regime != current:
            raise ValueError(
                f"Security regime persistence mismatch for {node_id}: "
                f"{item.current_regime} != {current}"
            )
        normalized[node_id] = item
    return normalized


def _normalize_security_regime_recovery_persistence_inputs(
    *,
    states: dict[str, EngineState],
    day_from: int,
    persistence: (
        dict[str, SecurityRegimeRecoveryPersistenceState | None] | None
    ),
) -> dict[str, SecurityRegimeRecoveryPersistenceState | None]:
    logger.info(
        "_normalize_security_regime_recovery_persistence_inputs "
        "day_from=%s supplied=%s",
        day_from,
        persistence is not None,
    )
    if persistence is None:
        if day_from != 0:
            raise ValueError(
                "Security regime recovery persistence is required after day zero "
                "when recovery evaluation is enabled"
            )
        return {node_id: None for node_id in sorted(states)}

    if set(persistence) != set(states):
        raise ValueError(
            "Security regime recovery persistence nodes must equal state nodes"
        )

    normalized: dict[str, SecurityRegimeRecoveryPersistenceState | None] = {}
    for node_id in sorted(states):
        item = persistence[node_id]
        if item is None:
            if day_from != 0:
                raise ValueError(
                    f"Missing security regime recovery persistence for "
                    f"{node_id} after day zero"
                )
            normalized[node_id] = None
            continue
        if item.node_id != node_id:
            raise ValueError(
                f"Security regime recovery persistence node mismatch "
                f"key={node_id} value={item.node_id}"
            )
        if item.last_evaluated_day != day_from:
            raise ValueError(
                f"Security regime recovery persistence day mismatch for "
                f"{node_id}: expected {day_from}, got {item.last_evaluated_day}"
            )
        current = states[node_id].regimes["security_force_regime"]
        if item.current_regime != current:
            raise ValueError(
                f"Security regime recovery persistence mismatch for {node_id}: "
                f"{item.current_regime} != {current}"
            )
        normalized[node_id] = item
    return normalized


def _security_regime_recovery_inputs_fingerprint(
    *,
    persistence: dict[str, SecurityRegimeRecoveryPersistenceState | None],
    recovery_config: dict[str, Any],
    transition_config: dict[str, Any] | None,
) -> dict[str, Any]:
    logger.info(
        "_security_regime_recovery_inputs_fingerprint nodes=%s",
        len(persistence),
    )
    return {
        "persistence": {
            node_id: item.to_dict() if item is not None else None
            for node_id, item in sorted(persistence.items())
        },
        "recovery_config_hash": canonical_hash(recovery_config),
        "transition_config_hash": (
            canonical_hash(transition_config)
            if transition_config is not None
            else None
        ),
    }


def _security_regime_inputs_fingerprint(
    *,
    persistence: dict[str, SecurityRegimePersistenceState | None],
    context_flags: dict[str, dict[str, bool]],
    regime_config: dict[str, Any],
    transition_config: dict[str, Any] | None,
) -> dict[str, Any]:
    logger.info(
        "_security_regime_inputs_fingerprint nodes=%s",
        len(persistence),
    )
    return {
        "persistence": {
            node_id: item.to_dict() if item is not None else None
            for node_id, item in sorted(persistence.items())
        },
        "context_flags": {
            node_id: dict(sorted(flags.items()))
            for node_id, flags in sorted(context_flags.items())
        },
        "regime_config_hash": canonical_hash(regime_config),
        "transition_config_hash": (
            canonical_hash(transition_config)
            if transition_config is not None
            else None
        ),
    }


def _normalize_spillover_queue_inputs(
    *,
    day_from: int,
    spillover_queue: SpilloverQueueState | None,
) -> SpilloverQueueState:
    logger.info(
        "_normalize_spillover_queue_inputs day_from=%s supplied=%s",
        day_from,
        spillover_queue is not None,
    )
    if spillover_queue is None:
        if day_from != 0:
            raise ValueError(
                "Spillover queue is required after day zero when graph spillover is enabled"
            )
        return empty_spillover_queue(day_from)
    if spillover_queue.last_processed_day != day_from:
        raise ValueError(
            "Spillover queue day mismatch: "
            f"expected {day_from}, got {spillover_queue.last_processed_day}"
        )
    return spillover_queue


def _phase_inputs_fingerprint(
    *,
    phase_persistence: dict[str, PhasePersistenceState | None],
    phase_context_flags: dict[str, dict[str, bool]],
    phase_config: dict[str, Any],
    phase_transition_config: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_phase_inputs_fingerprint nodes=%s", len(phase_persistence))
    return {
        "phase_persistence": {
            node_id: (
                persistence.to_dict()
                if persistence is not None
                else None
            )
            for node_id, persistence in sorted(phase_persistence.items())
        },
        "phase_context_flags": {
            node_id: dict(sorted(flags.items()))
            for node_id, flags in sorted(phase_context_flags.items())
        },
        "phase_config_hash": canonical_hash(phase_config),
        "phase_transition_config_hash": canonical_hash(phase_transition_config),
    }


def _transaction_id(
    *,
    manifest: RunManifest,
    day_from: int,
    graph: CountryGraph,
    states: dict[str, EngineState],
    phase_inputs: dict[str, Any] | None = None,
    recovery_inputs: dict[str, Any] | None = None,
    spillover_inputs: dict[str, Any] | None = None,
    network_inputs: dict[str, Any] | None = None,
    reciprocal_inputs: dict[str, Any] | None = None,
    security_inputs: dict[str, Any] | None = None,
    security_regime_inputs: dict[str, Any] | None = None,
    security_regime_recovery_inputs: dict[str, Any] | None = None,
    fractal_refinement_inputs: dict[str, Any] | None = None,
    fractal_materialization_inputs: dict[str, Any] | None = None,
    fractal_child_state_inputs: dict[str, Any] | None = None,
    fractal_uncertainty_inputs: dict[str, Any] | None = None,
    fractal_reaggregation_inputs: dict[str, Any] | None = None,
    fractal_runtime_inputs: dict[str, Any] | None = None,
    fractal_regional_regime_inputs: dict[str, Any] | None = None,
    fractal_graph_projection_inputs: dict[str, Any] | None = None,
    fractal_parent_child_coupling_inputs: dict[str, Any] | None = None,
) -> str:
    logger.info(
        "_transaction_id run_id=%s day_from=%s",
        manifest.run_id,
        day_from,
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "day_from": day_from,
            "day_to": day_from + 1,
            "graph_hash": graph.graph_hash(),
            "state_hashes": {
                node_id: state.state_hash()
                for node_id, state in sorted(states.items())
            },
            "execution_order_version": manifest.execution_order_version,
            "phase_inputs": phase_inputs,
            "recovery_inputs": recovery_inputs,
            "spillover_inputs": spillover_inputs,
            "network_inputs": network_inputs,
            "reciprocal_inputs": reciprocal_inputs,
            "security_inputs": security_inputs,
            "security_regime_inputs": security_regime_inputs,
            "security_regime_recovery_inputs": security_regime_recovery_inputs,
            "fractal_refinement_inputs": fractal_refinement_inputs,
            "fractal_materialization_inputs": fractal_materialization_inputs,
            "fractal_child_state_inputs": fractal_child_state_inputs,
            "fractal_uncertainty_inputs": fractal_uncertainty_inputs,
            "fractal_reaggregation_inputs": fractal_reaggregation_inputs,
            "fractal_runtime_inputs": fractal_runtime_inputs,
            "fractal_regional_regime_inputs": (
                fractal_regional_regime_inputs
            ),
            "fractal_graph_projection_inputs": (
                fractal_graph_projection_inputs
            ),
            "fractal_parent_child_coupling_inputs": (
                fractal_parent_child_coupling_inputs
            ),
        }
    )
    return f"daytx-{digest[:24]}"


def _validate_day_config(day_config: dict[str, Any]) -> None:
    logger.info("_validate_day_config")
    candidate_passes = day_config.get("candidate_passes")
    if not isinstance(candidate_passes, list) or not candidate_passes:
        raise ValueError("day_transaction candidate_passes must be a non-empty list")

    supported = {
        ("INTERSTATE_INCIDENT_V1", "all_graph_edges"),
        ("MASS_PROTEST_TRIGGER_V1", "all_country_nodes"),
    }
    seen: set[tuple[str, str]] = set()
    for item in candidate_passes:
        if not isinstance(item, dict):
            raise ValueError("candidate_pass entries must be mappings")
        key = (str(item.get("event_type")), str(item.get("scope")))
        if key not in supported:
            raise ValueError(f"Unsupported event pass {key}")
        if key in seen:
            raise ValueError(f"Duplicate event pass {key}")
        seen.add(key)


def _evaluate_candidates(
    *,
    day: int,
    states: dict[str, EngineState],
    graph: CountryGraph,
    day_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
    excluded_node_ids: set[str] | None = None,
) -> tuple[DailyCandidate, ...]:
    logger.info(
        "_evaluate_candidates day=%s passes=%s",
        day,
        len(day_config["candidate_passes"]),
    )
    candidates: list[DailyCandidate] = []
    excluded = excluded_node_ids or set()

    for pass_config in day_config["candidate_passes"]:
        event_type = str(pass_config["event_type"])
        scope = str(pass_config["scope"])

        if (event_type, scope) == (
            "INTERSTATE_INCIDENT_V1",
            "all_graph_edges",
        ):
            for edge in sorted(graph.edges, key=lambda item: item.edge_id()):
                if edge.a in excluded or edge.b in excluded:
                    logger.info(
                        "_evaluate_candidates skip refined L1 edge=%s",
                        edge.edge_id(),
                    )
                    continue
                state_a = states[edge.a]
                state_b = states[edge.b]
                if hasattr(edge, "edge_kind") and any(
                    edge.channel(edge.a, edge.b, channel) is None
                    for channel in (
                        "geographic_proximity",
                        "land_border",
                        "alliance_link",
                    )
                ):
                    logger.info(
                        "_evaluate_candidates skip unresolved multiscale edge=%s",
                        edge.edge_id(),
                    )
                    trace.append(
                        "regional_event_candidate_skipped",
                        day=day,
                        event_type=event_type,
                        edge_id=edge.edge_id(),
                        actors=list(sorted((edge.a, edge.b))),
                        reason="unresolved_required_structural_channel",
                    )
                    continue
                result = evaluate_interstate_incident(
                    day=day,
                    state_a=state_a,
                    state_b=state_b,
                    edge=edge,
                    parameter_registry=parameter_registry,
                    profile=profile,
                    rng=rng,
                    manifest=manifest,
                    trace=trace,
                )
                candidates.append(
                    DailyCandidate(
                        candidate_key=(
                            f"{event_type}:{edge.edge_id()}"
                        ),
                        event_type=event_type,
                        actors=tuple(sorted((edge.a, edge.b))),
                        result=result,
                    )
                )
            continue

        if (event_type, scope) == (
            "MASS_PROTEST_TRIGGER_V1",
            "all_country_nodes",
        ):
            for node_id in sorted(states):
                if node_id in excluded:
                    logger.info(
                        "_evaluate_candidates skip refined L1 node=%s",
                        node_id,
                    )
                    continue
                result = evaluate_mass_protest(
                    day=day,
                    state=states[node_id],
                    parameter_registry=parameter_registry,
                    profile=profile,
                    rng=rng,
                    manifest=manifest,
                    trace=trace,
                )
                candidates.append(
                    DailyCandidate(
                        candidate_key=f"{event_type}:{node_id}",
                        event_type=event_type,
                        actors=(node_id,),
                        result=result,
                    )
                )
            continue

        raise ValueError(f"Unsupported event pass {(event_type, scope)}")

    return tuple(candidates)


def _occurred_events(
    candidates: tuple[DailyCandidate, ...],
) -> tuple[SimEvent, ...]:
    logger.info("_occurred_events candidates=%s", len(candidates))
    events = [
        candidate.result.event
        for candidate in candidates
        if candidate.result.occurred and candidate.result.event is not None
    ]
    return tuple(sorted(events, key=lambda event: event.event_id))


def _propose_all_effects(
    *,
    events: tuple[SimEvent, ...],
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    logger.info("_propose_all_effects events=%s", len(events))
    proposals: list[DeltaProposal] = []
    for event in events:
        proposals.extend(
            propose_event_effects(
                event=event,
                states=states,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                trace=trace,
            )
        )
    return tuple(sorted(proposals, key=lambda proposal: proposal.proposal_id))


def _advance_resolved_states(
    *,
    resolved_states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
) -> dict[str, EngineState]:
    logger.info("_advance_resolved_states states=%s", len(resolved_states))
    latent_registry = extract_latent_registry(engine_state_registry)
    advanced: dict[str, EngineState] = {}
    for node_id, state in sorted(resolved_states.items()):
        next_state = state.clone_for_next_day()
        next_state.validate(latent_registry)
        advanced[node_id] = next_state
    return advanced


def _evaluate_and_commit_phases(
    *,
    states: dict[str, EngineState],
    phase_persistence: dict[str, PhasePersistenceState | None],
    phase_context_flags: dict[str, dict[str, bool]],
    phase_config: dict[str, Any],
    phase_transition_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    dict[str, EngineState],
    dict[str, PhasePersistenceState],
    tuple[PhaseEvaluationResult, ...],
    tuple[PhaseArbitrationRecord, ...],
    tuple[PhaseCommitRecord, ...],
]:
    logger.info("_evaluate_and_commit_phases states=%s", len(states))
    committed_states: dict[str, EngineState] = {}
    persistence_out: dict[str, PhasePersistenceState] = {}
    evaluations: list[PhaseEvaluationResult] = []
    arbitrations: list[PhaseArbitrationRecord] = []
    commits: list[PhaseCommitRecord] = []

    for node_id in sorted(states):
        state = states[node_id]
        evaluation = evaluate_national_phase(
            state=state,
            persistence=phase_persistence[node_id],
            context_flags=phase_context_flags.get(node_id, {}),
            phase_config=phase_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=trace,
        )
        evaluations.append(evaluation)
        arbitration = arbitrate_phase_proposals(
            proposals=evaluation.proposals,
            phase_config=phase_config,
            transition_config=phase_transition_config,
            manifest=manifest,
            trace=trace,
        )
        if arbitration is None:
            committed_states[node_id] = state
            persistence_out[node_id] = retain_phase_persistence(
                persistence=evaluation.persistence,
                trace=trace,
            )
            continue

        next_state, commit_record, persistence = commit_phase_transition(
            state=state,
            proposals=evaluation.proposals,
            arbitration=arbitration,
            transition_config=phase_transition_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=trace,
        )
        committed_states[node_id] = next_state
        persistence_out[node_id] = persistence
        arbitrations.append(arbitration)
        commits.append(commit_record)

    return (
        committed_states,
        persistence_out,
        tuple(evaluations),
        tuple(arbitrations),
        tuple(commits),
    )


def _evaluate_security_regimes(
    *,
    states: dict[str, EngineState],
    persistence: dict[str, SecurityRegimePersistenceState | None],
    context_flags: dict[str, dict[str, bool]],
    regime_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    dict[str, SecurityRegimePersistenceState],
    tuple[SecurityRegimeEvaluationResult, ...],
    tuple[SecurityRegimeTransitionProposal, ...],
]:
    logger.info("_evaluate_security_regimes states=%s", len(states))
    persistence_out: dict[str, SecurityRegimePersistenceState] = {}
    evaluations: list[SecurityRegimeEvaluationResult] = []
    proposals: list[SecurityRegimeTransitionProposal] = []

    for node_id in sorted(states):
        result = evaluate_security_regime(
            state=states[node_id],
            persistence=persistence[node_id],
            context_flags=context_flags.get(node_id, {}),
            regime_config=regime_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=trace,
        )
        persistence_out[node_id] = result.persistence
        evaluations.append(result)
        proposals.extend(result.proposals)

    return (
        persistence_out,
        tuple(evaluations),
        tuple(sorted(proposals, key=lambda item: item.proposal_id)),
    )


def _commit_security_regimes(
    *,
    states: dict[str, EngineState],
    persistence: dict[str, SecurityRegimePersistenceState],
    proposals: tuple[SecurityRegimeTransitionProposal, ...],
    transition_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    dict[str, EngineState],
    dict[str, SecurityRegimePersistenceState],
    tuple[SecurityRegimeCommitRecord, ...],
]:
    logger.info(
        "_commit_security_regimes states=%s proposals=%s",
        len(states),
        len(proposals),
    )
    proposals_by_node: dict[str, list[SecurityRegimeTransitionProposal]] = {
        node_id: [] for node_id in states
    }
    for proposal in proposals:
        if proposal.node_id not in proposals_by_node:
            raise ValueError(
                f"Security regime proposal targets unknown node {proposal.node_id}"
            )
        proposals_by_node[proposal.node_id].append(proposal)

    committed_states: dict[str, EngineState] = {}
    persistence_out: dict[str, SecurityRegimePersistenceState] = {}
    commits: list[SecurityRegimeCommitRecord] = []

    for node_id in sorted(states):
        node_proposals = sorted(
            proposals_by_node[node_id],
            key=lambda item: item.proposal_id,
        )
        if len(node_proposals) > 1:
            raise ValueError(
                f"Multiple matured security regime proposals for {node_id}"
            )

        if not node_proposals:
            committed_states[node_id] = states[node_id]
            persistence_out[node_id] = retain_security_regime_persistence(
                persistence=persistence[node_id],
                trace=trace,
            )
            continue

        committed_state, commit_record, committed_persistence = (
            commit_security_regime_transition(
                state=states[node_id],
                proposal=node_proposals[0],
                transition_config=transition_config,
                engine_state_registry=engine_state_registry,
                manifest=manifest,
                trace=trace,
            )
        )
        committed_states[node_id] = committed_state
        persistence_out[node_id] = committed_persistence
        commits.append(commit_record)

    return (
        committed_states,
        persistence_out,
        tuple(sorted(commits, key=lambda item: item.commit_id)),
    )


def _evaluate_security_regime_recoveries(
    *,
    states: dict[str, EngineState],
    persistence: dict[str, SecurityRegimeRecoveryPersistenceState | None],
    context_flags: dict[str, dict[str, bool]],
    recovery_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    escalation_commits: tuple[SecurityRegimeCommitRecord, ...],
    trace: TraceLedger,
) -> tuple[
    dict[str, SecurityRegimeRecoveryPersistenceState],
    tuple[SecurityRegimeRecoveryEvaluationResult, ...],
    tuple[SecurityRegimeRecoveryProposal, ...],
]:
    logger.info(
        "_evaluate_security_regime_recoveries states=%s commits=%s",
        len(states),
        len(escalation_commits),
    )
    committed_nodes = {item.node_id for item in escalation_commits}
    persistence_out: dict[str, SecurityRegimeRecoveryPersistenceState] = {}
    evaluations: list[SecurityRegimeRecoveryEvaluationResult] = []
    proposals: list[SecurityRegimeRecoveryProposal] = []

    for node_id in sorted(states):
        result = evaluate_security_regime_recovery(
            state=states[node_id],
            persistence=persistence[node_id],
            context_flags=context_flags.get(node_id, {}),
            recovery_config=recovery_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=trace,
            same_day_escalation_committed=node_id in committed_nodes,
        )
        persistence_out[node_id] = result.persistence
        evaluations.append(result)
        proposals.extend(result.proposals)

    return (
        persistence_out,
        tuple(evaluations),
        tuple(sorted(proposals, key=lambda item: item.proposal_id)),
    )


def _commit_security_regime_recoveries(
    *,
    states: dict[str, EngineState],
    escalation_persistence: dict[str, SecurityRegimePersistenceState],
    recovery_persistence: dict[str, SecurityRegimeRecoveryPersistenceState],
    proposals: tuple[SecurityRegimeRecoveryProposal, ...],
    transition_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    dict[str, EngineState],
    dict[str, SecurityRegimePersistenceState],
    dict[str, SecurityRegimeRecoveryPersistenceState],
    tuple[SecurityRegimeRecoveryCommitRecord, ...],
]:
    logger.info(
        "_commit_security_regime_recoveries states=%s proposals=%s",
        len(states),
        len(proposals),
    )
    proposals_by_node: dict[str, list[SecurityRegimeRecoveryProposal]] = {
        node_id: [] for node_id in states
    }
    for proposal in proposals:
        if proposal.node_id not in proposals_by_node:
            raise ValueError(
                f"Security recovery proposal targets unknown node "
                f"{proposal.node_id}"
            )
        proposals_by_node[proposal.node_id].append(proposal)

    committed_states: dict[str, EngineState] = {}
    escalation_out: dict[str, SecurityRegimePersistenceState] = {}
    recovery_out: dict[str, SecurityRegimeRecoveryPersistenceState] = {}
    commits: list[SecurityRegimeRecoveryCommitRecord] = []

    for node_id in sorted(states):
        node_proposals = sorted(
            proposals_by_node[node_id],
            key=lambda item: item.proposal_id,
        )
        if len(node_proposals) > 1:
            raise ValueError(
                f"Multiple matured security recovery proposals for {node_id}"
            )

        if not node_proposals:
            committed_states[node_id] = states[node_id]
            escalation_out[node_id] = escalation_persistence[node_id]
            recovery_out[node_id] = (
                retain_security_regime_recovery_persistence(
                    persistence=recovery_persistence[node_id],
                    trace=trace,
                )
            )
            continue

        (
            committed_state,
            commit_record,
            committed_escalation_persistence,
            committed_recovery_persistence,
        ) = commit_security_regime_recovery(
            state=states[node_id],
            proposal=node_proposals[0],
            transition_config=transition_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=trace,
        )
        committed_states[node_id] = committed_state
        escalation_out[node_id] = committed_escalation_persistence
        recovery_out[node_id] = committed_recovery_persistence
        commits.append(commit_record)

    return (
        committed_states,
        escalation_out,
        recovery_out,
        tuple(sorted(commits, key=lambda item: item.commit_id)),
    )


def _evaluate_fractal_refinements(
    *,
    states: dict[str, EngineState],
    persistence: dict[str, FractalRefinementPersistenceState | None],
    refinement_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
    excluded_node_ids: set[str] | None = None,
) -> tuple[
    dict[str, FractalRefinementPersistenceState],
    tuple[FractalRefinementEvaluationResult, ...],
    tuple[FractalRefinementActionProposal, ...],
]:
    logger.info("_evaluate_fractal_refinements states=%s", len(states))
    persistence_out: dict[str, FractalRefinementPersistenceState] = {
        node_id: item
        for node_id, item in persistence.items()
        if node_id not in states and item is not None
    }
    evaluations: list[FractalRefinementEvaluationResult] = []
    actions: list[FractalRefinementActionProposal] = []
    excluded = excluded_node_ids or set()

    unknown_excluded = excluded - set(states)
    if unknown_excluded:
        raise ValueError(
            "Fractal refinement exclusion contains unknown nodes: "
            f"{sorted(unknown_excluded)}"
        )

    for node_id in sorted(states):
        if node_id in excluded:
            prior = persistence[node_id]
            if prior is None:
                raise ValueError(
                    f"Cannot suppress fractal refinement for {node_id} "
                    "without persistence"
                )
            if prior.current_level != "L2_REGION":
                raise ValueError(
                    f"Suppressed fractal parent {node_id} must be L2_REGION"
                )
            carried = FractalRefinementPersistenceState(
                node_id=node_id,
                current_level=prior.current_level,
                last_evaluated_day=prior.last_evaluated_day,
                expand_streak=prior.expand_streak,
                collapse_streak=prior.collapse_streak,
            )
            persistence_out[node_id] = carried
            trace.append(
                "fractal_refinement_evaluation_deferred",
                node_id=node_id,
                day=states[node_id].day,
                current_level=prior.current_level,
                reason="awaiting_parent_child_coupling",
                expand_streak=prior.expand_streak,
                collapse_streak=prior.collapse_streak,
                last_evaluated_day=prior.last_evaluated_day,
            )
            continue

        result = evaluate_fractal_refinement(
            state=states[node_id],
            persistence=persistence[node_id],
            refinement_config=refinement_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=trace,
        )
        persistence_out[node_id] = result.persistence
        evaluations.append(result)
        actions.extend(result.proposals)

    return (
        persistence_out,
        tuple(evaluations),
        tuple(sorted(actions, key=lambda item: item.action_id)),
    )


def _commit_fractal_materializations(
    *,
    day: int,
    actions: tuple[FractalRefinementActionProposal, ...],
    persistence: dict[str, FractalRefinementPersistenceState],
    topology: FractalTopologyState,
    region_catalog: dict[str, Any],
    materialization_config: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    FractalTopologyState,
    dict[str, FractalRefinementPersistenceState],
    tuple[FractalMaterializationCommitRecord, ...],
]:
    logger.info(
        "_commit_fractal_materializations day=%s actions=%s",
        day,
        len(actions),
    )
    topology_out = topology
    persistence_out = dict(persistence)
    commits: list[FractalMaterializationCommitRecord] = []

    if not actions:
        if topology.last_committed_day == day:
            return topology, persistence_out, ()
        topology_out = advance_fractal_topology_without_materialization(
            topology=topology,
            day=day,
            trace=trace,
        )
        return topology_out, persistence_out, ()

    seen_parents: set[str] = set()
    for action in sorted(actions, key=lambda item: item.action_id):
        if action.node_id in seen_parents:
            raise ValueError(
                f"Multiple fractal actions for parent {action.node_id} in one day"
            )
        seen_parents.add(action.node_id)
        if action.node_id not in persistence_out:
            raise ValueError(
                f"Fractal action targets unknown persistence node {action.node_id}"
            )
        (
            topology_out,
            persistence_after,
            commit_record,
        ) = materialize_next_level(
            action=action,
            persistence=persistence_out[action.node_id],
            topology=topology_out,
            child_catalog=region_catalog,
            materialization_config=materialization_config,
            manifest=manifest,
            trace=trace,
        )
        persistence_out[action.node_id] = persistence_after
        if action.to_level == "L2_REGION":
            for child_node_id in commit_record.child_node_ids:
                if child_node_id in persistence_out:
                    raise ValueError(
                        f"New L2 child persistence already exists: "
                        f"{child_node_id}"
                    )
                persistence_out[child_node_id] = (
                    FractalRefinementPersistenceState(
                        node_id=child_node_id,
                        current_level="L2_REGION",
                        last_evaluated_day=day,
                        expand_streak=0,
                        collapse_streak=0,
                    )
                )
                trace.append(
                    "fractal_refinement_persistence_initialized",
                    node_id=child_node_id,
                    day=day,
                    current_level="L2_REGION",
                    source_action_id=action.action_id,
                )
        commits.append(commit_record)

    if topology_out.last_committed_day != day:
        raise RuntimeError(
            "Fractal topology materialization did not commit target day"
        )

    return (
        topology_out,
        persistence_out,
        tuple(sorted(commits, key=lambda item: item.commit_id)),
    )


def _checkpoint_node(
    *,
    node_id: str,
    state_before: EngineState,
    state_after: EngineState,
    events: tuple[SimEvent, ...],
    resolutions: tuple[ResolutionRecord, ...],
    spillover_proposals: tuple[DeltaProposal, ...],
    security_regime_commits: tuple[SecurityRegimeCommitRecord, ...],
    security_regime_recovery_commits: tuple[
        SecurityRegimeRecoveryCommitRecord, ...
    ],
    phase_commits: tuple[PhaseCommitRecord, ...],
    fractal_refinement_actions: tuple[FractalRefinementActionProposal, ...],
    fractal_child_initialization_records: tuple[
        FractalChildStateInitializationRecord, ...
    ],
    fractal_collapse_commits: tuple[
        FractalCollapseCommitRecord, ...
    ],
    fractal_reaggregation_audits: tuple[
        FractalReaggregationAuditRecord, ...
    ],
    manifest: RunManifest,
    trace: TraceLedger,
) -> None:
    logger.info(
        "_checkpoint_node node_id=%s day=%s",
        node_id,
        state_after.day,
    )
    node_events = tuple(
        sorted(
            event.event_id
            for event in events
            if node_id in event.actors
        )
    )
    node_resolutions = tuple(
        sorted(
            record.resolution_id
            for record in resolutions
            if record.target_node == node_id
        )
    )
    clamp_resolutions = tuple(
        sorted(
            record.resolution_id
            for record in resolutions
            if record.target_node == node_id
            and abs(record.clamp_amount) > 1e-15
        )
    )
    node_security_regime_commits = tuple(
        sorted(
            record.commit_id
            for record in security_regime_commits
            if record.node_id == node_id
        )
    )
    node_security_regime_recovery_commits = tuple(
        sorted(
            record.commit_id
            for record in security_regime_recovery_commits
            if record.node_id == node_id
        )
    )
    node_phase_commits = tuple(
        sorted(
            record.commit_id
            for record in phase_commits
            if record.node_id == node_id
        )
    )
    node_refinement_actions = tuple(
        sorted(
            item.action_id
            for item in fractal_refinement_actions
            if item.node_id == node_id
        )
    )
    node_child_initializations = tuple(
        sorted(
            item.initialization_id
            for item in fractal_child_initialization_records
            if item.parent_node_id == node_id
        )
    )
    node_collapse_commits = tuple(
        sorted(
            item.commit_id
            for item in fractal_collapse_commits
            if item.parent_node_id == node_id
        )
    )
    node_reaggregation_audits = tuple(
        sorted(
            item.audit_id
            for item in fractal_reaggregation_audits
            if item.parent_node_id == node_id
        )
    )
    node_spillovers = tuple(
        sorted(
            proposal.event_id
            for proposal in spillover_proposals
            if proposal.target_node == node_id
            and proposal.event_type == "GRAPH_SPILLOVER_V1"
        )
    )
    trace.append_daily_checkpoint(
        run_id=manifest.run_id,
        day=state_after.day,
        node_id=node_id,
        state_hash_before=state_before.state_hash(),
        state_hash_after=state_after.state_hash(),
        module_deltas=node_resolutions,
        event_ids_applied=node_events,
        spillover_ids_applied=node_spillovers,
        constraint_clamps=clamp_resolutions,
        phase_transition_ids=node_phase_commits,
        security_regime_transition_ids=node_security_regime_commits,
        security_regime_recovery_transition_ids=(
            node_security_regime_recovery_commits
        ),
        refinement_actions=node_refinement_actions,
        fractal_child_initialization_ids=node_child_initializations,
        fractal_collapse_commit_ids=node_collapse_commits,
        fractal_reaggregation_audit_ids=node_reaggregation_audits,
    )


def run_day_transaction(
    *,
    states: dict[str, EngineState],
    graph: CountryGraph,
    day_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
    enable_phase_transitions: bool = False,
    phase_config: dict[str, Any] | None = None,
    phase_transition_config: dict[str, Any] | None = None,
    phase_persistence: dict[str, PhasePersistenceState | None] | None = None,
    phase_context_flags: dict[str, dict[str, bool]] | None = None,
    enable_recovery: bool = False,
    recovery_config: dict[str, Any] | None = None,
    enable_graph_spillover: bool = False,
    spillover_config: dict[str, Any] | None = None,
    spillover_queue: SpilloverQueueState | None = None,
    enable_extremist_network_dynamics: bool = False,
    extremist_network_config: dict[str, Any] | None = None,
    enable_reciprocal_radicalization: bool = False,
    reciprocal_radicalization_config: dict[str, Any] | None = None,
    enable_security_chain_dynamics: bool = False,
    security_chain_config: dict[str, Any] | None = None,
    enable_security_regime_evaluator: bool = False,
    security_regime_config: dict[str, Any] | None = None,
    security_regime_persistence: (
        dict[str, SecurityRegimePersistenceState | None] | None
    ) = None,
    security_regime_context_flags: dict[str, dict[str, bool]] | None = None,
    enable_security_regime_commits: bool = False,
    security_regime_transition_config: dict[str, Any] | None = None,
    enable_security_regime_recovery_evaluator: bool = False,
    security_regime_recovery_config: dict[str, Any] | None = None,
    security_regime_recovery_persistence: (
        dict[str, SecurityRegimeRecoveryPersistenceState | None] | None
    ) = None,
    enable_security_regime_recovery_commits: bool = False,
    security_regime_recovery_transition_config: dict[str, Any] | None = None,
    enable_fractal_refinement_evaluator: bool = False,
    fractal_refinement_config: dict[str, Any] | None = None,
    fractal_refinement_persistence: (
        dict[str, FractalRefinementPersistenceState | None] | None
    ) = None,
    enable_fractal_materialization: bool = False,
    fractal_materialization_config: dict[str, Any] | None = None,
    fractal_region_catalog: dict[str, Any] | None = None,
    fractal_topology: FractalTopologyState | None = None,
    enable_fractal_child_state_initialization: bool = False,
    fractal_child_state_config: dict[str, Any] | None = None,
    fractal_child_state_store: FractalChildStateStore | None = None,
    enable_fractal_uncertainty: bool = False,
    fractal_uncertainty_config: dict[str, Any] | None = None,
    enable_fractal_reaggregation: bool = False,
    fractal_reaggregation_config: dict[str, Any] | None = None,
    enable_fractal_runtime_plan: bool = False,
    fractal_runtime_config: dict[str, Any] | None = None,
    enable_fractal_regional_regimes: bool = False,
    fractal_regional_regime_config: dict[str, Any] | None = None,
    fractal_regional_regime_store: FractalRegionalRegimeStore | None = None,
    fractal_regional_context_flags: (
        dict[str, dict[str, bool]] | None
    ) = None,
    enable_fractal_graph_projection: bool = False,
    fractal_graph_projection_config: dict[str, Any] | None = None,
    fractal_region_graph_catalog: dict[str, Any] | None = None,
    enable_fractal_parent_child_coupling: bool = False,
    fractal_parent_child_coupling_config: dict[str, Any] | None = None,
) -> DayTransactionResult:
    """Execute one atomic synchronous state-changing day."""
    logger.info(
        "run_day_transaction run_id=%s profile=%s states=%s",
        manifest.run_id,
        profile,
        len(states),
    )
    _validate_day_config(day_config)
    day_from = _validate_day_inputs(
        states=states,
        graph=graph,
        engine_state_registry=engine_state_registry,
    )
    day_to = day_from + 1
    normalized_phase_persistence: dict[str, PhasePersistenceState | None] = {}
    normalized_phase_context_flags = {
        node_id: dict(flags)
        for node_id, flags in (phase_context_flags or {}).items()
    }
    phase_inputs: dict[str, Any] | None = None
    recovery_inputs: dict[str, Any] | None = None
    spillover_inputs: dict[str, Any] | None = None
    network_inputs: dict[str, Any] | None = None
    reciprocal_inputs: dict[str, Any] | None = None
    security_inputs: dict[str, Any] | None = None
    security_regime_inputs: dict[str, Any] | None = None
    security_regime_recovery_inputs: dict[str, Any] | None = None
    fractal_refinement_inputs: dict[str, Any] | None = None
    fractal_materialization_inputs: dict[str, Any] | None = None
    fractal_child_state_inputs: dict[str, Any] | None = None
    fractal_uncertainty_inputs: dict[str, Any] | None = None
    fractal_reaggregation_inputs: dict[str, Any] | None = None
    fractal_runtime_inputs: dict[str, Any] | None = None
    fractal_regional_regime_inputs: dict[str, Any] | None = None
    fractal_graph_projection_inputs: dict[str, Any] | None = None
    fractal_parent_child_coupling_inputs: dict[str, Any] | None = None
    fractal_runtime_plan_before: FractalRuntimePlan | None = None
    fractal_projected_graph_before: FractalProjectedGraph | None = None
    normalized_fractal_regional_regime_store: (
        FractalRegionalRegimeStore | None
    ) = None
    normalized_fractal_regional_context_flags = {
        node_id: dict(flags)
        for node_id, flags in (
            fractal_regional_context_flags or {}
        ).items()
    }
    normalized_fractal_child_store: FractalChildStateStore | None = None
    normalized_fractal_topology: FractalTopologyState | None = None
    normalized_fractal_refinement_persistence: dict[
        str, FractalRefinementPersistenceState | None
    ] = {}
    normalized_security_regime_persistence: dict[
        str, SecurityRegimePersistenceState | None
    ] = {}
    normalized_security_regime_recovery_persistence: dict[
        str, SecurityRegimeRecoveryPersistenceState | None
    ] = {}
    normalized_security_regime_context_flags = {
        node_id: dict(flags)
        for node_id, flags in (security_regime_context_flags or {}).items()
    }
    normalized_spillover_queue: SpilloverQueueState | None = None

    if enable_fractal_reaggregation:
        if not enable_fractal_child_state_initialization:
            raise ValueError(
                "Fractal reaggregation requires child-state initialization"
            )
        if not enable_fractal_materialization:
            raise ValueError(
                "Fractal reaggregation requires fractal materialization"
            )
        if fractal_reaggregation_config is None:
            raise ValueError(
                "Fractal reaggregation requires fractal_reaggregation_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_reaggregation_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal reaggregation is disabled by the day transaction contract"
            )
        fractal_reaggregation_inputs = (
            _fractal_reaggregation_inputs_fingerprint(
                reaggregation_config=fractal_reaggregation_config,
            )
        )

    if enable_fractal_uncertainty:
        if not enable_fractal_child_state_initialization:
            raise ValueError(
                "Fractal uncertainty requires child-state initialization"
            )
        if fractal_uncertainty_config is None:
            raise ValueError(
                "Fractal uncertainty requires fractal_uncertainty_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_uncertainty_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal uncertainty is disabled by the day transaction contract"
            )
        fractal_uncertainty_inputs = (
            _fractal_uncertainty_inputs_fingerprint(
                uncertainty_config=fractal_uncertainty_config,
            )
        )

    if enable_fractal_child_state_initialization:
        if not enable_fractal_materialization:
            raise ValueError(
                "Fractal child-state initialization requires "
                "fractal materialization"
            )
        if fractal_child_state_config is None:
            raise ValueError(
                "Fractal child-state initialization requires "
                "fractal_child_state_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_child_state_initialization_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal child-state initialization is disabled by "
                "the day transaction contract"
            )
        normalized_fractal_child_store = _normalize_fractal_child_store_input(
            day_from=day_from,
            child_store=fractal_child_state_store,
        )
        fractal_child_state_inputs = (
            _fractal_child_state_inputs_fingerprint(
                child_store=normalized_fractal_child_store,
                initialization_config=fractal_child_state_config,
            )
        )

    if enable_fractal_materialization:
        if not enable_fractal_refinement_evaluator:
            raise ValueError(
                "Fractal materialization requires fractal refinement evaluator"
            )
        if fractal_materialization_config is None:
            raise ValueError(
                "Fractal materialization requires "
                "fractal_materialization_config"
            )
        if fractal_region_catalog is None:
            raise ValueError(
                "Fractal materialization requires explicit fractal_region_catalog"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_materialization_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal materialization is disabled by the day transaction contract"
            )
        normalized_fractal_topology = _normalize_fractal_topology_input(
            day_from=day_from,
            topology=fractal_topology,
        )

    if enable_fractal_refinement_evaluator:
        if fractal_refinement_config is None:
            raise ValueError(
                "Fractal refinement evaluator requires "
                "fractal_refinement_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_refinement_evaluator_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal refinement evaluator is disabled by the "
                "day transaction contract"
            )
        normalized_fractal_refinement_persistence = (
            _normalize_fractal_refinement_persistence_inputs(
                states=states,
                day_from=day_from,
                persistence=fractal_refinement_persistence,
                topology=normalized_fractal_topology,
            )
        )
        fractal_refinement_inputs = (
            _fractal_refinement_inputs_fingerprint(
                persistence=normalized_fractal_refinement_persistence,
                refinement_config=fractal_refinement_config,
            )
        )

        if enable_fractal_materialization:
            assert normalized_fractal_topology is not None
            assert fractal_materialization_config is not None
            assert fractal_region_catalog is not None
            _validate_fractal_topology_consistency(
                states=states,
                persistence=normalized_fractal_refinement_persistence,
                topology=normalized_fractal_topology,
            )
            fractal_materialization_inputs = (
                _fractal_materialization_inputs_fingerprint(
                    topology=normalized_fractal_topology,
                    materialization_config=fractal_materialization_config,
                    region_catalog=fractal_region_catalog,
                )
            )

    if enable_fractal_runtime_plan:
        if not enable_fractal_materialization:
            raise ValueError(
                "Fractal runtime planning requires fractal materialization"
            )
        if not enable_fractal_child_state_initialization:
            raise ValueError(
                "Fractal runtime planning requires child-state initialization"
            )
        if fractal_runtime_config is None:
            raise ValueError(
                "Fractal runtime planning requires fractal_runtime_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_runtime_plan_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal runtime planning is disabled by the day transaction contract"
            )
        assert normalized_fractal_topology is not None
        assert normalized_fractal_child_store is not None
        fractal_runtime_plan_before = build_fractal_runtime_plan(
            day=day_from,
            parent_states=states,
            topology=normalized_fractal_topology,
            child_store=normalized_fractal_child_store,
            runtime_config=fractal_runtime_config,
            engine_state_registry=engine_state_registry,
        )
        assert_beginning_of_day_runtime_supported(
            plan=fractal_runtime_plan_before,
            runtime_config=fractal_runtime_config,
        )
        fractal_runtime_inputs = {
            "runtime_config_hash": canonical_hash(fractal_runtime_config),
            "runtime_plan_before_hash": (
                fractal_runtime_plan_before.plan_hash()
            ),
        }

    if enable_fractal_parent_child_coupling:
        if not enable_fractal_runtime_plan:
            raise ValueError(
                "Parent-child coupling requires fractal runtime planning"
            )
        if fractal_parent_child_coupling_config is None:
            raise ValueError(
                "Parent-child coupling requires an aggregation config"
            )
        fractal_parent_child_coupling_inputs = {
            "policy_id": "FRACTAL_PARENT_CHILD_COUPLING_V1",
            "aggregation_config_hash": canonical_hash(
                fractal_parent_child_coupling_config
            ),
        }

        if fractal_runtime_plan_before.refined_parent_ids:
            if enable_graph_spillover and not enable_fractal_graph_projection:
                raise RuntimeError(
                    "Active L2 spillover execution requires "
                    "enable_fractal_graph_projection"
                )
            if enable_phase_transitions and not enable_fractal_regional_regimes:
                raise RuntimeError(
                    "Active L2 phase execution requires "
                    "enable_fractal_regional_regimes"
                )
            if (
                enable_security_regime_evaluator
                or enable_security_regime_recovery_evaluator
            ) and not enable_fractal_regional_regimes:
                raise RuntimeError(
                    "Active L2 security-regime execution requires "
                    "enable_fractal_regional_regimes"
                )

    if enable_fractal_graph_projection:
        if not enable_fractal_runtime_plan:
            raise ValueError(
                "Fractal graph projection requires runtime planning"
            )
        if fractal_graph_projection_config is None:
            raise ValueError(
                "Fractal graph projection requires "
                "fractal_graph_projection_config"
            )
        if fractal_region_graph_catalog is None:
            raise ValueError(
                "Fractal graph projection requires "
                "fractal_region_graph_catalog"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_graph_projection_allowed",
                False,
            )
        ):
            raise ValueError(
                "Fractal graph projection is disabled by the "
                "day transaction contract"
            )
        assert fractal_runtime_plan_before is not None
        fractal_projected_graph_before = (
            build_fractal_projected_graph(
                runtime_plan=fractal_runtime_plan_before,
                base_graph=graph,
                projection_config=fractal_graph_projection_config,
                regional_graph_catalog=fractal_region_graph_catalog,
            )
        )
        fractal_graph_projection_inputs = {
            "projection_config_hash": canonical_hash(
                fractal_graph_projection_config
            ),
            "regional_graph_catalog_hash": canonical_hash(
                fractal_region_graph_catalog
            ),
            "projected_graph_before_hash": (
                fractal_projected_graph_before.graph_hash()
            ),
        }

    if enable_fractal_regional_regimes:
        if not enable_fractal_runtime_plan:
            raise ValueError(
                "Regional regime runtime requires fractal runtime planning"
            )
        if fractal_regional_regime_config is None:
            raise ValueError(
                "Regional regime runtime requires "
                "fractal_regional_regime_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "fractal_regional_regime_runtime_allowed",
                False,
            )
        ):
            raise ValueError(
                "Regional regime runtime is disabled by the day transaction contract"
            )
        required_flags = {
            "phase_transitions": enable_phase_transitions,
            "security_regime_evaluator": enable_security_regime_evaluator,
            "security_regime_commits": enable_security_regime_commits,
            "security_regime_recovery_evaluator": (
                enable_security_regime_recovery_evaluator
            ),
            "security_regime_recovery_commits": (
                enable_security_regime_recovery_commits
            ),
        }
        disabled = sorted(
            name for name, enabled in required_flags.items()
            if not enabled
        )
        if disabled:
            raise ValueError(
                "Regional regime runtime requires global L1/L2 regime "
                f"features enabled: {disabled}"
            )
        required_configs = {
            "phase_config": phase_config,
            "phase_transition_config": phase_transition_config,
            "security_regime_config": security_regime_config,
            "security_regime_transition_config": (
                security_regime_transition_config
            ),
            "security_regime_recovery_config": (
                security_regime_recovery_config
            ),
            "security_regime_recovery_transition_config": (
                security_regime_recovery_transition_config
            ),
        }
        missing_configs = sorted(
            name for name, value in required_configs.items()
            if value is None
        )
        if missing_configs:
            raise ValueError(
                "Regional regime runtime missing configs: "
                f"{missing_configs}"
            )
        assert fractal_runtime_plan_before is not None
        assert normalized_fractal_child_store is not None
        active_regional_ids = (
            fractal_runtime_plan_before.active_regional_node_ids
        )
        unknown_regional_context = (
            set(normalized_fractal_regional_context_flags)
            - set(active_regional_ids)
        )
        if unknown_regional_context:
            raise ValueError(
                "Regional regime context contains unknown/inactive L2 nodes: "
                f"{sorted(unknown_regional_context)}"
            )
        normalized_fractal_regional_regime_store = (
            bootstrap_or_validate_regional_regime_store(
                child_store=normalized_fractal_child_store,
                active_node_ids=active_regional_ids,
                supplied_store=fractal_regional_regime_store,
            )
        )
        fractal_regional_regime_inputs = {
            "regional_config_hash": canonical_hash(
                fractal_regional_regime_config
            ),
            "persistence_store": (
                normalized_fractal_regional_regime_store.to_dict()
            ),
            "context_flags": {
                node_id: dict(sorted(flags.items()))
                for node_id, flags in sorted(
                    normalized_fractal_regional_context_flags.items()
                )
            },
            "phase_config_hash": canonical_hash(phase_config),
            "phase_transition_config_hash": canonical_hash(
                phase_transition_config
            ),
            "security_regime_config_hash": canonical_hash(
                security_regime_config
            ),
            "security_transition_config_hash": canonical_hash(
                security_regime_transition_config
            ),
            "security_recovery_config_hash": canonical_hash(
                security_regime_recovery_config
            ),
            "security_recovery_transition_config_hash": canonical_hash(
                security_regime_recovery_transition_config
            ),
        }

    if enable_security_regime_recovery_commits:
        if not enable_security_regime_recovery_evaluator:
            raise ValueError(
                "Security regime recovery commits require recovery evaluator"
            )
        if security_regime_recovery_transition_config is None:
            raise ValueError(
                "Security regime recovery commits require "
                "security_regime_recovery_transition_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "security_regime_recovery_commit_allowed",
                False,
            )
        ):
            raise ValueError(
                "Security regime recovery commit is disabled by the "
                "day transaction contract"
            )

    if enable_security_regime_recovery_evaluator:
        if not enable_security_regime_evaluator or not enable_security_regime_commits:
            raise ValueError(
                "Security regime recovery evaluator requires escalation "
                "evaluator and commit to establish same-day precedence"
            )
        if security_regime_recovery_config is None:
            raise ValueError(
                "Security regime recovery evaluator requires "
                "security_regime_recovery_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "security_regime_recovery_evaluator_allowed",
                False,
            )
        ):
            raise ValueError(
                "Security regime recovery evaluator is disabled by the "
                "day transaction contract"
            )
        normalized_security_regime_recovery_persistence = (
            _normalize_security_regime_recovery_persistence_inputs(
                states=states,
                day_from=day_from,
                persistence=security_regime_recovery_persistence,
            )
        )
        security_regime_recovery_inputs = (
            _security_regime_recovery_inputs_fingerprint(
                persistence=normalized_security_regime_recovery_persistence,
                recovery_config=security_regime_recovery_config,
                transition_config=(
                    security_regime_recovery_transition_config
                    if enable_security_regime_recovery_commits
                    else None
                ),
            )
        )

    if enable_security_regime_commits:
        if not enable_security_regime_evaluator:
            raise ValueError(
                "Security regime commits require security regime evaluator"
            )
        if security_regime_transition_config is None:
            raise ValueError(
                "Security regime commits require security_regime_transition_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "security_regime_commit_allowed",
                False,
            )
        ):
            raise ValueError(
                "Security regime commit is disabled by the day transaction contract"
            )

    if enable_security_regime_evaluator:
        if security_regime_config is None:
            raise ValueError(
                "Security regime evaluator requires security_regime_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "security_regime_evaluator_allowed",
                False,
            )
        ):
            raise ValueError(
                "Security regime evaluator is disabled by the day transaction contract"
            )
        normalized_security_regime_persistence = (
            _normalize_security_regime_persistence_inputs(
                states=states,
                day_from=day_from,
                persistence=security_regime_persistence,
            )
        )
        unknown_security_context_nodes = (
            set(normalized_security_regime_context_flags) - set(states)
        )
        if unknown_security_context_nodes:
            raise ValueError(
                "Unknown security regime context nodes: "
                f"{sorted(unknown_security_context_nodes)}"
            )
        security_regime_inputs = _security_regime_inputs_fingerprint(
            persistence=normalized_security_regime_persistence,
            context_flags=normalized_security_regime_context_flags,
            regime_config=security_regime_config,
            transition_config=(
                security_regime_transition_config
                if enable_security_regime_commits
                else None
            ),
        )

    if enable_security_chain_dynamics:
        if security_chain_config is None:
            raise ValueError(
                "Security-chain integration requires security_chain_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "security_chain_dynamics_allowed",
                False,
            )
        ):
            raise ValueError(
                "Security-chain dynamics are disabled by the day transaction contract"
            )
        security_inputs = {
            "security_chain_config_hash": canonical_hash(
                security_chain_config
            ),
        }

    if enable_reciprocal_radicalization:
        if reciprocal_radicalization_config is None:
            raise ValueError(
                "Reciprocal-radicalization integration requires "
                "reciprocal_radicalization_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "reciprocal_radicalization_allowed",
                False,
            )
        ):
            raise ValueError(
                "Reciprocal radicalization is disabled by the day transaction contract"
            )
        reciprocal_inputs = {
            "reciprocal_radicalization_config_hash": canonical_hash(
                reciprocal_radicalization_config
            ),
        }

    if enable_extremist_network_dynamics:
        if extremist_network_config is None:
            raise ValueError(
                "Extremist-network integration requires extremist_network_config"
            )
        if not bool(
            day_config.get("mode", {}).get(
                "extremist_network_dynamics_allowed",
                False,
            )
        ):
            raise ValueError(
                "Extremist-network dynamics are disabled by the day transaction contract"
            )
        network_inputs = {
            "extremist_network_config_hash": canonical_hash(
                extremist_network_config
            ),
        }

    if enable_graph_spillover:
        if spillover_config is None:
            raise ValueError("Graph spillover integration requires spillover_config")
        if not bool(
            day_config.get("mode", {}).get("graph_spillover_trace_allowed", False)
        ):
            raise ValueError(
                "Graph spillover trace is disabled by the day transaction contract"
            )
        if bool(spillover_config.get("mode", {}).get("state_effects_allowed", False)):
            if not bool(
                day_config.get("mode", {}).get("graph_spillover_effects_allowed", False)
            ):
                raise ValueError(
                    "Graph spillover effects are disabled by the day transaction contract"
                )
        normalized_spillover_queue = _normalize_spillover_queue_inputs(
            day_from=day_from,
            spillover_queue=spillover_queue,
        )
        spillover_inputs = {
            "spillover_config_hash": canonical_hash(spillover_config),
            "spillover_queue": normalized_spillover_queue.to_dict(),
        }

    if enable_recovery:
        if recovery_config is None:
            raise ValueError("Recovery integration requires recovery_config")
        if not bool(day_config.get("mode", {}).get("recovery_allowed", False)):
            raise ValueError("Recovery is disabled by the day transaction contract")
        recovery_inputs = {
            "recovery_config_hash": canonical_hash(recovery_config),
        }

    if enable_phase_transitions:
        if phase_config is None or phase_transition_config is None:
            raise ValueError(
                "Phase integration requires phase_config and phase_transition_config"
            )
        normalized_phase_persistence = _normalize_phase_persistence_inputs(
            states=states,
            day_from=day_from,
            phase_persistence=phase_persistence,
        )
        unknown_context_nodes = (
            set(normalized_phase_context_flags) - set(states)
        )
        if unknown_context_nodes:
            raise ValueError(
                f"Unknown phase context nodes: {sorted(unknown_context_nodes)}"
            )
        phase_inputs = _phase_inputs_fingerprint(
            phase_persistence=normalized_phase_persistence,
            phase_context_flags=normalized_phase_context_flags,
            phase_config=phase_config,
            phase_transition_config=phase_transition_config,
        )

    transaction_id = _transaction_id(
        manifest=manifest,
        day_from=day_from,
        graph=graph,
        states=states,
        phase_inputs=phase_inputs,
        recovery_inputs=recovery_inputs,
        spillover_inputs=spillover_inputs,
        network_inputs=network_inputs,
        reciprocal_inputs=reciprocal_inputs,
        security_inputs=security_inputs,
        security_regime_inputs=security_regime_inputs,
        security_regime_recovery_inputs=security_regime_recovery_inputs,
        fractal_refinement_inputs=fractal_refinement_inputs,
        fractal_materialization_inputs=fractal_materialization_inputs,
        fractal_child_state_inputs=fractal_child_state_inputs,
        fractal_uncertainty_inputs=fractal_uncertainty_inputs,
        fractal_reaggregation_inputs=fractal_reaggregation_inputs,
        fractal_runtime_inputs=fractal_runtime_inputs,
        fractal_regional_regime_inputs=(
            fractal_regional_regime_inputs
        ),
        fractal_graph_projection_inputs=(
            fractal_graph_projection_inputs
        ),
        fractal_parent_child_coupling_inputs=(
            fractal_parent_child_coupling_inputs
        ),
    )

    working_rng = rng.clone()
    staged_trace = TraceLedger()
    staged_trace.append(
        "day_transaction_started",
        run_id=manifest.run_id,
        transaction_id=transaction_id,
        day_from=day_from,
        day_to=day_to,
        graph_hash=graph.graph_hash(),
        state_hashes_before={
            node_id: state.state_hash()
            for node_id, state in sorted(states.items())
        },
        fractal_runtime_plan_before_hash=(
            fractal_runtime_plan_before.plan_hash()
            if fractal_runtime_plan_before is not None
            else None
        ),
    )
    if fractal_runtime_plan_before is not None:
        trace_fractal_runtime_plan(
            plan=fractal_runtime_plan_before,
            phase="BEGINNING_OF_DAY",
            trace=staged_trace,
        )
    if fractal_projected_graph_before is not None:
        trace_fractal_projected_graph(
            graph=fractal_projected_graph_before,
            phase="BEGINNING_OF_DAY",
            trace=staged_trace,
        )

    fractal_child_dynamics_proposals: tuple[DeltaProposal, ...] = ()
    fractal_child_dynamics_resolutions: tuple[ResolutionRecord, ...] = ()
    refined_parent_ids: set[str] = set()
    l1_regional_execution_states = states

    if (
        fractal_runtime_plan_before is not None
        and fractal_runtime_plan_before.refined_parent_ids
    ):
        assert normalized_fractal_child_store is not None
        refined_parent_ids = set(
            fractal_runtime_plan_before.refined_parent_ids
        )
        l1_regional_execution_states = {
            node_id: state
            for node_id, state in sorted(states.items())
            if node_id not in refined_parent_ids
        }
        child_dynamics = execute_autonomous_l2_dynamics(
            child_store=normalized_fractal_child_store,
            runtime_plan=fractal_runtime_plan_before,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=staged_trace,
            enable_recovery=enable_recovery,
            recovery_config=recovery_config,
            enable_extremist_network_dynamics=(
                enable_extremist_network_dynamics
            ),
            extremist_network_config=extremist_network_config,
            enable_reciprocal_radicalization=(
                enable_reciprocal_radicalization
            ),
            reciprocal_radicalization_config=(
                reciprocal_radicalization_config
            ),
            enable_security_chain_dynamics=(
                enable_security_chain_dynamics
            ),
            security_chain_config=security_chain_config,
        )
        normalized_fractal_child_store = child_dynamics.store
        fractal_child_dynamics_proposals = child_dynamics.proposals
        fractal_child_dynamics_resolutions = child_dynamics.resolutions

    regional_execution_states = dict(l1_regional_execution_states)
    if normalized_fractal_child_store is not None and refined_parent_ids:
        child_state_map = normalized_fractal_child_store.state_map()
        active_child_ids = (
            set(fractal_runtime_plan_before.active_regional_node_ids)
            if fractal_runtime_plan_before is not None
            else set()
        )
        missing_active_children = active_child_ids - set(child_state_map)
        if missing_active_children:
            raise ValueError(
                "Regional execution missing active fractal child states: "
                f"{sorted(missing_active_children)}"
            )
        regional_execution_states.update(
            {
                node_id: child_state_map[node_id]
                for node_id in sorted(active_child_ids)
            }
        )
    regional_execution_graph = (
        fractal_projected_graph_before
        if fractal_projected_graph_before is not None
        else graph
    )
    event_execution_states = (
        regional_execution_states
        if fractal_projected_graph_before is not None
        else states
    )
    event_excluded_node_ids = (
        set()
        if fractal_projected_graph_before is not None
        else refined_parent_ids
    )
    logger.info(
        "run_day_transaction regional execution nodes=%s graph=%s",
        len(regional_execution_states),
        type(regional_execution_graph).__name__,
    )

    spillover_candidates: tuple[GraphSpilloverRecord, ...] = ()
    matured_spillovers: tuple[GraphSpilloverRecord, ...] = ()
    spillover_queue_out: SpilloverQueueState | None = None
    if enable_graph_spillover:
        assert spillover_config is not None
        assert normalized_spillover_queue is not None
        spillover_result = evaluate_graph_spillovers(
            day=day_to,
            states=regional_execution_states,
            graph=regional_execution_graph,
            spillover_config=spillover_config,
            parameter_registry=parameter_registry,
            profile=profile,
            queue=normalized_spillover_queue,
            trace=staged_trace,
        )
        spillover_candidates = spillover_result.candidates
        matured_spillovers = spillover_result.matured
        spillover_queue_out = spillover_result.queue

    candidates = _evaluate_candidates(
        day=day_to,
        states=event_execution_states,
        graph=regional_execution_graph,
        day_config=day_config,
        parameter_registry=parameter_registry,
        profile=profile,
        rng=working_rng,
        manifest=manifest,
        trace=staged_trace,
        excluded_node_ids=event_excluded_node_ids,
    )
    events = _occurred_events(candidates)
    event_proposals = _propose_all_effects(
        events=events,
        states=regional_execution_states,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=staged_trace,
    )
    spillover_proposals: tuple[DeltaProposal, ...] = ()
    if enable_graph_spillover and matured_spillovers:
        spillover_proposals = propose_matured_spillover_effects(
            matured=matured_spillovers,
            states=regional_execution_states,
            engine_state_registry=engine_state_registry,
            trace=staged_trace,
        )

    network_proposals: tuple[DeltaProposal, ...] = ()
    if enable_extremist_network_dynamics:
        assert extremist_network_config is not None
        network_proposals = propose_extremist_network_dynamics(
            states=l1_regional_execution_states,
            network_config=extremist_network_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=staged_trace,
        )

    security_chain_proposals: tuple[DeltaProposal, ...] = ()
    if enable_security_chain_dynamics:
        assert security_chain_config is not None
        security_chain_proposals = propose_security_chain_dynamics(
            states=l1_regional_execution_states,
            security_config=security_chain_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=staged_trace,
        )

    reciprocal_radicalization_proposals: tuple[DeltaProposal, ...] = ()
    if enable_reciprocal_radicalization:
        assert reciprocal_radicalization_config is not None
        reciprocal_radicalization_proposals = (
            propose_reciprocal_radicalization_effects(
                states=l1_regional_execution_states,
                feedback_config=reciprocal_radicalization_config,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                trace=staged_trace,
            )
        )

    recovery_proposals: tuple[DeltaProposal, ...] = ()
    if enable_recovery:
        assert recovery_config is not None
        recovery_proposals = propose_recovery_effects(
            states=l1_regional_execution_states,
            recovery_config=recovery_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=staged_trace,
        )
    proposals = tuple(
        sorted(
            (
                *event_proposals,
                *recovery_proposals,
                *spillover_proposals,
                *network_proposals,
                *reciprocal_radicalization_proposals,
                *security_chain_proposals,
            ),
            key=lambda proposal: proposal.proposal_id,
        )
    )

    l1_runtime_context = (
        build_runtime_resolver_context(
            plan=fractal_runtime_plan_before,
            node_ids=set(states),
        )
        if fractal_runtime_plan_before is not None
        else None
    )
    active_l2_ids = (
        set(fractal_runtime_plan_before.active_regional_node_ids)
        if fractal_runtime_plan_before is not None
        else set()
    )
    l1_proposals = tuple(
        item for item in proposals if item.target_node not in active_l2_ids
    )
    l2_interaction_proposals = tuple(
        item for item in proposals if item.target_node in active_l2_ids
    )
    resolution = resolve_delta_proposals(
        states=states,
        proposals=l1_proposals,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=staged_trace,
        runtime_context_by_node=l1_runtime_context,
    )
    interaction_resolution_records: tuple[ResolutionRecord, ...] = ()
    if l2_interaction_proposals:
        assert normalized_fractal_child_store is not None
        assert fractal_runtime_plan_before is not None
        child_states = normalized_fractal_child_store.state_map()
        child_runtime_context = build_runtime_resolver_context(
            plan=fractal_runtime_plan_before,
            node_ids=set(child_states),
        )
        child_interaction_resolution = resolve_delta_proposals(
            states=child_states,
            proposals=l2_interaction_proposals,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=staged_trace,
            runtime_context_by_node=child_runtime_context,
        )
        normalized_fractal_child_store = FractalChildStateStore(
            last_initialized_day=normalized_fractal_child_store.last_initialized_day,
            states=tuple(
                child_interaction_resolution.states[node_id]
                for node_id in sorted(child_interaction_resolution.states)
            ),
        )
        interaction_resolution_records = child_interaction_resolution.records
    all_resolution_records = tuple(
        sorted(
            (*resolution.records, *interaction_resolution_records),
            key=lambda item: item.resolution_id,
        )
    )
    advanced_states = _advance_resolved_states(
        resolved_states=resolution.states,
        engine_state_registry=engine_state_registry,
    )
    l1_advanced_regional_states = {
        node_id: state
        for node_id, state in sorted(advanced_states.items())
        if node_id not in refined_parent_ids
    }

    security_regime_persistence_out: dict[
        str, SecurityRegimePersistenceState
    ] = {}
    security_regime_evaluations: tuple[SecurityRegimeEvaluationResult, ...] = ()
    security_regime_proposals: tuple[SecurityRegimeTransitionProposal, ...] = ()

    if enable_security_regime_evaluator:
        assert security_regime_config is not None
        (
            security_regime_persistence_out,
            security_regime_evaluations,
            security_regime_proposals,
        ) = _evaluate_security_regimes(
            states=l1_advanced_regional_states,
            persistence={
                node_id: normalized_security_regime_persistence[node_id]
                for node_id in sorted(l1_advanced_regional_states)
            },
            context_flags={
                node_id: normalized_security_regime_context_flags.get(
                    node_id,
                    {},
                )
                for node_id in sorted(l1_advanced_regional_states)
            },
            regime_config=security_regime_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=staged_trace,
        )

    security_regime_commits: tuple[SecurityRegimeCommitRecord, ...] = ()
    security_committed_states = dict(advanced_states)
    if enable_security_regime_commits:
        assert security_regime_transition_config is not None
        (
            regional_security_committed_states,
            security_regime_persistence_out,
            security_regime_commits,
        ) = _commit_security_regimes(
            states=l1_advanced_regional_states,
            persistence=security_regime_persistence_out,
            proposals=security_regime_proposals,
            transition_config=security_regime_transition_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=staged_trace,
        )
        security_committed_states.update(
            regional_security_committed_states
        )

    if enable_security_regime_evaluator:
        for node_id in sorted(refined_parent_ids):
            current_regime = str(
                advanced_states[node_id].regimes[
                    "security_force_regime"
                ]
            )
            security_regime_persistence_out[node_id] = (
                SecurityRegimePersistenceState(
                    node_id=node_id,
                    current_regime=current_regime,
                    last_evaluated_day=day_to,
                    streaks=(),
                )
            )
            staged_trace.append(
                "fractal_parent_regime_persistence_suppressed",
                node_id=node_id,
                day=day_to,
                regime_type="security_force_regime",
                value=current_regime,
                reason="active_l2_authority",
            )

    security_regime_recovery_persistence_out: dict[
        str, SecurityRegimeRecoveryPersistenceState
    ] = {}
    security_regime_recovery_evaluations: tuple[
        SecurityRegimeRecoveryEvaluationResult, ...
    ] = ()
    security_regime_recovery_proposals: tuple[
        SecurityRegimeRecoveryProposal, ...
    ] = ()

    if enable_security_regime_recovery_evaluator:
        assert security_regime_recovery_config is not None
        (
            security_regime_recovery_persistence_out,
            security_regime_recovery_evaluations,
            security_regime_recovery_proposals,
        ) = _evaluate_security_regime_recoveries(
            states={
                node_id: security_committed_states[node_id]
                for node_id in sorted(l1_advanced_regional_states)
            },
            persistence={
                node_id: normalized_security_regime_recovery_persistence[
                    node_id
                ]
                for node_id in sorted(l1_advanced_regional_states)
            },
            context_flags={
                node_id: normalized_security_regime_context_flags.get(
                    node_id,
                    {},
                )
                for node_id in sorted(l1_advanced_regional_states)
            },
            recovery_config=security_regime_recovery_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            escalation_commits=security_regime_commits,
            trace=staged_trace,
        )

    security_regime_recovery_commits: tuple[
        SecurityRegimeRecoveryCommitRecord, ...
    ] = ()
    security_recovered_states = dict(security_committed_states)

    if enable_security_regime_recovery_commits:
        assert security_regime_recovery_transition_config is not None
        (
            regional_security_recovered_states,
            regional_escalation_persistence,
            security_regime_recovery_persistence_out,
            security_regime_recovery_commits,
        ) = _commit_security_regime_recoveries(
            states={
                node_id: security_committed_states[node_id]
                for node_id in sorted(l1_advanced_regional_states)
            },
            escalation_persistence={
                node_id: security_regime_persistence_out[node_id]
                for node_id in sorted(l1_advanced_regional_states)
            },
            recovery_persistence=security_regime_recovery_persistence_out,
            proposals=security_regime_recovery_proposals,
            transition_config=security_regime_recovery_transition_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=staged_trace,
        )
        security_recovered_states.update(
            regional_security_recovered_states
        )
        for node_id, item in regional_escalation_persistence.items():
            security_regime_persistence_out[node_id] = item

    if enable_security_regime_recovery_evaluator:
        for node_id in sorted(refined_parent_ids):
            current_regime = str(
                security_recovered_states[node_id].regimes[
                    "security_force_regime"
                ]
            )
            security_regime_recovery_persistence_out[node_id] = (
                SecurityRegimeRecoveryPersistenceState(
                    node_id=node_id,
                    current_regime=current_regime,
                    last_evaluated_day=day_to,
                    streaks=(),
                )
            )
            staged_trace.append(
                "fractal_parent_regime_persistence_suppressed",
                node_id=node_id,
                day=day_to,
                regime_type="security_force_regime_recovery",
                value=current_regime,
                reason="active_l2_authority",
            )

    phase_persistence_out: dict[str, PhasePersistenceState] = {}
    phase_evaluations: tuple[PhaseEvaluationResult, ...] = ()
    phase_arbitrations: tuple[PhaseArbitrationRecord, ...] = ()
    phase_commits: tuple[PhaseCommitRecord, ...] = ()
    final_states = security_recovered_states

    if enable_phase_transitions:
        assert phase_config is not None
        assert phase_transition_config is not None
        (
            regional_phase_states,
            phase_persistence_out,
            phase_evaluations,
            phase_arbitrations,
            phase_commits,
        ) = _evaluate_and_commit_phases(
            states={
                node_id: security_recovered_states[node_id]
                for node_id in sorted(l1_advanced_regional_states)
            },
            phase_persistence={
                node_id: normalized_phase_persistence[node_id]
                for node_id in sorted(l1_advanced_regional_states)
            },
            phase_context_flags={
                node_id: normalized_phase_context_flags.get(
                    node_id,
                    {},
                )
                for node_id in sorted(l1_advanced_regional_states)
            },
            phase_config=phase_config,
            phase_transition_config=phase_transition_config,
            parameter_registry=parameter_registry,
            profile=profile,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=staged_trace,
        )
        final_states = dict(security_recovered_states)
        final_states.update(regional_phase_states)
        for node_id in sorted(refined_parent_ids):
            current_phase = str(
                final_states[node_id].regimes["national_phase"]
            )
            phase_persistence_out[node_id] = PhasePersistenceState(
                node_id=node_id,
                current_phase=current_phase,
                last_evaluated_day=day_to,
                streaks=(),
            )
            staged_trace.append(
                "fractal_parent_regime_persistence_suppressed",
                node_id=node_id,
                day=day_to,
                regime_type="national_phase",
                value=current_phase,
                reason="active_l2_authority",
            )

    fractal_refinement_persistence_out: dict[
        str, FractalRefinementPersistenceState
    ] = {}
    fractal_refinement_evaluations: tuple[
        FractalRefinementEvaluationResult, ...
    ] = ()
    fractal_refinement_actions: tuple[
        FractalRefinementActionProposal, ...
    ] = ()

    if enable_fractal_refinement_evaluator:
        assert fractal_refinement_config is not None
        (
            fractal_refinement_persistence_out,
            fractal_refinement_evaluations,
            fractal_refinement_actions,
        ) = _evaluate_fractal_refinements(
            states=final_states,
            persistence=normalized_fractal_refinement_persistence,
            refinement_config=fractal_refinement_config,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=staged_trace,
            excluded_node_ids=(
                set(fractal_runtime_plan_before.refined_parent_ids)
                if fractal_runtime_plan_before is not None
                else None
            ),
        )

    unknown_fractal_actions = {
        item.action
        for item in fractal_refinement_actions
        if item.action not in {"EXPAND", "COLLAPSE"}
    }
    if unknown_fractal_actions:
        raise ValueError(
            f"Unknown fractal actions: {sorted(unknown_fractal_actions)}"
        )
    fractal_expansion_actions = tuple(
        item
        for item in fractal_refinement_actions
        if item.action == "EXPAND"
    )
    fractal_collapse_actions = tuple(
        item
        for item in fractal_refinement_actions
        if item.action == "COLLAPSE"
    )

    fractal_topology_out: FractalTopologyState | None = None
    fractal_materialization_commits: tuple[
        FractalMaterializationCommitRecord, ...
    ] = ()

    if enable_fractal_materialization:
        assert normalized_fractal_topology is not None
        assert fractal_materialization_config is not None
        assert fractal_region_catalog is not None
        (
            fractal_topology_out,
            fractal_refinement_persistence_out,
            fractal_materialization_commits,
        ) = _commit_fractal_materializations(
            day=day_to,
            actions=fractal_expansion_actions,
            persistence=fractal_refinement_persistence_out,
            topology=normalized_fractal_topology,
            region_catalog=fractal_region_catalog,
            materialization_config=fractal_materialization_config,
            manifest=manifest,
            trace=staged_trace,
        )

    fractal_child_state_store_out: FractalChildStateStore | None = None
    fractal_child_initialization_records: tuple[
        FractalChildStateInitializationRecord, ...
    ] = ()
    fractal_conservation_audits: tuple[
        FractalConservationAuditRecord, ...
    ] = ()
    fractal_uncertainty_records: tuple[
        FractalUncertaintyRecord, ...
    ] = ()
    fractal_uncertainty_audits: tuple[
        FractalUncertaintyAuditRecord, ...
    ] = ()

    if enable_fractal_child_state_initialization:
        assert fractal_topology_out is not None
        assert normalized_fractal_child_store is not None
        assert fractal_child_state_config is not None
        child_result = initialize_fractal_child_states(
            parent_states=final_states,
            topology=fractal_topology_out,
            child_store=normalized_fractal_child_store,
            initialization_config=fractal_child_state_config,
            engine_state_registry=engine_state_registry,
            trace=staged_trace,
        )
        fractal_child_state_store_out = child_result.store
        fractal_child_initialization_records = (
            child_result.initialization_records
        )
        fractal_conservation_audits = child_result.conservation_audits

    if enable_fractal_uncertainty:
        assert fractal_topology_out is not None
        assert fractal_child_state_store_out is not None
        assert fractal_uncertainty_config is not None
        uncertainty_result = apply_fractal_uncertainty(
            parent_states=final_states,
            topology=fractal_topology_out,
            child_store=fractal_child_state_store_out,
            new_child_ids=tuple(
                item.child_node_id
                for item in fractal_child_initialization_records
            ),
            uncertainty_config=fractal_uncertainty_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            rng=working_rng,
            trace=staged_trace,
        )
        fractal_child_state_store_out = uncertainty_result.store
        fractal_uncertainty_records = uncertainty_result.records
        fractal_uncertainty_audits = uncertainty_result.audits

    fractal_regional_regime_result: (
        FractalRegionalRegimeResult | None
    ) = None
    if enable_fractal_regional_regimes:
        assert fractal_child_state_store_out is not None
        assert normalized_fractal_regional_regime_store is not None
        assert fractal_runtime_plan_before is not None
        assert fractal_regional_regime_config is not None
        assert phase_config is not None
        assert phase_transition_config is not None
        assert security_regime_config is not None
        assert security_regime_transition_config is not None
        assert security_regime_recovery_config is not None
        assert security_regime_recovery_transition_config is not None
        fractal_regional_regime_result = execute_regional_regime_runtime(
            child_store=fractal_child_state_store_out,
            beginning_active_node_ids=(
                fractal_runtime_plan_before.active_regional_node_ids
            ),
            persistence_store=(
                normalized_fractal_regional_regime_store
            ),
            context_flags=normalized_fractal_regional_context_flags,
            regional_config=fractal_regional_regime_config,
            phase_config=phase_config,
            phase_transition_config=phase_transition_config,
            security_regime_config=security_regime_config,
            security_transition_config=(
                security_regime_transition_config
            ),
            security_recovery_config=(
                security_regime_recovery_config
            ),
            security_recovery_transition_config=(
                security_regime_recovery_transition_config
            ),
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=staged_trace,
        )
        fractal_child_state_store_out = (
            fractal_regional_regime_result.child_store
        )

    fractal_parent_child_coupling_result: (
        FractalParentChildCouplingResult | None
    ) = None
    if (
        enable_fractal_parent_child_coupling
        and fractal_runtime_plan_before is not None
        and fractal_runtime_plan_before.refined_parent_ids
    ):
        assert fractal_child_state_store_out is not None
        assert fractal_parent_child_coupling_config is not None
        fractal_parent_child_coupling_result = execute_parent_child_coupling(
            parent_states=final_states,
            child_store=fractal_child_state_store_out,
            runtime_plan=fractal_runtime_plan_before,
            engine_state_registry=engine_state_registry,
            reaggregation_config=fractal_parent_child_coupling_config,
            trace=staged_trace,
        )
        final_states = (
            fractal_parent_child_coupling_result.parent_states
        )
        fractal_child_state_store_out = (
            fractal_parent_child_coupling_result.child_store
        )

    late_fractal_actions: tuple[
        FractalRefinementActionProposal, ...
    ] = ()
    if (
        enable_fractal_refinement_evaluator
        and fractal_topology_out is not None
        and fractal_child_state_store_out is not None
    ):
        assert fractal_refinement_config is not None
        child_state_map = fractal_child_state_store_out.state_map()
        active_l2_nodes = {
            item.node_id: item
            for item in fractal_topology_out.nodes
            if item.active and item.level == "L2_REGION"
        }
        late_refinement_states: dict[str, EngineState] = {}

        if fractal_runtime_plan_before is not None:
            for parent_id in sorted(
                fractal_runtime_plan_before.refined_parent_ids
            ):
                late_refinement_states[parent_id] = final_states[parent_id]

        for node_id, topology_node in sorted(active_l2_nodes.items()):
            if topology_node.created_day == day_to:
                continue
            if node_id not in child_state_map:
                raise ValueError(
                    f"Late fractal refinement missing L2 state {node_id}"
                )
            late_refinement_states[node_id] = child_state_map[node_id]

        if late_refinement_states:
            (
                fractal_refinement_persistence_out,
                late_evaluations,
                late_fractal_actions,
            ) = _evaluate_fractal_refinements(
                states=late_refinement_states,
                persistence=fractal_refinement_persistence_out,
                refinement_config=fractal_refinement_config,
                parameter_registry=parameter_registry,
                profile=profile,
                manifest=manifest,
                trace=staged_trace,
            )
            fractal_refinement_evaluations = tuple(
                sorted(
                    (
                        *fractal_refinement_evaluations,
                        *late_evaluations,
                    ),
                    key=lambda item: item.persistence.node_id,
                )
            )
            fractal_refinement_actions = tuple(
                sorted(
                    (
                        *fractal_refinement_actions,
                        *late_fractal_actions,
                    ),
                    key=lambda item: item.action_id,
                )
            )

    effective_late_actions: list[FractalRefinementActionProposal] = []
    late_action_nodes = {item.node_id for item in late_fractal_actions}
    for action in late_fractal_actions:
        if (
            action.action == "COLLAPSE"
            and action.from_level == "L2_REGION"
            and action.to_level == "L1_COUNTRY"
            and fractal_topology_out is not None
        ):
            direct_children = {
                item.node_id
                for item in fractal_topology_out.active_children(
                    action.node_id
                )
            }
            conflicting_descendants = direct_children & late_action_nodes
            if conflicting_descendants:
                staged_trace.append(
                    "fractal_collapse_deferred",
                    action_id=action.action_id,
                    node_id=action.node_id,
                    day=action.day,
                    reason="descendant_resolution_action_same_day",
                    conflicting_descendant_node_ids=sorted(
                        conflicting_descendants
                    ),
                )
                continue
        effective_late_actions.append(action)

    recursive_expansion_actions = tuple(
        item
        for item in effective_late_actions
        if item.action == "EXPAND"
    )
    recursive_collapse_actions = tuple(
        item
        for item in effective_late_actions
        if item.action == "COLLAPSE"
    )
    fractal_collapse_actions = tuple(
        sorted(
            (*fractal_collapse_actions, *recursive_collapse_actions),
            key=lambda item: item.action_id,
        )
    )

    if recursive_expansion_actions:
        if not enable_fractal_materialization:
            raise ValueError(
                "Recursive fractal expansion requires materialization"
            )
        assert fractal_topology_out is not None
        assert fractal_materialization_config is not None
        assert fractal_region_catalog is not None
        (
            fractal_topology_out,
            fractal_refinement_persistence_out,
            recursive_materialization_commits,
        ) = _commit_fractal_materializations(
            day=day_to,
            actions=recursive_expansion_actions,
            persistence=fractal_refinement_persistence_out,
            topology=fractal_topology_out,
            region_catalog=fractal_region_catalog,
            materialization_config=fractal_materialization_config,
            manifest=manifest,
            trace=staged_trace,
        )
        fractal_materialization_commits = tuple(
            sorted(
                (
                    *fractal_materialization_commits,
                    *recursive_materialization_commits,
                ),
                key=lambda item: item.commit_id,
            )
        )

        if not enable_fractal_child_state_initialization:
            raise ValueError(
                "Recursive fractal expansion requires child-state "
                "initialization"
            )
        assert fractal_child_state_store_out is not None
        assert fractal_child_state_config is not None
        recursive_child_result = initialize_fractal_child_states(
            parent_states=final_states,
            topology=fractal_topology_out,
            child_store=fractal_child_state_store_out,
            initialization_config=fractal_child_state_config,
            engine_state_registry=engine_state_registry,
            trace=staged_trace,
        )
        fractal_child_state_store_out = recursive_child_result.store
        recursive_initializations = (
            recursive_child_result.initialization_records
        )
        fractal_child_initialization_records = tuple(
            sorted(
                (
                    *fractal_child_initialization_records,
                    *recursive_initializations,
                ),
                key=lambda item: item.initialization_id,
            )
        )
        fractal_conservation_audits = tuple(
            sorted(
                (
                    *fractal_conservation_audits,
                    *recursive_child_result.conservation_audits,
                ),
                key=lambda item: item.audit_id,
            )
        )

        if enable_fractal_uncertainty and recursive_initializations:
            assert fractal_uncertainty_config is not None
            recursive_uncertainty = apply_fractal_uncertainty(
                parent_states=final_states,
                topology=fractal_topology_out,
                child_store=fractal_child_state_store_out,
                new_child_ids=tuple(
                    item.child_node_id
                    for item in recursive_initializations
                ),
                uncertainty_config=fractal_uncertainty_config,
                engine_state_registry=engine_state_registry,
                parameter_registry=parameter_registry,
                profile=profile,
                rng=working_rng,
                trace=staged_trace,
            )
            fractal_child_state_store_out = recursive_uncertainty.store
            fractal_uncertainty_records = tuple(
                sorted(
                    (
                        *fractal_uncertainty_records,
                        *recursive_uncertainty.records,
                    ),
                    key=lambda item: item.variation_id,
                )
            )
            fractal_uncertainty_audits = tuple(
                sorted(
                    (
                        *fractal_uncertainty_audits,
                        *recursive_uncertainty.audits,
                    ),
                    key=lambda item: item.audit_id,
                )
            )

    fractal_collapse_commits: tuple[
        FractalCollapseCommitRecord, ...
    ] = ()
    fractal_reaggregation_audits: tuple[
        FractalReaggregationAuditRecord, ...
    ] = ()

    if enable_fractal_reaggregation:
        assert fractal_topology_out is not None
        assert fractal_child_state_store_out is not None
        assert fractal_reaggregation_config is not None
        collapse_result = commit_fractal_collapses(
            parent_states=final_states,
            actions=fractal_collapse_actions,
            persistence=fractal_refinement_persistence_out,
            topology=fractal_topology_out,
            child_store=fractal_child_state_store_out,
            reaggregation_config=fractal_reaggregation_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=staged_trace,
        )
        final_states = collapse_result.states
        fractal_topology_out = collapse_result.topology
        fractal_child_state_store_out = collapse_result.child_store
        fractal_refinement_persistence_out = collapse_result.persistence
        fractal_collapse_commits = collapse_result.commits
        fractal_reaggregation_audits = collapse_result.audits

    fractal_runtime_plan_after: FractalRuntimePlan | None = None
    fractal_projected_graph_after: FractalProjectedGraph | None = None
    if enable_fractal_runtime_plan:
        assert fractal_topology_out is not None
        assert fractal_child_state_store_out is not None
        assert fractal_runtime_config is not None
        fractal_runtime_plan_after = build_fractal_runtime_plan(
            day=day_to,
            parent_states=final_states,
            topology=fractal_topology_out,
            child_store=fractal_child_state_store_out,
            runtime_config=fractal_runtime_config,
            engine_state_registry=engine_state_registry,
        )
        trace_fractal_runtime_plan(
            plan=fractal_runtime_plan_after,
            phase="COMMITTED_NEXT_DAY",
            trace=staged_trace,
        )

    if enable_fractal_graph_projection:
        assert fractal_runtime_plan_after is not None
        assert fractal_graph_projection_config is not None
        assert fractal_region_graph_catalog is not None
        fractal_projected_graph_after = (
            build_fractal_projected_graph(
                runtime_plan=fractal_runtime_plan_after,
                base_graph=graph,
                projection_config=fractal_graph_projection_config,
                regional_graph_catalog=fractal_region_graph_catalog,
            )
        )
        trace_fractal_projected_graph(
            graph=fractal_projected_graph_after,
            phase="COMMITTED_NEXT_DAY",
            trace=staged_trace,
        )

    for node_id in sorted(states):
        _checkpoint_node(
            node_id=node_id,
            state_before=states[node_id],
            state_after=final_states[node_id],
            events=events,
            resolutions=all_resolution_records,
            spillover_proposals=spillover_proposals,
            security_regime_commits=security_regime_commits,
            security_regime_recovery_commits=(
                security_regime_recovery_commits
            ),
            phase_commits=phase_commits,
            fractal_refinement_actions=fractal_refinement_actions,
            fractal_child_initialization_records=(
                fractal_child_initialization_records
            ),
            fractal_collapse_commits=fractal_collapse_commits,
            fractal_reaggregation_audits=fractal_reaggregation_audits,
            manifest=manifest,
            trace=staged_trace,
        )

    staged_trace.append(
        "day_transaction_committed",
        run_id=manifest.run_id,
        transaction_id=transaction_id,
        day_from=day_from,
        day_to=day_to,
        event_ids=[event.event_id for event in events],
        proposal_ids=[proposal.proposal_id for proposal in proposals],
        resolution_ids=[
            record.resolution_id for record in all_resolution_records
        ],
        phase_commit_ids=[
            record.commit_id for record in phase_commits
        ],
        fractal_refinement_action_ids=[
            item.action_id for item in fractal_refinement_actions
        ],
        fractal_materialization_commit_ids=[
            item.commit_id for item in fractal_materialization_commits
        ],
        fractal_child_initialization_ids=[
            item.initialization_id
            for item in fractal_child_initialization_records
        ],
        fractal_conservation_audit_ids=[
            item.audit_id for item in fractal_conservation_audits
        ],
        fractal_uncertainty_ids=[
            item.variation_id for item in fractal_uncertainty_records
        ],
        fractal_uncertainty_audit_ids=[
            item.audit_id for item in fractal_uncertainty_audits
        ],
        fractal_collapse_commit_ids=[
            item.commit_id for item in fractal_collapse_commits
        ],
        fractal_reaggregation_audit_ids=[
            item.audit_id for item in fractal_reaggregation_audits
        ],
        fractal_runtime_plan_before_hash=(
            fractal_runtime_plan_before.plan_hash()
            if fractal_runtime_plan_before is not None
            else None
        ),
        fractal_runtime_plan_after_hash=(
            fractal_runtime_plan_after.plan_hash()
            if fractal_runtime_plan_after is not None
            else None
        ),
        fractal_projected_graph_before_hash=(
            fractal_projected_graph_before.graph_hash()
            if fractal_projected_graph_before is not None
            else None
        ),
        fractal_projected_graph_after_hash=(
            fractal_projected_graph_after.graph_hash()
            if fractal_projected_graph_after is not None
            else None
        ),
        fractal_regional_regime_store_hash=(
            fractal_regional_regime_result.persistence_store.store_hash()
            if fractal_regional_regime_result is not None
            else None
        ),
        fractal_regional_phase_commit_ids=(
            [
                item.commit_id
                for item in fractal_regional_regime_result.phase_commits
            ]
            if fractal_regional_regime_result is not None
            else []
        ),
        fractal_regional_security_commit_ids=(
            [
                item.commit_id
                for item in fractal_regional_regime_result.security_commits
            ]
            if fractal_regional_regime_result is not None
            else []
        ),
        fractal_regional_security_recovery_commit_ids=(
            [
                item.commit_id
                for item in fractal_regional_regime_result.recovery_commits
            ]
            if fractal_regional_regime_result is not None
            else []
        ),
        fractal_parent_child_coupling_audit_ids=(
            [
                item.audit_id
                for item in fractal_parent_child_coupling_result.audits
            ]
            if fractal_parent_child_coupling_result is not None
            else []
        ),
        fractal_categorical_divergence_audit_ids=(
            [
                item.audit_id
                for item in fractal_regional_regime_result.divergence_audits
            ]
            if fractal_regional_regime_result is not None
            else []
        ),
        fractal_child_state_store=(
            fractal_child_state_store_out.to_dict()
            if fractal_child_state_store_out is not None
            else None
        ),
        fractal_topology=(
            fractal_topology_out.to_dict()
            if fractal_topology_out is not None
            else None
        ),
        fractal_refinement_persistence={
            node_id: item.to_dict()
            for node_id, item in sorted(
                fractal_refinement_persistence_out.items()
            )
        },
        spillover_candidate_ids=[
            record.spillover_id for record in spillover_candidates
        ],
        matured_spillover_ids=[
            record.spillover_id for record in matured_spillovers
        ],
        applied_spillover_ids=[
            proposal.event_id for proposal in spillover_proposals
        ],
        network_proposal_ids=[
            proposal.proposal_id for proposal in network_proposals
        ],
        reciprocal_radicalization_proposal_ids=[
            proposal.proposal_id
            for proposal in reciprocal_radicalization_proposals
        ],
        security_chain_proposal_ids=[
            proposal.proposal_id for proposal in security_chain_proposals
        ],
        security_regime_proposal_ids=[
            proposal.proposal_id for proposal in security_regime_proposals
        ],
        security_regime_commit_ids=[
            record.commit_id for record in security_regime_commits
        ],
        security_regime_recovery_proposal_ids=[
            proposal.proposal_id
            for proposal in security_regime_recovery_proposals
        ],
        security_regime_recovery_commit_ids=[
            record.commit_id
            for record in security_regime_recovery_commits
        ],
        security_regime_recovery_persistence={
            node_id: item.to_dict()
            for node_id, item in sorted(
                security_regime_recovery_persistence_out.items()
            )
        },
        security_regime_persistence={
            node_id: item.to_dict()
            for node_id, item in sorted(
                security_regime_persistence_out.items()
            )
        },
        spillover_queue=(
            spillover_queue_out.to_dict()
            if spillover_queue_out is not None
            else None
        ),
        phase_persistence={
            node_id: persistence.to_dict()
            for node_id, persistence in sorted(phase_persistence_out.items())
        },
        state_hashes_after={
            node_id: state.state_hash()
            for node_id, state in sorted(final_states.items())
        },
    )

    rng.replace_from(working_rng)
    trace.extend_from(staged_trace)

    return DayTransactionResult(
        transaction_id=transaction_id,
        day_from=day_from,
        day_to=day_to,
        states=final_states,
        candidates=candidates,
        events=events,
        proposals=proposals,
        resolutions=all_resolution_records,
        spillover_queue=spillover_queue_out,
        spillover_candidates=spillover_candidates,
        matured_spillovers=matured_spillovers,
        spillover_proposals=spillover_proposals,
        network_proposals=network_proposals,
        reciprocal_radicalization_proposals=(
            reciprocal_radicalization_proposals
        ),
        security_chain_proposals=security_chain_proposals,
        security_regime_persistence=security_regime_persistence_out,
        security_regime_evaluations=security_regime_evaluations,
        security_regime_proposals=security_regime_proposals,
        security_regime_commits=security_regime_commits,
        security_regime_recovery_persistence=(
            security_regime_recovery_persistence_out
        ),
        security_regime_recovery_evaluations=(
            security_regime_recovery_evaluations
        ),
        security_regime_recovery_proposals=(
            security_regime_recovery_proposals
        ),
        security_regime_recovery_commits=(
            security_regime_recovery_commits
        ),
        phase_persistence=phase_persistence_out,
        phase_evaluations=phase_evaluations,
        phase_arbitrations=phase_arbitrations,
        phase_commits=phase_commits,
        fractal_refinement_persistence=(
            fractal_refinement_persistence_out
        ),
        fractal_refinement_evaluations=(
            fractal_refinement_evaluations
        ),
        fractal_refinement_actions=fractal_refinement_actions,
        fractal_topology=fractal_topology_out,
        fractal_materialization_commits=fractal_materialization_commits,
        fractal_child_state_store=fractal_child_state_store_out,
        fractal_child_initialization_records=(
            fractal_child_initialization_records
        ),
        fractal_conservation_audits=fractal_conservation_audits,
        fractal_uncertainty_records=fractal_uncertainty_records,
        fractal_uncertainty_audits=fractal_uncertainty_audits,
        fractal_collapse_commits=fractal_collapse_commits,
        fractal_reaggregation_audits=fractal_reaggregation_audits,
        fractal_runtime_plan_before=fractal_runtime_plan_before,
        fractal_runtime_plan_after=fractal_runtime_plan_after,
        fractal_child_dynamics_proposals=(
            fractal_child_dynamics_proposals
        ),
        fractal_child_dynamics_resolutions=(
            fractal_child_dynamics_resolutions
        ),
        fractal_regional_regime_result=(
            fractal_regional_regime_result
        ),
        fractal_projected_graph_before=(
            fractal_projected_graph_before
        ),
        fractal_projected_graph_after=(
            fractal_projected_graph_after
        ),
        fractal_parent_child_coupling_result=(
            fractal_parent_child_coupling_result
        ),
    )
