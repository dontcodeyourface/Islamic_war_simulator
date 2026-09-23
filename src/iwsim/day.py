from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

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
class DailyCandidate:
    candidate_key: str
    actors: tuple[str, ...]
    result: EventCandidateResult

    def to_dict(self) -> dict[str, Any]:
        logger.info("DailyCandidate.to_dict candidate_key=%s", self.candidate_key)
        return {
            "candidate_key": self.candidate_key,
            "actors": list(self.actors),
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True)
class AtomicDayResult:
    transaction_day: int
    states: dict[str, EngineState]
    candidates: tuple[DailyCandidate, ...]
    events: tuple[SimEvent, ...]
    proposals: tuple[DeltaProposal, ...]
    resolutions: tuple[ResolutionRecord, ...]
    pre_hashes: tuple[tuple[str, str], ...]
    post_hashes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "AtomicDayResult.to_dict day=%s events=%s proposals=%s resolutions=%s",
            self.transaction_day,
            len(self.events),
            len(self.proposals),
            len(self.resolutions),
        )
        return {
            "transaction_day": self.transaction_day,
            "states": {
                node_id: state.to_dict()
                for node_id, state in sorted(self.states.items())
            },
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "events": [event.to_dict() for event in self.events],
            "proposals": [proposal.to_dict() for proposal in self.proposals],
            "resolutions": [record.to_dict() for record in self.resolutions],
            "pre_hashes": dict(self.pre_hashes),
            "post_hashes": dict(self.post_hashes),
        }


def _validate_pre_states(
    *,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    engine_state_registry: dict[str, Any],
) -> int:
    logger.info(
        "_validate_pre_states state_nodes=%s graph_nodes=%s",
        sorted(states),
        list(graph.nodes),
    )
    if not states:
        raise ValueError("Atomic day requires at least one state")

    graph_nodes = set(graph.nodes)
    unknown_nodes = sorted(set(states) - graph_nodes)
    if unknown_nodes:
        raise ValueError(f"State nodes absent from graph: {unknown_nodes}")

    days = {state.day for state in states.values()}
    if len(days) != 1:
        raise ValueError(f"Atomic day requires synchronized state days, got {sorted(days)}")

    latent_registry = extract_latent_registry(engine_state_registry)
    for node_id, state in sorted(states.items()):
        if state.node_id != node_id:
            raise ValueError(
                f"State dictionary key {node_id} does not match state.node_id {state.node_id}"
            )
        state.validate(latent_registry)

    return next(iter(days))


