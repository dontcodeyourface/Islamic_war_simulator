from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)

EXPECTED_NETWORK_VARIABLES = frozenset(
    {
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
    }
)
EXPECTED_DAMPING_VARIABLES = frozenset(
    {
        "social_cohesion",
        "government_legitimacy",
        "police_effective_capacity",
        "intelligence_effectiveness",
    }
)
EXPECTED_FEAR_VARIABLE = "communal_fear"
EXPECTED_NARRATIVE_VARIABLE = "civilizational_narrative_strength"


@dataclass(frozen=True)
class ReciprocalRadicalizationComponents:
    node_id: str
    direction_id: str
    source_variable: str
    target_variable: str
    source_pressure: float
    target_pressure: float
    communal_fear: float
    narrative_strength: float
    damping_score: float
    cross_component: float
    narrative_component: float
    damping_component: float
    raw_delta: float
    equation_id: str
    parameter_id: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "ReciprocalRadicalizationComponents.to_dict node_id=%s direction=%s",
            self.node_id,
            self.direction_id,
        )
        return {
            "node_id": self.node_id,
            "direction_id": self.direction_id,
            "source_variable": self.source_variable,
            "target_variable": self.target_variable,
            "source_pressure": self.source_pressure,
            "target_pressure": self.target_pressure,
            "communal_fear": self.communal_fear,
            "narrative_strength": self.narrative_strength,
            "damping_score": self.damping_score,
            "cross_component": self.cross_component,
            "narrative_component": self.narrative_component,
            "damping_component": self.damping_component,
            "raw_delta": self.raw_delta,
            "equation_id": self.equation_id,
            "parameter_id": self.parameter_id,
        }


def _parameter_id(profile: str) -> str:
    logger.info("_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "RECIPROCAL_RADICALIZATION_SYN_V1"
    if profile == "calibrated_v1":
        return "RECIPROCAL_RADICALIZATION_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _parameter_value(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
) -> tuple[dict[str, Any], str]:
    logger.info("_parameter_value profile=%s", profile)
    parameter_id = _parameter_id(profile)
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing reciprocal-radicalization parameter {parameter_id} "
            f"for profile {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Reciprocal-radicalization parameter {parameter_id} "
            "must contain a mapping value"
        )
    return value, parameter_id


def _owner_map(engine_state_registry: dict[str, Any]) -> dict[str, str]:
    logger.info("_owner_map")
    owners: dict[str, str] = {}
    for group in engine_state_registry["latent_groups"].values():
        owner = str(group["module_owner"])
        for variable in group["variables"]:
            variable_id = str(variable["id"])
            if variable_id in owners:
                raise ValueError(f"Duplicate latent owner for {variable_id}")
            owners[variable_id] = owner
    return owners


