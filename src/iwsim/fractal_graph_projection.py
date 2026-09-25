from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_runtime import FractalRuntimePlan
from .graph import (
    CANONICAL_CHANNELS,
    DIRECTED_CHANNELS,
    SYMMETRIC_CHANNELS,
    CountryGraph,
)
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalProjectedGraphNode:
    runtime_node_id: str
    parent_node_id: str | None
    level: str
    catalog_node_id: str
    lineage_generation: int | None

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalProjectedGraphNode.to_dict node=%s level=%s",
            self.runtime_node_id,
            self.level,
        )
        return {
            "runtime_node_id": self.runtime_node_id,
            "parent_node_id": self.parent_node_id,
            "level": self.level,
            "catalog_node_id": self.catalog_node_id,
            "lineage_generation": self.lineage_generation,
        }


@dataclass(frozen=True)
class FractalProjectedChannelValue:
    name: str
    a_to_b: float | None
    b_to_a: float | None
    status_a_to_b: str
    status_b_to_a: str
    parameter_id_a_to_b: str | None
    parameter_id_b_to_a: str | None
    source_id_a_to_b: str | None
    source_id_b_to_a: str | None
    projection_policy_id: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalProjectedChannelValue.to_dict channel=%s",
            self.name,
        )
        return {
            "name": self.name,
            "a_to_b": self.a_to_b,
            "b_to_a": self.b_to_a,
            "status_a_to_b": self.status_a_to_b,
            "status_b_to_a": self.status_b_to_a,
            "parameter_id_a_to_b": self.parameter_id_a_to_b,
            "parameter_id_b_to_a": self.parameter_id_b_to_a,
            "source_id_a_to_b": self.source_id_a_to_b,
            "source_id_b_to_a": self.source_id_b_to_a,
            "projection_policy_id": self.projection_policy_id,
        }


