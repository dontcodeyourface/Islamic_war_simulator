from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.graph import build_structural_graph, edge_by_nodes

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _build_graph():
    logger.info("_build_graph")
    graph_config = load_yaml(ROOT / "config/graph/base_country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    graph = build_structural_graph(
        repo_root=ROOT,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )
    return graph


def test_structural_graph_has_five_nodes_and_ten_edges() -> None:
    logger.info("test_structural_graph_has_five_nodes_and_ten_edges")
    graph = _build_graph()
    assert graph.nodes == ("DEU", "ESP", "FRA", "GBR", "MAR")
    assert len(graph.edges) == 10


def test_geographic_and_border_channels() -> None:
    logger.info("test_geographic_and_border_channels")
    graph = _build_graph()

    esp_mar = edge_by_nodes(graph, "ESP", "MAR")
    assert esp_mar.distance_km == 763
    assert esp_mar.channels["land_border"].value == 1.0
    assert esp_mar.channels["geographic_proximity"].value == pytest.approx(
        0.4662, rel=2e-3
    )

    fra_gbr = edge_by_nodes(graph, "FRA", "GBR")
    assert fra_gbr.distance_km == 344
    assert fra_gbr.channels["land_border"].value == 0.0
    assert fra_gbr.channels["geographic_proximity"].value == pytest.approx(
        0.7089, rel=2e-3
    )


def test_alliance_channel_uses_formal_membership_and_explicit_relationships() -> None:
    logger.info(
        "test_alliance_channel_uses_formal_membership_and_explicit_relationships"
    )
    graph = _build_graph()

    esp_fra = edge_by_nodes(graph, "ESP", "FRA")
    assert esp_fra.channels["alliance_link"].value == pytest.approx(1.0)
    assert "shared_membership:NATO" in esp_fra.channels[
        "alliance_link"
    ].evidence_refs

    esp_mar = edge_by_nodes(graph, "ESP", "MAR")
    assert esp_mar.channels["alliance_link"].value == pytest.approx(0.55)
    assert esp_mar.channels["alliance_link"].source_ids == (
        "MA-DGST-SPAIN-COOP-2025",
    )

    mar_fra = edge_by_nodes(graph, "MAR", "FRA")
    assert mar_fra.channels["alliance_link"].value == pytest.approx(0.0)
    assert mar_fra.channels["alliance_link"].source_ids == ()


def test_graph_hash_is_reproducible() -> None:
    logger.info("test_graph_hash_is_reproducible")
    a = _build_graph()
    b = _build_graph()
    assert a.to_dict() == b.to_dict()
    assert a.graph_hash() == b.graph_hash()


def test_graph_hash_changes_if_graph_configuration_changes() -> None:
    logger.info("test_graph_hash_changes_if_graph_configuration_changes")
    graph_config = load_yaml(ROOT / "config/graph/base_country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")

    baseline = build_structural_graph(
        repo_root=ROOT,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )

    changed = copy.deepcopy(graph_config)
    changed["explicit_relationships"] = []

    altered = build_structural_graph(
        repo_root=ROOT,
        graph_config=changed,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )

    assert baseline.graph_hash() != altered.graph_hash()
    assert edge_by_nodes(baseline, "ESP", "MAR").channels[
        "alliance_link"
    ].value == pytest.approx(0.55)
    assert edge_by_nodes(altered, "ESP", "MAR").channels[
        "alliance_link"
    ].value == pytest.approx(0.0)
