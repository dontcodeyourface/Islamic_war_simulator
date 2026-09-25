from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolutionRecord:
    resolution_id: str
    target_node: str
    variable: str
    owner_module: str
    proposal_ids: tuple[str, ...]
    value_before: float
    raw_sum_delta: float
    proposed_unbounded_value: float
    lower_bound: float
    upper_bound: float
    bounded_delta: float
    value_after: float
    clamp_amount: float
    equation_id: str
    parameter_ids: tuple[str, ...]
    apply_status: str
    runtime_level: str = "L1_COUNTRY"
    runtime_parent_node_id: str | None = None
    runtime_authority_scope: str = "FULL"
    runtime_plan_hash: str | None = None
    runtime_policy_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        logger.info("ResolutionRecord.to_dict resolution_id=%s", self.resolution_id)
        return {
            "resolution_id": self.resolution_id,
            "target_node": self.target_node,
            "variable": self.variable,
            "owner_module": self.owner_module,
            "proposal_ids": list(self.proposal_ids),
            "value_before": self.value_before,
            "raw_sum_delta": self.raw_sum_delta,
            "proposed_unbounded_value": self.proposed_unbounded_value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "bounded_delta": self.bounded_delta,
            "value_after": self.value_after,
            "clamp_amount": self.clamp_amount,
            "equation_id": self.equation_id,
            "parameter_ids": list(self.parameter_ids),
            "apply_status": self.apply_status,
            "runtime_level": self.runtime_level,
            "runtime_parent_node_id": self.runtime_parent_node_id,
            "runtime_authority_scope": self.runtime_authority_scope,
            "runtime_plan_hash": self.runtime_plan_hash,
            "runtime_policy_id": self.runtime_policy_id,
        }


@dataclass(frozen=True)
class ResolutionResult:
    states: dict[str, EngineState]
    records: tuple[ResolutionRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "ResolutionResult.to_dict states=%s records=%s",
            len(self.states),
            len(self.records),
        )
        return {
            "states": {
                node_id: state.to_dict()
                for node_id, state in sorted(self.states.items())
            },
            "records": [record.to_dict() for record in self.records],
        }


def _owner_map(engine_state_registry: dict[str, Any]) -> dict[str, str]:
    logger.info("_owner_map")
    owners: dict[str, str] = {}
    for group in engine_state_registry["latent_groups"].values():
        owner = str(group["module_owner"])
        for variable in group["variables"]:
            variable_id = str(variable["id"])
            if variable_id in owners:
                raise ValueError(f"Duplicate owner registration for {variable_id}")
            owners[variable_id] = owner
    return owners


def _resolver_parameter_id(profile: str) -> str:
    logger.info("_resolver_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "OWNER_RESOLVER_POLICY_SYN_V1"
    if profile == "calibrated_v1":
        return "OWNER_RESOLVER_POLICY_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _resolver_policy(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
) -> tuple[dict[str, Any], str]:
    logger.info("_resolver_policy profile=%s", profile)
    parameter_id = _resolver_parameter_id(profile)
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing owner resolver parameter {parameter_id} for profile {profile}"
        )
    return parameter["value"], parameter_id


def _clone_state(state: EngineState) -> EngineState:
    logger.info("_clone_state node_id=%s day=%s", state.node_id, state.day)
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes=dict(state.regimes),
        metadata=dict(state.metadata),
    )


