from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal import (
    FractalRefinementActionProposal,
    FractalRefinementPersistenceState,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
    materialize_next_level,
)
from iwsim.manifest import build_manifest
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    logger.info("_config")
    return load_yaml(
        ROOT / "config/engine/fractal_materialization_v1.yaml"
    )


def _manifest():
    logger.info("_manifest")
    parameters = load_yaml(
        ROOT / "config/engine/parameter_registry_v1.yaml"
    )
    return build_manifest(
        run_id="fractal-recursive-materialization-test",
        created_at="2026-09-25T00:00:00+00:00",
        engine_version="0.34.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-FRACTAL-RECURSIVE",
        scenario_hash=canonical_hash({"scenario": "recursive"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=3401,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-25",
        horizon_days=30,
        enabled_modules=("fractal_recursive_materialization",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )


def _l2_parent(
    *,
    runtime_id: str = "TST::R1",
    generation: int = 1,
    active: bool = True,
    closed_day: int | None = None,
) -> FractalTopologyNode:
    logger.info(
        "_l2_parent runtime_id=%s generation=%s active=%s",
        runtime_id,
        generation,
        active,
    )
    return FractalTopologyNode(
        node_id=runtime_id,
        label="Region 1",
        parent_node_id="TST",
        level="L2_REGION",
        created_day=1,
        refinement_action_id=f"expand-l2-g{generation}",
        refinement_reason="test",
        source_variables=("public_order_stress",),
        initialization_weight=1.0,
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
        catalog_source_id="SYNTHETIC_L2",
        de_refinement_day=closed_day,
        active=active,
        catalog_child_id="TST::R1",
        lineage_generation=generation,
        lineage_policy_id="FRACTAL_TOPOLOGY_GENERATION_V1",
    )


def _action(
    *,
    node_id: str = "TST::R1",
    day: int = 2,
    to_level: str = "L3_METRO_OR_LOGISTICS_AREA",
) -> FractalRefinementActionProposal:
    logger.info("_action node=%s day=%s to=%s", node_id, day, to_level)
    return FractalRefinementActionProposal(
        action_id=f"expand-{node_id}-{day}",
        node_id=node_id,
        day=day,
        action="EXPAND",
        from_level="L2_REGION",
        to_level=to_level,
        refinement_pressure=0.9,
        threshold=0.62,
        persistence_required=1,
        persistence_observed=1,
        refinement_reason="localized_stress",
        component_scores=(),
        source_variables=("public_order_stress",),
        equation_id="REFINEMENT_TRIGGER_V1",
        parameter_id="FRACTAL_REFINEMENT_SYN_V1",
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
    )


def _persistence(
    *,
    node_id: str = "TST::R1",
    day: int = 2,
) -> FractalRefinementPersistenceState:
    logger.info("_persistence node=%s day=%s", node_id, day)
    return FractalRefinementPersistenceState(
        node_id=node_id,
        current_level="L2_REGION",
        last_evaluated_day=day,
        expand_streak=1,
        collapse_streak=0,
    )


def _l3_catalog() -> dict:
    logger.info("_l3_catalog")
    return {
        "schema_version": "1.0",
        "parents": {
            "TST::R1": {
                "source_id": "SYNTHETIC_L3",
                "children": [
                    {
                        "child_id": "TST::R1::METRO_A",
                        "label": "Metro A",
                        "initialization_weight": 0.6,
                    },
                    {
                        "child_id": "TST::R1::LOGISTICS_B",
                        "label": "Logistics B",
                        "initialization_weight": 0.4,
                    },
                ],
            }
        },
    }


def test_l2_materializes_adjacent_l3_children() -> None:
    logger.info("test_l2_materializes_adjacent_l3_children")
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_l2_parent(),),
    )
    trace = TraceLedger()
    after, persistence, record = materialize_next_level(
        action=_action(),
        persistence=_persistence(),
        topology=topology,
        child_catalog=_l3_catalog(),
        materialization_config=_config(),
        manifest=_manifest(),
        trace=trace,
    )

    children = after.active_children("TST::R1")
    assert persistence.current_level == "L3_METRO_OR_LOGISTICS_AREA"
    assert record.from_level == "L2_REGION"
    assert record.to_level == "L3_METRO_OR_LOGISTICS_AREA"
    assert record.lineage_generation == 1
    assert {item.node_id for item in children} == {
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    }
    assert {item.catalog_child_id for item in children} == {
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    }
    assert all(
        item.level == "L3_METRO_OR_LOGISTICS_AREA"
        and item.parent_node_id == "TST::R1"
        for item in children
    )
    assert [item["record_type"] for item in trace.records].count(
        "fractal_lineage_created"
    ) == 2


def test_l3_runtime_ids_follow_generated_parent_lineage() -> None:
    logger.info("test_l3_runtime_ids_follow_generated_parent_lineage")
    historical = _l2_parent(
        runtime_id="TST::R1",
        generation=1,
        active=False,
        closed_day=10,
    )
    active_parent = _l2_parent(
        runtime_id="TST::R1::g2",
        generation=2,
        active=True,
    )
    topology = FractalTopologyState(
        last_committed_day=11,
        nodes=(historical, active_parent),
    )
    after, _, record = materialize_next_level(
        action=_action(node_id="TST::R1::g2", day=12),
        persistence=_persistence(node_id="TST::R1::g2", day=12),
        topology=topology,
        child_catalog=_l3_catalog(),
        materialization_config=_config(),
        manifest=_manifest(),
        trace=TraceLedger(),
    )

    children = after.active_children("TST::R1::g2")
    assert record.lineage_generation == 1
    assert {item.node_id for item in children} == {
        "TST::R1::g2::METRO_A",
        "TST::R1::g2::LOGISTICS_B",
    }
    assert {item.catalog_child_id for item in children} == {
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    }


def test_recursive_child_rerefine_gets_next_local_generation() -> None:
    logger.info("test_recursive_child_rerefine_gets_next_local_generation")
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_l2_parent(),),
    )
    first, _, _ = materialize_next_level(
        action=_action(day=2),
        persistence=_persistence(day=2),
        topology=topology,
        child_catalog=_l3_catalog(),
        materialization_config=_config(),
        manifest=_manifest(),
        trace=TraceLedger(),
    )
    closed = FractalTopologyState(
        last_committed_day=3,
        nodes=tuple(
            replace(item, active=False, de_refinement_day=3)
            if item.level == "L3_METRO_OR_LOGISTICS_AREA"
            else item
            for item in first.nodes
        ),
    )
    second, _, record = materialize_next_level(
        action=_action(day=4),
        persistence=_persistence(day=4),
        topology=closed,
        child_catalog=_l3_catalog(),
        materialization_config=_config(),
        manifest=_manifest(),
        trace=TraceLedger(),
    )

    active = second.active_children("TST::R1")
    assert record.lineage_generation == 2
    assert {item.node_id for item in active} == {
        "TST::R1::METRO_A::g2",
        "TST::R1::LOGISTICS_B::g2",
    }
    assert {item.catalog_child_id for item in active} == {
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    }


def test_recursive_materialization_rejects_level_skips() -> None:
    logger.info("test_recursive_materialization_rejects_level_skips")
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_l2_parent(),),
    )
    with pytest.raises(ValueError, match="adjacent expansion"):
        materialize_next_level(
            action=_action(to_level="L4_ACTOR_NETWORK"),
            persistence=_persistence(),
            topology=topology,
            child_catalog=_l3_catalog(),
            materialization_config=_config(),
            manifest=_manifest(),
            trace=TraceLedger(),
        )