@dataclass(frozen=True)
class FractalProjectedGraphEdge:
    a: str
    b: str
    catalog_a: str
    catalog_b: str
    edge_kind: str
    channels: tuple[FractalProjectedChannelValue, ...]

    def edge_id(self) -> str:
        logger.info(
            "FractalProjectedGraphEdge.edge_id a=%s b=%s",
            self.a,
            self.b,
        )
        return "--".join(sorted((self.a, self.b)))

    def _validate_endpoints(self, source: str, target: str) -> None:
        logger.info(
            "FractalProjectedGraphEdge._validate_endpoints edge=%s source=%s target=%s",
            self.edge_id(),
            source,
            target,
        )
        if source == target:
            raise ValueError("Projected graph source and target must differ")
        if {source, target} != {self.a, self.b}:
            raise ValueError(
                f"{source}->{target} does not match projected edge "
                f"{self.a}/{self.b}"
            )

    def _channel(self, channel_name: str) -> FractalProjectedChannelValue:
        logger.info(
            "FractalProjectedGraphEdge._channel edge=%s channel=%s",
            self.edge_id(),
            channel_name,
        )
        for channel in self.channels:
            if channel.name == channel_name:
                return channel
        raise KeyError(channel_name)

    def channel(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> float | None:
        logger.info(
            "FractalProjectedGraphEdge.channel edge=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)
        channel = self._channel(channel_name)
        return (
            channel.a_to_b
            if source == self.a
            else channel.b_to_a
        )

    def channel_status(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> str:
        logger.info(
            "FractalProjectedGraphEdge.channel_status edge=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)
        channel = self._channel(channel_name)
        return (
            channel.status_a_to_b
            if source == self.a
            else channel.status_b_to_a
        )

    def channel_parameter_id(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> str | None:
        logger.info(
            "FractalProjectedGraphEdge.channel_parameter_id edge=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)
        channel = self._channel(channel_name)
        return (
            channel.parameter_id_a_to_b
            if source == self.a
            else channel.parameter_id_b_to_a
        )

    def channel_source_id(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> str | None:
        logger.info(
            "FractalProjectedGraphEdge.channel_source_id edge=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)
        channel = self._channel(channel_name)
        return (
            channel.source_id_a_to_b
            if source == self.a
            else channel.source_id_b_to_a
        )

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalProjectedGraphEdge.to_dict edge=%s kind=%s",
            self.edge_id(),
            self.edge_kind,
        )
        return {
            "edge_id": self.edge_id(),
            "a": self.a,
            "b": self.b,
            "catalog_a": self.catalog_a,
            "catalog_b": self.catalog_b,
            "edge_kind": self.edge_kind,
            "channels": {
                item.name: item.to_dict()
                for item in sorted(
                    self.channels,
                    key=lambda value: value.name,
                )
            },
        }


@dataclass(frozen=True)
class FractalProjectedGraph:
    day: int
    policy_id: str
    runtime_plan_hash: str
    base_graph_hash: str
    catalog_hash: str
    nodes: tuple[FractalProjectedGraphNode, ...]
    edges: tuple[FractalProjectedGraphEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalProjectedGraph.to_dict day=%s nodes=%s edges=%s",
            self.day,
            len(self.nodes),
            len(self.edges),
        )
        return {
            "day": self.day,
            "policy_id": self.policy_id,
            "runtime_plan_hash": self.runtime_plan_hash,
            "base_graph_hash": self.base_graph_hash,
            "catalog_hash": self.catalog_hash,
            "nodes": [
                item.to_dict()
                for item in sorted(
                    self.nodes,
                    key=lambda value: value.runtime_node_id,
                )
            ],
            "edges": [
                item.to_dict()
                for item in sorted(
                    self.edges,
                    key=lambda value: value.edge_id(),
                )
            ],
        }

    def graph_hash(self) -> str:
        logger.info(
            "FractalProjectedGraph.graph_hash day=%s",
            self.day,
        )
        return canonical_hash(self.to_dict())

    def edge(self, a: str, b: str) -> FractalProjectedGraphEdge:
        logger.info(
            "FractalProjectedGraph.edge a=%s b=%s",
            a,
            b,
        )
        edge_id = "--".join(sorted((a, b)))
        for edge in self.edges:
            if edge.edge_id() == edge_id:
                return edge
        raise KeyError(edge_id)

    def validate(self) -> None:
        logger.info(
            "FractalProjectedGraph.validate day=%s nodes=%s edges=%s",
            self.day,
            len(self.nodes),
            len(self.edges),
        )
        node_ids = [
            item.runtime_node_id
            for item in self.nodes
        ]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate projected graph node IDs")
        expected_edges = len(node_ids) * (len(node_ids) - 1) // 2
        if len(self.edges) != expected_edges:
            raise ValueError(
                "Projected graph pair coverage mismatch: "
                f"expected={expected_edges} actual={len(self.edges)}"
            )

        seen_edges: set[str] = set()
        node_set = set(node_ids)
        for edge in self.edges:
            if edge.a == edge.b:
                raise ValueError(
                    f"Projected self-edge forbidden: {edge.a}"
                )
            if edge.a not in node_set or edge.b not in node_set:
                raise ValueError(
                    f"Projected edge references unknown node {edge.edge_id()}"
                )
            if edge.edge_id() in seen_edges:
                raise ValueError(
                    f"Duplicate projected edge {edge.edge_id()}"
                )
            seen_edges.add(edge.edge_id())

            channel_names = tuple(
                sorted(item.name for item in edge.channels)
            )
            if channel_names != tuple(sorted(CANONICAL_CHANNELS)):
                raise ValueError(
                    f"Projected edge {edge.edge_id()} channel mismatch"
                )
            for channel in edge.channels:
                _validate_optional_unit_interval(
                    value=channel.a_to_b,
                    label=(
                        f"{edge.edge_id()}:{channel.name}:a_to_b"
                    ),
                )
                _validate_optional_unit_interval(
                    value=channel.b_to_a,
                    label=(
                        f"{edge.edge_id()}:{channel.name}:b_to_a"
                    ),
                )
                if channel.name in SYMMETRIC_CHANNELS:
                    if channel.a_to_b != channel.b_to_a:
                        raise ValueError(
                            f"Projected symmetric channel {channel.name} "
                            f"differs by direction on {edge.edge_id()}"
                        )
                    if (
                        channel.status_a_to_b
                        != channel.status_b_to_a
                    ):
                        raise ValueError(
                            f"Projected symmetric status {channel.name} "
                            f"differs by direction on {edge.edge_id()}"
                        )


def _validate_optional_unit_interval(
    *,
    value: float | None,
    label: str,
) -> None:
    logger.info(
        "_validate_optional_unit_interval label=%s value=%s",
        label,
        value,
    )
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(
            f"Projected graph value {label} outside [0,1]: {value}"
        )


def _validate_projection_config(
    config: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_validate_projection_config")
    mode = config.get("mode", {})
    required_true = (
        "projection_allowed",
        "active_regional_authority_nodes_only",
        "complete_runtime_pair_coverage",
        "unresolved_values_remain_null",
        "topology_changes_take_effect_next_day",
        "inactive_lineage_forbidden",
        "no_implicit_parent_edge_cloning",
    )
    for key in required_true:
        if mode.get(key) is not True:
            raise ValueError(
                f"v0.29 graph projection requires {key}=true"
            )

    policy_id = str(config.get("policy_id", "")).strip()
    if not policy_id:
        raise ValueError(
            "Fractal graph projection policy_id is required"
        )

    raw_policies = config.get("channel_policies")
    if not isinstance(raw_policies, dict):
        raise ValueError(
            "Fractal graph projection channel_policies must be a mapping"
        )
    if set(raw_policies) != set(CANONICAL_CHANNELS):
        raise ValueError(
            "Fractal graph projection must classify every canonical channel"
        )

    policies: dict[str, dict[str, str]] = {}
    for channel in sorted(CANONICAL_CHANNELS):
        item = raw_policies[channel]
        if not isinstance(item, dict):
            raise ValueError(
                f"Projection policy for {channel} must be a mapping"
            )
        l1_mode = str(item.get("l1_to_l1", ""))
        l2_mode = str(item.get("any_l2", ""))
        channel_policy_id = str(
            item.get("projection_policy_id", "")
        )
        if l1_mode != "base_exact":
            raise ValueError(
                f"v0.29 L1-to-L1 channel {channel} must remain base_exact"
            )
        allowed_l2 = {
            "explicit_catalog_required",
            "parent_retained_not_projected",
        }
        if l2_mode not in allowed_l2:
            raise ValueError(
                f"Unsupported L2 projection mode {l2_mode} for {channel}"
            )
        if (
            channel == "alliance_link"
            and l2_mode != "parent_retained_not_projected"
        ):
            raise ValueError(
                "v0.29 alliance_link must remain parent-retained"
            )
        if (
            channel != "alliance_link"
            and l2_mode != "explicit_catalog_required"
        ):
            raise ValueError(
                f"v0.29 regional channel {channel} requires explicit catalog"
            )
        if not channel_policy_id:
            raise ValueError(
                f"Projection policy ID missing for {channel}"
            )
        policies[channel] = {
            "l1_mode": l1_mode,
            "l2_mode": l2_mode,
            "projection_policy_id": channel_policy_id,
        }

    statuses = config.get("statuses")
    if not isinstance(statuses, dict):
        raise ValueError(
            "Fractal graph projection statuses must be a mapping"
        )
    required_statuses = (
        "base_resolved",
        "base_unresolved",
        "explicit_resolved",
        "explicit_unresolved",
        "unresolved_projection",
        "parent_retained",
    )
    if set(statuses) != set(required_statuses):
        raise ValueError(
            "Fractal graph projection status registry mismatch"
        )

    return {
        "policy_id": policy_id,
        "policies": policies,
        "statuses": {
            key: str(statuses[key])
            for key in required_statuses
        },
    }


def _catalog_edge_index(
    catalog: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    logger.info("_catalog_edge_index")
    raw_edges = catalog.get("edges")
    if not isinstance(raw_edges, list):
        raise ValueError(
            "Regional graph catalog edges must be a list"
        )

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in raw_edges:
        if not isinstance(raw, dict):
            raise ValueError(
                "Regional graph catalog edge must be a mapping"
            )
        endpoint_a = str(raw.get("a", "")).strip()
        endpoint_b = str(raw.get("b", "")).strip()
        source_id = str(raw.get("source_id", "")).strip()
        if (
            not endpoint_a
            or not endpoint_b
            or endpoint_a == endpoint_b
        ):
            raise ValueError(
                f"Invalid regional graph catalog endpoints: {raw}"
            )
        if not source_id:
            raise ValueError(
                "Regional graph catalog edge requires source_id"
            )
        if "::g" in endpoint_a or "::g" in endpoint_b:
            raise ValueError(
                "Regional graph catalog must use stable catalog IDs, "
                "not runtime generation IDs"
            )

        channels = raw.get("channels", {})
        if not isinstance(channels, dict):
            raise ValueError(
                "Regional graph catalog edge channels must be a mapping"
            )
        unknown = set(channels) - set(CANONICAL_CHANNELS)
        if unknown:
            raise ValueError(
                "Regional graph catalog contains unknown channels: "
                f"{sorted(unknown)}"
            )

        key = tuple(sorted((endpoint_a, endpoint_b)))
        if key in result:
            raise ValueError(
                f"Duplicate regional graph catalog edge {key}"
            )
        result[key] = {
            "a": endpoint_a,
            "b": endpoint_b,
            "source_id": source_id,
            "channels": channels,
        }
    return result


def _catalog_optional_value(
    *,
    value: Any,
    label: str,
) -> float | None:
    logger.info(
        "_catalog_optional_value label=%s value=%s",
        label,
        value,
    )
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(
            f"Regional graph catalog value {label} must be numeric or null"
        )
    numeric = float(value)
    _validate_optional_unit_interval(
        value=numeric,
        label=label,
    )
    return numeric


def _runtime_nodes(
    *,
    runtime_plan: FractalRuntimePlan,
    base_graph: CountryGraph,
) -> tuple[FractalProjectedGraphNode, ...]:
    logger.info(
        "_runtime_nodes day=%s plan_nodes=%s",
        runtime_plan.day,
        len(runtime_plan.nodes),
    )
    base_ids = {node.iso3 for node in base_graph.nodes}
    nodes: list[FractalProjectedGraphNode] = []
    for authority in sorted(
        runtime_plan.nodes,
        key=lambda item: item.runtime_node_id,
    ):
        if not authority.owns_regionalizable_state:
            continue
        if authority.level == "L1_COUNTRY":
            if authority.runtime_node_id not in base_ids:
                raise ValueError(
                    "Projected graph L1 node missing from base graph: "
                    f"{authority.runtime_node_id}"
                )
        elif authority.level == "L2_REGION":
            if authority.parent_node_id not in base_ids:
                raise ValueError(
                    "Projected graph L2 parent missing from base graph: "
                    f"{authority.parent_node_id}"
                )
        else:
            raise ValueError(
                f"v0.29 unsupported runtime graph level {authority.level}"
            )
        nodes.append(
            FractalProjectedGraphNode(
                runtime_node_id=authority.runtime_node_id,
                parent_node_id=authority.parent_node_id,
                level=authority.level,
                catalog_node_id=authority.catalog_node_id,
                lineage_generation=authority.lineage_generation,
            )
        )
    return tuple(nodes)


def _edge_kind(
    *,
    a: FractalProjectedGraphNode,
    b: FractalProjectedGraphNode,
) -> str:
    logger.info(
        "_edge_kind a=%s b=%s",
        a.runtime_node_id,
        b.runtime_node_id,
    )
    if a.level == "L1_COUNTRY" and b.level == "L1_COUNTRY":
        return "BASE_L1"
    if a.level == "L2_REGION" and b.level == "L2_REGION":
        if a.parent_node_id == b.parent_node_id:
            return "INTERNAL_L2"
        return "CROSS_PARENT_L2"
    return "L2_EXTERNAL"


def _base_channel(
    *,
    runtime_a: str,
    runtime_b: str,
    channel_name: str,
    base_graph: CountryGraph,
    policy_id: str,
    statuses: dict[str, str],
) -> FractalProjectedChannelValue:
    logger.info(
        "_base_channel a=%s b=%s channel=%s",
        runtime_a,
        runtime_b,
        channel_name,
    )
    edge = base_graph.edge(runtime_a, runtime_b)
    value_ab = edge.channel(
        runtime_a,
        runtime_b,
        channel_name,
    )
    value_ba = edge.channel(
        runtime_b,
        runtime_a,
        channel_name,
    )
    status_ab = (
        statuses["base_resolved"]
        if value_ab is not None
        else statuses["base_unresolved"]
    )
    status_ba = (
        statuses["base_resolved"]
        if value_ba is not None
        else statuses["base_unresolved"]
    )
    source_id = f"BASE_COUNTRY_GRAPH:{edge.edge_id()}"
    return FractalProjectedChannelValue(
        name=channel_name,
        a_to_b=value_ab,
        b_to_a=value_ba,
        status_a_to_b=status_ab,
        status_b_to_a=status_ba,
        parameter_id_a_to_b=edge.channel_parameter_id(
            runtime_a,
            runtime_b,
            channel_name,
        ),
        parameter_id_b_to_a=edge.channel_parameter_id(
            runtime_b,
            runtime_a,
            channel_name,
        ),
        source_id_a_to_b=source_id,
        source_id_b_to_a=source_id,
        projection_policy_id=policy_id,
    )


def _parent_retained_channel(
    *,
    channel_name: str,
    policy_id: str,
    statuses: dict[str, str],
) -> FractalProjectedChannelValue:
    logger.info(
        "_parent_retained_channel channel=%s",
        channel_name,
    )
    status = statuses["parent_retained"]
    return FractalProjectedChannelValue(
        name=channel_name,
        a_to_b=None,
        b_to_a=None,
        status_a_to_b=status,
        status_b_to_a=status,
        parameter_id_a_to_b=None,
        parameter_id_b_to_a=None,
        source_id_a_to_b=None,
        source_id_b_to_a=None,
        projection_policy_id=policy_id,
    )


def _unresolved_channel(
    *,
    channel_name: str,
    policy_id: str,
    statuses: dict[str, str],
) -> FractalProjectedChannelValue:
    logger.info(
        "_unresolved_channel channel=%s",
        channel_name,
    )
    status = statuses["unresolved_projection"]
    return FractalProjectedChannelValue(
        name=channel_name,
        a_to_b=None,
        b_to_a=None,
        status_a_to_b=status,
        status_b_to_a=status,
        parameter_id_a_to_b=None,
        parameter_id_b_to_a=None,
        source_id_a_to_b=None,
        source_id_b_to_a=None,
        projection_policy_id=policy_id,
    )


def _catalog_directional_metadata(
    *,
    raw: dict[str, Any],
    direction: str,
    edge_source_id: str,
) -> tuple[float | None, str | None, str]:
    logger.info(
        "_catalog_directional_metadata direction=%s source=%s",
        direction,
        edge_source_id,
    )
    value = _catalog_optional_value(
        value=raw.get(direction),
        label=f"{edge_source_id}:{direction}",
    )
    parameter_id = raw.get(f"parameter_id_{direction}")
    source_id = raw.get(f"source_id_{direction}", edge_source_id)
    return (
        value,
        str(parameter_id) if parameter_id is not None else None,
        str(source_id),
    )


def _explicit_catalog_channel(
    *,
    node_a: FractalProjectedGraphNode,
    node_b: FractalProjectedGraphNode,
    channel_name: str,
    catalog_edge: dict[str, Any] | None,
    policy_id: str,
    statuses: dict[str, str],
) -> FractalProjectedChannelValue:
    logger.info(
        "_explicit_catalog_channel a=%s b=%s channel=%s catalog_edge=%s",
        node_a.runtime_node_id,
        node_b.runtime_node_id,
        channel_name,
        catalog_edge is not None,
    )
    if catalog_edge is None:
        return _unresolved_channel(
            channel_name=channel_name,
            policy_id=policy_id,
            statuses=statuses,
        )
    raw_channel = catalog_edge["channels"].get(channel_name)
    if raw_channel is None:
        return _unresolved_channel(
            channel_name=channel_name,
            policy_id=policy_id,
            statuses=statuses,
        )
    if not isinstance(raw_channel, dict):
        raise ValueError(
            f"Regional catalog channel {channel_name} must be a mapping"
        )

    source_id = str(catalog_edge["source_id"])
    if channel_name in SYMMETRIC_CHANNELS:
        value = _catalog_optional_value(
            value=raw_channel.get("value"),
            label=f"{source_id}:{channel_name}:value",
        )
        parameter = raw_channel.get("parameter_id")
        channel_source = str(
            raw_channel.get("source_id", source_id)
        )
        status = (
            statuses["explicit_resolved"]
            if value is not None
            else statuses["explicit_unresolved"]
        )
        return FractalProjectedChannelValue(
            name=channel_name,
            a_to_b=value,
            b_to_a=value,
            status_a_to_b=status,
            status_b_to_a=status,
            parameter_id_a_to_b=(
                str(parameter) if parameter is not None else None
            ),
            parameter_id_b_to_a=(
                str(parameter) if parameter is not None else None
            ),
            source_id_a_to_b=channel_source,
            source_id_b_to_a=channel_source,
            projection_policy_id=policy_id,
        )

    if channel_name not in DIRECTED_CHANNELS:
        raise ValueError(
            f"Unknown projected channel directionality {channel_name}"
        )

    catalog_a = str(catalog_edge["a"])
    catalog_b = str(catalog_edge["b"])
    runtime_matches_catalog = (
        node_a.catalog_node_id == catalog_a
        and node_b.catalog_node_id == catalog_b
    )
    reverse_matches_catalog = (
        node_a.catalog_node_id == catalog_b
        and node_b.catalog_node_id == catalog_a
    )
    if not runtime_matches_catalog and not reverse_matches_catalog:
        raise ValueError(
            "Regional graph catalog edge endpoint mismatch for "
            f"{node_a.catalog_node_id}/{node_b.catalog_node_id}"
        )

    ab_key = "a_to_b" if runtime_matches_catalog else "b_to_a"
    ba_key = "b_to_a" if runtime_matches_catalog else "a_to_b"
    value_ab, parameter_ab, source_ab = _catalog_directional_metadata(
        raw=raw_channel,
        direction=ab_key,
        edge_source_id=source_id,
    )
    value_ba, parameter_ba, source_ba = _catalog_directional_metadata(
        raw=raw_channel,
        direction=ba_key,
        edge_source_id=source_id,
    )
    return FractalProjectedChannelValue(
        name=channel_name,
        a_to_b=value_ab,
        b_to_a=value_ba,
        status_a_to_b=(
            statuses["explicit_resolved"]
            if value_ab is not None
            else statuses["explicit_unresolved"]
        ),
        status_b_to_a=(
            statuses["explicit_resolved"]
            if value_ba is not None
            else statuses["explicit_unresolved"]
        ),
        parameter_id_a_to_b=parameter_ab,
        parameter_id_b_to_a=parameter_ba,
        source_id_a_to_b=source_ab,
        source_id_b_to_a=source_ba,
        projection_policy_id=policy_id,
    )


def build_fractal_projected_graph(
    *,
    runtime_plan: FractalRuntimePlan,
    base_graph: CountryGraph,
    projection_config: dict[str, Any],
    regional_graph_catalog: dict[str, Any],
) -> FractalProjectedGraph:
    logger.info(
        "build_fractal_projected_graph day=%s runtime_nodes=%s",
        runtime_plan.day,
        len(runtime_plan.nodes),
    )
    policy = _validate_projection_config(projection_config)
    base_graph.validate()
    nodes = _runtime_nodes(
        runtime_plan=runtime_plan,
        base_graph=base_graph,
    )
    catalog_index = _catalog_edge_index(regional_graph_catalog)

    edges: list[FractalProjectedGraphEdge] = []
    for index, node_a in enumerate(nodes):
        for node_b in nodes[index + 1 :]:
            kind = _edge_kind(a=node_a, b=node_b)
            catalog_key = tuple(
                sorted(
                    (
                        node_a.catalog_node_id,
                        node_b.catalog_node_id,
                    )
                )
            )
            catalog_edge = catalog_index.get(catalog_key)
            channels: list[FractalProjectedChannelValue] = []
            for channel_name in sorted(CANONICAL_CHANNELS):
                channel_policy = policy["policies"][channel_name]
                policy_id = channel_policy["projection_policy_id"]
                if kind == "BASE_L1":
                    channel = _base_channel(
                        runtime_a=node_a.runtime_node_id,
                        runtime_b=node_b.runtime_node_id,
                        channel_name=channel_name,
                        base_graph=base_graph,
                        policy_id=policy_id,
                        statuses=policy["statuses"],
                    )
                elif (
                    channel_policy["l2_mode"]
                    == "parent_retained_not_projected"
                ):
                    channel = _parent_retained_channel(
                        channel_name=channel_name,
                        policy_id=policy_id,
                        statuses=policy["statuses"],
                    )
                else:
                    channel = _explicit_catalog_channel(
                        node_a=node_a,
                        node_b=node_b,
                        channel_name=channel_name,
                        catalog_edge=catalog_edge,
                        policy_id=policy_id,
                        statuses=policy["statuses"],
                    )
                channels.append(channel)

            edges.append(
                FractalProjectedGraphEdge(
                    a=node_a.runtime_node_id,
                    b=node_b.runtime_node_id,
                    catalog_a=node_a.catalog_node_id,
                    catalog_b=node_b.catalog_node_id,
                    edge_kind=kind,
                    channels=tuple(channels),
                )
            )

    projected = FractalProjectedGraph(
        day=runtime_plan.day,
        policy_id=policy["policy_id"],
        runtime_plan_hash=runtime_plan.plan_hash(),
        base_graph_hash=base_graph.graph_hash(),
        catalog_hash=canonical_hash(regional_graph_catalog),
        nodes=nodes,
        edges=tuple(edges),
    )
    projected.validate()

    expected_nodes = {
        item.runtime_node_id
        for item in runtime_plan.nodes
        if item.owns_regionalizable_state
    }
    actual_nodes = {
        item.runtime_node_id
        for item in projected.nodes
    }
    if actual_nodes != expected_nodes:
        raise ValueError(
            "Projected graph runtime authority coverage mismatch: "
            f"missing={sorted(expected_nodes - actual_nodes)} "
            f"extra={sorted(actual_nodes - expected_nodes)}"
        )
    logger.info(
        "build_fractal_projected_graph complete day=%s hash=%s",
        projected.day,
        projected.graph_hash(),
    )
    return projected


def trace_fractal_projected_graph(
    *,
    graph: FractalProjectedGraph,
    phase: str,
    trace: TraceLedger,
) -> None:
    logger.info(
        "trace_fractal_projected_graph phase=%s day=%s hash=%s",
        phase,
        graph.day,
        graph.graph_hash(),
    )
    trace.append(
        "fractal_projected_graph",
        phase=phase,
        graph_hash=graph.graph_hash(),
        **graph.to_dict(),
    )
