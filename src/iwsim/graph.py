from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import canonical_hash, get_path, load_yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraphChannel:
    value: float
    rule_id: str
    parameter_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        logger.info("GraphChannel.to_dict rule_id=%s", self.rule_id)
        return {
            "value": self.value,
            "rule_id": self.rule_id,
            "parameter_ids": list(self.parameter_ids),
            "evidence_refs": list(self.evidence_refs),
            "source_ids": list(self.source_ids),
        }


@dataclass(frozen=True)
class GraphEdge:
    a: str
    b: str
    distance_km: float
    channels: dict[str, GraphChannel]

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
            "channels": {
                key: channel.to_dict()
                for key, channel in sorted(self.channels.items())
            },
        }


@dataclass(frozen=True)
class StructuralGraph:
    schema_version: str
    nodes: tuple[str, ...]
    edges: tuple[GraphEdge, ...]
    source_hashes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "StructuralGraph.to_dict nodes=%s edges=%s",
            len(self.nodes),
            len(self.edges),
        )
        return {
            "schema_version": self.schema_version,
            "nodes": list(self.nodes),
            "edges": [edge.to_dict() for edge in self.edges],
            "source_hashes": dict(self.source_hashes),
        }

    def graph_hash(self) -> str:
        logger.info("StructuralGraph.graph_hash")
        return canonical_hash(self.to_dict())


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
        raise ValueError(f"Missing graph parameter {parameter_id} for {profile}")
    return parameter["value"]


def _snapshot_memberships(snapshot: dict[str, Any]) -> tuple[str, ...]:
    logger.info(
        "_snapshot_memberships country=%s",
        snapshot.get("identity", {}).get("country_name"),
    )
    try:
        memberships = get_path(snapshot, "alliances.memberships")
    except KeyError:
        return ()
    if not isinstance(memberships, list):
        return ()
    return tuple(str(item) for item in memberships)


def _normalize_geographic_proximity(
    *,
    distance_km: float,
    parameter_registry: dict[str, Any],
    profile: str,
) -> GraphChannel:
    logger.info(
        "_normalize_geographic_proximity distance_km=%s profile=%s",
        distance_km,
        profile,
    )
    parameter_id = (
        "EDGE_GEO_SCALE_SYN_V1"
        if profile == "synthetic_smoke_v1"
        else "EDGE_GEO_SCALE_CAL_V1"
    )
    params = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    lambda_km = float(params if isinstance(params, (int, float)) else params["value"])
    value = math.exp(-float(distance_km) / lambda_km)
    return GraphChannel(
        value=value,
        rule_id="EDGE_GEO_V1",
        parameter_ids=(parameter_id,),
        evidence_refs=("config/geography/country_distance_matrix_v1.yaml",),
    )


def _normalize_land_border(direct_land_border: bool) -> GraphChannel:
    logger.info("_normalize_land_border direct_land_border=%s", direct_land_border)
    return GraphChannel(
        value=1.0 if direct_land_border else 0.0,
        rule_id="EDGE_LAND_BORDER_V1",
        evidence_refs=("config/geography/country_distance_matrix_v1.yaml",),
    )


def _explicit_relationships_for_pair(
    graph_config: dict[str, Any],
    a: str,
    b: str,
) -> list[dict[str, Any]]:
    logger.info("_explicit_relationships_for_pair a=%s b=%s", a, b)
    pair = frozenset((a, b))
    return [
        item
        for item in graph_config.get("explicit_relationships", [])
        if frozenset((str(item["a"]), str(item["b"]))) == pair
    ]


