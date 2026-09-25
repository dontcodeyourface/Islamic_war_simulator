from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.fractal_graph_projection import (
    build_fractal_projected_graph,
)
from iwsim.fractal_runtime import (
    FractalRuntimeAuthorityNode,
    FractalRuntimePlan,
)
from iwsim.graph import CANONICAL_CHANNELS, build_country_graph

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _base_graph():
    logger.info("_base_graph")
    graph_config = load_yaml(
        ROOT / "config/graph/country_graph_v1.yaml"
    )
    distance_matrix = load_yaml(
        ROOT / graph_config["distance_matrix_path"]
    )
    parameters = load_yaml(
        ROOT / "config/engine/parameter_registry_v1.yaml"
    )
    snapshots = {
        iso3: load_yaml(ROOT / node["snapshot_path"])
        for iso3, node in graph_config["nodes"].items()
    }
    return build_country_graph(
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        snapshots=snapshots,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )


def _projection_config() -> dict:
    logger.info("_projection_config")
    return load_yaml(
        ROOT / "config/engine/fractal_graph_projection_v1.yaml"
    )


def _coarse_plan() -> FractalRuntimePlan:
    logger.info("_coarse_plan")
    nodes = tuple(
        FractalRuntimeAuthorityNode(
            runtime_node_id=node_id,
            parent_node_id=None,
            level="L1_COUNTRY",
            catalog_node_id=node_id,
            lineage_generation=None,
            authority_scope="FULL",
            owns_regionalizable_state=True,
            owns_national_only_state=True,
            execution_status="L1_FULL_AUTHORITY",
        )
        for node_id in ("DEU", "ESP", "FRA", "GBR", "MAR")
    )
    return FractalRuntimePlan(
        day=3,
        policy_id="FRACTAL_RUNTIME_AUTHORITY_V1",
        config_hash="runtime-config-test",
        topology_hash="topology-test",
        child_store_hash="child-store-test",
        autonomous_child_dynamics_allowed=True,
        nodes=nodes,
        refined_parent_ids=(),
        active_regional_node_ids=(),
        inactive_lineage_node_ids=(),
        regionalizable_physical_stocks=(),
        national_only_physical_stocks=(),
        regionalizable_latents=(),
        national_only_latents=(),
        regionalizable_regimes=(),
        national_only_regimes=(),
    )


def _refined_plan() -> FractalRuntimePlan:
    logger.info("_refined_plan")
    nodes = [
        FractalRuntimeAuthorityNode(
            runtime_node_id=node_id,
            parent_node_id=None,
            level="L1_COUNTRY",
            catalog_node_id=node_id,
            lineage_generation=None,
            authority_scope="FULL",
            owns_regionalizable_state=True,
            owns_national_only_state=True,
            execution_status="L1_FULL_AUTHORITY",
        )
        for node_id in ("DEU", "FRA", "GBR", "MAR")
    ]
    nodes.append(
        FractalRuntimeAuthorityNode(
            runtime_node_id="ESP",
            parent_node_id=None,
            level="L1_COUNTRY",
            catalog_node_id="ESP",
            lineage_generation=None,
            authority_scope="NATIONAL_ONLY",
            owns_regionalizable_state=False,
            owns_national_only_state=True,
            execution_status="L1_NATIONAL_ONLY_AUTHORITY",
        )
    )
    for runtime_id, catalog_id in (
        ("ESP::R1::g2", "ESP::R1"),
        ("ESP::R2::g2", "ESP::R2"),
    ):
        nodes.append(
            FractalRuntimeAuthorityNode(
                runtime_node_id=runtime_id,
                parent_node_id="ESP",
                level="L2_REGION",
                catalog_node_id=catalog_id,
                lineage_generation=2,
                authority_scope="REGIONALIZABLE",
                owns_regionalizable_state=True,
                owns_national_only_state=False,
                execution_status="L2_REGIONAL_AUTHORITY_ACTIVE_V0_28",
            )
        )
    return FractalRuntimePlan(
        day=7,
        policy_id="FRACTAL_RUNTIME_AUTHORITY_V1",
        config_hash="runtime-config-test",
        topology_hash="topology-generation-2",
        child_store_hash="child-store-generation-2",
        autonomous_child_dynamics_allowed=True,
        nodes=tuple(nodes),
        refined_parent_ids=("ESP",),
        active_regional_node_ids=(
            "ESP::R1::g2",
            "ESP::R2::g2",
        ),
        inactive_lineage_node_ids=("ESP::R1", "ESP::R2"),
        regionalizable_physical_stocks=(),
        national_only_physical_stocks=(),
        regionalizable_latents=(),
        national_only_latents=(),
        regionalizable_regimes=(),
        national_only_regimes=(),
    )


