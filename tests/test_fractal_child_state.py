from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.fractal_child_state import (
    empty_fractal_child_state_store,
    initialize_fractal_child_states,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    config = load_yaml(ROOT / "config/engine/fractal_child_state_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    parent = EngineState(
        node_id="TST",
        day=1,
        physical_stocks={
            "population_total": 11,
            "working_age_population": 7,
            "dependent_population": 4,
            "displaced_people": 3,
            "reception_population": 1,
            "fuel_stock_days_equivalent": 90.0,
            "strategic_food_stock_days": 30.0,
            "available_police_personnel": 5,
            "available_military_personnel": 100,
            "prison_population": 2,
            "foreign_reserves_usd": 1000.0,
            "gold_reserves_tonnes": 10.0,
        },
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={
            "country_name": "Testland",
            "initial_latents": dict(latents),
        },
    )
    parent.validate(latent_registry)
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(
            FractalTopologyNode(
                node_id="TST::R1",
                label="Region 1",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="refine-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.5,
                initialization_weight_policy_id=(
                    "FRACTAL_CHILD_INIT_WEIGHTS_V1"
                ),
                inherited_uncertainty_policy_id=(
                    "FRACTAL_UNCERTAINTY_WIDENING_V1"
                ),
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
            FractalTopologyNode(
                node_id="TST::R2",
                label="Region 2",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="refine-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.3,
                initialization_weight_policy_id=(
                    "FRACTAL_CHILD_INIT_WEIGHTS_V1"
                ),
                inherited_uncertainty_policy_id=(
                    "FRACTAL_UNCERTAINTY_WIDENING_V1"
                ),
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
            FractalTopologyNode(
                node_id="TST::R3",
                label="Region 3",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="refine-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.2,
                initialization_weight_policy_id=(
                    "FRACTAL_CHILD_INIT_WEIGHTS_V1"
                ),
                inherited_uncertainty_policy_id=(
                    "FRACTAL_UNCERTAINTY_WIDENING_V1"
                ),
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
        ),
    )
    return parent, topology, registry, config


def test_child_initialization_conserves_additive_integer_stocks_exactly() -> None:
    logger.info(
        "test_child_initialization_conserves_additive_integer_stocks_exactly"
    )
    parent, topology, registry, config = _fixture()
    trace = TraceLedger()

    result = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology,
        child_store=empty_fractal_child_state_store(0),
        initialization_config=config,
        engine_state_registry=registry,
        trace=trace,
    )

    children = result.store.state_map()
    assert set(children) == {"TST::R1", "TST::R2", "TST::R3"}
    assert result.store.last_initialized_day == 1

    assert [
        children["TST::R1"].physical_stocks["population_total"],
        children["TST::R2"].physical_stocks["population_total"],
        children["TST::R3"].physical_stocks["population_total"],
    ] == [6, 3, 2]
    assert [
        children["TST::R1"].physical_stocks["available_police_personnel"],
        children["TST::R2"].physical_stocks["available_police_personnel"],
        children["TST::R3"].physical_stocks["available_police_personnel"],
    ] == [3, 1, 1]

    for variable in (
        "population_total",
        "working_age_population",
        "dependent_population",
        "displaced_people",
        "reception_population",
        "available_police_personnel",
        "prison_population",
    ):
        assert sum(
            int(child.physical_stocks[variable])
            for child in children.values()
        ) == parent.physical_stocks[variable]

    assert len(result.conservation_audits) == 1
    assert result.conservation_audits[0].conserved is True


def test_intensive_and_parent_only_physical_stock_policies_are_distinct() -> None:
    logger.info(
        "test_intensive_and_parent_only_physical_stock_policies_are_distinct"
    )
    parent, topology, registry, config = _fixture()

    result = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology,
        child_store=empty_fractal_child_state_store(0),
        initialization_config=config,
        engine_state_registry=registry,
        trace=TraceLedger(),
    )

    for child in result.store.states:
        assert child.physical_stocks[
            "fuel_stock_days_equivalent"
        ] == pytest.approx(90.0)
        assert child.physical_stocks[
            "strategic_food_stock_days"
        ] == pytest.approx(30.0)
        assert child.physical_stocks["available_military_personnel"] is None
        assert child.physical_stocks["foreign_reserves_usd"] is None
        assert child.physical_stocks["gold_reserves_tonnes"] is None


def test_latents_regimes_and_lineage_metadata_inherit_without_variation() -> None:
    logger.info(
        "test_latents_regimes_and_lineage_metadata_inherit_without_variation"
    )
    parent, topology, registry, config = _fixture()

    result = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology,
        child_store=empty_fractal_child_state_store(0),
        initialization_config=config,
        engine_state_registry=registry,
        trace=TraceLedger(),
    )

    for child in result.store.states:
        assert child.latents == parent.latents
        assert child.regimes == parent.regimes
        assert child.metadata["fractal_parent_node_id"] == "TST"
        assert child.metadata["fractal_level"] == "L2_REGION"
        assert child.metadata["fractal_child_dynamics_active"] is False
        assert child.metadata["fractal_parent_state_hash_at_initialization"] == (
            parent.state_hash()
        )
        assert child.metadata["fractal_latent_policy_id"] == (
            "FRACTAL_LATENT_INHERIT_V1"
        )
        assert child.metadata["fractal_inherited_uncertainty_policy_id"] == (
            "FRACTAL_UNCERTAINTY_WIDENING_V1"
        )


