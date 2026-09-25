from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.fractal_child_state import FractalChildStateStore
from iwsim.fractal_coupling import execute_parent_child_coupling
from iwsim.fractal_runtime import (
    FractalRuntimeAuthorityNode,
    FractalRuntimePlan,
)
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
        key: (low + high) / 2.0
        for key, (low, high) in extract_latent_registry(_registry()).items()
    }


def _stocks(*, population: int, military: int | None) -> dict:
    logger.info("_stocks population=%s military=%s", population, military)
    return {
        "population_total": population,
        "working_age_population": int(population * 0.6),
        "dependent_population": int(population * 0.4),
        "displaced_people": 2,
        "reception_population": 1,
        "fuel_stock_days_equivalent": 60.0,
        "strategic_food_stock_days": 30.0,
        "available_police_personnel": 10,
        "available_military_personnel": military,
        "prison_population": 3,
        "foreign_reserves_usd": None if military is None else 1000.0,
        "gold_reserves_tonnes": None if military is None else 5.0,
    }


def _regimes(phase: str = "STABLE") -> dict[str, str]:
    logger.info("_regimes phase=%s", phase)
    return {
        "national_phase": phase,
        "security_force_regime": "COHESIVE",
        "prison_regime": "CONTROLLED",
        "organized_crime_regime": "NORMAL_MARKET",
    }


def _parent() -> EngineState:
    logger.info("_parent")
    latents = _latents()
    latents["alliance_support"] = 0.77
    return EngineState(
        node_id="TST",
        day=2,
        physical_stocks=_stocks(population=100, military=900),
        latents=latents,
        regimes=_regimes(),
        metadata={},
    )


def _child(node_id: str, weight: float, stress: float, phase: str) -> EngineState:
    logger.info("_child node=%s weight=%s", node_id, weight)
    latents = _latents()
    latents["public_order_stress"] = stress
    return EngineState(
        node_id=node_id,
        day=2,
        physical_stocks=_stocks(
            population=60 if weight == 0.6 else 40,
            military=None,
        ),
        latents=latents,
        regimes=_regimes(phase),
        metadata={
            "fractal_parent_node_id": "TST",
            "fractal_initialization_weight": weight,
        },
    )


def _plan() -> FractalRuntimePlan:
    logger.info("_plan")
    config = load_yaml(ROOT / "config/engine/fractal_runtime_v1.yaml")
    authority = config["authority"]
    nodes = (
        FractalRuntimeAuthorityNode(
            runtime_node_id="TST",
            parent_node_id=None,
            level="L1_COUNTRY",
            catalog_node_id="TST",
            lineage_generation=None,
            authority_scope="NATIONAL_ONLY",
            owns_regionalizable_state=False,
            owns_national_only_state=True,
            execution_status="L1_NATIONAL_ONLY_AUTHORITY",
        ),
        *(
            FractalRuntimeAuthorityNode(
                runtime_node_id=node_id,
                parent_node_id="TST",
                level="L2_REGION",
                catalog_node_id=node_id,
                lineage_generation=1,
                authority_scope="REGIONALIZABLE",
                owns_regionalizable_state=True,
                owns_national_only_state=False,
                execution_status="L2_REGIONAL_AUTHORITY_ACTIVE_V0_29",
            )
            for node_id in ("TST::R1", "TST::R2")
        ),
    )
    return FractalRuntimePlan(
        day=1,
        policy_id=authority["policy_id"],
        config_hash="config",
        topology_hash="topology",
        child_store_hash="children",
        autonomous_child_dynamics_allowed=True,
        nodes=nodes,
        refined_parent_ids=("TST",),
        active_regional_node_ids=("TST::R1", "TST::R2"),
        inactive_lineage_node_ids=(),
        regionalizable_physical_stocks=tuple(
            authority["physical_stocks"]["regionalizable"]
        ),
        national_only_physical_stocks=tuple(
            authority["physical_stocks"]["national_only"]
        ),
        regionalizable_latents=tuple(
            authority["latents"]["regionalizable"]
        ),
        national_only_latents=tuple(
            authority["latents"]["national_only"]
        ),
        regionalizable_regimes=tuple(
            authority["regimes"]["regionalizable"]
        ),
        national_only_regimes=tuple(
            authority["regimes"]["national_only"]
        ),
    )


def test_v031_couples_child_aggregate_and_parent_context() -> None:
    logger.info("test_v031_couples_child_aggregate_and_parent_context")
    store = FractalChildStateStore(
        last_initialized_day=2,
        states=(
            _child("TST::R1", 0.6, 0.8, "STABLE"),
            _child("TST::R2", 0.4, 0.2, "STABLE"),
        ),
    )
    trace = TraceLedger()
    result = execute_parent_child_coupling(
        parent_states={"TST": _parent()},
        child_store=store,
        runtime_plan=_plan(),
        engine_state_registry=_registry(),
        reaggregation_config=load_yaml(
            ROOT / "config/engine/fractal_reaggregation_v1.yaml"
        ),
        trace=trace,
    )

    parent = result.parent_states["TST"]
    assert parent.physical_stocks["population_total"] == 100
    assert parent.physical_stocks["available_military_personnel"] == 900
    assert parent.latents["public_order_stress"] == pytest.approx(0.56)
    assert parent.latents["alliance_support"] == pytest.approx(0.77)
    assert parent.regimes["national_phase"] == "STABLE"

    for child in result.child_store.states:
        context = child.metadata["fractal_parent_context"]
        assert context["physical_stocks"]["available_military_personnel"] == 900
        assert context["latents"]["alliance_support"] == pytest.approx(0.77)
        assert "public_order_stress" not in context["latents"]
    assert trace.records[-1]["record_type"] == "fractal_parent_child_coupling"


def test_v031_divergent_regime_remains_child_owned() -> None:
    logger.info("test_v031_divergent_regime_remains_child_owned")
    parent = _parent()
    store = FractalChildStateStore(
        last_initialized_day=2,
        states=(
            _child("TST::R1", 0.6, 0.8, "TENSION"),
            _child("TST::R2", 0.4, 0.2, "STABLE"),
        ),
    )
    result = execute_parent_child_coupling(
        parent_states={"TST": parent},
        child_store=store,
        runtime_plan=_plan(),
        engine_state_registry=_registry(),
        reaggregation_config=load_yaml(
            ROOT / "config/engine/fractal_reaggregation_v1.yaml"
        ),
        trace=TraceLedger(),
    )

    assert result.parent_states["TST"].regimes["national_phase"] == "STABLE"
    assert result.audits[0].divergent_regimes == ("national_phase",)
