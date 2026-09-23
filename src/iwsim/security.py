from __future__ import annotations

import logging
import math
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)

EXPECTED_STRESS_INPUTS = {
    "public_order_stress": ("public_order_stress", "identity"),
    "external_conflict_pressure": ("external_conflict_pressure", "identity"),
    "organized_armed_actor_capacity": (
        "organized_armed_actor_capacity",
        "identity",
    ),
    "salary_payment_discontinuity": (
        "salary_payment_continuity",
        "one_minus",
    ),
    "government_legitimacy_inverse": (
        "government_legitimacy",
        "one_minus",
    ),
    "transport_logistics_degradation": (
        "transport_logistics_functionality",
        "one_minus",
    ),
}

EXPECTED_RESILIENCE_INPUTS = {
    "government_legitimacy": ("government_legitimacy", "identity"),
    "salary_payment_continuity": (
        "salary_payment_continuity",
        "identity",
    ),
    "police_effective_capacity": (
        "police_effective_capacity",
        "identity",
    ),
    "intelligence_effectiveness": (
        "intelligence_effectiveness",
        "identity",
    ),
    "administrative_capacity": ("administrative_capacity", "identity"),
    "social_cohesion": ("social_cohesion", "identity"),
}


def _parameter_ids(profile: str) -> tuple[str, str]:
    logger.info("_parameter_ids profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "SECURITY_CHAIN_DYNAMICS_SYN_V1", "DYNAMIC_GAINS_SYN_V1"
    if profile == "calibrated_v1":
        return "SECURITY_CHAIN_DYNAMICS_CAL_V1", "DYNAMIC_GAINS_CAL_V1"
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
            f"Missing security-chain parameter {parameter_id} for {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Security-chain parameter {parameter_id} must contain a mapping value"
        )
    return value


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


def _validate_input(item: Any, *, kind: str) -> dict[str, str]:
    logger.info("_validate_input kind=%s", kind)
    if not isinstance(item, dict):
        raise ValueError(f"{kind} input must be a mapping")
    key = str(item.get("key", ""))
    variable = str(item.get("variable", ""))
    transform = str(item.get("transform", ""))
    if not key or not variable or transform not in {"identity", "one_minus"}:
        raise ValueError(f"Invalid {kind} input: {item}")
    return {"key": key, "variable": variable, "transform": transform}


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    logger.info("_validate_config")
    if config.get("equation_id") != "SECURITY_CHAIN_DYNAMICS_V1":
        raise ValueError("Unsupported security-chain equation_id")

    stress_inputs = tuple(
        _validate_input(item, kind="stress")
        for item in config.get("stress_inputs", [])
    )
    resilience_inputs = tuple(
        _validate_input(item, kind="resilience")
        for item in config.get("resilience_inputs", [])
    )
    if not stress_inputs or not resilience_inputs:
        raise ValueError("Security-chain stress/resilience inputs must be non-empty")

    stress_map = {
        item["key"]: (item["variable"], item["transform"])
        for item in stress_inputs
    }
    resilience_map = {
        item["key"]: (item["variable"], item["transform"])
        for item in resilience_inputs
    }
    if stress_map != EXPECTED_STRESS_INPUTS:
        raise ValueError("Security-chain stress inputs must remain canonical")
    if resilience_map != EXPECTED_RESILIENCE_INPUTS:
        raise ValueError("Security-chain resilience inputs must remain canonical")

    keys = [item["key"] for item in (*stress_inputs, *resilience_inputs)]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate security-chain input key")

    targets_raw = config.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ValueError("Security-chain targets must be a non-empty list")

    expected = {
        "security_chain_cohesion",
        "command_cohesion",
        "constitutional_loyalty",
        "operational_fatigue",
    }
    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in targets_raw:
        if not isinstance(item, dict):
            raise ValueError("Security-chain target must be a mapping")
        variable = str(item.get("variable", ""))
        direction = str(item.get("direction", ""))
        gain_key = str(item.get("gain_key", ""))
        max_delta_key = str(item.get("max_delta_key", ""))
        if (
            not variable
            or direction not in {"resilience", "stress"}
            or not gain_key
            or not max_delta_key
        ):
            raise ValueError(f"Invalid security-chain target: {item}")
        if variable in seen:
            raise ValueError(f"Duplicate security-chain target {variable}")
        seen.add(variable)
        targets.append(
            {
                "variable": variable,
                "direction": direction,
                "gain_key": gain_key,
                "max_delta_key": max_delta_key,
            }
        )
    if seen != expected:
        raise ValueError(
            "v0.15 security-chain targets must match canonical security variables"
        )
    if next(x for x in targets if x["variable"] == "operational_fatigue")[
        "direction"
    ] != "stress":
        raise ValueError("operational_fatigue must remain a stress-direction target")
    for item in targets:
        if item["variable"] != "operational_fatigue" and item["direction"] != "resilience":
            raise ValueError(
                f"{item['variable']} must remain a resilience-direction target"
            )

    safety = config.get("safety_and_integrity")
    if not isinstance(safety, dict):
        raise ValueError("safety_and_integrity must be a mapping")
    for key in (
        "political_party_preference_as_fracture_input",
        "religious_identity_as_fracture_input",
        "ethnicity_as_fracture_input",
    ):
        if safety.get(key) is not False:
            raise ValueError(f"Security-chain safety invariant {key} must remain false")
    for key in (
        "beginning_of_day_state_only",
        "proposals_only",
        "owner_resolver_required",
    ):
        if safety.get(key) is not True:
            raise ValueError(f"Security-chain invariant {key} must remain true")

    return {
        "equation_id": str(config["equation_id"]),
        "stress_inputs": stress_inputs,
        "resilience_inputs": resilience_inputs,
        "targets": tuple(sorted(targets, key=lambda item: item["variable"])),
    }