def _evaluate_candidates(
    *,
    transaction_day: int,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[DailyCandidate, ...]:
    logger.info(
        "_evaluate_candidates transaction_day=%s states=%s",
        transaction_day,
        sorted(states),
    )
    candidates: list[DailyCandidate] = []

    for edge in sorted(graph.edges, key=lambda item: item.edge_id()):
        if edge.a not in states or edge.b not in states:
            continue
        actors = tuple(sorted((edge.a, edge.b)))
        result = evaluate_interstate_incident(
            day=transaction_day,
            state_a=states[edge.a],
            state_b=states[edge.b],
            edge=edge,
            parameter_registry=parameter_registry,
            profile=profile,
            rng=rng,
            manifest=manifest,
            trace=trace,
            dry_run=False,
        )
        candidates.append(
            DailyCandidate(
                candidate_key="INTERSTATE_INCIDENT_V1:" + "--".join(actors),
                actors=actors,
                result=result,
            )
        )

    for node_id in sorted(states):
        result = evaluate_mass_protest(
            day=transaction_day,
            state=states[node_id],
            parameter_registry=parameter_registry,
            profile=profile,
            rng=rng,
            manifest=manifest,
            trace=trace,
            dry_run=False,
        )
        candidates.append(
            DailyCandidate(
                candidate_key=f"MASS_PROTEST_TRIGGER_V1:{node_id}",
                actors=(node_id,),
                result=result,
            )
        )

    return tuple(candidates)


def _collect_events(candidates: tuple[DailyCandidate, ...]) -> tuple[SimEvent, ...]:
    logger.info("_collect_events candidates=%s", len(candidates))
    events = [
        candidate.result.event
        for candidate in candidates
        if candidate.result.event is not None
    ]
    return tuple(sorted(events, key=lambda event: event.event_id))


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


def _advance_states(
    *,
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
    expected_day: int,
) -> dict[str, EngineState]:
    logger.info("_advance_states states=%s expected_day=%s", len(states), expected_day)
    latent_registry = extract_latent_registry(engine_state_registry)
    advanced: dict[str, EngineState] = {}
    for node_id, state in sorted(states.items()):
        next_state = state.clone_for_next_day()
        if next_state.day != expected_day:
            raise ValueError(
                f"Unexpected next day for {node_id}: {next_state.day} != {expected_day}"
            )
        next_state.validate(latent_registry)
        advanced[node_id] = next_state
    return advanced


def _hash_states(states: dict[str, EngineState]) -> tuple[tuple[str, str], ...]:
    logger.info("_hash_states states=%s", len(states))
    return tuple(
        (node_id, state.state_hash())
        for node_id, state in sorted(states.items())
    )


def run_atomic_day(
    *,
    states: dict[str, EngineState],
    graph: StructuralGraph,
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> AtomicDayResult:
    """Execute one atomic multi-node day without phase classification."""
    logger.info(
        "run_atomic_day run_id=%s states=%s profile=%s",
        manifest.run_id,
        sorted(states),
        profile,
    )
    current_day = _validate_pre_states(
        states=states,
        graph=graph,
        engine_state_registry=engine_state_registry,
    )
    if manifest.time_step_days != 1:
        raise ValueError("AtomicDay v0.7 requires a 1-day time step")

    transaction_day = current_day + 1
    pre_hashes = _hash_states(states)

    candidates = _evaluate_candidates(
        transaction_day=transaction_day,
        states=states,
        graph=graph,
        parameter_registry=parameter_registry,
        profile=profile,
        rng=rng,
        manifest=manifest,
        trace=trace,
    )
    events = _collect_events(candidates)
    proposals = _collect_proposals(
        events=events,
        states=states,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=trace,
    )

    resolution = resolve_delta_proposals(
        states=states,
        proposals=proposals,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
        trace=trace,
    )
    advanced_states = _advance_states(
        states=resolution.states,
        engine_state_registry=engine_state_registry,
        expected_day=transaction_day,
    )
    post_hashes = _hash_states(advanced_states)

    event_ids = tuple(event.event_id for event in events)
    proposal_ids = tuple(proposal.proposal_id for proposal in proposals)
    resolution_ids = tuple(record.resolution_id for record in resolution.records)

    for node_id in sorted(states):
        node_event_ids = tuple(
            event.event_id for event in events if node_id in event.actors
        )
        node_proposal_ids = tuple(
            proposal.proposal_id
            for proposal in proposals
            if proposal.target_node == node_id
        )
        node_resolution_ids = tuple(
            record.resolution_id
            for record in resolution.records
            if record.target_node == node_id
        )
        node_candidate_count = sum(
            1 for candidate in candidates if node_id in candidate.actors
        )
        trace.append_daily_checkpoint(
            run_id=manifest.run_id,
            day=transaction_day,
            node_id=node_id,
            state_hash_before=dict(pre_hashes)[node_id],
            state_hash_after=dict(post_hashes)[node_id],
            candidate_count=node_candidate_count,
            event_ids_applied=node_event_ids,
            proposal_ids=node_proposal_ids,
            resolution_ids=node_resolution_ids,
        )

    trace.append(
        "daily_transaction",
        run_id=manifest.run_id,
        transaction_day=transaction_day,
        pre_hashes=dict(pre_hashes),
        post_hashes=dict(post_hashes),
        candidate_count=len(candidates),
        event_ids=list(event_ids),
        proposal_ids=list(proposal_ids),
        resolution_ids=list(resolution_ids),
        phase_transitions_enabled=False,
    )

    return AtomicDayResult(
        transaction_day=transaction_day,
        states=advanced_states,
        candidates=candidates,
        events=events,
        proposals=proposals,
        resolutions=resolution.records,
        pre_hashes=pre_hashes,
        post_hashes=post_hashes,
    )