def _normalize_alliance_link(
    *,
    a: str,
    b: str,
    snapshot_a: dict[str, Any],
    snapshot_b: dict[str, Any],
    graph_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
) -> GraphChannel:
    logger.info("_normalize_alliance_link a=%s b=%s profile=%s", a, b, profile)
    parameter_id = (
        "ALLIANCE_EDGE_SYN_V1"
        if profile == "synthetic_smoke_v1"
        else "ALLIANCE_EDGE_CAL_V1"
    )
    params = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    memberships_a = set(_snapshot_memberships(snapshot_a))
    memberships_b = set(_snapshot_memberships(snapshot_b))
    shared = sorted(memberships_a & memberships_b)

    candidates: list[float] = []
    evidence_refs: list[str] = []
    source_ids: list[str] = []

    membership_scores = params["shared_membership_scores"]
    for membership in shared:
        if membership in membership_scores:
            candidates.append(float(membership_scores[membership]))
            evidence_refs.extend(
                [
                    f"snapshot:{a}:alliances.memberships:{membership}",
                    f"snapshot:{b}:alliances.memberships:{membership}",
                ]
            )

    relationship_scores = params["explicit_relationship_scores"]
    for relationship in _explicit_relationships_for_pair(graph_config, a, b):
        relation_type = str(relationship["relationship_type"])
        if relation_type in relationship_scores:
            candidates.append(float(relationship_scores[relation_type]))
            evidence_refs.append(f"explicit_relationship:{relationship['relationship_id']}")
            source_ids.extend(str(item) for item in relationship.get("source_ids", []))

    value = max(candidates) if candidates else 0.0
    return GraphChannel(
        value=value,
        rule_id="EDGE_ALLIANCE_V1",
        parameter_ids=(parameter_id,),
        evidence_refs=tuple(sorted(evidence_refs)),
        source_ids=tuple(sorted(set(source_ids))),
    )


def _country_name_to_iso(graph_config: dict[str, Any]) -> dict[str, str]:
    logger.info("_country_name_to_iso")
    return {
        str(spec["country_name"]): str(node_id)
        for node_id, spec in graph_config["nodes"].items()
    }


def _load_snapshots(
    *,
    repo_root: Path,
    graph_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    logger.info("_load_snapshots repo_root=%s", repo_root)
    snapshots: dict[str, dict[str, Any]] = {}
    for node_id, spec in graph_config["nodes"].items():
        snapshot = load_yaml(repo_root / spec["snapshot_path"])
        snapshot_iso3 = str(snapshot["identity"]["iso3"])
        if snapshot_iso3 != node_id:
            raise ValueError(
                f"Graph node {node_id} does not match snapshot iso3 {snapshot_iso3}"
            )
        snapshots[str(node_id)] = snapshot
    return snapshots


def build_structural_graph(
    *,
    repo_root: str | Path,
    graph_config: dict[str, Any],
    distance_matrix: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str = "synthetic_smoke_v1",
) -> StructuralGraph:
    logger.info("build_structural_graph profile=%s", profile)
    root = Path(repo_root)
    snapshots = _load_snapshots(repo_root=root, graph_config=graph_config)
    name_to_iso = _country_name_to_iso(graph_config)

    edges: list[GraphEdge] = []
    for pair in distance_matrix["pairs"]:
        name_a = str(pair["a"])
        name_b = str(pair["b"])
        if name_a not in name_to_iso or name_b not in name_to_iso:
            continue
        a = name_to_iso[name_a]
        b = name_to_iso[name_b]
        distance_km = float(pair["distance_km"])
        channels = {
            "geographic_proximity": _normalize_geographic_proximity(
                distance_km=distance_km,
                parameter_registry=parameter_registry,
                profile=profile,
            ),
            "land_border": _normalize_land_border(bool(pair["direct_land_border"])),
            "alliance_link": _normalize_alliance_link(
                a=a,
                b=b,
                snapshot_a=snapshots[a],
                snapshot_b=snapshots[b],
                graph_config=graph_config,
                parameter_registry=parameter_registry,
                profile=profile,
            ),
        }
        edges.append(
            GraphEdge(
                a=a,
                b=b,
                distance_km=distance_km,
                channels=channels,
            )
        )

    edges.sort(key=lambda item: item.edge_id())
    nodes = tuple(sorted(snapshots))
    source_hash_map = {
        "graph_config": canonical_hash(graph_config),
        "distance_matrix": canonical_hash(distance_matrix),
        "parameter_profile": canonical_hash(
            parameter_registry["parameter_sets"][profile]
        ),
    }
    for node_id, snapshot in sorted(snapshots.items()):
        source_hash_map[f"snapshot:{node_id}"] = canonical_hash(snapshot)
    source_hashes = tuple(sorted(source_hash_map.items()))
    return StructuralGraph(
        schema_version="1.0",
        nodes=nodes,
        edges=tuple(edges),
        source_hashes=source_hashes,
    )


def edge_by_nodes(
    graph: StructuralGraph,
    a: str,
    b: str,
) -> GraphEdge:
    logger.info("edge_by_nodes a=%s b=%s", a, b)
    target = frozenset((a, b))
    for edge in graph.edges:
        if frozenset((edge.a, edge.b)) == target:
            return edge
    raise KeyError(f"No edge for {a}-{b}")
