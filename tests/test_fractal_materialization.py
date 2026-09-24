from __future__ import annotations

import copy
import logging
from dataclasses import replace
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal import (
    FractalRefinementPersistenceState,
    evaluate_fractal_refinement,
)
from iwsim.fractal_materialization import (
    FractalTopologyState,
    empty_fractal_topology,
    materialize_l1_to_l2,
)
from iwsim.manifest import build_manifest
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    refinement_config = load_yaml(
        ROOT / "config/engine/fractal_refinement_v1.yaml"
    )
    materialization_config = load_yaml(
        ROOT / "config/engine/fractal_materialization_v1.yaml"
    )
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=1,
        physical_stocks={},
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={},
    )
    for variable in (
        "public_order_stress",
        "terrorism_threat_pressure",
        "organized_armed_actor_capacity",
        "regional_fragmentation_pressure",
        "criminal_network_power",
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
        "revolutionary_extremist_pressure",
        "displacement_pressure",
    ):
        state.latents[variable] = 1.0
    for variable in (
        "government_legitimacy",
        "state_cohesion",
        "security_chain_cohesion",
        "electricity_functionality",
        "fuel_distribution_functionality",
        "transport_logistics_functionality",
        "telecom_internet_functionality",
        "water_resilience",
    ):
        state.latents[variable] = 0.0

    manifest = build_manifest(
        run_id="fractal-materialization-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.20.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-FRACTAL-MATERIALIZATION-TEST",
        scenario_hash=canonical_hash({"scenario": "fractal-materialization"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=1,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=30,
        enabled_modules=("fractal_refinement", "fractal_materialization"),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )
    persistence = FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L1_COUNTRY",
        last_evaluated_day=0,
        expand_streak=7,
        collapse_streak=0,
    )
    evaluation = evaluate_fractal_refinement(
        state=state,
        persistence=persistence,
        refinement_config=refinement_config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert len(evaluation.proposals) == 1
    return (
        evaluation.proposals[0],
        evaluation.persistence,
        materialization_config,
        manifest,
    )


def _catalog():
    logger.info("_catalog")
    return {
        "schema_version": "1.0",
        "parents": {
            "TST": {
                "source_id": "SYNTHETIC_TEST_CATALOG",
                "children": [
                    {
                        "child_id": "TST::R1",
                        "label": "Region 1",
                        "initialization_weight": 0.5,
                    },
                    {
                        "child_id": "TST::R2",
                        "label": "Region 2",
                        "initialization_weight": 0.3,
                    },
                    {
                        "child_id": "TST::R3",
                        "label": "Region 3",
                        "initialization_weight": 0.2,
                    },
                ],
            }
        },
    }


def test_materialization_creates_lineage_and_advances_parent_level() -> None:
    logger.info(
        "test_materialization_creates_lineage_and_advances_parent_level"
    )
    action, persistence, config, manifest = _fixture()
    topology = empty_fractal_topology(0)
    trace = TraceLedger()

    topology_after, persistence_after, record = materialize_l1_to_l2(
        action=action,
        persistence=persistence,
        topology=topology,
        region_catalog=_catalog(),
        materialization_config=config,
        manifest=manifest,
        trace=trace,
    )

    children = topology_after.active_children("TST")
    assert topology.last_committed_day == 0
    assert topology.nodes == ()
    assert topology_after.last_committed_day == 1
    assert len(children) == 3
    assert sum(item.initialization_weight for item in children) == pytest.approx(
        1.0
    )
    assert {item.node_id for item in children} == {
        "TST::R1",
        "TST::R2",
        "TST::R3",
    }
    assert all(item.parent_node_id == "TST" for item in children)
    assert all(item.level == "L2_REGION" for item in children)
    assert all(item.created_day == 1 for item in children)
    assert all(
        item.refinement_action_id == action.action_id for item in children
    )
    assert all(
        item.initialization_weight_policy_id
        == "FRACTAL_CHILD_INIT_WEIGHTS_V1"
        for item in children
    )
    assert all(
        item.inherited_uncertainty_policy_id
        == "FRACTAL_UNCERTAINTY_WIDENING_V1"
        for item in children
    )
    assert all(
        item.aggregation_rule_id == "FRACTAL_PARENT_REAGGREGATION_V1"
        for item in children
    )
    assert all(
        item.catalog_source_id == "SYNTHETIC_TEST_CATALOG"
        for item in children
    )
    assert persistence_after.current_level == "L2_REGION"
    assert persistence_after.expand_streak == 0
    assert persistence_after.collapse_streak == 0
    assert record.child_node_ids == ("TST::R1", "TST::R2", "TST::R3")
    assert record.topology_hash_before == topology.topology_hash()
    assert record.topology_hash_after == topology_after.topology_hash()

    record_types = [item["record_type"] for item in trace.records]
    assert record_types[0] == "fractal_materialization_committed"
    assert record_types.count("fractal_lineage_created") == 3


def test_materialization_fails_closed_without_explicit_parent_catalog() -> None:
    logger.info(
        "test_materialization_fails_closed_without_explicit_parent_catalog"
    )
    action, persistence, config, manifest = _fixture()

    with pytest.raises(ValueError, match="No explicit regional catalog"):
        materialize_l1_to_l2(
            action=action,
            persistence=persistence,
            topology=empty_fractal_topology(0),
            region_catalog={"schema_version": "1.0", "parents": {}},
            materialization_config=config,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_materialization_weights_must_sum_to_one() -> None:
    logger.info("test_materialization_weights_must_sum_to_one")
    action, persistence, config, manifest = _fixture()
    broken = copy.deepcopy(_catalog())
    broken["parents"]["TST"]["children"][0]["initialization_weight"] = 0.4

    with pytest.raises(ValueError, match="must sum to 1.0"):
        materialize_l1_to_l2(
            action=action,
            persistence=persistence,
            topology=empty_fractal_topology(0),
            region_catalog=broken,
            materialization_config=config,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_materialization_rejects_collapse_action_in_v0_20() -> None:
    logger.info("test_materialization_rejects_collapse_action_in_v0_20")
    action, persistence, config, manifest = _fixture()
    collapse = action.__class__(
        action_id=action.action_id,
        node_id=action.node_id,
        day=action.day,
        action="COLLAPSE",
        from_level="L2_REGION",
        to_level="L1_COUNTRY",
        refinement_pressure=action.refinement_pressure,
        threshold=action.threshold,
        persistence_required=action.persistence_required,
        persistence_observed=action.persistence_observed,
        refinement_reason=action.refinement_reason,
        component_scores=action.component_scores,
        source_variables=action.source_variables,
        equation_id=action.equation_id,
        parameter_id=action.parameter_id,
        initialization_weight_policy_id=action.initialization_weight_policy_id,
        inherited_uncertainty_policy_id=action.inherited_uncertainty_policy_id,
        aggregation_rule_id=action.aggregation_rule_id,
        apply_status=action.apply_status,
    )

    with pytest.raises(ValueError, match="supports EXPAND only"):
        materialize_l1_to_l2(
            action=collapse,
            persistence=persistence,
            topology=empty_fractal_topology(0),
            region_catalog=_catalog(),
            materialization_config=config,
            manifest=manifest,
            trace=TraceLedger(),
        )



def _closed_generation_one_topology(
    *,
    action,
    persistence,
    config,
    manifest,
    closed_day: int = 10,
) -> FractalTopologyState:
    logger.info(
        "_closed_generation_one_topology closed_day=%s",
        closed_day,
    )
    first, _, _ = materialize_l1_to_l2(
        action=action,
        persistence=persistence,
        topology=empty_fractal_topology(0),
        region_catalog=_catalog(),
        materialization_config=config,
        manifest=manifest,
        trace=TraceLedger(),
    )
    return FractalTopologyState(
        last_committed_day=closed_day,
        nodes=tuple(
            replace(
                item,
                active=False,
                de_refinement_day=closed_day,
            )
            for item in first.nodes
        ),
    )


def test_materialization_second_refinement_creates_new_lineage_generation() -> None:
    logger.info(
        "test_materialization_second_refinement_creates_new_lineage_generation"
    )
    action, persistence, config, manifest = _fixture()
    closed = _closed_generation_one_topology(
        action=action,
        persistence=persistence,
        config=config,
        manifest=manifest,
    )
    second_action = replace(
        action,
        action_id="fractal-expand-generation-2",
        day=11,
    )
    second_persistence = FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L1_COUNTRY",
        last_evaluated_day=11,
        expand_streak=action.persistence_required,
        collapse_streak=0,
    )
    before = closed.to_dict()
    trace = TraceLedger()

    topology_after, persistence_after, record = materialize_l1_to_l2(
        action=second_action,
        persistence=second_persistence,
        topology=closed,
        region_catalog=_catalog(),
        materialization_config=config,
        manifest=manifest,
        trace=trace,
    )

    assert closed.to_dict() == before
    historical = [
        item for item in topology_after.nodes if not item.active
    ]
    active = topology_after.active_children("TST")

    assert {item.node_id for item in historical} == {
        "TST::R1",
        "TST::R2",
        "TST::R3",
    }
    assert all(item.lineage_generation == 1 for item in historical)
    assert all(item.de_refinement_day == 10 for item in historical)

    assert {item.node_id for item in active} == {
        "TST::R1::g2",
        "TST::R2::g2",
        "TST::R3::g2",
    }
    assert {item.catalog_child_id for item in active} == {
        "TST::R1",
        "TST::R2",
        "TST::R3",
    }
    assert all(item.lineage_generation == 2 for item in active)
    assert all(
        item.lineage_policy_id == "FRACTAL_TOPOLOGY_GENERATION_V1"
        for item in active
    )
    assert persistence_after.current_level == "L2_REGION"

    assert record.lineage_generation == 2
    assert record.lineage_policy_id == "FRACTAL_TOPOLOGY_GENERATION_V1"
    assert record.catalog_child_ids == (
        "TST::R1",
        "TST::R2",
        "TST::R3",
    )
    assert record.child_node_ids == (
        "TST::R1::g2",
        "TST::R2::g2",
        "TST::R3::g2",
    )
    created = [
        item
        for item in trace.records
        if item["record_type"] == "fractal_lineage_created"
    ]
    assert {item["node_id"] for item in created} == set(
        record.child_node_ids
    )
    assert all(item["lineage_generation"] == 2 for item in created)


def test_materialization_rejects_catalog_child_set_change_after_history() -> None:
    logger.info(
        "test_materialization_rejects_catalog_child_set_change_after_history"
    )
    action, persistence, config, manifest = _fixture()
    closed = _closed_generation_one_topology(
        action=action,
        persistence=persistence,
        config=config,
        manifest=manifest,
    )
    changed_catalog = copy.deepcopy(_catalog())
    changed_catalog["parents"]["TST"]["children"][2]["child_id"] = "TST::R4"
    second_action = replace(
        action,
        action_id="fractal-expand-catalog-change",
        day=11,
    )
    second_persistence = FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L1_COUNTRY",
        last_evaluated_day=11,
        expand_streak=action.persistence_required,
        collapse_streak=0,
    )

    with pytest.raises(
        ValueError,
        match="catalog child set changed across generations",
    ):
        materialize_l1_to_l2(
            action=second_action,
            persistence=second_persistence,
            topology=closed,
            region_catalog=changed_catalog,
            materialization_config=config,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_materialization_rejects_reserved_generation_suffix_in_catalog() -> None:
    logger.info(
        "test_materialization_rejects_reserved_generation_suffix_in_catalog"
    )
    action, persistence, config, manifest = _fixture()
    catalog = copy.deepcopy(_catalog())
    catalog["parents"]["TST"]["children"][0]["child_id"] = "TST::R1::g2"

    with pytest.raises(ValueError, match="reserved generation suffix"):
        materialize_l1_to_l2(
            action=action,
            persistence=persistence,
            topology=empty_fractal_topology(0),
            region_catalog=catalog,
            materialization_config=config,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_materialization_rejects_inconsistent_sibling_generation_history() -> None:
    logger.info(
        "test_materialization_rejects_inconsistent_sibling_generation_history"
    )
    action, persistence, config, manifest = _fixture()
    closed = _closed_generation_one_topology(
        action=action,
        persistence=persistence,
        config=config,
        manifest=manifest,
    )
    r1 = next(item for item in closed.nodes if item.node_id == "TST::R1")
    inconsistent = FractalTopologyState(
        last_committed_day=20,
        nodes=(
            *closed.nodes,
            replace(
                r1,
                node_id="TST::R1::g2",
                catalog_child_id="TST::R1",
                lineage_generation=2,
                lineage_policy_id="FRACTAL_TOPOLOGY_GENERATION_V1",
                created_day=11,
                de_refinement_day=20,
                refinement_action_id="old-generation-2",
            ),
        ),
    )
    third_action = replace(
        action,
        action_id="fractal-expand-inconsistent-history",
        day=21,
    )
    third_persistence = FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L1_COUNTRY",
        last_evaluated_day=21,
        expand_streak=action.persistence_required,
        collapse_streak=0,
    )

    with pytest.raises(
        ValueError,
        match="sibling lineage generation history is inconsistent",
    ):
        materialize_l1_to_l2(
            action=third_action,
            persistence=third_persistence,
            topology=inconsistent,
            region_catalog=_catalog(),
            materialization_config=config,
            manifest=manifest,
            trace=TraceLedger(),
        )
