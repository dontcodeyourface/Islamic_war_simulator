from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash

logger = logging.getLogger(__name__)

CANONICAL_CHANNELS = (
    "geographic_proximity",
    "land_border",
    "trade_dependency",
    "energy_dependency",
    "migration_link",
    "diaspora_link",
    "alliance_link",
    "information_link",
    "criminal_network_link",
    "extremist_network_link",
)


@dataclass(frozen=True)
class GraphNode:
    iso3: str
    country_name: str
    snapshot_path: str

    def to_dict(self) -> dict[str, str]:
        logger.info("GraphNode.to_dict iso3=%s", self.iso3)
        return {
            "iso3": self.iso3,
            "country_name": self.country_name,
            "snapshot_path": self.snapshot_path,
        }


@dataclass(frozen=True)
class GraphEdge:
    a: str
    b: str
    distance_km: float
    direct_land_border: bool
    channels: dict[str, float | None]
    channel_parameter_ids: dict[str, str | None]
    metadata: dict[str, Any]

    def edge_id(self) -> str:
        logger.info("GraphEdge.edge_id a=%s b=%s", self.a, self.b)
        return "--".join(sorted((self.a, self.b)))

    def to_dict(self) -> dict[str, Any]:
        logger.info("GraphEdge.to_dict edge_id=%s", self.edge_id())
        return {
            "edge_id": self.edge_id(),
            "a": self.a,
            "b": self.b,
            "distance_km": self.distance_km,
            "direct_land_border": self.direct_land_border,
            "channels": dict(sorted(self.channels.items())),
            "channel_parameter_ids": dict(sorted(self.channel_parameter_ids.items())),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class CountryGraph:
    schema_version: str
    profile: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info("CountryGraph.to_dict nodes=%s edges=%s", len(self.nodes), len(self.edges))
        return {
            "schema_version": self.schema_version,
            "profile": self.profile,
            "nodes": [node.to_dict() for node in sorted(self.nodes, key=lambda item: item.iso3)],
            "edges": [edge.to_dict() for edge in sorted(self.edges, key=lambda item: item.edge_id())],
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
        logger.info("CountryGraph.validate nodes=%s edges=%s", len(self.nodes), len(self.edges))
        node_ids = [node.iso3 for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate graph node ISO3 identifiers")

        expected_edges = len(node_ids) * (len(node_ids) - 1) // 2
        if len(self.edges) != expected_edges:
            raise ValueError(
                f"Incomplete graph edge coverage: expected={expected_edges} actual={len(self.edges)}"
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

            if set(edge.channels) != set(CANONICAL_CHANNELS):
                raise ValueError(
                    f"Edge {edge.edge_id()} channel mismatch "
                    f"expected={CANONICAL_CHANNELS} actual={tuple(edge.channels)}"
                )
            for channel, value in edge.channels.items():
                if value is not None and not 0.0 <= value <= 1.0:
                    raise ValueError(
                        f"Edge {edge.edge_id()} channel {channel} outside [0,1]: {value}"
                    )


def _parameter_value(
    parameter_registry: dict[str, Any],
    profile: str,
    parameter_id: str,
) -> Any:
    logger.info("_parameter_value profile=%s parameter_id=%s", profile, parameter_id)
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(parameter_id)
    if parameter is None:
        raise ValueError(f"Missing graph parameter {parameter_id} for profile {profile}")
    return parameter["value"]


def _distance_pair_index(distance_matrix: dict[str, Any]) -> dict[frozenset[str], dict[str, Any]]:
    logger.info("_distance_pair_index")
    result: dict[frozenset[str], dict[str, Any]] = {}
    for pair in distance_matrix["pairs"]:
        key = frozenset((str(pair["a"]), str(pair["b"])))
        if key in result:
            raise ValueError(f"Duplicate distance pair: {sorted(key)}")
        result[key] = pair
    return result


def _membership_set(snapshot: dict[str, Any]) -> set[str]:
    logger.info("_membership_set country=%s", snapshot["identity"]["country_name"])
    memberships = snapshot.get("alliances", {}).get("memberships", [])
    if not isinstance(memberships, list):
        raise ValueError("alliances.memberships must be a list")
    return {str(item) for item in memberships}


def _geographic_proximity(distance_km: float, lambda_km: float) -> float:
    logger.info("_geographic_proximity distance_km=%s lambda_km=%s", distance_km, lambda_km)
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
    iso3: str,
    snapshot_path: str,
    snapshot: dict[str, Any],
) -> GraphNode:
    logger.info("_node_from_snapshot iso3=%s snapshot_path=%s", iso3, snapshot_path)
    snapshot_iso3 = str(snapshot["identity"]["iso3"])
    if snapshot_iso3 != iso3:
        raise ValueError(
            f"Graph config ISO3 {iso3} does not match snapshot ISO3 {snapshot_iso3}"
        )
    return GraphNode(
        iso3=iso3,
        country_name=str(snapshot["identity"]["country_name"]),
        snapshot_path=snapshot_path,
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
    nodes: list[GraphNode] = []
    for iso3, node_config in graph_config["nodes"].items():
        if iso3 not in snapshots:
            raise ValueError(f"Missing snapshot for graph node {iso3}")
        nodes.append(
            _node_from_snapshot(
                iso3=iso3,
                snapshot_path=str(node_config["snapshot_path"]),
                snapshot=snapshots[iso3],
            )
        )

    geo_parameter_id = (
        "EDGE_GEO_SCALE_SYN_V1"
        if profile == "synthetic_smoke_v1"
        else "EDGE_GEO_SCALE_CAL_V1"
    )
    alliance_parameter_id = (
        "EDGE_ALLIANCE_FORMAL_SYN_V1"
        if profile == "synthetic_smoke_v1"
        else "EDGE_ALLIANCE_FORMAL_CAL_V1"
    )
    lambda_km = float(_parameter_value(parameter_registry, profile, geo_parameter_id))
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
            pair_key = frozenset((node_a.country_name, node_b.country_name))
            pair = pair_index.get(pair_key)
            if pair is None:
                raise ValueError(
                    f"Distance matrix missing pair {node_a.country_name}/{node_b.country_name}"
                )

            distance_km = float(pair["distance_km"])
            land_border = bool(pair["direct_land_border"])
            alliance_value, shared_memberships = _formal_alliance_link(
                _membership_set(snapshots[a]),
                _membership_set(snapshots[b]),
                alliance_scores,
            )

            channels: dict[str, float | None] = {
                channel: None for channel in CANONICAL_CHANNELS
            }
            channels["geographic_proximity"] = _geographic_proximity(
                distance_km,
                lambda_km,
            )
            channels["land_border"] = 1.0 if land_border else 0.0
            channels["alliance_link"] = alliance_value

            parameter_ids: dict[str, str | None] = {
                channel: None for channel in CANONICAL_CHANNELS
            }
            parameter_ids["geographic_proximity"] = geo_parameter_id
            parameter_ids["land_border"] = None
            parameter_ids["alliance_link"] = alliance_parameter_id

            edges.append(
                GraphEdge(
                    a=a,
                    b=b,
                    distance_km=distance_km,
                    direct_land_border=land_border,
                    channels=channels,
                    channel_parameter_ids=parameter_ids,
                    metadata={
                        "distance_metric": distance_matrix["metric"],
                        "distance_method": distance_matrix["method"],
                        "shared_formal_memberships": list(shared_memberships),
                        "unresolved_channels": [
                            channel
                            for channel, value in channels.items()
                            if value is None
                        ],
                    },
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
