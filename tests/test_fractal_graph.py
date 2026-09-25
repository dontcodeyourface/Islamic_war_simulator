from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.fractal_graph import build_fractal_projected_graph
from iwsim.fractal_runtime import (
    FractalRuntimeAuthorityNode,
    FractalRuntimePlan,
)
from iwsim.graph import (
    DIRECTED_CHANNELS,
    CountryGraph,
    DirectedChannelValue,
    GraphEdge,
    GraphNode,
    SymmetricChannelValue,
)

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _projection_config() -> dict:
    logger.info("_projection_config")
    return load_yaml(
        ROOT / "config/engine/fractal_graph_projection_v1.yaml"
    )


def _empty_graph_data() -> dict:
    logger.info("_empty_graph_data")
    return load_yaml(
        ROOT / "config/engine/fractal_region_graph_v1.yaml"
    )


def _region_catalog() -> dict:
    logger.info("_region_catalog")
    return {
        "schema_version": "1.0",
        "parents": {
            "ESP": {
                "source_id": "SYNTHETIC_GRAPH_TEST",
                "children": [
                    {
                        "child_id": "ESP::R1",
                        "label": "Region 1",
                        "initialization_weight": 0.55,
                    },
                    {
                        "child_id": "ESP::R2",
                        "label": "Region 2",
                        "initialization_weight": 0.45,
                    },
                ],
            }
        },
    }


def _directed(
    *,
    information_a_to_b: float | None = None,
    information_b_to_a: float | None = None,
) -> tuple[DirectedChannelValue, ...]:
    logger.info(
        "_directed information_a_to_b=%s information_b_to_a=%s",
        information_a_to_b,
        information_b_to_a,
    )
    values: list[DirectedChannelValue] = []
    for channel in DIRECTED_CHANNELS:
        if channel == "information_link":
            values.append(
                DirectedChannelValue(
                    name=channel,
                    a_to_b=information_a_to_b,
                    b_to_a=information_b_to_a,
                    parameter_id_a_to_b=(
                        "INFO_A_B" if information_a_to_b is not None else None
                    ),
                    parameter_id_b_to_a=(
                        "INFO_B_A" if information_b_to_a is not None else None
                    ),
                )
            )
        else:
            values.append(
                DirectedChannelValue(
                    name=channel,
                    a_to_b=None,
                    b_to_a=None,
                    parameter_id_a_to_b=None,
                    parameter_id_b_to_a=None,
                )
            )
    return tuple(values)


def _edge(
    a: str,
    b: str,
    *,
    distance: float,
    border: bool,
    geo: float,
    alliance: float,
    information_a_to_b: float | None = None,
    information_b_to_a: float | None = None,
) -> GraphEdge:
    logger.info("_edge a=%s b=%s", a, b)
    return GraphEdge(
        a=a,
        b=b,
        distance_km=distance,
        direct_land_border=border,
        symmetric_channels=(
            SymmetricChannelValue(
                name="geographic_proximity",
                value=geo,
                parameter_id="GEO",
            ),
            SymmetricChannelValue(
                name="land_border",
                value=1.0 if border else 0.0,
                parameter_id=None,
            ),
            SymmetricChannelValue(
                name="alliance_link",
                value=alliance,
                parameter_id="ALLIANCE",
            ),
        ),
        directed_channels=_directed(
            information_a_to_b=information_a_to_b,
            information_b_to_a=information_b_to_a,
        ),
        metadata=(("source", "synthetic-test"),),
    )


def _country_graph() -> CountryGraph:
    logger.info("_country_graph")
    graph = CountryGraph(
        schema_version="1.0",
        profile="synthetic_smoke_v1",
        nodes=(
            GraphNode(
                iso3="ESP",
                country_name="Spain",
                snapshot_path="spain.yaml",
                distance_matrix_name="Spain",
            ),
            GraphNode(
                iso3="FRA",
                country_name="France",
                snapshot_path="france.yaml",
                distance_matrix_name="France",
            ),
            GraphNode(
                iso3="MAR",
                country_name="Morocco",
                snapshot_path="morocco.yaml",
                distance_matrix_name="Morocco",
            ),
        ),
        edges=(
            _edge(
                "ESP",
                "FRA",
                distance=1050.0,
                border=True,
                geo=0.55,
                alliance=0.8,
                information_a_to_b=0.8,
                information_b_to_a=0.6,
            ),
            _edge(
                "ESP",
                "MAR",
                distance=1300.0,
                border=True,
                geo=0.45,
                alliance=0.1,
                information_a_to_b=None,
                information_b_to_a=None,
            ),
            _edge(
                "FRA",
                "MAR",
                distance=1800.0,
                border=False,
                geo=0.35,
                alliance=0.1,
                information_a_to_b=0.4,
                information_b_to_a=0.3,
            ),
        ),
    )
    graph.validate()
    return graph