def _regional_catalog() -> dict:
    logger.info("_regional_catalog")
    return {
        "schema_version": "1.0",
        "status": "synthetic-test",
        "edges": [
            {
                "a": "ESP::R1",
                "b": "ESP::R2",
                "source_id": "SYN_INTERNAL_R1_R2",
                "channels": {
                    "geographic_proximity": {
                        "value": 0.85,
                    },
                    "land_border": {
                        "value": 1.0,
                    },
                    "information_link": {
                        "a_to_b": 0.20,
                        "b_to_a": 0.70,
                    },
                },
            },
            {
                "a": "ESP::R1",
                "b": "FRA",
                "source_id": "SYN_R1_FRA",
                "channels": {
                    "geographic_proximity": {
                        "value": 0.55,
                    },
                    "land_border": {
                        "value": 1.0,
                    },
                    "migration_link": {
                        "a_to_b": 0.30,
                        "b_to_a": 0.10,
                    },
                },
            },
        ],
    }


def test_coarse_projection_reproduces_base_l1_graph() -> None:
    logger.info("test_coarse_projection_reproduces_base_l1_graph")
    base = _base_graph()
    projected = build_fractal_projected_graph(
        runtime_plan=_coarse_plan(),
        base_graph=base,
        projection_config=_projection_config(),
        regional_graph_catalog={
            "schema_version": "1.0",
            "edges": [],
        },
    )

    assert len(projected.nodes) == 5
    assert len(projected.edges) == 10
    for base_edge in base.edges:
        edge = projected.edge(base_edge.a, base_edge.b)
        assert edge.edge_kind == "BASE_L1"
        for channel in CANONICAL_CHANNELS:
            for source, target in (
                (base_edge.a, base_edge.b),
                (base_edge.b, base_edge.a),
            ):
                assert edge.channel(source, target, channel) == (
                    base_edge.channel(source, target, channel)
                )
                status = edge.channel_status(
                    source,
                    target,
                    channel,
                )
                if base_edge.channel(source, target, channel) is None:
                    assert status == "BASE_L1_UNRESOLVED"
                else:
                    assert status == "BASE_L1_RESOLVED"


def test_refined_parent_is_replaced_by_generation_aware_l2_nodes() -> None:
    logger.info(
        "test_refined_parent_is_replaced_by_generation_aware_l2_nodes"
    )
    projected = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=_base_graph(),
        projection_config=_projection_config(),
        regional_graph_catalog=_regional_catalog(),
    )

    node_ids = {
        item.runtime_node_id
        for item in projected.nodes
    }
    assert "ESP" not in node_ids
    assert "ESP::R1::g2" in node_ids
    assert "ESP::R2::g2" in node_ids
    assert len(node_ids) == 6
    assert len(projected.edges) == 15

    r1_fra = projected.edge("ESP::R1::g2", "FRA")
    assert r1_fra.edge_kind == "L2_EXTERNAL"
    assert r1_fra.channel(
        "ESP::R1::g2",
        "FRA",
        "geographic_proximity",
    ) == pytest.approx(0.55)
    assert r1_fra.channel(
        "ESP::R1::g2",
        "FRA",
        "migration_link",
    ) == pytest.approx(0.30)
    assert r1_fra.channel(
        "FRA",
        "ESP::R1::g2",
        "migration_link",
    ) == pytest.approx(0.10)


