from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash

logger = logging.getLogger(__name__)

SYMMETRIC_CHANNELS = (
    "geographic_proximity",
    "land_border",
    "alliance_link",
)

DIRECTED_CHANNELS = (
    "trade_dependency",
    "energy_dependency",
    "migration_link",
    "diaspora_link",
    "information_link",
    "criminal_network_link",
    "extremist_network_link",
)

CANONICAL_CHANNELS = SYMMETRIC_CHANNELS + DIRECTED_CHANNELS


@dataclass(frozen=True)
class GraphNode:
    iso3: str
    country_name: str
    snapshot_path: str
    distance_matrix_name: str

    def to_dict(self) -> dict[str, str]:
        logger.info("GraphNode.to_dict iso3=%s", self.iso3)
        return {
            "iso3": self.iso3,
            "country_name": self.country_name,
            "snapshot_path": self.snapshot_path,
            "distance_matrix_name": self.distance_matrix_name,
        }


@dataclass(frozen=True)
class SymmetricChannelValue:
    name: str
    value: float | None
    parameter_id: str | None

    def to_dict(self) -> dict[str, Any]:
        logger.info("SymmetricChannelValue.to_dict name=%s", self.name)
        return {
            "name": self.name,
            "value": self.value,
            "parameter_id": self.parameter_id,
        }


@dataclass(frozen=True)
class DirectedChannelValue:
    name: str
    a_to_b: float | None
    b_to_a: float | None
    parameter_id_a_to_b: str | None
    parameter_id_b_to_a: str | None

    def to_dict(self) -> dict[str, Any]:
        logger.info("DirectedChannelValue.to_dict name=%s", self.name)
        return {
            "name": self.name,
            "a_to_b": self.a_to_b,
            "b_to_a": self.b_to_a,
            "parameter_id_a_to_b": self.parameter_id_a_to_b,
            "parameter_id_b_to_a": self.parameter_id_b_to_a,
        }


