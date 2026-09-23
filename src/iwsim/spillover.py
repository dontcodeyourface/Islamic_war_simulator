from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any

from .config import canonical_hash
from .effects import DeltaProposal
from .graph import CANONICAL_CHANNELS, CountryGraph
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraphSpilloverRecord:
    spillover_id: str
    rule_id: str
    day_created: int
    day_effective: int
    source_node: str
    target_node: str
    source_variable: str
    target_variable: str
    channel: str
    edge_id: str
    edge_weight: float | None
    source_pressure: float
    transmission_factor: float
    latency_days: int
    raw_effect: float | None
    bounded_effect: float | None
    edge_data_version: str
    parameter_ids: tuple[str, ...]
    edge_parameter_id: str | None
    apply_to_state: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "GraphSpilloverRecord.to_dict spillover_id=%s status=%s",
            self.spillover_id,
            self.status,
        )
        return {
            "spillover_id": self.spillover_id,
            "rule_id": self.rule_id,
            "day_created": self.day_created,
            "day_effective": self.day_effective,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "source_variable": self.source_variable,
            "target_variable": self.target_variable,
            "channel": self.channel,
            "edge_id": self.edge_id,
            "edge_weight": self.edge_weight,
            "source_pressure": self.source_pressure,
            "transmission_factor": self.transmission_factor,
            "latency_days": self.latency_days,
            "raw_effect": self.raw_effect,
            "bounded_effect": self.bounded_effect,
            "edge_data_version": self.edge_data_version,
            "parameter_ids": list(self.parameter_ids),
            "edge_parameter_id": self.edge_parameter_id,
            "apply_to_state": self.apply_to_state,
            "status": self.status,
        }


@dataclass(frozen=True)
class SpilloverQueueState:
    last_processed_day: int
    pending: tuple[GraphSpilloverRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SpilloverQueueState.to_dict day=%s pending=%s",
            self.last_processed_day,
            len(self.pending),
        )
        return {
            "last_processed_day": self.last_processed_day,
            "pending": [item.to_dict() for item in self.pending],
        }


@dataclass(frozen=True)
class SpilloverPassResult:
    queue: SpilloverQueueState
    candidates: tuple[GraphSpilloverRecord, ...]
    matured: tuple[GraphSpilloverRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SpilloverPassResult.to_dict candidates=%s matured=%s pending=%s",
            len(self.candidates),
            len(self.matured),
            len(self.queue.pending),
        )
        return {
            "queue": self.queue.to_dict(),
            "candidates": [item.to_dict() for item in self.candidates],
            "matured": [item.to_dict() for item in self.matured],
        }


def _parameter_id(profile: str, family: str) -> str:
    logger.info("_parameter_id profile=%s family=%s", profile, family)
    mapping = {
        "synthetic_smoke_v1": {
            "transmission": "GRAPH_TRANSMISSION_SYN_V1",
            "latency": "GRAPH_LATENCIES_SYN_V1",
        },
        "calibrated_v1": {
            "transmission": "GRAPH_TRANSMISSION_CAL_V1",
            "latency": "GRAPH_LATENCIES_CAL_V1",
        },
    }
    if profile not in mapping:
        raise ValueError(f"Unknown parameter profile: {profile}")
    return mapping[profile][family]


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
            f"Missing spillover parameter {parameter_id} for profile {profile}"
        )
    return parameter["value"]