def _l1_node(node_id: str, *, full: bool) -> FractalRuntimeAuthorityNode:
    logger.info("_l1_node node=%s full=%s", node_id, full)
    return FractalRuntimeAuthorityNode(
        runtime_node_id=node_id,
        parent_node_id=None,
        level="L1_COUNTRY",
        catalog_node_id=node_id,
        lineage_generation=None,
        authority_scope="FULL" if full else "NATIONAL_ONLY",
        owns_regionalizable_state=full,
        owns_national_only_state=True,
        execution_status=(
            "L1_FULL_AUTHORITY"
            if full
            else "L1_NATIONAL_ONLY_AUTHORITY"
        ),
    )


def _l2_node(
    *,
    runtime_id: str,
    catalog_id: str,
    generation: int,
) -> FractalRuntimeAuthorityNode:
    logger.info(
        "_l2_node runtime=%s catalog=%s generation=%s",
        runtime_id,
        catalog_id,
        generation,
    )
    return FractalRuntimeAuthorityNode(
        runtime_node_id=runtime_id,
        parent_node_id="ESP",
        level="L2_REGION",
        catalog_node_id=catalog_id,
        lineage_generation=generation,
        authority_scope="REGIONALIZABLE",
        owns_regionalizable_state=True,
        owns_national_only_state=False,
        execution_status="L2_REGIONAL_AUTHORITY_ACTIVE_V0_26",
    )


def _plan(
    *,
    refined: bool,
    generation: int = 1,
) -> FractalRuntimePlan:
    logger.info(
        "_plan refined=%s generation=%s",
        refined,
        generation,
    )
    if not refined:
        nodes = (
            _l1_node("ESP", full=True),
            _l1_node("FRA", full=True),
            _l1_node("MAR", full=True),
        )
        refined_ids: tuple[str, ...] = ()
        regional_ids: tuple[str, ...] = ()
    else:
        suffix = "" if generation == 1 else f"::g{generation}"
        r1 = f"ESP::R1{suffix}"
        r2 = f"ESP::R2{suffix}"
        nodes = (
            _l1_node("ESP", full=False),
            _l1_node("FRA", full=True),
            _l1_node("MAR", full=True),
            _l2_node(
                runtime_id=r1,
                catalog_id="ESP::R1",
                generation=generation,
            ),
            _l2_node(
                runtime_id=r2,
                catalog_id="ESP::R2",
                generation=generation,
            ),
        )
        refined_ids = ("ESP",)
        regional_ids = tuple(sorted((r1, r2)))

    return FractalRuntimePlan(
        day=7,
        policy_id="FRACTAL_RUNTIME_AUTHORITY_V1",
        config_hash="runtime-config",
        topology_hash="topology",
        child_store_hash="children",
        autonomous_child_dynamics_allowed=True,
        nodes=nodes,
        refined_parent_ids=refined_ids,
        active_regional_node_ids=regional_ids,
        inactive_lineage_node_ids=(),
        regionalizable_physical_stocks=(),
        national_only_physical_stocks=(),
        regionalizable_latents=(),
        national_only_latents=(),
        regionalizable_regimes=(
            "national_phase",
            "security_force_regime",
        ),
        national_only_regimes=(
            "prison_regime",
            "organized_crime_regime",
        ),
    )


def test_coarse_runtime_projection_copies_country_graph_exactly() -> None:
    logger.info(
        "test_coarse_runtime_projection_copies_country_graph_exactly"
    )
    country = _country_graph()
    projected = build_fractal_projected_graph(
        country_graph=country,
        runtime_plan=_plan(refined=False),
        projection_config=_projection_config(),
        regional_graph_data=_empty_graph_data(),
        region_catalog=_region_catalog(),
    )

    assert {node.runtime_node_id for node in projected.nodes} == {
        "ESP",
        "FRA",
        "MAR",
    }
    assert len(projected.edges) == 3
    for source_edge in country.edges:
        edge = projected.edge(source_edge.a, source_edge.b)
        assert edge.relation_type == "COARSE_L1"
        assert edge.parent_edge_id == source_edge.edge_id()
        assert edge.distance_km == source_edge.distance_km
        assert edge.direct_land_border == source_edge.direct_land_border
        for channel in (
            "geographic_proximity",
            "land_border",
            "alliance_link",
            *DIRECTED_CHANNELS,
        ):
            assert edge.channel(
                source_edge.a,
                source_edge.b,
                channel,
            ) == source_edge.channel(
                source_edge.a,
                source_edge.b,
                channel,
            )


