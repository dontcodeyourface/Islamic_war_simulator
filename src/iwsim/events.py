from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .graph import GraphEdge
from .manifest import RunManifest
from .rng import RNGManager
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimEvent:
    event_id: str
    event_type: str
    provenance_class: str
    day_created: int
    day_effective: int
    duration_days: int
    actors: tuple[str, ...]
    source_nodes: tuple[str, ...]
    target_nodes: tuple[str, ...]
    hazard_score: float
    occurrence_probability: float | None
    random_draw: float | None
    generated_threshold: float
    feature_values: tuple[tuple[str, float], ...]
    parameter_ids: tuple[str, ...]
    parent_event_ids: tuple[str, ...]
    causal_trace_id: str
    scenario_id: str
    run_id: str
    rng_stream: str | None
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        logger.info("SimEvent.to_dict event_id=%s", self.event_id)
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "provenance_class": self.provenance_class,
            "day_created": self.day_created,
            "day_effective": self.day_effective,
            "duration_days": self.duration_days,
            "actors": list(self.actors),
            "source_nodes": list(self.source_nodes),
            "target_nodes": list(self.target_nodes),
            "hazard_score": self.hazard_score,
            "occurrence_probability": self.occurrence_probability,
            "random_draw": self.random_draw,
            "generated_threshold": self.generated_threshold,
            "feature_values": dict(self.feature_values),
            "parameter_ids": list(self.parameter_ids),
            "parent_event_ids": list(self.parent_event_ids),
            "causal_trace_id": self.causal_trace_id,
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "rng_stream": self.rng_stream,
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class EventCandidateResult:
    event_type: str
    occurred: bool
    provenance_class: str | None
    hazard_score: float
    occurrence_probability: float | None
    random_draw: float | None
    generated_threshold: float
    feature_values: tuple[tuple[str, float], ...]
    event: SimEvent | None

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "EventCandidateResult.to_dict event_type=%s occurred=%s",
            self.event_type,
            self.occurred,
        )
        return {
            "event_type": self.event_type,
            "occurred": self.occurred,
            "provenance_class": self.provenance_class,
            "hazard_score": self.hazard_score,
            "occurrence_probability": self.occurrence_probability,
            "random_draw": self.random_draw,
            "generated_threshold": self.generated_threshold,
            "feature_values": dict(self.feature_values),
            "event": self.event.to_dict() if self.event is not None else None,
        }


def _clamp01(value: float) -> float:
    logger.info("_clamp01 value=%s", value)
    return min(1.0, max(0.0, float(value)))


