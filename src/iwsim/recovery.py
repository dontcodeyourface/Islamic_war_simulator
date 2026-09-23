from __future__ import annotations

import logging
import math
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


def _dynamic_gains_parameter_id(profile: str) -> str:
    logger.info("_dynamic_gains_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "DYNAMIC_GAINS_SYN_V1"
    if profile == "calibrated_v1":
        return "DYNAMIC_GAINS_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _dynamic_gains(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
) -> tuple[dict[str, Any], str]:
    logger.info("_dynamic_gains profile=%s", profile)
    parameter_id = _dynamic_gains_parameter_id(profile)
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing recovery parameter {parameter_id} for profile {profile}"
        )
    return parameter["value"], parameter_id


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


def _validate_recovery_config(recovery_config: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    logger.info("_validate_recovery_config")
    if recovery_config.get("baseline_source") != "state.metadata.initial_latents":
        raise ValueError("Unsupported recovery baseline source")
    targets = recovery_config.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("Recovery config targets must be a non-empty list")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("Recovery target must be a mapping")
        variable = str(target.get("variable"))
        gain_key = str(target.get("gain_key"))
        max_delta_key = str(target.get("max_delta_key"))
        equation_id = str(target.get("equation_id"))
        if not all((variable, gain_key, max_delta_key, equation_id)):
            raise ValueError("Recovery target fields must be non-empty")
        if variable in seen:
            raise ValueError(f"Duplicate recovery target {variable}")
        seen.add(variable)
        normalized.append(
            {
                "variable": variable,
                "gain_key": gain_key,
                "max_delta_key": max_delta_key,
                "equation_id": equation_id,
            }
        )
    return tuple(sorted(normalized, key=lambda item: item["variable"]))


def _proposal_id(
    *,
    state: EngineState,
    variable: str,
    baseline: float,
    raw_delta: float,
    equation_id: str,
) -> str:
    logger.info(
        "_proposal_id node_id=%s day=%s variable=%s",
        state.node_id,
        state.day,
        variable,
    )
    digest = canonical_hash(
        {
            "source": "ENDOGENOUS_RECOVERY",
            "node_id": state.node_id,
            "day": state.day + 1,
            "variable": variable,
            "baseline": baseline,
            "value_before": state.latents[variable],
            "raw_delta": raw_delta,
            "equation_id": equation_id,
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
            "source": "ENDOGENOUS_RECOVERY",
            "node_id": state.node_id,
            "day": state.day + 1,
            "variable": variable,
            "equation_id": equation_id,
        }
    )
    return f"recovery-{digest[:24]}"


def propose_recovery_effects(
    *,
    states: dict[str, EngineState],
    recovery_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    """Propose bounded deterministic relaxation toward immutable initial latents."""
    logger.info(
        "propose_recovery_effects states=%s profile=%s",
        len(states),
        profile,
    )
    targets = _validate_recovery_config(recovery_config)
    gains, parameter_id = _dynamic_gains(
        parameter_registry,
        profile=profile,
    )
    owners = _owner_map(engine_state_registry)
    proposals: list[DeltaProposal] = []

    for node_id, state in sorted(states.items()):
        baselines = state.metadata.get("initial_latents")
        if not isinstance(baselines, dict):
            raise ValueError(
                f"Recovery baseline memory missing for {node_id}: "
                "state.metadata.initial_latents"
            )

        for target in targets:
            variable = target["variable"]
            if variable not in state.latents:
                raise KeyError(f"Recovery variable {variable} missing from {node_id}")
            if variable not in baselines:
                raise KeyError(f"Recovery baseline {variable} missing from {node_id}")
            if variable not in owners:
                raise KeyError(f"No owner module registered for {variable}")

            gain_key = target["gain_key"]
            max_delta_key = target["max_delta_key"]
            if gain_key not in gains or max_delta_key not in gains:
                raise KeyError(
                    f"Recovery gain keys missing for {variable}: "
                    f"{gain_key}, {max_delta_key}"
                )

            current = float(state.latents[variable])
            baseline = float(baselines[variable])
            gain = float(gains[gain_key])
            max_delta = float(gains[max_delta_key])
            if not 0.0 <= gain <= 1.0:
                raise ValueError(f"Recovery gain {gain_key} must be within [0,1]")
            if max_delta < 0.0:
                raise ValueError(f"Recovery max delta {max_delta_key} must be non-negative")
            if not math.isfinite(current) or not math.isfinite(baseline):
                raise ValueError(f"Non-finite recovery input for {node_id}.{variable}")

            raw_delta = (baseline - current) * gain
            bounded_delta = min(max_delta, max(-max_delta, raw_delta))
            if bounded_delta == 0.0:
                continue

            equation_id = target["equation_id"]
            proposal = DeltaProposal(
                proposal_id=_proposal_id(
                    state=state,
                    variable=variable,
                    baseline=baseline,
                    raw_delta=bounded_delta,
                    equation_id=equation_id,
                ),
                event_id=_source_id(
                    state=state,
                    variable=variable,
                    equation_id=equation_id,
                ),
                event_type="ENDOGENOUS_RECOVERY_V1",
                target_node=node_id,
                variable=variable,
                owner_module=owners[variable],
                value_before=current,
                raw_delta=bounded_delta,
                proposed_unbounded_value=current + bounded_delta,
                equation_id=equation_id,
                parameter_ids=(parameter_id,),
                apply_status="PROPOSED_NOT_APPLIED",
                dry_run=True,
            )
            trace.append(
                "recovery_proposal",
                baseline=baseline,
                gain_key=gain_key,
                max_delta_key=max_delta_key,
                **proposal.to_dict(),
            )
            trace.append("delta_proposal", **proposal.to_dict())
            proposals.append(proposal)

    return tuple(sorted(proposals, key=lambda item: item.proposal_id))
