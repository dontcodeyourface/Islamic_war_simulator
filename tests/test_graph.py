from __future__ import annotations

import logging
import math
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.graph import DIRECTED_CHANNELS, build_country_graph

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _build_graph(profile: str = "synthetic_smoke_v1"):
    logger.info("_build_graph profile=%s", profile)
    graph_config = load_yaml(ROOT / "config/graph/country_graph_v1.yaml")
    distance_matrix = load_yaml(
        ROOT / graph_config["distance_matrix_path"]
    )
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    snapshots = {
        iso3: load_yaml(ROOT / node["snapshot_path"])
        for iso3, node in graph_config["nodes"].items()
    }
    return build_country_graph(
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        snapshots=snapshots,
        parameter_registry=parameters,
        profile=profile,
    )


def test_graph_has_five_nodes_and_complete_pair_coverage() -> None:
    logger.info("test_graph_has_five_nodes_and_complete_pair_coverage")
    graph = _build_graph()
    assert {node.iso3 for node in graph.nodes} == {
        "ESP",
        "MAR",
        "FRA",
        "DEU",
        "GBR",
    }
    assert len(graph.edges) == 10
    graph.validate()


def test_united_kingdom_distance_alias_resolves() -> None:
    logger.info("test_united_kingdom_distance_alias_resolves")
    graph = _build_graph()
    edge = graph.edge("FRA", "GBR")
    assert edge.distance_km == 344
    assert edge.direct_land_border is False


def test_spain_morocco_geography_and_border_are_symmetric() -> None:
    logger.info("test_spain_morocco_geography_and_border_are_symmetric")
    graph = _build_graph()
    edge = graph.edge("ESP", "MAR")

    expected = math.exp(-763 / 1000)
    assert edge.channel("ESP", "MAR", "geographic_proximity") == pytest.approx(expected)
    assert edge.channel("MAR", "ESP", "geographic_proximity") == pytest.approx(expected)
    assert edge.channel("ESP", "MAR", "land_border") == 1.0
    assert edge.channel("MAR", "ESP", "land_border") == 1.0


def test_formal_alliance_channel_uses_shared_membership_only() -> None:
    logger.info("test_formal_alliance_channel_uses_shared_membership_only")
    graph = _build_graph()

    assert graph.edge("ESP", "FRA").channel(
        "ESP", "FRA", "alliance_link"
    ) == pytest.approx(1.0)
    assert graph.edge("ESP", "GBR").channel(
        "ESP", "GBR", "alliance_link"
    ) == pytest.approx(1.0)
    assert graph.edge("ESP", "MAR").channel(
        "ESP", "MAR", "alliance_link"
    ) == pytest.approx(0.0)

    metadata = graph.edge("ESP", "FRA").to_dict()["metadata"]
    assert metadata["shared_formal_memberships"] == (
        "European Union",
        "NATO",
    )


def test_unresolved_directed_channels_remain_null_both_directions() -> None:
    logger.info("test_unresolved_directed_channels_remain_null_both_directions")
    graph = _build_graph()
    edge = graph.edge("ESP", "FRA")

    for channel in DIRECTED_CHANNELS:
        assert edge.channel("ESP", "FRA", channel) is None
        assert edge.channel("FRA", "ESP", channel) is None


def test_directional_channel_access_rejects_wrong_endpoints() -> None:
    logger.info("test_directional_channel_access_rejects_wrong_endpoints")
    graph = _build_graph()
    edge = graph.edge("ESP", "FRA")

    with pytest.raises(ValueError):
        edge.channel("ESP", "DEU", "trade_dependency")


def test_graph_hash_is_deterministic() -> None:
    logger.info("test_graph_hash_is_deterministic")
    a = _build_graph()
    b = _build_graph()
    assert a.to_dict() == b.to_dict()
    assert a.graph_hash() == b.graph_hash()


def test_calibrated_graph_fails_closed_until_parameters_exist() -> None:
    logger.info("test_calibrated_graph_fails_closed_until_parameters_exist")
    with pytest.raises(ValueError):
        _build_graph("calibrated_v1")


def test_graph_config_does_not_infer_extremist_links_from_identity() -> None:
    logger.info("test_graph_config_does_not_infer_extremist_links_from_identity")
    config = load_yaml(ROOT / "config/graph/country_graph_v1.yaml")
    assert config["channels"]["extremist_network_link"]["source"] == "unresolved"
    assert config["rules"]["population_identity_must_not_create_extremist_edge"] is True
    assert config["rules"]["directed_dependency_channels_must_not_be_symmetrized_without_evidence"] is True
