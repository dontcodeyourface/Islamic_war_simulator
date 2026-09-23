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
from .graph import CountryGraph
from .manifest import RunManifest
from .resolver import ResolutionRecord, resolve_delta_proposals
from .rng import RNGManager
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


def _transaction_id(
    *,
    manifest: RunManifest,
    day_from: int,
    graph: CountryGraph,
    states: dict[str, EngineState],
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


def _checkpoint_node(
    *,
    node_id: str,
    state_before: EngineState,
    state_after: EngineState,
    events: tuple[SimEvent, ...],
    resolutions: tuple[ResolutionRecord, ...],
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
    trace.append_daily_checkpoint(
        run_id=manifest.run_id,
        day=state_after.day,
        node_id=node_id,
        state_hash_before=state_before.state_hash(),
        state_hash_after=state_after.state_hash(),
        module_deltas=node_resolutions,
        event_ids_applied=node_events,
        constraint_clamps=clamp_resolutions,
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
    transaction_id = _transaction_id(
        manifest=manifest,
        day_from=day_from,
        graph=graph,
        states=states,
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
    proposals = _propose_all_effects(
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
    advanced_states = _advance_resolved_states(
        resolved_states=resolution.states,
        engine_state_registry=engine_state_registry,
    )

    for node_id in sorted(states):
        _checkpoint_node(
            node_id=node_id,
            state_before=states[node_id],
            state_after=advanced_states[node_id],
            events=events,
            resolutions=resolution.records,
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
        state_hashes_after={
            node_id: state.state_hash()
            for node_id, state in sorted(advanced_states.items())
        },
    )

    rng.replace_from(working_rng)
    trace.extend_from(staged_trace)

    return DayTransactionResult(
        transaction_id=transaction_id,
        day_from=day_from,
        day_to=day_to,
        states=advanced_states,
        candidates=candidates,
        events=events,
        proposals=proposals,
        resolutions=resolution.records,
    )