def _transform(value: float, transform: str) -> float:
    logger.info("_transform value=%s transform=%s", value, transform)
    if transform == "identity":
        return value
    if transform == "one_minus":
        return 1.0 - value
    raise ValueError(f"Unsupported transform {transform}")


def _weighted_score(
    *,
    state: EngineState,
    specs: tuple[dict[str, str], ...],
    weights: dict[str, Any],
    score_name: str,
) -> tuple[float, dict[str, float]]:
    logger.info(
        "_weighted_score node_id=%s score_name=%s inputs=%s",
        state.node_id,
        score_name,
        len(specs),
    )
    expected_weight_keys = {spec["key"] for spec in specs}
    if set(weights) != expected_weight_keys:
        raise ValueError(
            f"Security-chain {score_name} weight keys must match configured inputs"
        )

    values: dict[str, float] = {}
    terms: list[float] = []
    weight_sum = 0.0
    for spec in specs:
        key = spec["key"]
        variable = spec["variable"]
        if variable not in state.latents:
            raise KeyError(
                f"Security-chain {score_name} variable {variable} missing from {state.node_id}"
            )
        if key not in weights:
            raise KeyError(f"Security-chain {score_name} weight missing for {key}")
        raw = float(state.latents[variable])
        value = _transform(raw, spec["transform"])
        weight = float(weights[key])
        if not math.isfinite(value) or not math.isfinite(weight):
            raise ValueError(
                f"Non-finite security-chain {score_name} input {state.node_id}.{key}"
            )
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"Security-chain transformed input {key}={value} outside [0,1]"
            )
        if weight < 0.0:
            raise ValueError(f"Security-chain weight {key} must be non-negative")
        values[key] = value
        terms.append(value * weight)
        weight_sum += weight

    if not math.isclose(weight_sum, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            f"Security-chain {score_name} weights must sum to 1.0, got {weight_sum}"
        )
    return math.fsum(terms), values


def _proposal_id(
    *,
    state: EngineState,
    variable: str,
    raw_delta: float,
    equation_id: str,
    parameter_ids: tuple[str, ...],
) -> str:
    logger.info(
        "_proposal_id node_id=%s day=%s variable=%s",
        state.node_id,
        state.day,
        variable,
    )
    digest = canonical_hash(
        {
            "source": "ENDOGENOUS_SECURITY_CHAIN_DYNAMICS",
            "node_id": state.node_id,
            "day": state.day + 1,
            "variable": variable,
            "value_before": state.latents[variable],
            "raw_delta": raw_delta,
            "equation_id": equation_id,
            "parameter_ids": list(parameter_ids),
        }
    )
    return f"delta-{digest[:24]}"


def _source_id(
    *,
    state: EngineState,
    variable: str,
    equation_id: str,
) -> str:
    logger.info(
        "_source_id node_id=%s day=%s variable=%s",
        state.node_id,
        state.day,
        variable,
    )
    digest = canonical_hash(
        {
            "source": "ENDOGENOUS_SECURITY_CHAIN_DYNAMICS",
            "node_id": state.node_id,
            "day": state.day + 1,
            "variable": variable,
            "equation_id": equation_id,
        }
    )
    return f"security-{digest[:24]}"