def test_missing_regional_projection_remains_null_not_zero() -> None:
    logger.info(
        "test_missing_regional_projection_remains_null_not_zero"
    )
    projected = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=_base_graph(),
        projection_config=_projection_config(),
        regional_graph_catalog=_regional_catalog(),
    )

    r2_fra = projected.edge("ESP::R2::g2", "FRA")
    for channel in (
        "geographic_proximity",
        "land_border",
        "trade_dependency",
        "migration_link",
        "information_link",
        "criminal_network_link",
        "extremist_network_link",
    ):
        assert r2_fra.channel(
            "ESP::R2::g2",
            "FRA",
            channel,
        ) is None
        assert r2_fra.channel_status(
            "ESP::R2::g2",
            "FRA",
            channel,
        ) == "UNRESOLVED_REGIONAL_PROJECTION"


def test_alliance_link_is_parent_retained_not_cloned_to_l2() -> None:
    logger.info(
        "test_alliance_link_is_parent_retained_not_cloned_to_l2"
    )
    projected = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=_base_graph(),
        projection_config=_projection_config(),
        regional_graph_catalog=_regional_catalog(),
    )
    edge = projected.edge("ESP::R1::g2", "FRA")
    assert edge.channel(
        "ESP::R1::g2",
        "FRA",
        "alliance_link",
    ) is None
    assert edge.channel_status(
        "ESP::R1::g2",
        "FRA",
        "alliance_link",
    ) == "PARENT_RETAINED_NOT_PROJECTED"


def test_internal_l2_directionality_uses_stable_catalog_ids() -> None:
    logger.info(
        "test_internal_l2_directionality_uses_stable_catalog_ids"
    )
    projected = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=_base_graph(),
        projection_config=_projection_config(),
        regional_graph_catalog=_regional_catalog(),
    )
    edge = projected.edge("ESP::R1::g2", "ESP::R2::g2")
    assert edge.edge_kind == "INTERNAL_L2"
    assert edge.channel(
        "ESP::R1::g2",
        "ESP::R2::g2",
        "information_link",
    ) == pytest.approx(0.20)
    assert edge.channel(
        "ESP::R2::g2",
        "ESP::R1::g2",
        "information_link",
    ) == pytest.approx(0.70)


def test_projection_is_deterministic_and_catalog_sensitive() -> None:
    logger.info(
        "test_projection_is_deterministic_and_catalog_sensitive"
    )
    base = _base_graph()
    config = _projection_config()
    catalog_a = _regional_catalog()
    catalog_b = copy.deepcopy(catalog_a)
    catalog_b["edges"][1]["channels"]["geographic_proximity"][
        "value"
    ] = 0.45

    a = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=base,
        projection_config=config,
        regional_graph_catalog=catalog_a,
    )
    replay = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=base,
        projection_config=config,
        regional_graph_catalog=catalog_a,
    )
    b = build_fractal_projected_graph(
        runtime_plan=_refined_plan(),
        base_graph=base,
        projection_config=config,
        regional_graph_catalog=catalog_b,
    )

    assert a.to_dict() == replay.to_dict()
    assert a.graph_hash() == replay.graph_hash()
    assert a.graph_hash() != b.graph_hash()


def test_runtime_generation_ids_are_forbidden_in_catalog() -> None:
    logger.info(
        "test_runtime_generation_ids_are_forbidden_in_catalog"
    )
    catalog = _regional_catalog()
    catalog["edges"][0]["a"] = "ESP::R1::g2"
    with pytest.raises(
        ValueError,
        match="stable catalog IDs",
    ):
        build_fractal_projected_graph(
            runtime_plan=_refined_plan(),
            base_graph=_base_graph(),
            projection_config=_projection_config(),
            regional_graph_catalog=catalog,
        )


def test_regional_catalog_cannot_project_parent_retained_alliance() -> None:
    logger.info(
        "test_regional_catalog_cannot_project_parent_retained_alliance"
    )
    catalog = _regional_catalog()
    catalog["edges"][1]["channels"]["alliance_link"] = {
        "value": 1.0,
    }
    with pytest.raises(
        ValueError,
        match="may not project alliance_link",
    ):
        build_fractal_projected_graph(
            runtime_plan=_refined_plan(),
            base_graph=_base_graph(),
            projection_config=_projection_config(),
            regional_graph_catalog=catalog,
        )
