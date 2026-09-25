from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .manifest import RunManifest
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)

CANONICAL_COMPONENTS = (
    "violence",
    "institutional_stress",
    "infrastructure_stress",
    "network_activity",
    "displacement",
)

SUPPORTED_BASE_LEVELS = ("L1_COUNTRY", "L2_REGION")
SUPPORTED_RESOLUTION_LEVELS = (
    "L1_COUNTRY",
    "L2_REGION",
    "L3_METRO_OR_LOGISTICS_AREA",
)
NEXT_RESOLUTION_LEVEL = {
    "L1_COUNTRY": "L2_REGION",
    "L2_REGION": "L3_METRO_OR_LOGISTICS_AREA",
}


@dataclass(frozen=True)
class FractalComponentScore:
    component: str
    score: float
    source_values: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalComponentScore.to_dict component=%s score=%s",
            self.component,
            self.score,
        )
        return {
            "component": self.component,
            "score": self.score,
            "source_values": dict(self.source_values),
        }


@dataclass(frozen=True)
class FractalRefinementPersistenceState:
    node_id: str
    current_level: str
    last_evaluated_day: int
    expand_streak: int
    collapse_streak: int

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRefinementPersistenceState.to_dict node=%s level=%s day=%s",
            self.node_id,
            self.current_level,
            self.last_evaluated_day,
        )
        return {
            "node_id": self.node_id,
            "current_level": self.current_level,
            "last_evaluated_day": self.last_evaluated_day,
            "expand_streak": self.expand_streak,
            "collapse_streak": self.collapse_streak,
        }


@dataclass(frozen=True)
class FractalRefinementActionProposal:
    action_id: str
    node_id: str
    day: int
    action: str
    from_level: str
    to_level: str
    refinement_pressure: float
    threshold: float
    persistence_required: int
    persistence_observed: int
    refinement_reason: str
    component_scores: tuple[FractalComponentScore, ...]
    source_variables: tuple[str, ...]
    equation_id: str
    parameter_id: str
    initialization_weight_policy_id: str
    inherited_uncertainty_policy_id: str
    aggregation_rule_id: str
    apply_status: str = "PROPOSED_NOT_APPLIED"

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRefinementActionProposal.to_dict action_id=%s action=%s",
            self.action_id,
            self.action,
        )
        return {
            "action_id": self.action_id,
            "node_id": self.node_id,
            "day": self.day,
            "action": self.action,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "refinement_pressure": self.refinement_pressure,
            "threshold": self.threshold,
            "persistence_required": self.persistence_required,
            "persistence_observed": self.persistence_observed,
            "refinement_reason": self.refinement_reason,
            "component_scores": [
                item.to_dict() for item in self.component_scores
            ],
            "source_variables": list(self.source_variables),
            "equation_id": self.equation_id,
            "parameter_id": self.parameter_id,
            "initialization_weight_policy_id": (
                self.initialization_weight_policy_id
            ),
            "inherited_uncertainty_policy_id": (
                self.inherited_uncertainty_policy_id
            ),
            "aggregation_rule_id": self.aggregation_rule_id,
            "apply_status": self.apply_status,
        }


@dataclass(frozen=True)
class FractalRefinementEvaluationResult:
    persistence: FractalRefinementPersistenceState
    component_scores: tuple[FractalComponentScore, ...]
    refinement_pressure: float
    expand_threshold: float
    collapse_threshold: float
    proposals: tuple[FractalRefinementActionProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRefinementEvaluationResult.to_dict node=%s proposals=%s",
            self.persistence.node_id,
            len(self.proposals),
        )
        return {
            "persistence": self.persistence.to_dict(),
            "component_scores": [
                item.to_dict() for item in self.component_scores
            ],
            "refinement_pressure": self.refinement_pressure,
            "expand_threshold": self.expand_threshold,
            "collapse_threshold": self.collapse_threshold,
            "proposals": [item.to_dict() for item in self.proposals],
        }


def _parameter_id(profile: str) -> str:
    logger.info("_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "FRACTAL_REFINEMENT_SYN_V1"
    if profile == "calibrated_v1":
        return "FRACTAL_REFINEMENT_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _parameter_value(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info(
        "_parameter_value profile=%s parameter_id=%s",
        profile,
        parameter_id,
    )
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing fractal-refinement parameter {parameter_id} for {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Fractal-refinement parameter {parameter_id} "
            "must contain a mapping value"
        )
    return value


