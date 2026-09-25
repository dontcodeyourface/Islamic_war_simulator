from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal import (
    FractalRefinementActionProposal,
    FractalRefinementPersistenceState,
)
from iwsim.fractal_child_state import FractalChildStateStore
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
    materialize_next_level,
)
from iwsim.fractal_reaggregation import collapse_l3_to_l2
from iwsim.manifest import build_manifest
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _registry() -> dict:
    logger.info("_registry")
    return load_yaml(ROOT / "config/engine/engine_state_v1.yaml")


def _parameters() -> dict:
    logger.info("_parameters")
    return load_yaml(
        ROOT / "config/engine/parameter_registry_v1.yaml"
    )


def _manifest():
    logger.info("_manifest")
    parameters = _parameters()
    return build_manifest(
        run_id="fractal-l3-reaggregation-test",
        created_at="2026-09-25T00:00:00+00:00",
        engine_version="0.34.3",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-FRACTAL-L3-REAGGREGATION",
        scenario_hash=canonical_hash({"scenario": "l3-collapse"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=3431,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-25",
        horizon_days=30,
        enabled_modules=("fractal_l3_reaggregation",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )


def _latents(stress: float) -> dict[str, float]:
    logger.info("_latents stress=%s", stress)
    values = {
        variable: (low + high) / 2.0
        for variable, (low, high) in extract_latent_registry(
            _registry()
        ).items()
    }
    values["public_order_stress"] = stress
    return values


def _stocks(
    *,
    population: int,
    working: int,
    dependent: int,
    displaced: int,
    reception: int,
    police: int,
    prisoners: int,
) -> dict:
    logger.info(
        "_stocks population=%s working=%s dependent=%s",
        population,
        working,
        dependent,
    )
    return {
        "population_total": population,
        "working_age_population": working,
        "dependent_population": dependent,
        "displaced_people": displaced,
        "reception_population": reception,
        "fuel_stock_days_equivalent": 60.0,
        "strategic_food_stock_days": 30.0,
        "available_police_personnel": police,
        "available_military_personnel": None,
        "prison_population": prisoners,
        "foreign_reserves_usd": None,
        "gold_reserves_tonnes": None,
    }


def _regimes(phase: str = "STABLE") -> dict[str, str]:
    logger.info("_regimes phase=%s", phase)
    return {
        "national_phase": phase,
        "security_force_regime": "COHESIVE",
        "prison_regime": "CONTROLLED",
        "organized_crime_regime": "NORMAL_MARKET",
    }


def _l2_parent() -> EngineState:
    logger.info("_l2_parent")
    return EngineState(
        node_id="TST::R1",
        day=5,
        physical_stocks=_stocks(
            population=100,
            working=60,
            dependent=40,
            displaced=4,
            reception=2,
            police=10,
            prisoners=4,
        ),
        latents=_latents(0.50),
        regimes=_regimes(),
        metadata={
            "fractal_parent_node_id": "TST",
            "fractal_level": "L2_REGION",
            "fractal_runtime_node_id": "TST::R1",
            "fractal_catalog_child_id": "TST::R1",
            "fractal_lineage_generation": 1,
            "fractal_lineage_policy_id": "FRACTAL_TOPOLOGY_GENERATION_V1",
            "fractal_initialization_weight": 1.0,
            "fractal_aggregation_rule_id": (
                "FRACTAL_PARENT_REAGGREGATION_V1"
            ),
            "fractal_child_dynamics_active": False,
        },
    )


def _l3_child(
    node_id: str,
    *,
    weight: float,
    population: int,
    working: int,
    dependent: int,
    displaced: int,
    reception: int,
    police: int,
    prisoners: int,
    stress: float,
    phase: str = "STABLE",
) -> EngineState:
    logger.info(
        "_l3_child node=%s weight=%s population=%s",
        node_id,
        weight,
        population,
    )
    return EngineState(
        node_id=node_id,
        day=5,
        physical_stocks=_stocks(
            population=population,
            working=working,
            dependent=dependent,
            displaced=displaced,
            reception=reception,
            police=police,
            prisoners=prisoners,
        ),
        latents=_latents(stress),
        regimes=_regimes(phase),
        metadata={
            "fractal_parent_node_id": "TST::R1",
            "fractal_level": "L3_METRO_OR_LOGISTICS_AREA",
            "fractal_runtime_node_id": node_id,
            "fractal_catalog_child_id": node_id,
            "fractal_lineage_generation": 1,
            "fractal_lineage_policy_id": "FRACTAL_TOPOLOGY_GENERATION_V1",
            "fractal_initialization_weight": weight,
            "fractal_aggregation_rule_id": (
                "FRACTAL_PARENT_REAGGREGATION_V1"
            ),
            "fractal_child_dynamics_active": True,
        },
    )


def _topology() -> FractalTopologyState:
    logger.info("_topology")
    common = {
        "refinement_reason": "localized_stress",
        "source_variables": ("public_order_stress",),
        "initialization_weight_policy_id": (
            "FRACTAL_CHILD_INIT_WEIGHTS_V1"
        ),
        "inherited_uncertainty_policy_id": (
            "FRACTAL_UNCERTAINTY_WIDENING_V1"
        ),
        "aggregation_rule_id": "FRACTAL_PARENT_REAGGREGATION_V1",
        "lineage_policy_id": "FRACTAL_TOPOLOGY_GENERATION_V1",
    }
    return FractalTopologyState(
        last_committed_day=5,
        nodes=(
            FractalTopologyNode(
                node_id="TST::R1",
                label="Region 1",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="expand-l2",
                initialization_weight=1.0,
                catalog_source_id="SYNTHETIC_L2",
                catalog_child_id="TST::R1",
                lineage_generation=1,
                **common,
            ),
            FractalTopologyNode(
                node_id="TST::R1::A",
                label="Area A",
                parent_node_id="TST::R1",
                level="L3_METRO_OR_LOGISTICS_AREA",
                created_day=3,
                refinement_action_id="expand-l3",
                initialization_weight=0.6,
                catalog_source_id="SYNTHETIC_L3",
                catalog_child_id="TST::R1::A",
                lineage_generation=1,
                **common,
            ),
            FractalTopologyNode(
                node_id="TST::R1::B",
                label="Area B",
                parent_node_id="TST::R1",
                level="L3_METRO_OR_LOGISTICS_AREA",
                created_day=3,
                refinement_action_id="expand-l3",
                initialization_weight=0.4,
                catalog_source_id="SYNTHETIC_L3",
                catalog_child_id="TST::R1::B",
                lineage_generation=1,
                **common,
            ),
        ),
    )


def _store(*, divergent: bool = False) -> FractalChildStateStore:
    logger.info("_store divergent=%s", divergent)
    return FractalChildStateStore(
        last_initialized_day=5,
        states=(
            _l2_parent(),
            _l3_child(
                "TST::R1::A",
                weight=0.6,
                population=60,
                working=36,
                dependent=24,
                displaced=3,
                reception=1,
                police=6,
                prisoners=2,
                stress=0.80,
            ),
            _l3_child(
                "TST::R1::B",
                weight=0.4,
                population=40,
                working=24,
                dependent=16,
                displaced=1,
                reception=1,
                police=4,
                prisoners=2,
                stress=0.20,
                phase="TENSION" if divergent else "STABLE",
            ),
        ),
    )


def _collapse_action() -> FractalRefinementActionProposal:
    logger.info("_collapse_action")
    return FractalRefinementActionProposal(
        action_id="collapse-l3-test",
        node_id="TST::R1",
        day=5,
        action="COLLAPSE",
        from_level="L3_METRO_OR_LOGISTICS_AREA",
        to_level="L2_REGION",
        refinement_pressure=0.1,
        threshold=0.38,
        persistence_required=34,
        persistence_observed=34,
        refinement_reason="localized_stress",
        component_scores=(),
        source_variables=("public_order_stress",),
        equation_id="REFINEMENT_TRIGGER_V1",
        parameter_id="FRACTAL_REFINEMENT_SYN_V1",
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
    )


def _collapse_persistence() -> FractalRefinementPersistenceState:
    logger.info("_collapse_persistence")
    return FractalRefinementPersistenceState(
        node_id="TST::R1",
        current_level="L3_METRO_OR_LOGISTICS_AREA",
        last_evaluated_day=5,
        expand_streak=0,
        collapse_streak=34,
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
                        "child_id": "TST::R1::A",
                        "label": "Area A",
                        "initialization_weight": 0.6,
                    },
                    {
                        "child_id": "TST::R1::B",
                        "label": "Area B",
                        "initialization_weight": 0.4,
                    },
                ],
            }
        },
    }


