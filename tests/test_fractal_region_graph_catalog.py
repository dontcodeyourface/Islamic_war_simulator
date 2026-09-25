from __future__ import annotations

import logging
from pathlib import Path

from iwsim.config import load_yaml

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _regions() -> dict:
    logger.info("_regions")
    return load_yaml(ROOT / "config/engine/fractal_region_catalog_v1.yaml")


def _graph() -> dict:
    logger.info("_graph")
    return load_yaml(
        ROOT / "config/engine/fractal_region_graph_catalog_v1.yaml"
    )


def test_regional_graph_endpoints_are_canonical_children() -> None:
    logger.info("test_regional_graph_endpoints_are_canonical_children")
    valid = {
        child["child_id"]
        for parent in _regions()["parents"].values()
        for child in parent["children"]
    }
    seen = set()
    for edge in _graph()["edges"]:
        assert edge["a"] in valid
        assert edge["b"] in valid
        assert edge["a"] != edge["b"]
        edge_id = tuple(sorted((edge["a"], edge["b"])))
        assert edge_id not in seen
        seen.add(edge_id)
        assert edge["source_id"]
        assert edge["channels"] == {"land_border": {"value": 1.0}}


def test_every_contiguous_parent_has_connected_l2_land_graph() -> None:
    logger.info("test_every_contiguous_parent_has_connected_l2_land_graph")
    regions = _regions()["parents"]
    edges = _graph()["edges"]
    # Island/overseas children are deliberately excluded: absence of a land
    # border is not encoded as a zero-valued strategic relationship.
    excluded = {
        "ESP": {"ESP::IB", "ESP::CN", "ESP::CE", "ESP::ML"},
        "FRA": {"FRA::COR", "FRA::GUA", "FRA::MTQ", "FRA::GUF", "FRA::REU", "FRA::MAY"},
        "GBR": {"GBR::NIR"},
        "DEU": set(),
        "MAR": set(),
    }
    for parent_id, parent in regions.items():
        nodes = {
            child["child_id"] for child in parent["children"]
        } - excluded[parent_id]
        adjacency = {node: set() for node in nodes}
        for edge in edges:
            a, b = edge["a"], edge["b"]
            if a in nodes and b in nodes:
                adjacency[a].add(b)
                adjacency[b].add(a)
        assert nodes
        start = next(iter(nodes))
        visited = {start}
        frontier = [start]
        while frontier:
            node = frontier.pop()
            for neighbor in adjacency[node] - visited:
                visited.add(neighbor)
                frontier.append(neighbor)
        assert visited == nodes, (parent_id, sorted(nodes - visited))


def test_graph_does_not_invent_unresolved_strategic_channels() -> None:
    logger.info("test_graph_does_not_invent_unresolved_strategic_channels")
    for edge in _graph()["edges"]:
        assert set(edge["channels"]) == {"land_border"}
