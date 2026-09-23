from __future__ import annotations

import logging
import math
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .manifest import RunManifest
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


def _owner_map(engine_state_registry: dict[str, Any]) -> dict[str, str]:
    logger.info("_owner_map")
    owners: dict[str, str] = {}
    for group in engine_state_registry["latent_groups"].values():
        owner = str(group["module_owner"])
        for item in group["variables"]:
            variable = str(item["id"])
            if variable in owners:
                raise ValueError(f"Duplicate owner registration for {variable}")
            owners[variable] = owner
    return owners


def _recovery_parameter(
    *,
    parameter_registry: dict[str, Any],
    recovery_config: dict[str, Any],
    profile: str,
) -> tuple[dict[str, Any], str]:
    logger.info("_recovery_parameter profile=%s", profile)
    parameter_id = str(recovery_config["parameter_id"][profile])
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing recovery parameter {parameter_id} for profile {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Recovery parameter {parameter_id} must contain a mapping value"
        )
    return value, parameter_id


def _baseline_map(state: EngineState, recovery_config: dict[str, Any]) -> dict[str, float]:
    logger.info("_baseline_map node_id=%s day=%s", state.node_id, state.day)
    expected_version = str(
        recovery_config["mode"]["baseline_version_required"]
    )
    actual_version = state.metadata.get("baseline_latents_version")
    if actual_version != expected_version:
        raise ValueError(
            f"Missing or incompatible baseline version for {state.node_id}: "
            f"{actual_version!r} != {expected_version!r}"
        )
    raw = state.metadata.get("baseline_latents")
    if not isinstance(raw, (tuple, list)):
        raise ValueError(f"Missing baseline_latents for {state.node_id}")
    baseline: dict[str, float] = {}
    for item in raw:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"Invalid baseline_latents entry for {state.node_id}")
        variable = str(item[0])
        if variable in baseline:
            raise ValueError(f"Duplicate baseline latent {variable}")
        baseline[variable] = float(item[1])
    if set(baseline) != set(state.latents):
        raise ValueError(
            f"Baseline/state latent mismatch for {state.node_id}"
        )
    return baseline


def _daily_alpha(half_life_days: float) -> float:
    logger.info("_daily_alpha half_life_days=%s", half_life_days)
    if half_life_days <= 0:
        raise ValueError("Recovery half-life must be > 0")
    return 1.0 - math.pow(2.0, -1.0 / half_life_days)


def _recovery_source_id(
    *,
    manifest: RunManifest,
    state: EngineState,
) -> str:
    logger.info(
        "_recovery_source_id node_id=%s day=%s",
        state.node_id,
        state.day,
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "node_id": state.node_id,
            "day_from": state.day,
            "day_to": state.day + 1,
            "source_type": "ENDOGENOUS_RECOVERY_V1",
        }
    )
    return f"recovery-{digest[:24]}"


def _recovery_proposal_id(
    *,
    recovery_source_id: str,
    state: EngineState,
    variable: str,
    equation_id: str,
) -> str:
    logger.info(
        "_recovery_proposal_id node_id=%s variable=%s",
        state.node_id,
        variable,
    )
    digest = canonical_hash(
        {
            "recovery_source_id": recovery_source_id,
            "node_id": state.node_id,
            "day": state.day,
            "variable": variable,
            "equation_id": equation_id,
        }
    )
    return f"delta-{digest[:24]}"


def _validate_recovery_config(
    *,
    recovery_config: dict[str, Any],
    owners: dict[str, str],
) -> None:
    logger.info("_validate_recovery_config")
    if not bool(recovery_config["mode"].get("enabled", False)):
        raise ValueError("Recovery configuration is disabled")
    if not bool(recovery_config["mode"].get("proposal_only", False)):
        raise ValueError("v0.10 recovery must remain proposal-only")
    variables = recovery_config.get("variables")
    if not isinstance(variables, dict) or not variables:
        raise ValueError("Recovery variables must be a non-empty mapping")
    forbidden = set(
        str(item)
        for item in recovery_config.get("forbidden_generic_recovery", [])
    )
    overlap = forbidden & set(variables)
    if overlap:
        raise ValueError(
            f"Forbidden generic recovery variables configured: {sorted(overlap)}"
        )
    unknown = set(variables) - set(owners)
    if unknown:
        raise ValueError(f"Unknown recovery variables: {sorted(unknown)}")


def propose_recovery_effects(
    *,
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    recovery_config: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    """Create deterministic owner-routed recovery proposals from beginning-of-day state."""
    logger.info(
        "propose_recovery_effects states=%s profile=%s",
        len(states),
        profile,
    )
    owners = _owner_map(engine_state_registry)
    _validate_recovery_config(
        recovery_config=recovery_config,
        owners=owners,
    )
    memory_parameters, parameter_id = _recovery_parameter(
        parameter_registry=parameter_registry,
        recovery_config=recovery_config,
        profile=profile,
    )
    equation_id = str(recovery_config["equation"]["rule_id"])
    baseline_version = str(
        recovery_config["mode"]["baseline_version_required"]
    )

    proposals: list[DeltaProposal] = []
    for node_id, state in sorted(states.items()):
        if state.node_id != node_id:
            raise ValueError(
                f"Recovery state key {node_id} != state.node_id {state.node_id}"
            )
        baseline = _baseline_map(state, recovery_config)
        recovery_source_id = _recovery_source_id(
            manifest=manifest,
            state=state,
        )

        for variable, variable_config in sorted(
            recovery_config["variables"].items()
        ):
            memory_class = str(variable_config["memory_class"])
            parameter_key = f"{memory_class}_days"
            if parameter_key not in memory_parameters:
                raise ValueError(
                    f"Missing memory half-life {parameter_key} in {parameter_id}"
                )
            half_life_days = float(memory_parameters[parameter_key])
            alpha = _daily_alpha(half_life_days)
            value_before = float(state.latents[variable])
            baseline_value = float(baseline[variable])
            raw_delta = (baseline_value - value_before) * alpha
            if math.isclose(raw_delta, 0.0, rel_tol=0.0, abs_tol=1e-15):
                continue

            proposal = DeltaProposal(
                proposal_id=_recovery_proposal_id(
                    recovery_source_id=recovery_source_id,
                    state=state,
                    variable=variable,
                    equation_id=equation_id,
                ),
                event_id=recovery_source_id,
                event_type="ENDOGENOUS_RECOVERY_V1",
                target_node=node_id,
                variable=variable,
                owner_module=owners[variable],
                value_before=value_before,
                raw_delta=raw_delta,
                proposed_unbounded_value=value_before + raw_delta,
                equation_id=equation_id,
                parameter_ids=(parameter_id,),
                apply_status="PROPOSED_NOT_APPLIED",
                dry_run=True,
            )
            proposals.append(proposal)
            trace.append("delta_proposal", **proposal.to_dict())
            trace.append(
                "recovery_proposal",
                proposal_id=proposal.proposal_id,
                recovery_source_id=recovery_source_id,
                node_id=node_id,
                day=state.day + 1,
                variable=variable,
                baseline_value=baseline_value,
                value_before=value_before,
                memory_class=memory_class,
                half_life_days=half_life_days,
                daily_alpha=alpha,
                raw_delta=raw_delta,
                equation_id=equation_id,
                parameter_ids=[parameter_id],
                baseline_version=baseline_version,
            )

    return tuple(sorted(proposals, key=lambda item: item.proposal_id))