def _parameter(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info("_parameter profile=%s parameter_id=%s", profile, parameter_id)
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(f"Missing event parameter {parameter_id} for {profile}")
    return parameter["value"]


def _hazard_config(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    event_type: str,
) -> tuple[dict[str, Any], str]:
    logger.info("_hazard_config profile=%s event_type=%s", profile, event_type)
    parameter_id = (
        "EVENT_HAZARD_WEIGHTS_SYN_V1"
        if profile == "synthetic_smoke_v1"
        else "EVENT_HAZARD_WEIGHTS_CAL_V1"
    )
    value = _parameter(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    if event_type not in value:
        raise ValueError(f"Unsupported event type {event_type}")
    return value[event_type], parameter_id


def _probability_config(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
) -> tuple[dict[str, Any], str]:
    logger.info("_probability_config profile=%s", profile)
    parameter_id = (
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
        if profile == "synthetic_smoke_v1"
        else "EVENT_HAZARD_PROBABILITY_CAL_V1"
    )
    return (
        _parameter(
            parameter_registry,
            profile=profile,
            parameter_id=parameter_id,
        ),
        parameter_id,
    )


def interstate_incident_features(
    state_a: EngineState,
    state_b: EngineState,
    edge: GraphEdge,
) -> dict[str, float]:
    logger.info(
        "interstate_incident_features a=%s b=%s edge=%s",
        state_a.node_id,
        state_b.node_id,
        edge.edge_id(),
    )
    geographic = edge.channel(
        state_a.node_id,
        state_b.node_id,
        "geographic_proximity",
    )
    land_border = edge.channel(
        state_a.node_id,
        state_b.node_id,
        "land_border",
    )
    alliance = edge.channel(
        state_a.node_id,
        state_b.node_id,
        "alliance_link",
    )
    if geographic is None or land_border is None or alliance is None:
        raise ValueError("Interstate incident requires resolved structural graph channels")
    return {
        "external_conflict_pressure_mean": (
            state_a.latents["external_conflict_pressure"]
            + state_b.latents["external_conflict_pressure"]
        )
        / 2.0,
        "geographic_proximity": geographic,
        "land_border": land_border,
        "alliance_deterrence": alliance,
    }


def mass_protest_features(state: EngineState) -> dict[str, float]:
    logger.info("mass_protest_features node_id=%s", state.node_id)
    return {
        "polarization": state.latents["polarization"],
        "inflation_pressure": state.latents["inflation_pressure"],
        "unemployment_pressure": state.latents["unemployment_pressure"],
        "government_legitimacy_inverse": 1.0
        - state.latents["government_legitimacy"],
        "social_cohesion": state.latents["social_cohesion"],
    }


def compute_hazard_score(
    *,
    event_type: str,
    features: dict[str, float],
    parameter_registry: dict[str, Any],
    profile: str,
) -> tuple[float, float, str]:
    logger.info(
        "compute_hazard_score event_type=%s profile=%s",
        event_type,
        profile,
    )
    config, parameter_id = _hazard_config(
        parameter_registry,
        profile=profile,
        event_type=event_type,
    )
    score = float(config["base_score"])
    weights = config["weights"]
    missing = sorted(set(weights) - set(features))
    extra = sorted(set(features) - set(weights))
    if missing or extra:
        raise ValueError(
            f"Feature mismatch for {event_type}: missing={missing} extra={extra}"
        )
    for feature_name, weight in weights.items():
        score += float(weight) * float(features[feature_name])
    return _clamp01(score), float(config["generated_threshold"]), parameter_id


def score_to_probability(
    *,
    hazard_score: float,
    parameter_registry: dict[str, Any],
    profile: str,
) -> tuple[float, str]:
    logger.info(
        "score_to_probability hazard_score=%s profile=%s",
        hazard_score,
        profile,
    )
    config, parameter_id = _probability_config(
        parameter_registry,
        profile=profile,
    )
    probability = float(config["p_floor"]) + float(config["score_scale"]) * float(
        hazard_score
    )
    return _clamp01(probability), parameter_id


def _deterministic_event_id(
    *,
    manifest: RunManifest,
    day: int,
    event_type: str,
    actors: tuple[str, ...],
) -> str:
    logger.info(
        "_deterministic_event_id day=%s event_type=%s actors=%s",
        day,
        event_type,
        actors,
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "day": day,
            "event_type": event_type,
            "actors": list(actors),
        }
    )
    return f"evt-{digest[:24]}"


def evaluate_candidate(
    *,
    event_type: str,
    day: int,
    actors: tuple[str, ...],
    source_nodes: tuple[str, ...],
    target_nodes: tuple[str, ...],
    features: dict[str, float],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> EventCandidateResult:
    logger.info(
        "evaluate_candidate event_type=%s day=%s actors=%s",
        event_type,
        day,
        actors,
    )
    hazard_score, generated_threshold, weight_parameter_id = compute_hazard_score(
        event_type=event_type,
        features=features,
        parameter_registry=parameter_registry,
        profile=profile,
    )
    occurrence_probability, probability_parameter_id = score_to_probability(
        hazard_score=hazard_score,
        parameter_registry=parameter_registry,
        profile=profile,
    )

    provenance_class: str | None = None
    random_draw: float | None = None
    rng_stream: str | None = None

    if hazard_score >= generated_threshold:
        occurred = True
        provenance_class = "GENERATED"
    else:
        rng_stream = "events:" + event_type + ":" + "--".join(sorted(actors))
        stream = rng.stream(rng_stream)
        draw_index = stream.draw_index
        random_draw = stream.random()
        occurred = random_draw < occurrence_probability
        if occurred:
            provenance_class = "RANDOM_SHOCK"
        trace.append(
            "event_rng_draw",
            run_id=manifest.run_id,
            day=day,
            event_type=event_type,
            actors=list(actors),
            rng_stream=rng_stream,
            draw_index=draw_index,
            random_draw=random_draw,
            occurrence_probability=occurrence_probability,
        )

    event: SimEvent | None = None
    if occurred and provenance_class is not None:
        event_id = _deterministic_event_id(
            manifest=manifest,
            day=day,
            event_type=event_type,
            actors=actors,
        )
        causal_trace_id = "cause-" + canonical_hash(
            {"event_id": event_id, "hazard": hazard_score}
        )[:24]
        event = SimEvent(
            event_id=event_id,
            event_type=event_type,
            provenance_class=provenance_class,
            day_created=day,
            day_effective=day,
            duration_days=1,
            actors=actors,
            source_nodes=source_nodes,
            target_nodes=target_nodes,
            hazard_score=hazard_score,
            occurrence_probability=(
                None if provenance_class == "GENERATED" else occurrence_probability
            ),
            random_draw=(None if provenance_class == "GENERATED" else random_draw),
            generated_threshold=generated_threshold,
            feature_values=tuple(sorted(features.items())),
            parameter_ids=(weight_parameter_id, probability_parameter_id),
            parent_event_ids=(),
            causal_trace_id=causal_trace_id,
            scenario_id=manifest.scenario_id,
            run_id=manifest.run_id,
            rng_stream=(None if provenance_class == "GENERATED" else rng_stream),
            dry_run=True,
        )
        trace.append("event_created", **event.to_dict())

    trace.append(
        "event_candidate",
        run_id=manifest.run_id,
        day=day,
        event_type=event_type,
        actors=list(actors),
        hazard_score=hazard_score,
        generated_threshold=generated_threshold,
        occurrence_probability=occurrence_probability,
        random_draw=random_draw,
        occurred=occurred,
        provenance_class=provenance_class,
        feature_values=dict(sorted(features.items())),
        parameter_ids=[weight_parameter_id, probability_parameter_id],
        dry_run=True,
    )
    return EventCandidateResult(
        event_type=event_type,
        occurred=occurred,
        provenance_class=provenance_class,
        hazard_score=hazard_score,
        occurrence_probability=occurrence_probability,
        random_draw=random_draw,
        generated_threshold=generated_threshold,
        feature_values=tuple(sorted(features.items())),
        event=event,
    )


def evaluate_interstate_incident(
    *,
    day: int,
    state_a: EngineState,
    state_b: EngineState,
    edge: GraphEdge,
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> EventCandidateResult:
    logger.info(
        "evaluate_interstate_incident day=%s a=%s b=%s",
        day,
        state_a.node_id,
        state_b.node_id,
    )
    actors = tuple(sorted((state_a.node_id, state_b.node_id)))
    return evaluate_candidate(
        event_type="INTERSTATE_INCIDENT_V1",
        day=day,
        actors=actors,
        source_nodes=actors,
        target_nodes=actors,
        features=interstate_incident_features(state_a, state_b, edge),
        parameter_registry=parameter_registry,
        profile=profile,
        rng=rng,
        manifest=manifest,
        trace=trace,
    )


def evaluate_mass_protest(
    *,
    day: int,
    state: EngineState,
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    manifest: RunManifest,
    trace: TraceLedger,
) -> EventCandidateResult:
    logger.info("evaluate_mass_protest day=%s node_id=%s", day, state.node_id)
    actors = (state.node_id,)
    return evaluate_candidate(
        event_type="MASS_PROTEST_TRIGGER_V1",
        day=day,
        actors=actors,
        source_nodes=actors,
        target_nodes=actors,
        features=mass_protest_features(state),
        parameter_registry=parameter_registry,
        profile=profile,
        rng=rng,
        manifest=manifest,
        trace=trace,
    )