def test_l3_collapse_reaggregates_live_state_and_restores_l2() -> None:
    logger.info(
        "test_l3_collapse_reaggregates_live_state_and_restores_l2"
    )
    trace = TraceLedger()
    (
        parent_after,
        topology_after,
        store_after,
        persistence_after,
        commit,
        audit,
    ) = collapse_l3_to_l2(
        parent_state=_l2_parent(),
        action=_collapse_action(),
        persistence=_collapse_persistence(),
        topology=_topology(),
        child_store=_store(),
        reaggregation_config=load_yaml(
            ROOT / "config/engine/fractal_reaggregation_v1.yaml"
        ),
        engine_state_registry=_registry(),
        manifest=_manifest(),
        trace=trace,
    )

    assert audit.conserved is True
    assert commit.from_level == "L3_METRO_OR_LOGISTICS_AREA"
    assert commit.to_level == "L2_REGION"
    assert parent_after.physical_stocks["population_total"] == 100
    assert parent_after.physical_stocks["working_age_population"] == 60
    assert parent_after.physical_stocks["dependent_population"] == 40
    assert parent_after.physical_stocks["available_police_personnel"] == 10
    assert parent_after.latents["public_order_stress"] == pytest.approx(0.56)
    assert persistence_after.current_level == "L2_REGION"

    states = store_after.state_map()
    assert set(states) == {"TST::R1"}
    assert states["TST::R1"].state_hash() == parent_after.state_hash()

    assert topology_after.active_children("TST::R1") == ()
    l3_history = tuple(
        item
        for item in topology_after.nodes
        if item.parent_node_id == "TST::R1"
    )
    assert len(l3_history) == 2
    assert all(
        item.active is False and item.de_refinement_day == 5
        for item in l3_history
    )
    l2_parent = next(
        item for item in topology_after.nodes if item.node_id == "TST::R1"
    )
    assert l2_parent.active is True
    assert l2_parent.de_refinement_day is None

    record_types = [item["record_type"] for item in trace.records]
    assert record_types.count("fractal_lineage_closed") == 2
    assert "fractal_reaggregation_audit" in record_types
    assert "fractal_collapse_committed" in record_types