def _validate_source(item: Any) -> dict[str, str]:
    logger.info("_validate_source")
    if not isinstance(item, dict):
        raise ValueError("Fractal component source must be a mapping")
    variable = str(item.get("variable", ""))
    transform = str(item.get("transform", ""))
    if not variable or transform not in {"identity", "one_minus"}:
        raise ValueError(f"Invalid fractal component source: {item}")
    return {"variable": variable, "transform": transform}


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    logger.info("_validate_config")
    mode = config.get("mode", {})
    if mode.get("read_only") is not True:
        raise ValueError("v0.19 fractal evaluator requires read_only=true")
    if mode.get("node_materialization_allowed") is not False:
        raise ValueError("v0.19 forbids fractal node materialization")
    if mode.get("one_level_per_action") is not True:
        raise ValueError("v0.19 requires one-level refinement actions")

    if config.get("equation_id") != "REFINEMENT_TRIGGER_V1":
        raise ValueError("Unsupported fractal refinement equation_id")

    levels = tuple(
        str(item)
        for item in config.get(
            "supported_base_levels",
            config.get("supported_levels", []),
        )
    )
    if levels != SUPPORTED_BASE_LEVELS:
        raise ValueError(
            "Fractal evaluator supported base levels must remain canonical"
        )

    components_raw = config.get("components")
    if not isinstance(components_raw, dict):
        raise ValueError("Fractal components must be a mapping")
    if tuple(sorted(components_raw)) != tuple(sorted(CANONICAL_COMPONENTS)):
        raise ValueError("Fractal component set must remain canonical")

    components: dict[str, tuple[dict[str, str], ...]] = {}
    for component in CANONICAL_COMPONENTS:
        raw = components_raw[component]
        if not isinstance(raw, dict):
            raise ValueError(f"Fractal component {component} must be a mapping")
        if raw.get("reduction") != "mean":
            raise ValueError(
                f"Fractal component {component} must use mean reduction"
            )
        sources = raw.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError(
                f"Fractal component {component} requires sources"
            )
        normalized = tuple(_validate_source(item) for item in sources)
        source_vars = [item["variable"] for item in normalized]
        if len(source_vars) != len(set(source_vars)):
            raise ValueError(
                f"Duplicate source variable in fractal component {component}"
            )
        components[component] = normalized

    lineage = config.get("lineage_policy")
    if not isinstance(lineage, dict):
        raise ValueError("Fractal lineage_policy must be a mapping")
    required_lineage = (
        "initialization_weight_policy_id",
        "inherited_uncertainty_policy_id",
        "aggregation_rule_id",
    )
    for key in required_lineage:
        if not str(lineage.get(key, "")):
            raise ValueError(f"Fractal lineage policy missing {key}")

    safety = config.get("safety", {})
    if safety.get("civilian_identity_direct_refinement_input") is not False:
        raise ValueError(
            "Civilian identity must not be a direct fractal refinement input"
        )
    if safety.get("refinement_is_resolution_not_outcome") is not True:
        raise ValueError(
            "Fractal refinement must remain a resolution decision"
        )

    return {
        "equation_id": str(config["equation_id"]),
        "components": components,
        "lineage_policy": {
            key: str(lineage[key]) for key in required_lineage
        },
    }


def _transform(value: float, transform: str) -> float:
    logger.info("_transform value=%s transform=%s", value, transform)
    if transform == "identity":
        return value
    if transform == "one_minus":
        return 1.0 - value
    raise ValueError(f"Unsupported fractal transform {transform}")


def _component_score(
    *,
    state: EngineState,
    component: str,
    sources: tuple[dict[str, str], ...],
) -> FractalComponentScore:
    logger.info(
        "_component_score node=%s component=%s sources=%s",
        state.node_id,
        component,
        len(sources),
    )
    values: list[tuple[str, float]] = []
    for source in sources:
        variable = source["variable"]
        if variable not in state.latents:
            raise KeyError(
                f"Fractal source variable {variable} missing from {state.node_id}"
            )
        raw = float(state.latents[variable])
        if not math.isfinite(raw) or not 0.0 <= raw <= 1.0:
            raise ValueError(
                f"Fractal source {state.node_id}.{variable} outside [0,1]"
            )
        transformed = _transform(raw, source["transform"])
        if not 0.0 <= transformed <= 1.0:
            raise ValueError(
                f"Fractal transformed source {variable} outside [0,1]"
            )
        values.append((variable, transformed))

    score = math.fsum(value for _, value in values) / len(values)
    return FractalComponentScore(
        component=component,
        score=score,
        source_values=tuple(sorted(values)),
    )