def _runtime_context(
    *,
    target_node: str,
    runtime_context_by_node: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    logger.info("_runtime_context target_node=%s", target_node)
    default = {
        "runtime_level": "L1_COUNTRY",
        "runtime_parent_node_id": None,
        "runtime_authority_scope": "FULL",
        "runtime_plan_hash": None,
        "runtime_policy_id": None,
    }
    if runtime_context_by_node is None:
        return default
    raw = runtime_context_by_node.get(target_node)
    if raw is None:
        raise ValueError(
            f"Missing runtime resolver context for target node {target_node}"
        )
    level = str(raw.get("runtime_level", "")).strip()
    scope = str(raw.get("runtime_authority_scope", "")).strip()
    if not level or not scope:
        raise ValueError(
            f"Incomplete runtime resolver context for {target_node}"
        )
    return {
        "runtime_level": level,
        "runtime_parent_node_id": raw.get("runtime_parent_node_id"),
        "runtime_authority_scope": scope,
        "runtime_plan_hash": raw.get("runtime_plan_hash"),
        "runtime_policy_id": raw.get("runtime_policy_id"),
    }


def _resolution_id(
    *,
    target_node: str,
    variable: str,
    proposal_ids: tuple[str, ...],
    equation_id: str,
    runtime_context: dict[str, Any],
) -> str:
    logger.info(
        "_resolution_id target_node=%s variable=%s proposals=%s",
        target_node,
        variable,
        len(proposal_ids),
    )
    payload: dict[str, Any] = {
        "target_node": target_node,
        "variable": variable,
        "proposal_ids": list(proposal_ids),
        "equation_id": equation_id,
    }
    if runtime_context.get("runtime_plan_hash") is not None:
        payload["runtime_context"] = runtime_context
    digest = canonical_hash(payload)
    return f"resolve-{digest[:24]}"


def _clamp(value: float, low: float, high: float) -> float:
    logger.info("_clamp value=%s low=%s high=%s", value, low, high)
    return min(high, max(low, value))


def resolve_delta_proposals(
    *,
    states: dict[str, EngineState],
    proposals: tuple[DeltaProposal, ...] | list[DeltaProposal],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    trace: TraceLedger,
    runtime_context_by_node: dict[str, dict[str, Any]] | None = None,
) -> ResolutionResult:
    logger.info(
        "resolve_delta_proposals states=%s proposals=%s profile=%s",
        len(states),
        len(proposals),
        profile,
    )
    if runtime_context_by_node is not None:
        unknown_context_nodes = set(runtime_context_by_node) - set(states)
        if unknown_context_nodes:
            raise ValueError(
                "Runtime resolver context contains unknown nodes: "
                f"{sorted(unknown_context_nodes)}"
            )
    policy, policy_parameter_id = _resolver_policy(
        parameter_registry,
        profile=profile,
    )
    if policy["aggregation"] != "sum":
        raise ValueError(f"Unsupported aggregation policy {policy['aggregation']}")
    if not bool(policy["clamp"]):
        raise ValueError("v0.6 requires canonical bound clamping")

    latent_registry = extract_latent_registry(engine_state_registry)
    owners = _owner_map(engine_state_registry)

    proposal_ids = [proposal.proposal_id for proposal in proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate proposal_id detected")

    grouped: dict[tuple[str, str], list[DeltaProposal]] = {}
    for proposal in proposals:
        if proposal.apply_status != "PROPOSED_NOT_APPLIED":
            raise ValueError(
                f"Proposal {proposal.proposal_id} is not eligible for resolution"
            )
        if proposal.target_node not in states:
            raise KeyError(f"Unknown target node {proposal.target_node}")
        if proposal.variable not in latent_registry:
            raise KeyError(f"Unknown latent variable {proposal.variable}")
        expected_owner = owners[proposal.variable]
        if proposal.owner_module != expected_owner:
            raise ValueError(
                f"Owner mismatch for {proposal.variable}: "
                f"{proposal.owner_module} != {expected_owner}"
            )

        current_value = float(states[proposal.target_node].latents[proposal.variable])
        if not math.isclose(
            float(proposal.value_before),
            current_value,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(
                f"Stale proposal {proposal.proposal_id}: "
                f"value_before={proposal.value_before} current={current_value}"
            )
        grouped.setdefault(
            (proposal.target_node, proposal.variable),
            [],
        ).append(proposal)

    next_states = {
        node_id: _clone_state(state)
        for node_id, state in sorted(states.items())
    }
    records: list[ResolutionRecord] = []

    for target_node, variable in sorted(grouped):
        group = sorted(
            grouped[(target_node, variable)],
            key=lambda item: item.proposal_id,
        )
        proposal_id_tuple = tuple(item.proposal_id for item in group)
        value_before = float(states[target_node].latents[variable])
        raw_sum_delta = math.fsum(float(item.raw_delta) for item in group)
        unbounded = value_before + raw_sum_delta
        lower_bound, upper_bound = latent_registry[variable]
        value_after = _clamp(unbounded, lower_bound, upper_bound)
        bounded_delta = value_after - value_before
        clamp_amount = unbounded - value_after
        owner_module = owners[variable]
        runtime_context = _runtime_context(
            target_node=target_node,
            runtime_context_by_node=runtime_context_by_node,
        )

        record = ResolutionRecord(
            resolution_id=_resolution_id(
                target_node=target_node,
                variable=variable,
                proposal_ids=proposal_id_tuple,
                equation_id="OWNER_RESOLVE_SUM_CLAMP_V1",
                runtime_context=runtime_context,
            ),
            target_node=target_node,
            variable=variable,
            owner_module=owner_module,
            proposal_ids=proposal_id_tuple,
            value_before=value_before,
            raw_sum_delta=raw_sum_delta,
            proposed_unbounded_value=unbounded,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            bounded_delta=bounded_delta,
            value_after=value_after,
            clamp_amount=clamp_amount,
            equation_id="OWNER_RESOLVE_SUM_CLAMP_V1",
            parameter_ids=(policy_parameter_id,),
            apply_status="COMMITTED",
            runtime_level=runtime_context["runtime_level"],
            runtime_parent_node_id=(
                runtime_context["runtime_parent_node_id"]
            ),
            runtime_authority_scope=(
                runtime_context["runtime_authority_scope"]
            ),
            runtime_plan_hash=runtime_context["runtime_plan_hash"],
            runtime_policy_id=runtime_context["runtime_policy_id"],
        )
        next_states[target_node].latents[variable] = value_after
        trace.append("owner_resolution", **record.to_dict())
        records.append(record)

    for state in next_states.values():
        state.validate(latent_registry)

    return ResolutionResult(
        states=next_states,
        records=tuple(records),
    )
