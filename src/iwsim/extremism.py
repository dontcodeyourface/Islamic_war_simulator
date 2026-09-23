from __future__ import annotations

import logging
import math
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)

FORBIDDEN_DIRECT_NETWORK_INPUTS = frozenset(
    {
        "religious_fraction_muslim",
        "religious_fraction_christian",
        "religious_fraction_other",
        "foreign_born_fraction",
        "second_generation_fraction",
        "demographic_momentum",
        "migration_pressure",
        "dependency_pressure",
    }
)


def _parameter_ids(profile: str) -> tuple[str, str]:
    logger.info("_parameter_ids profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return (
            "EXTREMIST_NETWORK_DYNAMICS_SYN_V1",
            "DYNAMIC_GAINS_SYN_V1",
        )
    if profile == "calibrated_v1":
        return (
            "EXTREMIST_NETWORK_DYNAMICS_CAL_V1",
            "DYNAMIC_GAINS_CAL_V1",
        )
    raise ValueError(f"Unknown parameter profile: {profile}")


def _parameter_value(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> Any:
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
            f"Missing extremist-network parameter {parameter_id} for {profile}"
        )
    return parameter["value"]


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


def _validate_input_spec(item: Any, *, kind: str) -> dict[str, str]:
    logger.info("_validate_input_spec kind=%s", kind)
    if not isinstance(item, dict):
        raise ValueError(f"{kind} input must be a mapping")
    key = str(item.get("key", ""))
    variable = str(item.get("variable", ""))
    transform = str(item.get("transform", ""))
    if not key or not variable or transform not in {"identity", "one_minus"}:
        raise ValueError(f"Invalid {kind} input specification: {item}")
    return {
        "key": key,
        "variable": variable,
        "transform": transform,
    }


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    logger.info("_validate_config")
    if config.get("equation_id") != "EXTREMIST_NETWORK_PRESSURE_V1":
        raise ValueError("Unsupported extremist-network equation_id")

    families = config.get("families")
    if not isinstance(families, list) or not families:
        raise ValueError("Extremist-network families must be a non-empty list")
    normalized_families: list[dict[str, str]] = []
    seen_variables: set[str] = set()
    for family in families:
        if not isinstance(family, dict):
            raise ValueError("Extremist-network family must be a mapping")
        family_id = str(family.get("family_id", ""))
        variable = str(family.get("variable", ""))
        if not family_id or not variable:
            raise ValueError("Extremist-network family fields must be non-empty")
        if variable in seen_variables:
            raise ValueError(f"Duplicate extremist-network variable {variable}")
        seen_variables.add(variable)
        normalized_families.append(
            {"family_id": family_id, "variable": variable}
        )

    expected_variables = {
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
        "revolutionary_extremist_pressure",
    }
    if seen_variables != expected_variables:
        raise ValueError(
            "v0.13 requires the three parallel canonical violent-network variables"
        )

    driver_inputs = tuple(
        _validate_input_spec(item, kind="driver")
        for item in config.get("driver_inputs", [])
    )
    damping_inputs = tuple(
        _validate_input_spec(item, kind="damping")
        for item in config.get("damping_inputs", [])
    )
    if not driver_inputs or not damping_inputs:
        raise ValueError("Driver and damping inputs must be non-empty")

    all_keys = [item["key"] for item in (*driver_inputs, *damping_inputs)]
    if len(all_keys) != len(set(all_keys)):
        raise ValueError("Duplicate extremist-network input key")

    configured_forbidden = set(
        str(item) for item in config.get("forbidden_direct_inputs", [])
    )
    forbidden = configured_forbidden | set(FORBIDDEN_DIRECT_NETWORK_INPUTS)
    used_variables = {
        item["variable"] for item in (*driver_inputs, *damping_inputs)
    }
    blocked = sorted(used_variables & forbidden)
    if blocked:
        raise ValueError(f"Forbidden direct extremist-network inputs: {blocked}")

    return {
        "equation_id": str(config["equation_id"]),
        "families": tuple(
            sorted(normalized_families, key=lambda item: item["variable"])
        ),
        "driver_inputs": driver_inputs,
        "damping_inputs": damping_inputs,
    }


def _transform(value: float, transform: str) -> float:
    logger.info("_transform transform=%s value=%s", transform, value)
    if transform == "identity":
        return value
    if transform == "one_minus":
        return 1.0 - value
    raise ValueError(f"Unsupported transform {transform}")