def _validate_parameters(
    parameters: dict[str, Any],
) -> tuple[dict[str, float], float, int, float, int]:
    logger.info("_validate_parameters")
    weights_raw = parameters.get("weights")
    if not isinstance(weights_raw, dict):
        raise ValueError("Fractal refinement weights must be a mapping")
    if set(weights_raw) != set(CANONICAL_COMPONENTS):
        raise ValueError(
            "Fractal refinement weight keys must match canonical components"
        )
    weights = {key: float(value) for key, value in weights_raw.items()}
    if any(
        not math.isfinite(value) or value < 0.0
        for value in weights.values()
    ):
        raise ValueError(
            "Fractal refinement weights must be finite and non-negative"
        )
    if not math.isclose(
        math.fsum(weights.values()),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("Fractal refinement weights must sum to 1.0")

    expand_threshold = float(parameters["expand_threshold"])
    collapse_threshold = float(parameters["collapse_threshold"])
    expand_days = int(parameters["expand_persistence_days"])
    collapse_days = int(parameters["collapse_persistence_days"])

    if not (
        0.0
        <= collapse_threshold
        < expand_threshold
        <= 1.0
    ):
        raise ValueError(
            "Fractal refinement requires "
            "0 <= collapse_threshold < expand_threshold <= 1"
        )
    if expand_days < 1 or collapse_days < 1:
        raise ValueError(
            "Fractal refinement persistence windows must be >= 1"
        )
    return (
        weights,
        expand_threshold,
        expand_days,
        collapse_threshold,
        collapse_days,
    )


def _node_base_level(state: EngineState) -> str:
    logger.info("_node_base_level node=%s", state.node_id)
    raw = state.metadata.get("fractal_level")
    base_level = "L1_COUNTRY" if raw is None else str(raw)
    if base_level not in SUPPORTED_BASE_LEVELS:
        raise ValueError(
            f"Unsupported fractal base level {base_level} for {state.node_id}"
        )
    return base_level


def _initial_persistence(
    *,
    state: EngineState,
    persistence: FractalRefinementPersistenceState | None,
    base_level: str,
) -> tuple[str, int, int]:
    logger.info(
        "_initial_persistence node=%s day=%s base=%s supplied=%s",
        state.node_id,
        state.day,
        base_level,
        persistence is not None,
    )
    if persistence is None:
        return base_level, 0, 0
    if persistence.node_id != state.node_id:
        raise ValueError("Fractal refinement persistence node mismatch")
    if state.day != persistence.last_evaluated_day + 1:
        raise ValueError(
            "Fractal refinement persistence requires consecutive days: "
            f"last={persistence.last_evaluated_day} current={state.day}"
        )
    if persistence.current_level not in SUPPORTED_RESOLUTION_LEVELS:
        raise ValueError(
            f"Unsupported fractal resolution level "
            f"{persistence.current_level}"
        )
    allowed = {
        base_level,
        NEXT_RESOLUTION_LEVEL[base_level],
    }
    if persistence.current_level not in allowed:
        raise ValueError(
            f"Persistence level {persistence.current_level} is not adjacent "
            f"to base level {base_level}"
        )
    return (
        persistence.current_level,
        persistence.expand_streak,
        persistence.collapse_streak,
    )


def _reason(component_scores: tuple[FractalComponentScore, ...]) -> str:
    logger.info("_reason components=%s", len(component_scores))
    ranked = sorted(
        component_scores,
        key=lambda item: (-item.score, item.component),
    )
    return ranked[0].component


def _action_id(
    *,
    manifest: RunManifest,
    state: EngineState,
    action: str,
    from_level: str,
    to_level: str,
    pressure: float,
    parameter_id: str,
) -> str:
    logger.info(
        "_action_id node=%s day=%s action=%s",
        state.node_id,
        state.day,
        action,
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "node_id": state.node_id,
            "day": state.day,
            "action": action,
            "from_level": from_level,
            "to_level": to_level,
            "refinement_pressure": pressure,
            "equation_id": "REFINEMENT_TRIGGER_V1",
            "parameter_id": parameter_id,
        }
    )
    return f"refine-{digest[:24]}"


