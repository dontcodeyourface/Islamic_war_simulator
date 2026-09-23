from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .events import SimEvent
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeltaProposal:
    proposal_id: str
    event_id: str
    event_type: str
    target_node: str
    variable: str
    owner_module: str
    value_before: float
    raw_delta: float
    proposed_unbounded_value: float
    equation_id: str
    parameter_ids: tuple[str, ...]
    apply_status: str
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        logger.info("DeltaProposal.to_dict proposal_id=%s", self.proposal_id)
        return {
            "proposal_id": self.proposal_id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "target_node": self.target_node,
            "variable": self.variable,
            "owner_module": self.owner_module,
            "value_before": self.value_before,
            "raw_delta": self.raw_delta,
            "proposed_unbounded_value": self.proposed_unbounded_value,
            "equation_id": self.equation_id,
            "parameter_ids": list(self.parameter_ids),
            "apply_status": self.apply_status,
            "dry_run": self.dry_run,
        }


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
        raise ValueError(f"Missing effect parameter {parameter_id} for {profile}")
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


def _effect_parameter_id(profile: str) -> str:
    logger.info("_effect_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "EVENT_EFFECT_PROPOSALS_SYN_V1"
    if profile == "calibrated_v1":
        return "EVENT_EFFECT_PROPOSALS_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _proposal_id(
    *,
    event: SimEvent,
    target_node: str,
    variable: str,
) -> str:
    logger.info(
        "_proposal_id event_id=%s target_node=%s variable=%s",
        event.event_id,
        target_node,
        variable,
    )
    digest = canonical_hash(
        {
            "event_id": event.event_id,
            "target_node": target_node,
            "variable": variable,
            "equation_id": "EVENT_EFFECT_PROPOSAL_V1",
        }
    )
    return f"delta-{digest[:24]}"


def propose_event_effects(
    *,
    event: SimEvent,
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    logger.info(
        "propose_event_effects event_id=%s event_type=%s profile=%s",
        event.event_id,
        event.event_type,
        profile,
    )
    if not event.dry_run:
        raise ValueError("v0.5 proposal layer expects dry-run SimEvent inputs")

    parameter_id = _effect_parameter_id(profile)
    effect_set = _parameter(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    event_effect = effect_set.get(event.event_type)
    if event_effect is None:
        return ()

    owners = _owner_map(engine_state_registry)
    each_actor = event_effect.get("each_actor", {})
    proposals: list[DeltaProposal] = []

    for target_node in event.actors:
        if target_node not in states:
            raise KeyError(f"Missing EngineState for event actor {target_node}")
        state = states[target_node]
        for variable, raw_delta_value in sorted(each_actor.items()):
            if variable not in state.latents:
                raise KeyError(
                    f"Effect variable {variable} missing from state {target_node}"
                )
            if variable not in owners:
                raise KeyError(f"No owner module registered for {variable}")
            value_before = float(state.latents[variable])
            raw_delta = float(raw_delta_value)
            proposal = DeltaProposal(
                proposal_id=_proposal_id(
                    event=event,
                    target_node=target_node,
                    variable=variable,
                ),
                event_id=event.event_id,
                event_type=event.event_type,
                target_node=target_node,
                variable=variable,
                owner_module=owners[variable],
                value_before=value_before,
                raw_delta=raw_delta,
                proposed_unbounded_value=value_before + raw_delta,
                equation_id="EVENT_EFFECT_PROPOSAL_V1",
                parameter_ids=(parameter_id,),
                apply_status="PROPOSED_NOT_APPLIED",
                dry_run=True,
            )
            proposals.append(proposal)
            trace.append("delta_proposal", **proposal.to_dict())

    return tuple(proposals)
