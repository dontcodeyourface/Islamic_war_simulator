from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.fractal_child_state import (
    FractalChildStateStore,
    empty_fractal_child_state_store,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from iwsim.fractal_runtime import (
    assert_beginning_of_day_runtime_supported,
    build_fractal_runtime_plan,
)
from iwsim.state import EngineState, extract_latent_registry

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _registry() -> dict:
    logger.info("_registry")
    return load_yaml(ROOT / "config/engine/engine_state_v1.yaml")


def _runtime_config() -> dict:
    logger.info("_runtime_config")
    return load_yaml(ROOT / "config/engine/fractal_runtime_v1.yaml")


def _latents(registry: dict) -> dict[str, float]:
    logger.info("_latents")
    return {
        variable: (low + high) / 2.0
        for variable, (low, high) in extract_latent_registry(
            registry
        ).items()
    }


def _parent_state(
    *,
    node_id: str = "TST",
    day: int = 1,
) -> EngineState:
    logger.info("_parent_state node=%s day=%s", node_id, day)
    registry = _registry()
    return EngineState(
        node_id=node_id,
        day=day,
        physical_stocks={
            "population_total": 1000,
            "working_age_population": 600,
            "dependent_population": 400,
            "displaced_people": 10,
            "reception_population": 5,
            "fuel_stock_days_equivalent": 60.0,
            "strategic_food_stock_days": 30.0,
            "available_police_personnel": 100,
            "available_military_personnel": 5000,
            "prison_population": 20,
            "foreign_reserves_usd": 1_000_000.0,
            "gold_reserves_tonnes": 5.0,
        },
        latents=_latents(registry),
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={"country_name": "Testland"},
    )


def _topology_node(
    *,
    node_id: str,
    parent_node_id: str = "TST",
    active: bool = True,
    catalog_child_id: str | None = None,
    generation: int = 1,
    de_refinement_day: int | None = None,
) -> FractalTopologyNode:
    logger.info(
        "_topology_node node=%s parent=%s active=%s generation=%s",
        node_id,
        parent_node_id,
        active,
        generation,
    )
    return FractalTopologyNode(
        node_id=node_id,
        label=node_id,
        parent_node_id=parent_node_id,
        level="L2_REGION",
        created_day=1,
        refinement_action_id="refine-test",
        refinement_reason="test",
        source_variables=("public_order_stress",),
        initialization_weight=0.5,
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
        catalog_source_id="SYNTHETIC_TEST",
        de_refinement_day=de_refinement_day,
        active=active,
        catalog_child_id=catalog_child_id,
        lineage_generation=generation,
        lineage_policy_id="FRACTAL_TOPOLOGY_GENERATION_V1",
    )


def _child_state(
    *,
    node_id: str,
    parent_node_id: str = "TST",
    catalog_child_id: str | None = None,
    generation: int = 1,
    day: int = 1,
) -> EngineState:
    logger.info(
        "_child_state node=%s parent=%s generation=%s",
        node_id,
        parent_node_id,
        generation,
    )
    registry = _registry()
    return EngineState(
        node_id=node_id,
        day=day,
        physical_stocks={
            "population_total": 500,
            "working_age_population": 300,
            "dependent_population": 200,
            "displaced_people": 5,
            "reception_population": 2,
            "fuel_stock_days_equivalent": 60.0,
            "strategic_food_stock_days": 30.0,
            "available_police_personnel": 50,
            "available_military_personnel": None,
            "prison_population": 10,
            "foreign_reserves_usd": None,
            "gold_reserves_tonnes": None,
        },
        latents=_latents(registry),
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={
            "fractal_parent_node_id": parent_node_id,
            "fractal_level": "L2_REGION",
            "fractal_runtime_node_id": node_id,
            "fractal_catalog_child_id": (
                catalog_child_id
                if catalog_child_id is not None
                else node_id
            ),
            "fractal_lineage_generation": generation,
        },
    )


def test_coarse_plan_keeps_full_l1_authority() -> None:
    logger.info("test_coarse_plan_keeps_full_l1_authority")
    registry = _registry()
    plan = build_fractal_runtime_plan(
        day=1,
        parent_states={"TST": _parent_state()},
        topology=FractalTopologyState(
            last_committed_day=1,
            nodes=(),
        ),
        child_store=empty_fractal_child_state_store(1),
        runtime_config=_runtime_config(),
        engine_state_registry=registry,
    )

    assert plan.refined_parent_ids == ()
    assert plan.active_regional_node_ids == ()
    assert len(plan.nodes) == 1
    authority = plan.nodes[0]
    assert authority.runtime_node_id == "TST"
    assert authority.level == "L1_COUNTRY"
    assert authority.authority_scope == "FULL"
    assert authority.owns_regionalizable_state is True
    assert authority.owns_national_only_state is True
    assert authority.execution_status == "L1_FULL_AUTHORITY"


def test_refined_plan_moves_regionalizable_authority_to_active_l2() -> None:
    logger.info(
        "test_refined_plan_moves_regionalizable_authority_to_active_l2"
    )
    registry = _registry()
    active_one = _topology_node(node_id="TST::R1")
    active_two = _topology_node(node_id="TST::R2")
    inactive = _topology_node(
        node_id="TST::OLD",
        active=False,
        de_refinement_day=1,
    )
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(active_one, active_two, inactive),
    )
    child_store = FractalChildStateStore(
        last_initialized_day=1,
        states=(
            _child_state(node_id="TST::R1"),
            _child_state(node_id="TST::R2"),
        ),
    )

    plan = build_fractal_runtime_plan(
        day=1,
        parent_states={"TST": _parent_state()},
        topology=topology,
        child_store=child_store,
        runtime_config=_runtime_config(),
        engine_state_registry=registry,
    )

    assert plan.refined_parent_ids == ("TST",)
    assert plan.active_regional_node_ids == (
        "TST::R1",
        "TST::R2",
    )
    assert plan.inactive_lineage_node_ids == ("TST::OLD",)

    by_id = {
        item.runtime_node_id: item
        for item in plan.nodes
    }
    parent = by_id["TST"]
    assert parent.owns_regionalizable_state is False
    assert parent.owns_national_only_state is True
    assert parent.authority_scope == "NATIONAL_ONLY"

    for node_id in ("TST::R1", "TST::R2"):
        child = by_id[node_id]
        assert child.owns_regionalizable_state is True
        assert child.owns_national_only_state is False
        assert child.authority_scope == "REGIONALIZABLE"
        assert child.execution_status == "L2_REGIONAL_AUTHORITY_ACTIVE_V0_29"

    assert "TST::OLD" not in by_id