def propose_security_chain_dynamics(
    *,
    states: dict[str, EngineState],
    security_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    """Propose bounded endogenous security-chain state dynamics."""
    logger.info(
        "propose_security_chain_dynamics states=%s profile=%s",
        len(states),
        profile,
    )
    config = _validate_config(security_config)
    dynamics_parameter_id, gains_parameter_id = _parameter_ids(profile)
    parameters = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=dynamics_parameter_id,
    )
    gains = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=gains_parameter_id,
    )
    stress_weights = parameters.get("stress_weights")
    resilience_weights = parameters.get("resilience_weights")
    if not isinstance(stress_weights, dict) or not isinstance(
        resilience_weights, dict
    ):
        raise ValueError("Security-chain weight sets must be mappings")

    owners = _owner_map(engine_state_registry)
    equation_id = config["equation_id"]
    parameter_ids = (dynamics_parameter_id, gains_parameter_id)
    proposals: list[DeltaProposal] = []

    for node_id, state in sorted(states.items()):
        stress_score, stress_inputs = _weighted_score(
            state=state,
            specs=config["stress_inputs"],
            weights=stress_weights,
            score_name="stress",
        )
        resilience_score, resilience_inputs = _weighted_score(
            state=state,
            specs=config["resilience_inputs"],
            weights=resilience_weights,
            score_name="resilience",
        )

        for target in config["targets"]:
            variable = target["variable"]
            if variable not in state.latents:
                raise KeyError(
                    f"Security-chain target {variable} missing from {node_id}"
                )
            if variable not in owners:
                raise KeyError(f"No owner module registered for {variable}")
            if owners[variable] != "security":
                raise ValueError(
                    f"Security-chain target {variable} owner must remain security"
                )

            gain_key = target["gain_key"]
            max_delta_key = target["max_delta_key"]
            if gain_key not in gains or max_delta_key not in gains:
                raise KeyError(
                    f"Security-chain gain keys missing for {variable}: "
                    f"{gain_key}, {max_delta_key}"
                )
            gain = float(gains[gain_key])
            max_delta = float(gains[max_delta_key])
            if not math.isfinite(gain) or not 0.0 <= gain <= 1.0:
                raise ValueError(
                    f"Security-chain gain {gain_key} must be finite within [0,1]"
                )
            if not math.isfinite(max_delta) or max_delta < 0.0:
                raise ValueError(
                    f"Security-chain max delta {max_delta_key} must be finite and non-negative"
                )

            current = float(state.latents[variable])
            if not math.isfinite(current) or not 0.0 <= current <= 1.0:
                raise ValueError(
                    f"Security-chain target {node_id}.{variable} outside [0,1]"
                )

            if target["direction"] == "resilience":
                positive_component = resilience_score * (1.0 - current)
                negative_component = stress_score * current
            else:
                positive_component = stress_score * (1.0 - current)
                negative_component = resilience_score * current

            unbounded_delta = gain * (
                positive_component - negative_component
            )
            raw_delta = min(max_delta, max(-max_delta, unbounded_delta))
            trace.append(
                "security_chain_dynamics_evaluation",
                node_id=node_id,
                variable=variable,
                direction=target["direction"],
                value_before=current,
                stress_inputs=stress_inputs,
                resilience_inputs=resilience_inputs,
                stress_score=stress_score,
                resilience_score=resilience_score,
                positive_component=positive_component,
                negative_component=negative_component,
                gain_key=gain_key,
                max_delta_key=max_delta_key,
                unbounded_delta=unbounded_delta,
                raw_delta=raw_delta,
                equation_id=equation_id,
                parameter_ids=list(parameter_ids),
            )
            if raw_delta == 0.0:
                continue

            proposal = DeltaProposal(
                proposal_id=_proposal_id(
                    state=state,
                    variable=variable,
                    raw_delta=raw_delta,
                    equation_id=equation_id,
                    parameter_ids=parameter_ids,
                ),
                event_id=_source_id(
                    state=state,
                    variable=variable,
                    equation_id=equation_id,
                ),
                event_type="ENDOGENOUS_SECURITY_CHAIN_V1",
                target_node=node_id,
                variable=variable,
                owner_module=owners[variable],
                value_before=current,
                raw_delta=raw_delta,
                proposed_unbounded_value=current + raw_delta,
                equation_id=equation_id,
                parameter_ids=parameter_ids,
                apply_status="PROPOSED_NOT_APPLIED",
                dry_run=True,
            )
            trace.append(
                "security_chain_dynamics_delta_proposal",
                direction=target["direction"],
                gain_key=gain_key,
                max_delta_key=max_delta_key,
                **proposal.to_dict(),
            )
            trace.append("delta_proposal", **proposal.to_dict())
            proposals.append(proposal)

    proposal_ids = [item.proposal_id for item in proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate security-chain proposal IDs")
    return tuple(sorted(proposals, key=lambda item: item.proposal_id))