def _validate_config(spillover_config: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    logger.info("_validate_config")
    mode = spillover_config.get("mode", {})
    trace_only = mode.get("trace_only")
    state_effects_allowed = mode.get("state_effects_allowed")
    if not isinstance(trace_only, bool) or not isinstance(state_effects_allowed, bool):
        raise ValueError("Spillover mode flags must be booleans")
    if trace_only and state_effects_allowed:
        raise ValueError("trace_only and state_effects_allowed cannot both be true")

    rules = spillover_config.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("Spillover rules must be a non-empty list")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("Spillover rule must be a mapping")
        rule_id = str(rule.get("rule_id", ""))
        source_variable = str(rule.get("source_variable", ""))
        target_variable = str(rule.get("target_variable", ""))
        channels = rule.get("channels")
        apply_to_state = rule.get("apply_to_state", False)
        if not isinstance(apply_to_state, bool):
            raise ValueError(f"Spillover rule {rule_id} apply_to_state must be boolean")
        if apply_to_state and not state_effects_allowed:
            raise ValueError(
                f"Spillover rule {rule_id} requests state effects while disabled"
            )
        if not rule_id or not source_variable or not target_variable:
            raise ValueError("Spillover rule identifiers must be non-empty")
        if rule_id in seen:
            raise ValueError(f"Duplicate spillover rule {rule_id}")
        seen.add(rule_id)
        if not isinstance(channels, list) or not channels:
            raise ValueError(f"Spillover rule {rule_id} requires channels")
        channel_names = tuple(sorted(str(item) for item in channels))
        if len(channel_names) != len(set(channel_names)):
            raise ValueError(f"Duplicate channel in spillover rule {rule_id}")
        unknown = sorted(set(channel_names) - set(CANONICAL_CHANNELS))
        if unknown:
            raise ValueError(
                f"Unknown channels in spillover rule {rule_id}: {unknown}"
            )
        normalized.append(
            {
                "rule_id": rule_id,
                "source_variable": source_variable,
                "target_variable": target_variable,
                "channels": channel_names,
                "apply_to_state": apply_to_state,
            }
        )
    return tuple(sorted(normalized, key=lambda item: item["rule_id"]))


def _validate_queue(
    *,
    queue: SpilloverQueueState,
    expected_day: int,
) -> None:
    logger.info(
        "_validate_queue expected_day=%s queue_day=%s pending=%s",
        expected_day,
        queue.last_processed_day,
        len(queue.pending),
    )
    if queue.last_processed_day != expected_day:
        raise ValueError(
            "Spillover queue day mismatch: "
            f"expected {expected_day}, got {queue.last_processed_day}"
        )
    ids = [item.spillover_id for item in queue.pending]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate spillover IDs in queue")
    for item in queue.pending:
        if item.status != "SCHEDULED":
            raise ValueError(
                f"Pending spillover {item.spillover_id} is not SCHEDULED"
            )
        if item.day_effective <= expected_day:
            raise ValueError(
                f"Stale pending spillover {item.spillover_id} "
                f"effective={item.day_effective} queue_day={expected_day}"
            )


def empty_spillover_queue(day: int) -> SpilloverQueueState:
    logger.info("empty_spillover_queue day=%s", day)
    return SpilloverQueueState(last_processed_day=day, pending=())


def _latency_days(
    *,
    day: int,
    source_node: str,
    target_node: str,
    channel: str,
    rule_id: str,
    interval: Any,
) -> int:
    logger.info(
        "_latency_days day=%s source=%s target=%s channel=%s rule=%s",
        day,
        source_node,
        target_node,
        channel,
        rule_id,
    )
    if (
        not isinstance(interval, list)
        or len(interval) != 2
        or isinstance(interval[0], bool)
        or isinstance(interval[1], bool)
    ):
        raise ValueError(f"Invalid latency interval for {channel}: {interval}")
    low = int(interval[0])
    high = int(interval[1])
    if low < 0 or high < low:
        raise ValueError(f"Invalid latency bounds for {channel}: {interval}")
    span = high - low + 1
    digest = canonical_hash(
        {
            "day": day,
            "source_node": source_node,
            "target_node": target_node,
            "channel": channel,
            "rule_id": rule_id,
            "latency_contract": "DETERMINISTIC_HASH_INTERVAL_V1",
        }
    )
    return low + (int(digest[:16], 16) % span)


def _spillover_id(
    *,
    day: int,
    day_effective: int,
    rule_id: str,
    source_node: str,
    target_node: str,
    channel: str,
    edge_id: str,
    edge_weight: float | None,
    source_pressure: float,
    transmission_factor: float,
    edge_data_version: str,
    apply_to_state: bool,
) -> str:
    logger.info(
        "_spillover_id day=%s rule=%s source=%s target=%s channel=%s",
        day,
        rule_id,
        source_node,
        target_node,
        channel,
    )
    digest = canonical_hash(
        {
            "day_created": day,
            "day_effective": day_effective,
            "rule_id": rule_id,
            "source_node": source_node,
            "target_node": target_node,
            "channel": channel,
            "edge_id": edge_id,
            "edge_weight": edge_weight,
            "source_pressure": source_pressure,
            "transmission_factor": transmission_factor,
            "edge_data_version": edge_data_version,
            "apply_to_state": apply_to_state,
        }
    )
    return f"spill-{digest[:24]}"


def _candidate_status(
    *,
    edge_weight: float | None,
    source_pressure: float,
    transmission_factor: float,
) -> str:
    logger.info(
        "_candidate_status edge_weight=%s source_pressure=%s factor=%s",
        edge_weight,
        source_pressure,
        transmission_factor,
    )
    if edge_weight is None:
        return "UNRESOLVED_CHANNEL"
    if edge_weight == 0.0:
        return "ZERO_EDGE"
    if source_pressure == 0.0:
        return "ZERO_SOURCE"
    if transmission_factor == 0.0:
        return "ZERO_TRANSMISSION"
    return "SCHEDULED"


def evaluate_graph_spillovers(
    *,
    day: int,
    states: dict[str, EngineState],
    graph: CountryGraph,
    spillover_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    queue: SpilloverQueueState,
    trace: TraceLedger,
) -> SpilloverPassResult:
    """Evaluate trace-only cross-node transmissions and deterministic latency queues."""
    logger.info(
        "evaluate_graph_spillovers day=%s states=%s edges=%s profile=%s",
        day,
        len(states),
        len(graph.edges),
        profile,
    )
    if day <= 0:
        raise ValueError("Spillover evaluation day must be positive")
    _validate_queue(queue=queue, expected_day=day - 1)
    rules = _validate_config(spillover_config)

    graph.validate()
    graph_nodes = {node.iso3 for node in graph.nodes}
    if set(states) != graph_nodes:
        raise ValueError("Spillover state nodes must equal graph nodes")

    transmission_id = _parameter_id(profile, "transmission")
    latency_id = _parameter_id(profile, "latency")
    transmission = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=transmission_id,
    )
    latencies = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=latency_id,
    )
    edge_data_version = graph.graph_hash()

    matured: list[GraphSpilloverRecord] = []
    pending: list[GraphSpilloverRecord] = []
    for item in sorted(queue.pending, key=lambda record: record.spillover_id):
        if item.day_effective <= day:
            matured_item = replace(
                item,
                status=(
                    "MATURED_READY_FOR_PROPOSAL"
                    if item.apply_to_state
                    else "MATURED_TRACE_ONLY"
                ),
            )
            matured.append(matured_item)
            trace.append("graph_spillover_matured", **matured_item.to_dict())
        else:
            pending.append(item)

    candidates: list[GraphSpilloverRecord] = []
    for rule in rules:
        source_variable = rule["source_variable"]
        target_variable = rule["target_variable"]
        for node_id, state in sorted(states.items()):
            if source_variable not in state.latents:
                raise KeyError(
                    f"Spillover source variable {source_variable} missing from {node_id}"
                )
            if target_variable not in state.latents:
                raise KeyError(
                    f"Spillover target variable {target_variable} missing from {node_id}"
                )

        for edge in sorted(graph.edges, key=lambda item: item.edge_id()):
            directions = tuple(sorted(((edge.a, edge.b), (edge.b, edge.a))))
            for source_node, target_node in directions:
                source_pressure = float(states[source_node].latents[source_variable])
                for channel in rule["channels"]:
                    if channel not in transmission:
                        raise KeyError(
                            f"Transmission factor missing for channel {channel}"
                        )
                    if channel not in latencies:
                        raise KeyError(f"Latency interval missing for channel {channel}")
                    factor = float(transmission[channel])
                    edge_weight = edge.channel(source_node, target_node, channel)
                    edge_parameter_id = edge.channel_parameter_id(
                        source_node,
                        target_node,
                        channel,
                    )
                    latency = _latency_days(
                        day=day,
                        source_node=source_node,
                        target_node=target_node,
                        channel=channel,
                        rule_id=rule["rule_id"],
                        interval=latencies[channel],
                    )
                    day_effective = day + latency
                    status = _candidate_status(
                        edge_weight=edge_weight,
                        source_pressure=source_pressure,
                        transmission_factor=factor,
                    )
                    raw_effect = (
                        None
                        if edge_weight is None
                        else edge_weight * source_pressure * factor
                    )
                    parameter_ids = tuple(
                        item
                        for item in (
                            transmission_id,
                            latency_id,
                            edge_parameter_id,
                        )
                        if item is not None
                    )
                    record = GraphSpilloverRecord(
                        spillover_id=_spillover_id(
                            day=day,
                            day_effective=day_effective,
                            rule_id=rule["rule_id"],
                            source_node=source_node,
                            target_node=target_node,
                            channel=channel,
                            edge_id=edge.edge_id(),
                            edge_weight=edge_weight,
                            source_pressure=source_pressure,
                            transmission_factor=factor,
                            edge_data_version=edge_data_version,
                            apply_to_state=bool(rule["apply_to_state"]),
                        ),
                        rule_id=rule["rule_id"],
                        day_created=day,
                        day_effective=day_effective,
                        source_node=source_node,
                        target_node=target_node,
                        source_variable=source_variable,
                        target_variable=target_variable,
                        channel=channel,
                        edge_id=edge.edge_id(),
                        edge_weight=edge_weight,
                        source_pressure=source_pressure,
                        transmission_factor=factor,
                        latency_days=latency,
                        raw_effect=raw_effect,
                        bounded_effect=raw_effect,
                        edge_data_version=edge_data_version,
                        parameter_ids=parameter_ids,
                        edge_parameter_id=edge_parameter_id,
                        apply_to_state=bool(rule["apply_to_state"]),
                        status=status,
                    )
                    candidates.append(record)
                    trace.append("graph_spillover_candidate", **record.to_dict())

                    if status != "SCHEDULED":
                        continue
                    if record.day_effective <= day:
                        matured_item = replace(
                            record,
                            status=(
                                "MATURED_READY_FOR_PROPOSAL"
                                if record.apply_to_state
                                else "MATURED_TRACE_ONLY"
                            ),
                        )
                        matured.append(matured_item)
                        trace.append(
                            "graph_spillover_matured",
                            **matured_item.to_dict(),
                        )
                    else:
                        pending.append(record)

    candidate_ids = [item.spillover_id for item in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Duplicate spillover candidate IDs")
    pending_ids = [item.spillover_id for item in pending]
    if len(pending_ids) != len(set(pending_ids)):
        raise ValueError("Duplicate spillover pending IDs")

    next_queue = SpilloverQueueState(
        last_processed_day=day,
        pending=tuple(sorted(pending, key=lambda item: item.spillover_id)),
    )
    trace.append(
        "graph_spillover_queue_committed",
        day=day,
        pending_spillover_ids=[
            item.spillover_id for item in next_queue.pending
        ],
        matured_spillover_ids=[
            item.spillover_id
            for item in sorted(matured, key=lambda record: record.spillover_id)
        ],
    )
    return SpilloverPassResult(
        queue=next_queue,
        candidates=tuple(
            sorted(candidates, key=lambda item: item.spillover_id)
        ),
        matured=tuple(sorted(matured, key=lambda item: item.spillover_id)),
    )


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


def _spillover_proposal_id(record: GraphSpilloverRecord) -> str:
    logger.info(
        "_spillover_proposal_id spillover_id=%s target=%s variable=%s",
        record.spillover_id,
        record.target_node,
        record.target_variable,
    )
    digest = canonical_hash(
        {
            "spillover_id": record.spillover_id,
            "target_node": record.target_node,
            "target_variable": record.target_variable,
            "equation_id": record.rule_id,
            "proposal_contract": "GRAPH_SPILLOVER_PROPOSAL_V1",
        }
    )
    return f"delta-{digest[:24]}"


def propose_matured_spillover_effects(
    *,
    matured: tuple[GraphSpilloverRecord, ...] | list[GraphSpilloverRecord],
    states: dict[str, EngineState],
    engine_state_registry: dict[str, Any],
    trace: TraceLedger,
) -> tuple[DeltaProposal, ...]:
    """Convert eligible matured spillovers into canonical owner-resolved proposals."""
    logger.info(
        "propose_matured_spillover_effects matured=%s states=%s",
        len(matured),
        len(states),
    )
    owners = _owner_map(engine_state_registry)
    proposals: list[DeltaProposal] = []

    for record in sorted(matured, key=lambda item: item.spillover_id):
        if not record.apply_to_state:
            if record.status != "MATURED_TRACE_ONLY":
                raise ValueError(
                    f"Trace-only spillover {record.spillover_id} has invalid status "
                    f"{record.status}"
                )
            continue

        if record.status != "MATURED_READY_FOR_PROPOSAL":
            raise ValueError(
                f"State-changing spillover {record.spillover_id} is not proposal-ready"
            )
        if record.target_node not in states:
            raise KeyError(f"Unknown spillover target node {record.target_node}")
        if record.target_variable not in owners:
            raise KeyError(
                f"No owner module registered for {record.target_variable}"
            )
        if record.target_variable not in states[record.target_node].latents:
            raise KeyError(
                f"Spillover target variable {record.target_variable} missing from "
                f"{record.target_node}"
            )
        if record.bounded_effect is None:
            raise ValueError(
                f"State-changing spillover {record.spillover_id} has no effect value"
            )

        value_before = float(
            states[record.target_node].latents[record.target_variable]
        )
        raw_delta = float(record.bounded_effect)
        proposal = DeltaProposal(
            proposal_id=_spillover_proposal_id(record),
            event_id=record.spillover_id,
            event_type="GRAPH_SPILLOVER_V1",
            target_node=record.target_node,
            variable=record.target_variable,
            owner_module=owners[record.target_variable],
            value_before=value_before,
            raw_delta=raw_delta,
            proposed_unbounded_value=value_before + raw_delta,
            equation_id=record.rule_id,
            parameter_ids=record.parameter_ids,
            apply_status="PROPOSED_NOT_APPLIED",
            dry_run=True,
        )
        trace.append(
            "spillover_delta_proposal",
            spillover_id=record.spillover_id,
            source_node=record.source_node,
            channel=record.channel,
            **proposal.to_dict(),
        )
        trace.append("delta_proposal", **proposal.to_dict())
        proposals.append(proposal)

    proposal_ids = [item.proposal_id for item in proposals]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise ValueError("Duplicate spillover proposal IDs")
    return tuple(sorted(proposals, key=lambda item: item.proposal_id))