def test_null_additive_stock_propagates_as_null_without_false_zero() -> None:
    logger.info(
        "test_null_additive_stock_propagates_as_null_without_false_zero"
    )
    parent, topology, registry, config = _fixture()
    parent.physical_stocks["dependent_population"] = None

    result = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology,
        child_store=empty_fractal_child_state_store(0),
        initialization_config=config,
        engine_state_registry=registry,
        trace=TraceLedger(),
    )

    assert all(
        child.physical_stocks["dependent_population"] is None
        for child in result.store.states
    )
    audit = result.conservation_audits[0].to_dict()
    assert audit["additive_parent_values"]["dependent_population"] is None
    assert audit["additive_child_sums"]["dependent_population"] is None


def test_non_integer_additive_person_stock_fails_closed() -> None:
    logger.info("test_non_integer_additive_person_stock_fails_closed")
    parent, topology, registry, config = _fixture()
    parent.physical_stocks["available_police_personnel"] = 5.5

    with pytest.raises(ValueError, match="is not integer-valued"):
        initialize_fractal_child_states(
            parent_states={"TST": parent},
            topology=topology,
            child_store=empty_fractal_child_state_store(0),
            initialization_config=config,
            engine_state_registry=registry,
            trace=TraceLedger(),
        )


def test_physical_stock_policy_must_cover_registry_exactly_once() -> None:
    logger.info("test_physical_stock_policy_must_cover_registry_exactly_once")
    parent, topology, registry, config = _fixture()
    broken = copy.deepcopy(config)
    broken["physical_stock_policies"]["parent_only_null"].remove(
        "gold_reserves_tonnes"
    )

    with pytest.raises(ValueError, match="Physical stock policy coverage mismatch"):
        initialize_fractal_child_states(
            parent_states={"TST": parent},
            topology=topology,
            child_store=empty_fractal_child_state_store(0),
            initialization_config=broken,
            engine_state_registry=registry,
            trace=TraceLedger(),
        )


def test_existing_child_states_advance_clock_without_dynamics() -> None:
    logger.info("test_existing_child_states_advance_clock_without_dynamics")
    parent, topology, registry, config = _fixture()
    first = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology,
        child_store=empty_fractal_child_state_store(0),
        initialization_config=config,
        engine_state_registry=registry,
        trace=TraceLedger(),
    )

    parent.day = 2
    topology_day_two = FractalTopologyState(
        last_committed_day=2,
        nodes=topology.nodes,
    )
    second = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology_day_two,
        child_store=first.store,
        initialization_config=config,
        engine_state_registry=registry,
        trace=TraceLedger(),
    )

    assert second.initialization_records == ()
    assert second.conservation_audits == ()
    assert second.store.last_initialized_day == 2
    for before, after in zip(
        sorted(first.store.states, key=lambda item: item.node_id),
        sorted(second.store.states, key=lambda item: item.node_id),
    ):
        assert after.day == 2
        assert after.physical_stocks == before.physical_stocks
        assert after.latents == before.latents
        assert after.regimes == before.regimes
        assert after.metadata == before.metadata