def test_runtime_plan_hash_is_deterministic() -> None:
    logger.info("test_runtime_plan_hash_is_deterministic")
    registry = _registry()
    kwargs = {
        "day": 1,
        "parent_states": {"TST": _parent_state()},
        "topology": FractalTopologyState(
            last_committed_day=1,
            nodes=(),
        ),
        "child_store": empty_fractal_child_state_store(1),
        "runtime_config": _runtime_config(),
        "engine_state_registry": registry,
    }
    first = build_fractal_runtime_plan(**kwargs)
    replay = build_fractal_runtime_plan(**kwargs)

    assert first.to_dict() == replay.to_dict()
    assert first.plan_hash() == replay.plan_hash()


def test_runtime_authority_policy_must_cover_registry_exactly() -> None:
    logger.info(
        "test_runtime_authority_policy_must_cover_registry_exactly"
    )
    registry = _registry()
    broken = copy.deepcopy(_runtime_config())
    broken["authority"]["latents"]["regionalizable"].remove(
        "external_conflict_pressure"
    )

    with pytest.raises(
        ValueError,
        match="latents authority coverage mismatch",
    ):
        build_fractal_runtime_plan(
            day=1,
            parent_states={"TST": _parent_state()},
            topology=FractalTopologyState(
                last_committed_day=1,
                nodes=(),
            ),
            child_store=empty_fractal_child_state_store(1),
            runtime_config=broken,
            engine_state_registry=registry,
        )


def test_active_topology_requires_exact_child_state_coverage() -> None:
    logger.info(
        "test_active_topology_requires_exact_child_state_coverage"
    )
    registry = _registry()
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_topology_node(node_id="TST::R1"),),
    )

    with pytest.raises(
        ValueError,
        match="active child-state coverage mismatch",
    ):
        build_fractal_runtime_plan(
            day=1,
            parent_states={"TST": _parent_state()},
            topology=topology,
            child_store=empty_fractal_child_state_store(1),
            runtime_config=_runtime_config(),
            engine_state_registry=registry,
        )


def test_inactive_lineage_state_is_forbidden() -> None:
    logger.info("test_inactive_lineage_state_is_forbidden")
    registry = _registry()
    inactive = _topology_node(
        node_id="TST::R1",
        active=False,
        de_refinement_day=1,
    )
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(inactive,),
    )
    store = FractalChildStateStore(
        last_initialized_day=1,
        states=(_child_state(node_id="TST::R1"),),
    )

    with pytest.raises(
        ValueError,
        match="active child-state coverage mismatch",
    ):
        build_fractal_runtime_plan(
            day=1,
            parent_states={"TST": _parent_state()},
            topology=topology,
            child_store=store,
            runtime_config=_runtime_config(),
            engine_state_registry=registry,
        )


def test_v026_accepts_beginning_of_day_active_l2_authority() -> None:
    logger.info(
        "test_v026_accepts_beginning_of_day_active_l2_authority"
    )
    registry = _registry()
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_topology_node(node_id="TST::R1"),),
    )
    store = FractalChildStateStore(
        last_initialized_day=1,
        states=(_child_state(node_id="TST::R1"),),
    )
    config = _runtime_config()
    plan = build_fractal_runtime_plan(
        day=1,
        parent_states={"TST": _parent_state()},
        topology=topology,
        child_store=store,
        runtime_config=config,
        engine_state_registry=registry,
    )

    assert plan.autonomous_child_dynamics_allowed is True
    assert_beginning_of_day_runtime_supported(
        plan=plan,
        runtime_config=config,
    )


def test_child_parent_metadata_mismatch_fails_closed() -> None:
    logger.info(
        "test_child_parent_metadata_mismatch_fails_closed"
    )
    registry = _registry()
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_topology_node(node_id="TST::R1"),),
    )
    store = FractalChildStateStore(
        last_initialized_day=1,
        states=(
            _child_state(
                node_id="TST::R1",
                parent_node_id="WRONG",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="parent metadata mismatch",
    ):
        build_fractal_runtime_plan(
            day=1,
            parent_states={"TST": _parent_state()},
            topology=topology,
            child_store=store,
            runtime_config=_runtime_config(),
            engine_state_registry=registry,
        )