def evaluate_fractal_refinement(
    *,
    state: EngineState,
    persistence: FractalRefinementPersistenceState | None,
    refinement_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> FractalRefinementEvaluationResult:
    """Evaluate one read-only adjacent refinement/collapse decision."""
    logger.info(
        "evaluate_fractal_refinement node=%s day=%s profile=%s",
        state.node_id,
        state.day,
        profile,
    )
    state_hash_before = state.state_hash()
    config = _validate_config(refinement_config)
    parameter_id = _parameter_id(profile)
    parameters = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    (
        weights,
        expand_threshold,
        expand_days,
        collapse_threshold,
        collapse_days,
    ) = _validate_parameters(parameters)

    component_scores = tuple(
        _component_score(
            state=state,
            component=component,
            sources=config["components"][component],
        )
        for component in CANONICAL_COMPONENTS
    )
    score_by_component = {
        item.component: item.score for item in component_scores
    }
    refinement_pressure = math.fsum(
        weights[component] * score_by_component[component]
        for component in CANONICAL_COMPONENTS
    )
    if not 0.0 <= refinement_pressure <= 1.0:
        raise ValueError("Fractal refinement pressure outside [0,1]")

    base_level = _node_base_level(state)
    current_level, prior_expand, prior_collapse = _initial_persistence(
        state=state,
        persistence=persistence,
        base_level=base_level,
    )
    expand_streak = 0
    collapse_streak = 0
    proposals: list[FractalRefinementActionProposal] = []

    refined_level = NEXT_RESOLUTION_LEVEL[base_level]
    if current_level == base_level:
        expand_streak = (
            prior_expand + 1
            if refinement_pressure >= expand_threshold
            else 0
        )
        matured = expand_streak >= expand_days
        action = "EXPAND"
        from_level = base_level
        to_level = refined_level
        threshold = expand_threshold
        observed = expand_streak
        required = expand_days
    elif current_level == refined_level:
        collapse_streak = (
            prior_collapse + 1
            if refinement_pressure <= collapse_threshold
            else 0
        )
        matured = collapse_streak >= collapse_days
        action = "COLLAPSE"
        from_level = refined_level
        to_level = base_level
        threshold = collapse_threshold
        observed = collapse_streak
        required = collapse_days
    else:
        raise ValueError(
            f"Unsupported active resolution {current_level} "
            f"for base level {base_level}"
        )

    source_variables = tuple(
        sorted(
            {
                variable
                for item in component_scores
                for variable, _ in item.source_values
            }
        )
    )
    reason = _reason(component_scores)
    trace.append(
        "fractal_refinement_evaluation",
        node_id=state.node_id,
        day=state.day,
        current_level=current_level,
        base_level=base_level,
        refinement_pressure=refinement_pressure,
        component_scores=[
            item.to_dict() for item in component_scores
        ],
        weights=dict(sorted(weights.items())),
        expand_threshold=expand_threshold,
        collapse_threshold=collapse_threshold,
        action_considered=action,
        persistence_required=required,
        persistence_observed=observed,
        matured=matured,
        refinement_reason=reason,
        equation_id=config["equation_id"],
        parameter_id=parameter_id,
    )

    if matured:
        lineage = config["lineage_policy"]
        proposal = FractalRefinementActionProposal(
            action_id=_action_id(
                manifest=manifest,
                state=state,
                action=action,
                from_level=from_level,
                to_level=to_level,
                pressure=refinement_pressure,
                parameter_id=parameter_id,
            ),
            node_id=state.node_id,
            day=state.day,
            action=action,
            from_level=from_level,
            to_level=to_level,
            refinement_pressure=refinement_pressure,
            threshold=threshold,
            persistence_required=required,
            persistence_observed=observed,
            refinement_reason=reason,
            component_scores=component_scores,
            source_variables=source_variables,
            equation_id=config["equation_id"],
            parameter_id=parameter_id,
            initialization_weight_policy_id=lineage[
                "initialization_weight_policy_id"
            ],
            inherited_uncertainty_policy_id=lineage[
                "inherited_uncertainty_policy_id"
            ],
            aggregation_rule_id=lineage["aggregation_rule_id"],
        )
        proposals.append(proposal)
        trace.append(
            "fractal_refinement_action_proposal",
            **proposal.to_dict(),
        )

    persistence_out = FractalRefinementPersistenceState(
        node_id=state.node_id,
        current_level=current_level,
        last_evaluated_day=state.day,
        expand_streak=expand_streak,
        collapse_streak=collapse_streak,
    )

    if state.state_hash() != state_hash_before:
        raise RuntimeError(
            "Read-only fractal refinement evaluator mutated EngineState"
        )

    return FractalRefinementEvaluationResult(
        persistence=persistence_out,
        component_scores=component_scores,
        refinement_pressure=refinement_pressure,
        expand_threshold=expand_threshold,
        collapse_threshold=collapse_threshold,
        proposals=tuple(proposals),
    )
