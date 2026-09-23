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
from .graph import StructuralGraph
from .manifest import RunManifest
from .resolver import ResolutionRecord, resolve_delta_proposals
from .rng import RNGManager
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DayTransactionResult:
    transaction_id: str
    day_from: int
    day_to: int
    states: dict[str, EngineState]
    candidate_results: tuple[EventCandidateResult, ...]
    events: tuple[SimEvent, ...]
    proposals: tuple[DeltaProposal, ...]
    resolutions: tuple[ResolutionRecord, ...]
    state_hashes_before: tuple[tuple[str, str], ...]
    state_hashes_after: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "DayTransactionResult.to_dict transaction_id=%s",
            self.transaction_id,
        )
        return {
            "transaction_id": self.transaction_id,
            "day_from": self.day_from,
            "day_to": self.day_to,
            "states": {
                node_id: state.to_dict()
                for node_id, state in sorted(self.states.items())
            },
            "candidate_results": [
                result.to_dict() for result in self.candidate_results
            ],
            "events": [event.to_dict() for event in self.events],
            "proposals": [proposal.to_dict() for proposal in self.proposals],
            "resolutions": [record.to_dict() for record in self.resolutions],
            "state_hashes_before": dict(self.state_hashes_before),
            "state_hashes_after": dict(self.state_hashes_after),
        }


def _validate_transaction_inputs(
    *,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    engine_state_registry: dict[str, Any],
    transaction_config: dict[str, Any],
    manifest: RunManifest,
) -> int:
    logger.info(
        "_validate_transaction_inputs states=%s graph_nodes=%s",
        len(states),
        len(graph.nodes),
    )
    if manifest.time_step_days != 1:
        raise ValueError("Day transaction v0.7 requires manifest.time_step_days == 1")

    graph_nodes = set(graph.nodes)
    state_nodes = set(states)
    if bool(transaction_config["atomicity"]["all_graph_nodes_required"]):
        if state_nodes != graph_nodes:
            raise ValueError(
                f"State/graph node mismatch states={sorted(state_nodes)} "
                f"graph={sorted(graph_nodes)}"
            )

    if not states:
        raise ValueError("Day transaction requires at least one state")

    days = {state.day for state in states.values()}
    if bool(transaction_config["atomicity"]["all_states_same_day_required"]):
        if len(days) != 1:
            raise ValueError(f"State days are not synchronized: {sorted(days)}")

    latent_registry = extract_latent_registry(engine_state_registry)
    for node_id, state in sorted(states.items()):
        if state.node_id != node_id:
            raise ValueError(
                f"State key {node_id} does not match state.node_id {state.node_id}"
            )
        state.validate(latent_registry)

    return next(iter(days))


def _transaction_id(
    *,
    manifest: RunManifest,
    day_from: int,
    state_hashes_before: tuple[tuple[str, str], ...],
    graph: StructuralGraph,
) -> str:
    logger.info("_transaction_id day_from=%s", day_from)
    digest = canonical_hash(
        {
            "rule_id": "DAY_TRANSACTION_V1",
            "replay_key": manifest.replay_key,
            "day_from": day_from,
            "graph_hash": graph.graph_hash(),
            "state_hashes_before": dict(state_hashes_before),
        }
    )
    return f"daytx-{digest[:24]}"


