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
from .resolver import ResolutionRecord, resolve_delta_proposals
from .rng import RNGManager
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
    phase_persistence: dict[str, PhasePersistenceState]
    phase_evaluations: tuple[PhaseEvaluationResult, ...]
    phase_arbitrations: tuple[PhaseArbitrationRecord, ...]
    phase_commits: tuple[PhaseCommitRecord, ...]

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
) -> tuple[DailyCandidate, ...]:
    logger.info(
        "_evaluate_candidates day=%s passes=%s",
        day,
        len(day_config["candidate_passes"]),
    )
    candidates: list[DailyCandidate] = []

    for pass_config in day_config["candidate_passes"]:
        event_type = str(pass_config["event_type"])
        scope = str(pass_config["scope"])

        if (event_type, scope) == (
            "INTERSTATE_INCIDENT_V1",
            "all_graph_edges",
        ):
            for edge in sorted(graph.edges, key=lambda item: item.edge_id()):
                state_a = states[edge.a]
                state_b = states[edge.b]
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


def _checkpoint_node(
    *,
    node_id: str,
    state_before: EngineState,
    state_after: EngineState,
    events: tuple[SimEvent, ...],
    resolutions: tuple[ResolutionRecord, ...],
    spillover_proposals: tuple[DeltaProposal, ...],
    phase_commits: tuple[PhaseCommitRecord, ...],
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
    node_phase_commits = tuple(
        sorted(
            record.commit_id
            for record in phase_commits
            if record.node_id == node_id
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
    normalized_spillover_queue: SpilloverQueueState | None = None

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
    )

    spillover_candidates: tuple[GraphSpilloverRecord, ...] = ()
    matured_spillovers: tuple[GraphSpilloverRecord, ...] = ()
    spillover_queue_out: SpilloverQueueState | None = None
    if enable_graph_spillover:
        assert spillover_config is not None
        assert normalized_spillover_queue is not None
        spillover_result = evaluate_graph_spillovers(
            day=day_to,
            states=states,
            graph=graph,
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
        states=states,
        graph=graph,
        day_config=day_config,
        parameter_registry=parameter_registry,
        profile=profile,
        rng=working_rng,
        manifest=manifest,
        trace=staged_trace,
    )
    events = _occurred_events(candidates)
    event_proposals = _propose_all_effects(
        events=events,
        states=states,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=staged_trace,
    )
    spillover_proposals: tuple[DeltaProposal, ...] = ()
    if enable_graph_spillover and matured_spillovers:
        spillover_proposals = propose_matured_spillover_effects(
            matured=matured_spillovers,
            states=states,
            engine_state_registry=engine_state_registry,
            trace=staged_trace,
        )

    network_proposals: tuple[DeltaProposal, ...] = ()
    if enable_extremist_network_dynamics:
        assert extremist_network_config is not None
        network_proposals = propose_extremist_network_dynamics(
            states=states,
            network_config=extremist_network_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            trace=staged_trace,
        )

    recovery_proposals: tuple[DeltaProposal, ...] = ()
    if enable_recovery:
        assert recovery_config is not None
        recovery_proposals = propose_recovery_effects(
            states=states,
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
            ),
            key=lambda proposal: proposal.proposal_id,
        )
    )

    resolution = resolve_delta_proposals(
        states=states,
        proposals=proposals,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=staged_trace,
    )
    advanced_states = _advance_resolved_states(
        resolved_states=resolution.states,
        engine_state_registry=engine_state_registry,
    )

    phase_persistence_out: dict[str, PhasePersistenceState] = {}
    phase_evaluations: tuple[PhaseEvaluationResult, ...] = ()
    phase_arbitrations: tuple[PhaseArbitrationRecord, ...] = ()
    phase_commits: tuple[PhaseCommitRecord, ...] = ()
    final_states = advanced_states

    if enable_phase_transitions:
        assert phase_config is not None
        assert phase_transition_config is not None
        (
            final_states,
            phase_persistence_out,
            phase_evaluations,
            phase_arbitrations,
            phase_commits,
        ) = _evaluate_and_commit_phases(
            states=advanced_states,
            phase_persistence=normalized_phase_persistence,
            phase_context_flags=normalized_phase_context_flags,
            phase_config=phase_config,
            phase_transition_config=phase_transition_config,
            parameter_registry=parameter_registry,
            profile=profile,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=staged_trace,
        )

    for node_id in sorted(states):
        _checkpoint_node(
            node_id=node_id,
            state_before=states[node_id],
            state_after=final_states[node_id],
            events=events,
            resolutions=resolution.records,
            spillover_proposals=spillover_proposals,
            phase_commits=phase_commits,
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
            record.resolution_id for record in resolution.records
        ],
        phase_commit_ids=[
            record.commit_id for record in phase_commits
        ],
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
        resolutions=resolution.records,
        spillover_queue=spillover_queue_out,
        spillover_candidates=spillover_candidates,
        matured_spillovers=matured_spillovers,
        spillover_proposals=spillover_proposals,
        network_proposals=network_proposals,
        phase_persistence=phase_persistence_out,
        phase_evaluations=phase_evaluations,
        phase_arbitrations=phase_arbitrations,
        phase_commits=phase_commits,
    )