def test_l3_collapse_fails_closed_on_categorical_divergence() -> None:
    logger.info(
        "test_l3_collapse_fails_closed_on_categorical_divergence"
    )
    with pytest.raises(ValueError, match="unanimous sibling consensus"):
        collapse_l3_to_l2(
            parent_state=_l2_parent(),
            action=_collapse_action(),
            persistence=_collapse_persistence(),
            topology=_topology(),
            child_store=_store(divergent=True),
            reaggregation_config=load_yaml(
                ROOT / "config/engine/fractal_reaggregation_v1.yaml"
            ),
            engine_state_registry=_registry(),
            manifest=_manifest(),
            trace=TraceLedger(),
        )


def test_l3_collapse_then_real_rerefine_creates_generation_two() -> None:
    logger.info(
        "test_l3_collapse_then_real_rerefine_creates_generation_two"
    )
    (
        parent_after,
        topology_after,
        store_after,
        _,
        _,
        audit,
    ) = collapse_l3_to_l2(
        parent_state=_l2_parent(),
        action=_collapse_action(),
        persistence=_collapse_persistence(),
        topology=_topology(),
        child_store=_store(),
        reaggregation_config=load_yaml(
            ROOT / "config/engine/fractal_reaggregation_v1.yaml"
        ),
        engine_state_registry=_registry(),
        manifest=_manifest(),
        trace=TraceLedger(),
    )
    assert audit.conserved is True
    assert set(store_after.state_map()) == {"TST::R1"}
    assert store_after.state_map()["TST::R1"].state_hash() == (
        parent_after.state_hash()
    )

    historical = {
        item.node_id: item.to_dict()
        for item in topology_after.nodes
        if item.parent_node_id == "TST::R1"
    }

    expand = FractalRefinementActionProposal(
        action_id="expand-l3-generation-2",
        node_id="TST::R1",
        day=6,
        action="EXPAND",
        from_level="L2_REGION",
        to_level="L3_METRO_OR_LOGISTICS_AREA",
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
    expand_persistence = FractalRefinementPersistenceState(
        node_id="TST::R1",
        current_level="L2_REGION",
        last_evaluated_day=6,
        expand_streak=1,
        collapse_streak=0,
    )

    generation_two, persistence_two, commit_two = materialize_next_level(
        action=expand,
        persistence=expand_persistence,
        topology=topology_after,
        child_catalog=_l3_catalog(),
        materialization_config=load_yaml(
            ROOT / "config/engine/fractal_materialization_v1.yaml"
        ),
        manifest=_manifest(),
        trace=TraceLedger(),
    )

    active = generation_two.active_children("TST::R1")
    assert persistence_two.current_level == "L3_METRO_OR_LOGISTICS_AREA"
    assert commit_two.lineage_generation == 2
    assert {item.node_id for item in active} == {
        "TST::R1::A::g2",
        "TST::R1::B::g2",
    }
    assert {item.catalog_child_id for item in active} == {
        "TST::R1::A",
        "TST::R1::B",
    }
    assert all(item.lineage_generation == 2 for item in active)

    for node_id, before in historical.items():
        after = next(
            item for item in generation_two.nodes if item.node_id == node_id
        )
        assert after.to_dict() == before
        assert after.active is False