@dataclass(frozen=True)
class GraphEdge:
    a: str
    b: str
    distance_km: float
    direct_land_border: bool
    symmetric_channels: tuple[SymmetricChannelValue, ...]
    directed_channels: tuple[DirectedChannelValue, ...]
    metadata: tuple[tuple[str, Any], ...]

    def edge_id(self) -> str:
        logger.info("GraphEdge.edge_id a=%s b=%s", self.a, self.b)
        return "--".join(sorted((self.a, self.b)))

    def _validate_endpoints(self, source: str, target: str) -> None:
        logger.info(
            "GraphEdge._validate_endpoints edge_id=%s source=%s target=%s",
            self.edge_id(),
            source,
            target,
        )
        if source == target:
            raise ValueError("source and target must differ")
        if {source, target} != {self.a, self.b}:
            raise ValueError(
                f"{source}->{target} does not match edge endpoints {self.a}/{self.b}"
            )

    def channel(self, source: str, target: str, channel_name: str) -> float | None:
        logger.info(
            "GraphEdge.channel edge_id=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)

        for channel in self.symmetric_channels:
            if channel.name == channel_name:
                return channel.value

        for channel in self.directed_channels:
            if channel.name == channel_name:
                if source == self.a and target == self.b:
                    return channel.a_to_b
                return channel.b_to_a

        raise KeyError(channel_name)

    def channel_parameter_id(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> str | None:
        logger.info(
            "GraphEdge.channel_parameter_id edge_id=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)

        for channel in self.symmetric_channels:
            if channel.name == channel_name:
                return channel.parameter_id

        for channel in self.directed_channels:
            if channel.name == channel_name:
                if source == self.a and target == self.b:
                    return channel.parameter_id_a_to_b
                return channel.parameter_id_b_to_a

        raise KeyError(channel_name)

    def to_dict(self) -> dict[str, Any]:
        logger.info("GraphEdge.to_dict edge_id=%s", self.edge_id())
        return {
            "edge_id": self.edge_id(),
            "a": self.a,
            "b": self.b,
            "distance_km": self.distance_km,
            "direct_land_border": self.direct_land_border,
            "symmetric_channels": {
                channel.name: {
                    "value": channel.value,
                    "parameter_id": channel.parameter_id,
                }
                for channel in sorted(
                    self.symmetric_channels,
                    key=lambda item: item.name,
                )
            },
            "directed_channels": {
                channel.name: {
                    "a_to_b": channel.a_to_b,
                    "b_to_a": channel.b_to_a,
                    "parameter_id_a_to_b": channel.parameter_id_a_to_b,
                    "parameter_id_b_to_a": channel.parameter_id_b_to_a,
                }
                for channel in sorted(
                    self.directed_channels,
                    key=lambda item: item.name,
                )
            },
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CountryGraph:
    schema_version: str
    profile: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "CountryGraph.to_dict nodes=%s edges=%s",
            len(self.nodes),
            len(self.edges),
        )
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "nodes": [
                node.to_dict()
                for node in sorted(self.nodes, key=lambda item: item.iso3)
            ],
            "edges": [
                edge.to_dict()
                for edge in sorted(self.edges, key=lambda item: item.edge_id())
            ],
        }

    def graph_hash(self) -> str:
        logger.info("CountryGraph.graph_hash")
        return canonical_hash(self.to_dict())

    def edge(self, a: str, b: str) -> GraphEdge:
        logger.info("CountryGraph.edge a=%s b=%s", a, b)
        edge_id = "--".join(sorted((a, b)))
        for edge in self.edges:
            if edge.edge_id() == edge_id:
                return edge
        raise KeyError(edge_id)

    def validate(self) -> None:
        logger.info(
            "CountryGraph.validate nodes=%s edges=%s",
            len(self.nodes),
            len(self.edges),
        )
        node_ids = [node.iso3 for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate graph node ISO3 identifiers")

        matrix_names = [node.distance_matrix_name for node in self.nodes]
        if len(matrix_names) != len(set(matrix_names)):
            raise ValueError("Duplicate distance-matrix node names")

        expected_edges = len(node_ids) * (len(node_ids) - 1) // 2
        if len(self.edges) != expected_edges:
            raise ValueError(
                f"Incomplete graph edge coverage: expected={expected_edges} "
                f"actual={len(self.edges)}"
            )

        seen_edges: set[str] = set()
        for edge in self.edges:
            if edge.a == edge.b:
                raise ValueError(f"Self edge forbidden: {edge.a}")
            if edge.a not in node_ids or edge.b not in node_ids:
                raise ValueError(f"Edge references unknown node: {edge.edge_id()}")
            if edge.edge_id() in seen_edges:
                raise ValueError(f"Duplicate edge: {edge.edge_id()}")
            seen_edges.add(edge.edge_id())

            symmetric_names = tuple(
                sorted(channel.name for channel in edge.symmetric_channels)
            )
            if symmetric_names != tuple(sorted(SYMMETRIC_CHANNELS)):
                raise ValueError(
                    f"Edge {edge.edge_id()} symmetric channel mismatch "
                    f"expected={SYMMETRIC_CHANNELS} actual={symmetric_names}"
                )

            directed_names = tuple(
                sorted(channel.name for channel in edge.directed_channels)
            )
            if directed_names != tuple(sorted(DIRECTED_CHANNELS)):
                raise ValueError(
                    f"Edge {edge.edge_id()} directed channel mismatch "
                    f"expected={DIRECTED_CHANNELS} actual={directed_names}"
                )

            for channel in edge.symmetric_channels:
                _validate_optional_unit_interval(
                    value=channel.value,
                    label=f"{edge.edge_id()}:{channel.name}",
                )

            for channel in edge.directed_channels:
                _validate_optional_unit_interval(
                    value=channel.a_to_b,
                    label=f"{edge.edge_id()}:{channel.name}:a_to_b",
                )
                _validate_optional_unit_interval(
                    value=channel.b_to_a,
                    label=f"{edge.edge_id()}:{channel.name}:b_to_a",
                )


def _validate_optional_unit_interval(
    *,
    value: float | None,
    label: str,
) -> None:
    logger.info("_validate_optional_unit_interval label=%s value=%s", label, value)
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} outside [0,1]: {value}")


def _parameter_value(
    parameter_registry: dict[str, Any],
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
            f"Missing graph parameter {parameter_id} for profile {profile}"
        )
    return parameter["value"]


def _distance_pair_index(
    distance_matrix: dict[str, Any],
) -> dict[frozenset[str], dict[str, Any]]:
    logger.info("_distance_pair_index")
    result: dict[frozenset[str], dict[str, Any]] = {}
    for pair in distance_matrix["pairs"]:
        key = frozenset((str(pair["a"]), str(pair["b"])))
        if key in result:
            raise ValueError(f"Duplicate distance pair: {sorted(key)}")
        result[key] = pair
    return result


def _membership_set(snapshot: dict[str, Any]) -> set[str]:
    logger.info(
        "_membership_set country=%s",
        snapshot["identity"]["country_name"],
    )
    memberships = snapshot.get("alliances", {}).get("memberships", [])
    if not isinstance(memberships, list):
        raise ValueError("alliances.memberships must be a list")
    return {str(item) for item in memberships}


def _geographic_proximity(distance_km: float, lambda_km: float) -> float:
    logger.info(
        "_geographic_proximity distance_km=%s lambda_km=%s",
        distance_km,
        lambda_km,
    )
    if distance_km < 0:
        raise ValueError("distance_km must be >= 0")
    if lambda_km <= 0:
        raise ValueError("lambda_km must be > 0")
    return math.exp(-distance_km / lambda_km)


def _formal_alliance_link(
    memberships_a: set[str],
    memberships_b: set[str],
    score_map: dict[str, float],
) -> tuple[float, tuple[str, ...]]:
    logger.info(
        "_formal_alliance_link memberships_a=%s memberships_b=%s",
        sorted(memberships_a),
        sorted(memberships_b),
    )
    shared = tuple(sorted(memberships_a & memberships_b))
    applicable = [
        float(score_map[membership])
        for membership in shared
        if membership in score_map
    ]
    if applicable:
        return max(applicable), shared
    return float(score_map["no_shared_formal_membership"]), shared


def _node_from_snapshot(
    *,
    iso3: str,
    node_config: dict[str, Any],
    snapshot: dict[str, Any],
) -> GraphNode:
    logger.info(
        "_node_from_snapshot iso3=%s snapshot_path=%s",
        iso3,
        node_config["snapshot_path"],
    )
    snapshot_iso3 = str(snapshot["identity"]["iso3"])
    if snapshot_iso3 != iso3:
        raise ValueError(
            f"Graph config ISO3 {iso3} does not match snapshot ISO3 {snapshot_iso3}"
        )
    return GraphNode(
        iso3=iso3,
        country_name=str(snapshot["identity"]["country_name"]),
        snapshot_path=str(node_config["snapshot_path"]),
        distance_matrix_name=str(node_config["distance_matrix_name"]),
    )


def _validate_channel_config(graph_config: dict[str, Any]) -> None:
    logger.info("_validate_channel_config")
    channel_config = graph_config.get("channels", {})
    if set(channel_config) != set(CANONICAL_CHANNELS):
        raise ValueError(
            "Graph channel config does not match canonical channel registry"
        )

    for name in SYMMETRIC_CHANNELS:
        directionality = channel_config[name].get("directionality")
        if directionality != "symmetric":
            raise ValueError(
                f"Channel {name} must be symmetric, got {directionality}"
            )

    for name in DIRECTED_CHANNELS:
        directionality = channel_config[name].get("directionality")
        if directionality != "directed":
            raise ValueError(
                f"Channel {name} must be directed, got {directionality}"
            )


def _graph_parameter_ids(profile: str) -> tuple[str, str]:
    logger.info("_graph_parameter_ids profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "EDGE_GEO_SCALE_SYN_V1", "EDGE_ALLIANCE_FORMAL_SYN_V1"
    if profile == "calibrated_v1":
        return "EDGE_GEO_SCALE_CAL_V1", "EDGE_ALLIANCE_FORMAL_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _build_unresolved_directed_channels() -> tuple[DirectedChannelValue, ...]:
    logger.info("_build_unresolved_directed_channels")
    return tuple(
        DirectedChannelValue(
            name=name,
            a_to_b=None,
            b_to_a=None,
            parameter_id_a_to_b=None,
            parameter_id_b_to_a=None,
        )
        for name in DIRECTED_CHANNELS
    )


def build_country_graph(
    *,
    graph_config: dict[str, Any],
    distance_matrix: dict[str, Any],
    snapshots: dict[str, dict[str, Any]],
    parameter_registry: dict[str, Any],
    profile: str = "synthetic_smoke_v1",
) -> CountryGraph:
    logger.info(
        "build_country_graph profile=%s configured_nodes=%s",
        profile,
        len(graph_config["nodes"]),
    )
    _validate_channel_config(graph_config)

    nodes: list[GraphNode] = []
    for iso3, node_config in graph_config["nodes"].items():
        if iso3 not in snapshots:
            raise ValueError(f"Missing snapshot for graph node {iso3}")
        nodes.append(
            _node_from_snapshot(
                iso3=iso3,
                node_config=node_config,
                snapshot=snapshots[iso3],
            )
        )

    geo_parameter_id, alliance_parameter_id = _graph_parameter_ids(profile)
    lambda_km = float(
        _parameter_value(
            parameter_registry,
            profile,
            geo_parameter_id,
        )
    )
    alliance_scores = _parameter_value(
        parameter_registry,
        profile,
        alliance_parameter_id,
    )

    pair_index = _distance_pair_index(distance_matrix)
    node_by_iso = {node.iso3: node for node in nodes}

    edges: list[GraphEdge] = []
    sorted_ids = sorted(node_by_iso)
    for i, a in enumerate(sorted_ids):
        for b in sorted_ids[i + 1 :]:
            node_a = node_by_iso[a]
            node_b = node_by_iso[b]
            pair_key = frozenset(
                (node_a.distance_matrix_name, node_b.distance_matrix_name)
            )
            pair = pair_index.get(pair_key)
            if pair is None:
                raise ValueError(
                    "Distance matrix missing pair "
                    f"{node_a.distance_matrix_name}/{node_b.distance_matrix_name}"
                )

            distance_km = float(pair["distance_km"])
            land_border = bool(pair["direct_land_border"])
            alliance_value, shared_memberships = _formal_alliance_link(
                _membership_set(snapshots[a]),
                _membership_set(snapshots[b]),
                alliance_scores,
            )

            symmetric_channels = (
                SymmetricChannelValue(
                    name="geographic_proximity",
                    value=_geographic_proximity(distance_km, lambda_km),
                    parameter_id=geo_parameter_id,
                ),
                SymmetricChannelValue(
                    name="land_border",
                    value=1.0 if land_border else 0.0,
                    parameter_id=None,
                ),
                SymmetricChannelValue(
                    name="alliance_link",
                    value=alliance_value,
                    parameter_id=alliance_parameter_id,
                ),
            )

            directed_channels = _build_unresolved_directed_channels()

            metadata = (
                ("distance_metric", str(distance_matrix["metric"])),
                ("distance_method", str(distance_matrix["method"])),
                ("shared_formal_memberships", tuple(shared_memberships)),
                (
                    "unresolved_directed_channels",
                    tuple(DIRECTED_CHANNELS),
                ),
            )

            edges.append(
                GraphEdge(
                    a=a,
                    b=b,
                    distance_km=distance_km,
                    direct_land_border=land_border,
                    symmetric_channels=symmetric_channels,
                    directed_channels=directed_channels,
                    metadata=metadata,
                )
            )

    graph = CountryGraph(
        schema_version=str(graph_config["schema_version"]),
        profile=profile,
        nodes=tuple(nodes),
        edges=tuple(edges),
    )
    graph.validate()
    return graph
