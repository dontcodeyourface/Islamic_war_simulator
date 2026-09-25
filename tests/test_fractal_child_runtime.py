from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.effects import DeltaProposal
from iwsim.fractal_child_runtime import (
    _validate_proposal_authority,
    execute_autonomous_l2_dynamics,
)
from iwsim.fractal_child_state import FractalChildStateStore
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from iwsim.fractal_runtime import build_fractal_runtime_plan
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


def _parent() -> EngineState:
    logger.info("_parent")
    latents = _latents()
    return EngineState(
        node_id="TST",
        day=1,
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


def _topology_node(node_id: str) -> FractalTopologyNode:
    logger.info("_topology_node node=%s", node_id)
    return FractalTopologyNode(
        node_id=node_id,
        label=node_id,
        parent_node_id="TST",
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
        active=True,
        catalog_child_id=node_id,
        lineage_generation=1,
        lineage_policy_id="FRACTAL_TOPOLOGY_GENERATION_V1",
    )


def _child(node_id: str, *, stressed: bool) -> EngineState:
    logger.info("_child node=%s stressed=%s", node_id, stressed)
    latents = _latents()
    baseline = dict(latents)
    if stressed:
        latents["communal_fear"] = 0.90
        latents["public_order_stress"] = 0.90
        latents["polarization"] = 0.80
        latents["violent_islamist_pressure"] = 0.70
        latents["violent_ultranationalist_pressure"] = 0.60
        latents["government_legitimacy"] = 0.30
        latents["social_cohesion"] = 0.30
        latents["police_effective_capacity"] = 0.40
        latents["security_chain_cohesion"] = 0.40
    return EngineState(
        node_id=node_id,
        day=1,
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
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={
            "initial_latents": baseline,
            "fractal_parent_node_id": "TST",
            "fractal_level": "L2_REGION",
            "fractal_runtime_node_id": node_id,
            "fractal_catalog_child_id": node_id,
            "fractal_lineage_generation": 1,
        },
    )


def _runtime():
    logger.info("_runtime")
    registry = _registry()
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(
            _topology_node("TST::R1"),
            _topology_node("TST::R2"),
        ),
    )
    store = FractalChildStateStore(
        last_initialized_day=1,
        states=(
            _child("TST::R1", stressed=True),
            _child("TST::R2", stressed=False),
        ),
    )
    runtime_config = load_yaml(
        ROOT / "config/engine/fractal_runtime_v1.yaml"
    )
    plan = build_fractal_runtime_plan(
        day=1,
        parent_states={"TST": _parent()},
        topology=topology,
        child_store=store,
        runtime_config=runtime_config,
        engine_state_registry=registry,
    )
    return registry, store, plan


def test_v026_l2_recovery_resolves_without_double_clock_advance() -> None:
    logger.info(
        "test_v026_l2_recovery_resolves_without_double_clock_advance"
    )
    registry, store, plan = _runtime()
    trace = TraceLedger()
    result = execute_autonomous_l2_dynamics(
        child_store=store,
        runtime_plan=plan,
        engine_state_registry=registry,
        parameter_registry=load_yaml(
            ROOT / "config/engine/parameter_registry_v1.yaml"
        ),
        profile="synthetic_smoke_v1",
        trace=trace,
        enable_recovery=True,
        recovery_config=load_yaml(
            ROOT / "config/engine/recovery_v1.yaml"
        ),
    )

    assert result.executed_node_ids == ("TST::R1", "TST::R2")
    assert result.enabled_modules == ("bounded_recovery",)
    assert result.proposals
    assert result.resolutions

    before = store.state_map()["TST::R1"]
    after = result.store.state_map()["TST::R1"]
    assert after.day == before.day == 1
    assert after.latents["communal_fear"] < before.latents["communal_fear"]
    assert after.latents["public_order_stress"] < (
        before.latents["public_order_stress"]
    )
    assert after.metadata["fractal_child_dynamics_active"] is True
    assert after.metadata["fractal_child_dynamics_applied_from_day"] == 1
    assert after.metadata["fractal_child_dynamics_applied_to_day"] == 2
    assert trace.records[-1]["record_type"] == (
        "fractal_child_dynamics_committed"
    )