def _validate_config(
    feedback_config: dict[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...], str, str]:
    logger.info("_validate_config")
    mode = feedback_config.get("mode", {})
    if mode.get("proposal_only") is not True:
        raise ValueError(
            "v0.14 reciprocal radicalization requires proposal_only=true"
        )
    if mode.get("symmetric_pair_required") is not True:
        raise ValueError(
            "v0.14 reciprocal radicalization requires symmetric_pair_required=true"
        )
    if mode.get("skip_zero_delta") is not True:
        raise ValueError(
            "v0.14 reciprocal radicalization requires skip_zero_delta=true"
        )

    safety = feedback_config.get("safety_and_integrity")
    if not isinstance(safety, dict):
        raise ValueError("safety_and_integrity must be a mapping")
    for key in (
        "civilian_population_identity_as_propensity_input",
        "religious_population_share_as_propensity_input",
        "political_party_preference_as_propensity_input",
    ):
        if safety.get(key) is not False:
            raise ValueError(f"Safety invariant {key} must remain false")
    for key in (
        "violent_network_state_only",
        "owner_resolver_required",
        "beginning_of_day_state_only",
    ):
        if safety.get(key) is not True:
            raise ValueError(f"Safety invariant {key} must remain true")

    shared = feedback_config.get("shared_inputs")
    if not isinstance(shared, dict):
        raise ValueError("shared_inputs must be a mapping")
    fear_variable = str(shared.get("fear_variable", ""))
    narrative_variable = str(shared.get("narrative_variable", ""))
    damping_variables_raw = shared.get("damping_variables")
    if not fear_variable or not narrative_variable:
        raise ValueError("fear/narrative variables must be non-empty")
    if fear_variable != EXPECTED_FEAR_VARIABLE:
        raise ValueError(
            f"fear_variable must remain {EXPECTED_FEAR_VARIABLE}"
        )
    if narrative_variable != EXPECTED_NARRATIVE_VARIABLE:
        raise ValueError(
            f"narrative_variable must remain {EXPECTED_NARRATIVE_VARIABLE}"
        )
    if not isinstance(damping_variables_raw, list) or not damping_variables_raw:
        raise ValueError("damping_variables must be a non-empty list")
    damping_variables = tuple(str(item) for item in damping_variables_raw)
    if len(damping_variables) != len(set(damping_variables)):
        raise ValueError("Duplicate damping variable")
    if frozenset(damping_variables) != EXPECTED_DAMPING_VARIABLES:
        raise ValueError(
            "damping_variables must remain the canonical institutional set"
        )

    directions_raw = feedback_config.get("directions")
    if not isinstance(directions_raw, list) or len(directions_raw) != 2:
        raise ValueError("Exactly two reciprocal directions are required")

    directions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in directions_raw:
        if not isinstance(item, dict):
            raise ValueError("Reciprocal direction must be a mapping")
        direction_id = str(item.get("direction_id", ""))
        source_variable = str(item.get("source_variable", ""))
        target_variable = str(item.get("target_variable", ""))
        equation_id = str(item.get("equation_id", ""))
        if not all((direction_id, source_variable, target_variable, equation_id)):
            raise ValueError("Reciprocal direction fields must be non-empty")
        if direction_id in seen_ids:
            raise ValueError(f"Duplicate reciprocal direction {direction_id}")
        if source_variable == target_variable:
            raise ValueError(
                f"Reciprocal direction {direction_id} cannot self-target"
            )
        seen_ids.add(direction_id)
        directions.append(
            {
                "direction_id": direction_id,
                "source_variable": source_variable,
                "target_variable": target_variable,
                "equation_id": equation_id,
            }
        )

    first, second = directions
    if (
        first["source_variable"] != second["target_variable"]
        or first["target_variable"] != second["source_variable"]
    ):
        raise ValueError("Reciprocal directions must be exact mirrors")
    configured_network_variables = frozenset(
        {
            first["source_variable"],
            first["target_variable"],
            second["source_variable"],
            second["target_variable"],
        }
    )
    if configured_network_variables != EXPECTED_NETWORK_VARIABLES:
        raise ValueError(
            "Reciprocal directions must remain limited to canonical violent-network state"
        )

    return (
        tuple(sorted(directions, key=lambda item: item["direction_id"])),
        damping_variables,
        fear_variable,
        narrative_variable,
    )


def _require_latent(
    *,
    state: EngineState,
    variable: str,
) -> float:
    logger.info(
        "_require_latent node_id=%s variable=%s",
        state.node_id,
        variable,
    )
    if variable not in state.latents:
        raise KeyError(f"Missing latent {variable} from node {state.node_id}")
    value = float(state.latents[variable])
    if not math.isfinite(value):
        raise ValueError(f"Non-finite latent {state.node_id}.{variable}")
    return value


def _validate_gains(gains: dict[str, Any]) -> tuple[float, float, float]:
    logger.info("_validate_gains")
    required = (
        "cross_reaction_gain",
        "damping_gain",
        "narrative_amplification_gain",
    )
    missing = [key for key in required if key not in gains]
    if missing:
        raise KeyError(f"Missing reciprocal-radicalization gains: {missing}")
    cross_gain = float(gains["cross_reaction_gain"])
    damping_gain = float(gains["damping_gain"])
    narrative_gain = float(gains["narrative_amplification_gain"])
    for key, value in (
        ("cross_reaction_gain", cross_gain),
        ("damping_gain", damping_gain),
        ("narrative_amplification_gain", narrative_gain),
    ):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"{key} must be finite and non-negative")
    return cross_gain, damping_gain, narrative_gain


def _source_id(
    *,
    state: EngineState,
    direction: dict[str, Any],
    components: ReciprocalRadicalizationComponents,
) -> str:
    logger.info(
        "_source_id node_id=%s day=%s direction=%s",
        state.node_id,
        state.day,
        direction["direction_id"],
    )
    digest = canonical_hash(
        {
            "source_type": "RECIPROCAL_RADICALIZATION_V1",
            "node_id": state.node_id,
            "day_effective": state.day + 1,
            "direction_id": direction["direction_id"],
            "source_variable": direction["source_variable"],
            "target_variable": direction["target_variable"],
            "equation_id": direction["equation_id"],
            "components": components.to_dict(),
        }
    )
    return f"feedback-{digest[:24]}"