def _weighted_score(
    *,
    state: EngineState,
    inputs: tuple[dict[str, str], ...],
    weights: dict[str, Any],
    score_name: str,
) -> tuple[float, dict[str, float]]:
    logger.info(
        "_weighted_score node_id=%s score_name=%s inputs=%s",
        state.node_id,
        score_name,
        len(inputs),
    )
    input_values: dict[str, float] = {}
    weighted_terms: list[float] = []
    weight_sum = 0.0

    for spec in inputs:
        key = spec["key"]
        variable = spec["variable"]
        if variable not in state.latents:
            raise KeyError(
                f"{score_name} variable {variable} missing from {state.node_id}"
            )
        if key not in weights:
            raise KeyError(f"{score_name} weight missing for key {key}")
        raw_value = float(state.latents[variable])
        value = _transform(raw_value, spec["transform"])
        weight = float(weights[key])
        if not math.isfinite(value) or not math.isfinite(weight):
            raise ValueError(
                f"Non-finite {score_name} input for {state.node_id}.{key}"
            )
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{score_name} transformed input {key}={value} outside [0,1]"
            )
        if weight < 0.0:
            raise ValueError(f"{score_name} weight {key} must be non-negative")
        input_values[key] = value
        weighted_terms.append(value * weight)
        weight_sum += weight

    if not math.isclose(weight_sum, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            f"{score_name} weights must sum to 1.0, got {weight_sum}"
        )
    return math.fsum(weighted_terms), input_values


def _proposal_id(
    *,
    state: EngineState,
    variable: str,
    equation_id: str,
    raw_delta: float,
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
            "source": "ENDOGENOUS_EXTREMIST_NETWORK_DYNAMICS",
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
            "source": "ENDOGENOUS_EXTREMIST_NETWORK_DYNAMICS",
            "node_id": state.node_id,
            "day": state.day + 1,
            "variable": variable,
            "equation_id": equation_id,
        }
    )
    return f"network-{digest[:24]}"


def propose_extremist_network_dynamics(
    *,
    states: dict[str, EngineState],
    network_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    """Propose symmetric bounded endogenous dynamics for violent-network pressures."""
    logger.info(
        "propose_extremist_network_dynamics states=%s profile=%s",
        len(states),
        profile,
    )
    config = _validate_config(network_config)
    network_parameter_id, gains_parameter_id = _parameter_ids(profile)
    parameters = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=network_parameter_id,
    )
    gains = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=gains_parameter_id,
    )

    driver_weights = parameters.get("driver_weights")
    damping_weights = parameters.get("damping_weights")
    gain_key = str(parameters.get("gain_key", ""))
    max_delta_key = str(parameters.get("max_delta_key", ""))
    if not isinstance(driver_weights, dict) or not isinstance(damping_weights, dict):
        raise ValueError("Extremist-network weights must be mappings")
    if gain_key not in gains or max_delta_key not in gains:
        raise KeyError(
            f"Extremist-network gain keys missing: {gain_key}, {max_delta_key}"
        )

    gain = float(gains[gain_key])
    max_delta = float(gains[max_delta_key])
    if not 0.0 <= gain <= 1.0:
        raise ValueError(f"Extremist-network gain {gain_key} must be within [0,1]")
    if max_delta < 0.0:
        raise ValueError("Extremist-network max daily delta must be non-negative")

    owners = _owner_map(engine_state_registry)
    equation_id = config["equation_id"]
    parameter_ids = (network_parameter_id, gains_parameter_id)
    proposals: list[DeltaProposal] = []

    for node_id, state in sorted(states.items()):
        driver_score, driver_inputs = _weighted_score(
            state=state,
            inputs=config["driver_inputs"],
            weights=driver_weights,
            score_name="driver",
        )
        damping_score, damping_inputs = _weighted_score(
            state=state,
            inputs=config["damping_inputs"],
            weights=damping_weights,
            score_name="damping",
        )

        for family in config["families"]:
            variable = family["variable"]
            if variable not in state.latents:
                raise KeyError(
                    f"Extremist-network variable {variable} missing from {node_id}"
                )
            if variable not in owners:
                raise KeyError(f"No owner module registered for {variable}")
            current = float(state.latents[variable])
            if not math.isfinite(current):
                raise ValueError(f"Non-finite network pressure {node_id}.{variable}")

            growth_component = driver_score * (1.0 - current)
            damping_component = damping_score * current
            unbounded_delta = gain * (growth_component - damping_component)
            raw_delta = min(max_delta, max(-max_delta, unbounded_delta))
            if raw_delta == 0.0:
                continue

            proposal = DeltaProposal(
                proposal_id=_proposal_id(
                    state=state,
                    variable=variable,
                    equation_id=equation_id,
                    raw_delta=raw_delta,
                    parameter_ids=parameter_ids,
                ),
                event_id=_source_id(
                    state=state,
                    variable=variable,
                    equation_id=equation_id,
                ),
                event_type="ENDOGENOUS_EXTREMIST_NETWORK_V1",
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
                "extremist_network_dynamics_proposal",
                family_id=family["family_id"],
                driver_inputs=driver_inputs,
                damping_inputs=damping_inputs,
                driver_score=driver_score,
                damping_score=damping_score,
                growth_component=growth_component,
                damping_component=damping_component,
                gain_key=gain_key,
                max_delta_key=max_delta_key,
                **proposal.to_dict(),
            )
            trace.append("delta_proposal", **proposal.to_dict())
            proposals.append(proposal)

    proposal_ids = [item.proposal_id for item in proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate extremist-network proposal IDs")
    return tuple(sorted(proposals, key=lambda item: item.proposal_id))