def test_refinement_replaces_parent_with_l2_and_does_not_clone_edges() -> None:
    logger.info(
        "test_refinement_replaces_parent_with_l2_and_does_not_clone_edges"
    )
    projected = build_fractal_projected_graph(
        country_graph=_country_graph(),
        runtime_plan=_plan(refined=True),
        projection_config=_projection_config(),
        regional_graph_data=_empty_graph_data(),
        region_catalog=_region_catalog(),
    )

    assert {node.runtime_node_id for node in projected.nodes} == {
        "ESP::R1",
        "ESP::R2",
        "FRA",
        "MAR",
    }
    assert len(projected.edges) == 6
    assert projected.edge("FRA", "MAR").relation_type == "COARSE_L1"

    internal = projected.edge("ESP::R1", "ESP::R2")
    assert internal.relation_type == "INTERNAL_L2"
    assert internal.distance_km is None
    assert internal.direct_land_border is None

    external = projected.edge("ESP::R1", "FRA")
    assert external.relation_type == "L2_TO_COARSE_L1"
    assert external.parent_edge_id == "ESP--FRA"
    for channel in (
        "geographic_proximity",
        "land_border",
        "alliance_link",
        *DIRECTED_CHANNELS,
    ):
        assert external.channel(
            "ESP::R1",
            "FRA",
            channel,
        ) is None


def test_explicit_internal_l2_data_resolves_only_declared_channels() -> None:
    logger.info(
        "test_explicit_internal_l2_data_resolves_only_declared_channels"
    )
    data = {
        "schema_version": "1.0",
        "edges": [
            {
                "a": {
                    "kind": "regional_catalog",
                    "id": "ESP::R1",
                },
                "b": {
                    "kind": "regional_catalog",
                    "id": "ESP::R2",
                },
                "source_id": "REGIONAL_ADJ_TEST",
                "distance_km": 220.0,
                "direct_land_border": True,
                "symmetric_channels": {
                    "geographic_proximity": {
                        "mode": "explicit",
                        "value": 0.9,
                        "parameter_id": "REGIONAL_GEO_TEST",
                    },
                    "land_border": {
                        "mode": "explicit",
                        "value": 1.0,
                    },
                },
            }
        ],
    }
    graph = build_fractal_projected_graph(
        country_graph=_country_graph(),
        runtime_plan=_plan(refined=True),
        projection_config=_projection_config(),
        regional_graph_data=data,
        region_catalog=_region_catalog(),
    )
    edge = graph.edge("ESP::R1", "ESP::R2")
    assert edge.distance_km == 220.0
    assert edge.direct_land_border is True
    assert (
        edge.channel(
            "ESP::R1",
            "ESP::R2",
            "geographic_proximity",
        )
        == pytest.approx(0.9)
    )
    assert (
        edge.channel("ESP::R1", "ESP::R2", "land_border")
        == 1.0
    )
    assert (
        edge.channel("ESP::R1", "ESP::R2", "alliance_link")
        is None
    )
    assert (
        edge.channel("ESP::R1", "ESP::R2", "information_link")
        is None
    )


def test_explicit_directed_projection_preserves_data_orientation() -> None:
    logger.info(
        "test_explicit_directed_projection_preserves_data_orientation"
    )
    data = {
        "schema_version": "1.0",
        "edges": [
            {
                "a": {
                    "kind": "regional_catalog",
                    "id": "ESP::R1",
                },
                "b": {"kind": "country", "id": "FRA"},
                "source_id": "REGIONAL_INFO_TEST",
                "directed_channels": {
                    "information_link": {
                        "a_to_b": {
                            "mode": "explicit",
                            "value": 0.7,
                        },
                        "b_to_a": {
                            "mode": "explicit",
                            "value": 0.2,
                        },
                    }
                },
            }
        ],
    }
    graph = build_fractal_projected_graph(
        country_graph=_country_graph(),
        runtime_plan=_plan(refined=True),
        projection_config=_projection_config(),
        regional_graph_data=data,
        region_catalog=_region_catalog(),
    )
    edge = graph.edge("ESP::R1", "FRA")
    assert (
        edge.channel("ESP::R1", "FRA", "information_link")
        == pytest.approx(0.7)
    )
    assert (
        edge.channel("FRA", "ESP::R1", "information_link")
        == pytest.approx(0.2)
    )