def _proposal_id(
    *,
    source_id: str,
    target_node: str,
    variable: str,
    equation_id: str,
) -> str:
    logger.info(
        "_proposal_id source_id=%s target=%s variable=%s",
        source_id,
        target_node,
        variable,
    )
    digest = canonical_hash(
        {
            "source_id": source_id,
            "target_node": target_node,
            "variable": variable,
            "equation_id": equation_id,
            "proposal_contract": "RECIPROCAL_RADICALIZATION_PROPOSAL_V1",
        }
    )
    return f"delta-{digest[:24]}"


def propose_reciprocal_radicalization_effects(
    *,
    states: dict[str, EngineState],
    feedback_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    """Create symmetric bounded-owner proposals from beginning-of-day state."""
    logger.info(
        "propose_reciprocal_radicalization_effects states=%s profile=%s",
        len(states),
        profile,
    )
    (
        directions,
        damping_variables,
        fear_variable,
        narrative_variable,
    ) = _validate_config(feedback_config)
    gains, parameter_id = _parameter_value(
        parameter_registry,
        profile=profile,
    )
    cross_gain, damping_gain, narrative_gain = _validate_gains(gains)
    owners = _owner_map(engine_state_registry)
    proposals: list[DeltaProposal] = []

    for node_id, state in sorted(states.items()):
        communal_fear = _require_latent(state=state, variable=fear_variable)
        narrative_strength = _require_latent(
            state=state,
            variable=narrative_variable,
        )
        damping_values = tuple(
            _require_latent(state=state, variable=variable)
            for variable in damping_variables
        )
        damping_score = math.fsum(damping_values) / len(damping_values)

        for direction in directions:
            source_variable = direction["source_variable"]
            target_variable = direction["target_variable"]
            if target_variable not in owners:
                raise KeyError(f"No owner module registered for {target_variable}")

            source_pressure = _require_latent(
                state=state,
                variable=source_variable,
            )
            target_pressure = _require_latent(
                state=state,
                variable=target_variable,
            )
            cross_component = cross_gain * source_pressure * communal_fear
            narrative_component = (
                narrative_gain * narrative_strength * target_pressure
            )
            damping_component = damping_gain * damping_score * target_pressure
            raw_delta = (
                cross_component
                + narrative_component
                - damping_component
            )
            components = ReciprocalRadicalizationComponents(
                node_id=node_id,
                direction_id=direction["direction_id"],
                source_variable=source_variable,
                target_variable=target_variable,
                source_pressure=source_pressure,
                target_pressure=target_pressure,
                communal_fear=communal_fear,
                narrative_strength=narrative_strength,
                damping_score=damping_score,
                cross_component=cross_component,
                narrative_component=narrative_component,
                damping_component=damping_component,
                raw_delta=raw_delta,
                equation_id=direction["equation_id"],
                parameter_id=parameter_id,
            )
            trace.append(
                "reciprocal_radicalization_evaluation",
                **components.to_dict(),
            )

            if raw_delta == 0.0:
                continue

            source_id = _source_id(
                state=state,
                direction=direction,
                components=components,
            )
            value_before = target_pressure
            proposal = DeltaProposal(
                proposal_id=_proposal_id(
                    source_id=source_id,
                    target_node=node_id,
                    variable=target_variable,
                    equation_id=direction["equation_id"],
                ),
                event_id=source_id,
                event_type="RECIPROCAL_RADICALIZATION_V1",
                target_node=node_id,
                variable=target_variable,
                owner_module=owners[target_variable],
                value_before=value_before,
                raw_delta=raw_delta,
                proposed_unbounded_value=value_before + raw_delta,
                equation_id=direction["equation_id"],
                parameter_ids=(parameter_id,),
                apply_status="PROPOSED_NOT_APPLIED",
                dry_run=True,
            )
            trace.append(
                "reciprocal_radicalization_delta_proposal",
                direction_id=direction["direction_id"],
                **proposal.to_dict(),
            )
            trace.append("delta_proposal", **proposal.to_dict())
            proposals.append(proposal)

    proposal_ids = [item.proposal_id for item in proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate reciprocal-radicalization proposal IDs")
    return tuple(sorted(proposals, key=lambda item: item.proposal_id))