def test_v026_safe_modules_only_target_active_l2() -> None:
    logger.info("test_v026_safe_modules_only_target_active_l2")
    registry, store, plan = _runtime()
    result = execute_autonomous_l2_dynamics(
        child_store=store,
        runtime_plan=plan,
        engine_state_registry=registry,
        parameter_registry=load_yaml(
            ROOT / "config/engine/parameter_registry_v1.yaml"
        ),
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
        enable_recovery=True,
        recovery_config=load_yaml(
            ROOT / "config/engine/recovery_v1.yaml"
        ),
        enable_extremist_network_dynamics=True,
        extremist_network_config=load_yaml(
            ROOT / "config/engine/extremist_network_dynamics_v1.yaml"
        ),
        enable_reciprocal_radicalization=True,
        reciprocal_radicalization_config=load_yaml(
            ROOT / "config/engine/reciprocal_radicalization_v1.yaml"
        ),
        enable_security_chain_dynamics=True,
        security_chain_config=load_yaml(
            ROOT / "config/engine/security_chain_dynamics_v1.yaml"
        ),
    )

    assert result.enabled_modules == (
        "bounded_recovery",
        "extremist_network_dynamics",
        "reciprocal_radicalization",
        "security_chain_dynamics",
    )
    assert set(item.target_node for item in result.proposals) <= {
        "TST::R1",
        "TST::R2",
    }
    assert set(item.variable for item in result.proposals) <= set(
        plan.regionalizable_latents
    )
    assert set(item.target_node for item in result.resolutions) <= {
        "TST::R1",
        "TST::R2",
    }
    assert all(
        item.runtime_level == "L2_REGION"
        for item in result.resolutions
    )
    assert all(
        item.runtime_parent_node_id == "TST"
        for item in result.resolutions
    )
    assert all(
        item.runtime_authority_scope == "REGIONALIZABLE"
        for item in result.resolutions
    )
    assert all(
        item.runtime_plan_hash == plan.plan_hash()
        for item in result.resolutions
    )
    assert all(
        item.runtime_policy_id == plan.policy_id
        for item in result.resolutions
    )


def test_v026_rejects_national_only_child_mutation() -> None:
    logger.info("test_v026_rejects_national_only_child_mutation")
    _, _, plan = _runtime()
    proposal = DeltaProposal(
        proposal_id="bad-l2-national-only",
        event_id="test-source",
        event_type="TEST",
        target_node="TST::R1",
        variable="alliance_support",
        owner_module="external_system",
        value_before=0.5,
        raw_delta=0.1,
        proposed_unbounded_value=0.6,
        equation_id="TEST_V1",
        parameter_ids=("TEST",),
        apply_status="PROPOSED_NOT_APPLIED",
        dry_run=True,
    )
    with pytest.raises(
        ValueError,
        match="national-only latent alliance_support",
    ):
        _validate_proposal_authority(
            proposals=(proposal,),
            runtime_plan=plan,
        )


def test_v027_child_runtime_failure_is_trace_and_state_atomic() -> None:
    logger.info(
        "test_v027_child_runtime_failure_is_trace_and_state_atomic"
    )
    registry, store, plan = _runtime()
    before = store.to_dict()
    trace = TraceLedger()
    broken = replace(
        plan,
        regionalizable_latents=tuple(
            item
            for item in plan.regionalizable_latents
            if item != "communal_fear"
        ),
        national_only_latents=tuple(
            sorted((*plan.national_only_latents, "communal_fear"))
        ),
    )

    with pytest.raises(
        ValueError,
        match="national-only latent communal_fear",
    ):
        execute_autonomous_l2_dynamics(
            child_store=store,
            runtime_plan=broken,
            engine_state_registry=registry,
            parameter_registry=load_yaml(
                ROOT / "config/engine/parameter_registry_v1.yaml"
            ),
            profile="synthetic_smoke_v1",
            trace=trace,
            enable_recovery=True,
            recovery_config=load_yaml(
                ROOT / "config/engine/recovery_v1.yaml"
            ),
        )

    assert store.to_dict() == before
    assert trace.records == []
