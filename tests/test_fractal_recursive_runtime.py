from __future__ import annotations

import logging
from pathlib import Path

from iwsim.config import load_yaml
from iwsim.fractal_child_runtime import execute_autonomous_l2_dynamics
from iwsim.fractal_uncertainty import apply_fractal_uncertainty
from iwsim.fractal_child_state import (
    FractalChildStateStore,
    initialize_fractal_child_states,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from iwsim.fractal_runtime import build_fractal_runtime_plan
from iwsim.rng import RNGManager
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _registry() -> dict:
    logger.info("_registry")
    return load_yaml(ROOT / "config/engine/engine_state_v1.yaml")


def _latents() -> dict[str, float]:
    logger.info("_latents")
    return {
        variable: (low + high) / 2.0
        for variable, (low, high) in extract_latent_registry(
            _registry()
        ).items()
    }


def _stocks(
    *,
    population: int,
    working: int,
    dependent: int,
    police: int,
    prisoners: int,
    parent_only: bool,
) -> dict:
    logger.info(
        "_stocks population=%s parent_only=%s",
        population,
        parent_only,
    )
    return {
        "population_total": population,
        "working_age_population": working,
        "dependent_population": dependent,
        "displaced_people": 4,
        "reception_population": 2,
        "fuel_stock_days_equivalent": 60.0,
        "strategic_food_stock_days": 30.0,
        "available_police_personnel": police,
        "available_military_personnel": 5000 if parent_only else None,
        "prison_population": prisoners,
        "foreign_reserves_usd": 1_000_000.0 if parent_only else None,
        "gold_reserves_tonnes": 5.0 if parent_only else None,
    }


def _regimes() -> dict[str, str]:
    logger.info("_regimes")
    return {
        "national_phase": "STABLE",
        "security_force_regime": "COHESIVE",
        "prison_regime": "CONTROLLED",
        "organized_crime_regime": "NORMAL_MARKET",
    }


def _l1(day: int = 2) -> EngineState:
    logger.info("_l1 day=%s", day)
    return EngineState(
        node_id="TST",
        day=day,
        physical_stocks=_stocks(
            population=1000,
            working=600,
            dependent=400,
            police=100,
            prisoners=20,
            parent_only=True,
        ),
        latents=_latents(),
        regimes=_regimes(),
        metadata={"country_name": "Testland"},
    )


def _l2_state(day: int = 1) -> EngineState:
    logger.info("_l2_state day=%s", day)
    return EngineState(
        node_id="TST::R1",
        day=day,
        physical_stocks=_stocks(
            population=600,
            working=360,
            dependent=240,
            police=60,
            prisoners=12,
            parent_only=False,
        ),
        latents=_latents(),
        regimes=_regimes(),
        metadata={
            "fractal_parent_node_id": "TST",
            "fractal_level": "L2_REGION",
            "fractal_runtime_node_id": "TST::R1",
            "fractal_catalog_child_id": "TST::R1",
            "fractal_lineage_generation": 1,
        },
    )


def _node(
    *,
    node_id: str,
    parent_node_id: str,
    level: str,
    weight: float,
    created_day: int,
    catalog_child_id: str,
) -> FractalTopologyNode:
    logger.info("_node node=%s level=%s", node_id, level)
    return FractalTopologyNode(
        node_id=node_id,
        label=node_id,
        parent_node_id=parent_node_id,
        level=level,
        created_day=created_day,
        refinement_action_id=f"expand-{parent_node_id}",
        refinement_reason="localized_stress",
        source_variables=("public_order_stress",),
        initialization_weight=weight,
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
        catalog_source_id="SYNTHETIC_RECURSIVE_RUNTIME",
        catalog_child_id=catalog_child_id,
        lineage_generation=1,
        lineage_policy_id="FRACTAL_TOPOLOGY_GENERATION_V1",
    )


def _topology() -> FractalTopologyState:
    logger.info("_topology")
    return FractalTopologyState(
        last_committed_day=2,
        nodes=(
            _node(
                node_id="TST::R1",
                parent_node_id="TST",
                level="L2_REGION",
                weight=1.0,
                created_day=1,
                catalog_child_id="TST::R1",
            ),
            _node(
                node_id="TST::R1::METRO_A",
                parent_node_id="TST::R1",
                level="L3_METRO_OR_LOGISTICS_AREA",
                weight=0.6,
                created_day=2,
                catalog_child_id="TST::R1::METRO_A",
            ),
            _node(
                node_id="TST::R1::LOGISTICS_B",
                parent_node_id="TST::R1",
                level="L3_METRO_OR_LOGISTICS_AREA",
                weight=0.4,
                created_day=2,
                catalog_child_id="TST::R1::LOGISTICS_B",
            ),
        ),
    )


def _initialized_store() -> FractalChildStateStore:
    logger.info("_initialized_store")
    result = initialize_fractal_child_states(
        parent_states={"TST": _l1(day=2)},
        topology=_topology(),
        child_store=FractalChildStateStore(
            last_initialized_day=1,
            states=(_l2_state(day=1),),
        ),
        initialization_config=load_yaml(
            ROOT / "config/engine/fractal_child_state_v1.yaml"
        ),
        engine_state_registry=_registry(),
        trace=TraceLedger(),
    )
    return result.store


def _plan(store: FractalChildStateStore):
    logger.info("_plan")
    return build_fractal_runtime_plan(
        day=2,
        parent_states={"TST": _l1(day=2)},
        topology=_topology(),
        child_store=store,
        runtime_config=load_yaml(
            ROOT / "config/engine/fractal_runtime_v1.yaml"
        ),
        engine_state_registry=_registry(),
    )


def test_recursive_initialization_uses_live_l2_parent_state() -> None:
    logger.info(
        "test_recursive_initialization_uses_live_l2_parent_state"
    )
    store = _initialized_store()
    states = store.state_map()

    assert set(states) == {
        "TST::R1",
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    }
    assert states["TST::R1"].day == 2
    assert (
        states["TST::R1::METRO_A"].metadata["fractal_level"]
        == "L3_METRO_OR_LOGISTICS_AREA"
    )
    assert (
        states["TST::R1::LOGISTICS_B"].metadata[
            "fractal_parent_node_id"
        ]
        == "TST::R1"
    )
    assert (
        states["TST::R1::METRO_A"].physical_stocks["population_total"]
        + states["TST::R1::LOGISTICS_B"].physical_stocks[
            "population_total"
        ]
        == states["TST::R1"].physical_stocks["population_total"]
    )


def test_runtime_authority_moves_from_refined_l2_to_l3_leaves() -> None:
    logger.info(
        "test_runtime_authority_moves_from_refined_l2_to_l3_leaves"
    )
    plan = _plan(_initialized_store())
    by_id = {item.runtime_node_id: item for item in plan.nodes}

    assert plan.active_regional_node_ids == (
        "TST::R1::LOGISTICS_B",
        "TST::R1::METRO_A",
    )
    assert by_id["TST"].authority_scope == "NATIONAL_ONLY"
    assert by_id["TST::R1"].authority_scope == "PARENT_CONTEXT"
    assert by_id["TST::R1"].owns_regionalizable_state is False
    assert by_id["TST::R1"].owns_national_only_state is False

    for node_id in plan.active_regional_node_ids:
        leaf = by_id[node_id]
        assert leaf.level == "L3_METRO_OR_LOGISTICS_AREA"
        assert leaf.authority_scope == "REGIONALIZABLE"
        assert leaf.owns_regionalizable_state is True
        assert leaf.owns_national_only_state is False
        assert (
            leaf.execution_status
            == "L3_REGIONAL_AUTHORITY_ACTIVE_V0_34B"
        )


def test_autonomous_execution_preserves_refined_l2_context_state() -> None:
    logger.info(
        "test_autonomous_execution_preserves_refined_l2_context_state"
    )
    store = _initialized_store()
    parent_before = store.state_map()["TST::R1"].to_dict()
    plan = _plan(store)

    result = execute_autonomous_l2_dynamics(
        child_store=store,
        runtime_plan=plan,
        engine_state_registry=_registry(),
        parameter_registry=load_yaml(
            ROOT / "config/engine/parameter_registry_v1.yaml"
        ),
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )

    states = result.store.state_map()
    assert states["TST::R1"].to_dict() == parent_before
    assert result.executed_node_ids == (
        "TST::R1::LOGISTICS_B",
        "TST::R1::METRO_A",
    )
    assert states["TST::R1"].metadata.get(
        "fractal_child_dynamics_active"
    ) is not True
    assert all(
        states[node_id].metadata["fractal_child_dynamics_active"] is True
        for node_id in result.executed_node_ids
    )



def test_same_day_recursive_augmentation_does_not_advance_parent_twice() -> None:
    logger.info(
        "test_same_day_recursive_augmentation_does_not_advance_parent_twice"
    )
    parent = _l2_state(day=2)
    result = initialize_fractal_child_states(
        parent_states={"TST": _l1(day=2)},
        topology=_topology(),
        child_store=FractalChildStateStore(
            last_initialized_day=2,
            states=(parent,),
        ),
        initialization_config=load_yaml(
            ROOT / "config/engine/fractal_child_state_v1.yaml"
        ),
        engine_state_registry=_registry(),
        trace=TraceLedger(),
    )

    states = result.store.state_map()
    assert states["TST::R1"].day == 2
    assert states["TST::R1"].state_hash() == parent.state_hash()
    assert {
        item.parent_node_id
        for item in result.initialization_records
    } == {"TST::R1"}
    assert {
        item.child_node_id
        for item in result.initialization_records
    } == {
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    }
    assert result.conservation_audits[0].conserved is True


def test_recursive_uncertainty_uses_l2_parent_from_child_store() -> None:
    logger.info(
        "test_recursive_uncertainty_uses_l2_parent_from_child_store"
    )
    initialized = initialize_fractal_child_states(
        parent_states={"TST": _l1(day=2)},
        topology=_topology(),
        child_store=FractalChildStateStore(
            last_initialized_day=2,
            states=(_l2_state(day=2),),
        ),
        initialization_config=load_yaml(
            ROOT / "config/engine/fractal_child_state_v1.yaml"
        ),
        engine_state_registry=_registry(),
        trace=TraceLedger(),
    )
    before = {
        node_id: state.to_dict()
        for node_id, state in initialized.store.state_map().items()
    }

    result = apply_fractal_uncertainty(
        parent_states={"TST": _l1(day=2)},
        topology=_topology(),
        child_store=initialized.store,
        new_child_ids=tuple(
            item.child_node_id
            for item in initialized.initialization_records
        ),
        uncertainty_config=load_yaml(
            ROOT / "config/engine/fractal_uncertainty_v1.yaml"
        ),
        engine_state_registry=_registry(),
        parameter_registry=load_yaml(
            ROOT / "config/engine/parameter_registry_v1.yaml"
        ),
        profile="synthetic_smoke_v1",
        rng=RNGManager(3434),
        trace=TraceLedger(),
    )

    states = result.store.state_map()
    assert states["TST::R1"].to_dict() == before["TST::R1"]
    assert {
        item.parent_node_id for item in result.records
    } == {"TST::R1"}
    assert {
        item.parent_node_id for item in result.audits
    } == {"TST::R1"}
    assert all(item.preserved for item in result.audits)

    for node_id in (
        "TST::R1::METRO_A",
        "TST::R1::LOGISTICS_B",
    ):
        assert (
            states[node_id].physical_stocks
            == before[node_id]["physical_stocks"]
        )
        assert states[node_id].regimes == before[node_id]["regimes"]
        assert (
            states[node_id].metadata[
                "fractal_uncertainty_policy_id"
            ]
            == "FRACTAL_SPATIAL_LOCAL_VARIATION_V2"
        )