def _evaluate_event_spec(
    *,
    spec: dict[str, Any],
    day: int,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[EventCandidateResult, ...]:
    logger.info(
        "_evaluate_event_spec event_type=%s scope=%s day=%s",
        spec.get("event_type"),
        spec.get("scope"),
        day,
    )
    event_type = str(spec["event_type"])
    scope = str(spec["scope"])
    results: list[EventCandidateResult] = []

    if event_type == "INTERSTATE_INCIDENT_V1" and scope == "all_edges":
        for edge in sorted(graph.edges, key=lambda item: item.edge_id()):
            results.append(
                evaluate_interstate_incident(
                    day=day,
                    state_a=states[edge.a],
                    state_b=states[edge.b],
                    edge=edge,
                    parameter_registry=parameter_registry,
                    profile=profile,
                    rng=rng,
                    manifest=manifest,
                    trace=trace,
                )
            )
        return tuple(results)

    if event_type == "MASS_PROTEST_TRIGGER_V1" and scope == "all_nodes":
        for node_id in sorted(states):
            results.append(
                evaluate_mass_protest(
                    day=day,
                    state=states[node_id],
                    parameter_registry=parameter_registry,
                    profile=profile,
                    rng=rng,
                    manifest=manifest,
                    trace=trace,
                )
            )
        return tuple(results)

    raise ValueError(
        f"Unsupported day transaction event spec "
        f"event_type={event_type} scope={scope}"
    )


def _evaluate_all_candidates(
    *,
    day: int,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    transaction_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[EventCandidateResult, ...]:
    logger.info("_evaluate_all_candidates day=%s", day)
    results: list[EventCandidateResult] = []
    seen_event_types: set[str] = set()
    for spec in transaction_config["event_evaluation_order"]:
        event_type = str(spec["event_type"])
        if event_type in seen_event_types:
            raise ValueError(f"Duplicate event type in day transaction: {event_type}")
        seen_event_types.add(event_type)
        results.extend(
            _evaluate_event_spec(
                spec=spec,
                day=day,
                states=states,
                graph=graph,
                parameter_registry=parameter_registry,
                profile=profile,
                rng=rng,
                manifest=manifest,
                trace=trace,
            )
        )
    return tuple(results)


def _collect_events(
    candidate_results: tuple[EventCandidateResult, ...],
) -> tuple[SimEvent, ...]:
    logger.info("_collect_events candidates=%s", len(candidate_results))
    return tuple(
        result.event
        for result in candidate_results
        if result.occurred and result.event is not None
    )


def _collect_proposals(
    *,
    events: tuple[SimEvent, ...],
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    logger.info("_collect_proposals events=%s", len(events))
    proposals: list[DeltaProposal] = []
    for event in sorted(events, key=lambda item: item.event_id):
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
    return tuple(proposals)


def _advance_states(
    *,
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
) -> dict[str, EngineState]:
    logger.info("_advance_states states=%s", len(states))
    latent_registry = extract_latent_registry(engine_state_registry)
    advanced: dict[str, EngineState] = {}
    for node_id, state in sorted(states.items()):
        next_state = state.clone_for_next_day()
        next_state.validate(latent_registry)
        advanced[node_id] = next_state
    return advanced


def execute_day_transaction(
    *,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    transaction_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> DayTransactionResult:
    """Evaluate and commit one simulation day atomically."""
    logger.info(
        "execute_day_transaction run_id=%s profile=%s states=%s",
        manifest.run_id,
        profile,
        len(states),
    )
    day_from = _validate_transaction_inputs(
        states=states,
        graph=graph,
        engine_state_registry=engine_state_registry,
        transaction_config=transaction_config,
        manifest=manifest,
    )
    day_to = day_from + 1
    state_hashes_before = tuple(
        (node_id, state.state_hash())
        for node_id, state in sorted(states.items())
    )
    transaction_id = _transaction_id(
        manifest=manifest,
        day_from=day_from,
        state_hashes_before=state_hashes_before,
        graph=graph,
    )

    working_rng = rng.clone()
    staged_trace = TraceLedger()
    rng_before = rng.describe()

    staged_trace.append(
        "day_transaction_started",
        run_id=manifest.run_id,
        transaction_id=transaction_id,
        rule_id="DAY_TRANSACTION_V1",
        day_from=day_from,
        day_to=day_to,
        state_hashes_before=dict(state_hashes_before),
        graph_hash=graph.graph_hash(),
        rng_before=rng_before,
    )

    candidate_results = _evaluate_all_candidates(
        day=day_to,
        states=states,
        graph=graph,
        transaction_config=transaction_config,
        parameter_registry=parameter_registry,
        profile=profile,
        rng=working_rng,
        manifest=manifest,
        trace=staged_trace,
    )
    events = _collect_events(candidate_results)
    proposals = _collect_proposals(
        events=events,
        states=states,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=staged_trace,
    )
    resolution = resolve_delta_proposals(
        states=states,
        proposals=proposals,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=staged_trace,
    )
    advanced_states = _advance_states(
        states=resolution.states,
        engine_state_registry=engine_state_registry,
    )
    state_hashes_after = tuple(
        (node_id, state.state_hash())
        for node_id, state in sorted(advanced_states.items())
    )

    event_ids = tuple(sorted(event.event_id for event in events))
    for node_id in sorted(advanced_states):
        node_resolution_ids = tuple(
            record.resolution_id
            for record in resolution.records
            if record.target_node == node_id
        )
        node_event_ids = tuple(
            sorted(
                event.event_id
                for event in events
                if node_id in event.actors
            )
        )
        node_clamps = tuple(
            record.resolution_id
            for record in resolution.records
            if record.target_node == node_id and record.clamp_amount != 0.0
        )
        staged_trace.append_daily_checkpoint(
            run_id=manifest.run_id,
            day=day_to,
            node_id=node_id,
            state_hash_before=dict(state_hashes_before)[node_id],
            state_hash_after=dict(state_hashes_after)[node_id],
            module_deltas=node_resolution_ids,
            event_ids_applied=node_event_ids,
            constraint_clamps=node_clamps,
        )

    staged_trace.append(
        "day_transaction_committed",
        run_id=manifest.run_id,
        transaction_id=transaction_id,
        rule_id="DAY_TRANSACTION_V1",
        day_from=day_from,
        day_to=day_to,
        state_hashes_before=dict(state_hashes_before),
        state_hashes_after=dict(state_hashes_after),
        candidate_count=len(candidate_results),
        event_ids=list(event_ids),
        proposal_ids=sorted(proposal.proposal_id for proposal in proposals),
        resolution_ids=sorted(
            record.resolution_id for record in resolution.records
        ),
        rng_after=working_rng.describe(),
    )

    rng.replace_from(working_rng)
    trace.extend_from(staged_trace)

    return DayTransactionResult(
        transaction_id=transaction_id,
        day_from=day_from,
        day_to=day_to,
        states=advanced_states,
        candidate_results=candidate_results,
        events=events,
        proposals=proposals,
        resolutions=resolution.records,
        state_hashes_before=state_hashes_before,
        state_hashes_after=state_hashes_after,
    )