def test_parent_scaled_projection_uses_country_edge_and_preserves_null() -> None:
    logger.info(
        "test_parent_scaled_projection_uses_country_edge_and_preserves_null"
    )
    data = {
        "schema_version": "1.0",
        "edges": [
            {
                "a": {
                    "kind": "regional_catalog",
                    "id": "ESP::R1",
                },
                "b": {"kind": "country", "id": "FRA"},
                "source_id": "REGIONAL_SCALE_TEST",
                "directed_channels": {
                    "information_link": {
                        "a_to_b": {
                            "mode": "parent_scaled",
                            "factor": 0.5,
                            "parameter_id": "REGIONAL_INFO_SHARE_TEST",
                        }
                    },
                    "migration_link": {
                        "a_to_b": {
                            "mode": "parent_scaled",
                            "factor": 0.5,
                            "parameter_id": "REGIONAL_MIG_SHARE_TEST",
                        }
                    },
                },
            }
        ],
    }
    graph = build_fractal_projected_graph(
        country_graph=_country_graph(),
        runtime_plan=_plan(refined=True),
        projection_config=_projection_config(),
        regional_graph_data=data,
        region_catalog=_region_catalog(),
    )
    edge = graph.edge("ESP::R1", "FRA")
    assert (
        edge.channel("ESP::R1", "FRA", "information_link")
        == pytest.approx(0.4)
    )
    assert (
        edge.channel("ESP::R1", "FRA", "migration_link")
        is None
    )


def test_parent_scaled_internal_l2_edge_fails_closed() -> None:
    logger.info("test_parent_scaled_internal_l2_edge_fails_closed")
    data = {
        "schema_version": "1.0",
        "edges": [
            {
                "a": {
                    "kind": "regional_catalog",
                    "id": "ESP::R1",
                },
                "b": {
                    "kind": "regional_catalog",
                    "id": "ESP::R2",
                },
                "source_id": "INVALID_INTERNAL_SCALE",
                "directed_channels": {
                    "information_link": {
                        "a_to_b": {
                            "mode": "parent_scaled",
                            "factor": 0.5,
                        }
                    }
                },
            }
        ],
    }
    with pytest.raises(
        ValueError,
        match="parent_scaled projection requires a distinct parent-country",
    ):
        build_fractal_projected_graph(
            country_graph=_country_graph(),
            runtime_plan=_plan(refined=True),
            projection_config=_projection_config(),
            regional_graph_data=data,
            region_catalog=_region_catalog(),
        )


def test_unknown_regional_catalog_endpoint_fails_closed() -> None:
    logger.info("test_unknown_regional_catalog_endpoint_fails_closed")
    data = {
        "schema_version": "1.0",
        "edges": [
            {
                "a": {
                    "kind": "regional_catalog",
                    "id": "ESP::UNKNOWN",
                },
                "b": {"kind": "country", "id": "FRA"},
                "source_id": "BAD_REGION",
            }
        ],
    }
    with pytest.raises(
        ValueError,
        match="Unknown regional catalog endpoint",
    ):
        build_fractal_projected_graph(
            country_graph=_country_graph(),
            runtime_plan=_plan(refined=True),
            projection_config=_projection_config(),
            regional_graph_data=data,
            region_catalog=_region_catalog(),
        )


def test_same_catalog_evidence_maps_to_generation_two_runtime_ids() -> None:
    logger.info(
        "test_same_catalog_evidence_maps_to_generation_two_runtime_ids"
    )
    data = {
        "schema_version": "1.0",
        "edges": [
            {
                "a": {
                    "kind": "regional_catalog",
                    "id": "ESP::R1",
                },
                "b": {"kind": "country", "id": "FRA"},
                "source_id": "GENERATION_STABLE_EVIDENCE",
                "directed_channels": {
                    "information_link": {
                        "a_to_b": {
                            "mode": "explicit",
                            "value": 0.65,
                        }
                    }
                },
            }
        ],
    }
    graph = build_fractal_projected_graph(
        country_graph=_country_graph(),
        runtime_plan=_plan(refined=True, generation=2),
        projection_config=_projection_config(),
        regional_graph_data=data,
        region_catalog=_region_catalog(),
    )
    assert {node.runtime_node_id for node in graph.nodes} == {
        "ESP::R1::g2",
        "ESP::R2::g2",
        "FRA",
        "MAR",
    }
    assert (
        graph.edge("ESP::R1::g2", "FRA").channel(
            "ESP::R1::g2",
            "FRA",
            "information_link",
        )
        == pytest.approx(0.65)
    )
