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


def _latents(stress: float) -> dict[str, float]:
    logger.info("_latents stress=%s", stress)
    values = {
        key: (low + high) / 2.0
        for key, (low, high) in extract_latent_registry(_registry()).items()
    }
    values["public_order_stress"] = stress
    values["alliance_support"] = 0.77
    return values


def _stocks(
    *,
    population: int,
    police: int,
    parent_only: bool,
) -> dict:
    logger.info(
        "_stocks population=%s police=%s parent_only=%s",
        population,
        police,
        parent_only,
    )
    return {
        "population_total": population,
        "working_age_population": int(population * 0.6),
        "dependent_population": int(population * 0.4),
        "displaced_people": 2,
        "reception_population": 1,
        "fuel_stock_days_equivalent": 60.0,
        "strategic_food_stock_days": 30.0,
        "available_police_personnel": police,
        "available_military_personnel": 900 if parent_only else None,
        "prison_population": 3,
        "foreign_reserves_usd": 1000.0 if parent_only else None,
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


def _parent() -> EngineState:
    logger.info("_parent")
    return EngineState(
        node_id="TST",
        day=2,
        physical_stocks=_stocks(
            population=100,
            police=20,
            parent_only=True,
        ),
        latents=_latents(0.5),
        regimes=_regimes(),
        metadata={},
    )


def _child(
    node_id: str,
    *,
    parent_id: str,
    level: str,
    weight: float,
    population: int,
    police: int,
    stress: float,
) -> EngineState:
    logger.info(
        "_child node=%s parent=%s level=%s weight=%s",
        node_id,
        parent_id,
        level,
        weight,
    )
    return EngineState(
        node_id=node_id,
        day=2,
        physical_stocks=_stocks(
            population=population,
            police=police,
            parent_only=False,
        ),
        latents=_latents(stress),
        regimes=_regimes(),
        metadata={
            "fractal_parent_node_id": parent_id,
            "fractal_level": level,
            "fractal_initialization_weight": weight,
            "fractal_runtime_node_id": node_id,
            "fractal_catalog_child_id": node_id,
            "fractal_lineage_generation": 1,
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
        FractalRuntimeAuthorityNode(
            runtime_node_id="TST::R1",
            parent_node_id="TST",
            level="L2_REGION",
            catalog_node_id="TST::R1",
            lineage_generation=1,
            authority_scope="PARENT_CONTEXT",
            owns_regionalizable_state=False,
            owns_national_only_state=False,
            execution_status=(
                "FRACTAL_PARENT_CONTEXT_NO_DUPLICATE_EXECUTION"
            ),
        ),
        FractalRuntimeAuthorityNode(
            runtime_node_id="TST::R2",
            parent_node_id="TST",
            level="L2_REGION",
            catalog_node_id="TST::R2",
            lineage_generation=1,
            authority_scope="REGIONALIZABLE",
            owns_regionalizable_state=True,
            owns_national_only_state=False,
            execution_status="L2_REGIONAL_AUTHORITY_ACTIVE_V0_29",
        ),
        FractalRuntimeAuthorityNode(
            runtime_node_id="TST::R1::A",
            parent_node_id="TST::R1",
            level="L3_METRO_OR_LOGISTICS_AREA",
            catalog_node_id="TST::R1::A",
            lineage_generation=1,
            authority_scope="REGIONALIZABLE",
            owns_regionalizable_state=True,
            owns_national_only_state=False,
            execution_status="L3_REGIONAL_AUTHORITY_ACTIVE_V0_34B",
        ),
        FractalRuntimeAuthorityNode(
            runtime_node_id="TST::R1::B",
            parent_node_id="TST::R1",
            level="L3_METRO_OR_LOGISTICS_AREA",
            catalog_node_id="TST::R1::B",
            lineage_generation=1,
            authority_scope="REGIONALIZABLE",
            owns_regionalizable_state=True,
            owns_national_only_state=False,
            execution_status="L3_REGIONAL_AUTHORITY_ACTIVE_V0_34B",
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
        active_regional_node_ids=(
            "TST::R1::A",
            "TST::R1::B",
            "TST::R2",
        ),
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


def _store() -> FractalChildStateStore:
    logger.info("_store")
    return FractalChildStateStore(
        last_initialized_day=2,
        states=(
            _child(
                "TST::R1",
                parent_id="TST",
                level="L2_REGION",
                weight=0.6,
                population=60,
                police=12,
                stress=0.5,
            ),
            _child(
                "TST::R2",
                parent_id="TST",
                level="L2_REGION",
                weight=0.4,
                population=40,
                police=8,
                stress=0.2,
            ),
            _child(
                "TST::R1::A",
                parent_id="TST::R1",
                level="L3_METRO_OR_LOGISTICS_AREA",
                weight=0.5,
                population=30,
                police=6,
                stress=0.8,
            ),
            _child(
                "TST::R1::B",
                parent_id="TST::R1",
                level="L3_METRO_OR_LOGISTICS_AREA",
                weight=0.5,
                population=30,
                police=6,
                stress=0.4,
            ),
        ),
    )


def test_v034c2_recursive_coupling_aggregates_bottom_up() -> None:
    logger.info(
        "test_v034c2_recursive_coupling_aggregates_bottom_up"
    )
    result = execute_parent_child_coupling(
        parent_states={"TST": _parent()},
        child_store=_store(),
        runtime_plan=_plan(),
        engine_state_registry=_registry(),
        reaggregation_config=load_yaml(
            ROOT / "config/engine/fractal_reaggregation_v1.yaml"
        ),
        trace=TraceLedger(),
    )

    children = result.child_store.state_map()
    r1 = children["TST::R1"]
    assert r1.physical_stocks["population_total"] == 60
    assert r1.physical_stocks["available_police_personnel"] == 12
    assert r1.latents["public_order_stress"] == pytest.approx(0.60)

    parent = result.parent_states["TST"]
    assert parent.physical_stocks["population_total"] == 100
    assert parent.physical_stocks["available_police_personnel"] == 20
    assert parent.physical_stocks["available_military_personnel"] == 900
    assert parent.latents["public_order_stress"] == pytest.approx(0.44)
    assert parent.latents["alliance_support"] == pytest.approx(0.77)

    audits = {item.parent_node_id: item for item in result.audits}
    assert set(audits) == {"TST", "TST::R1"}
    assert audits["TST::R1"].child_node_ids == (
        "TST::R1::A",
        "TST::R1::B",
    )
    assert audits["TST"].child_node_ids == (
        "TST::R1",
        "TST::R2",
    )


def test_v034c2_national_context_reaches_only_active_execution_leaves() -> None:
    logger.info(
        "test_v034c2_national_context_reaches_only_active_execution_leaves"
    )
    result = execute_parent_child_coupling(
        parent_states={"TST": _parent()},
        child_store=_store(),
        runtime_plan=_plan(),
        engine_state_registry=_registry(),
        reaggregation_config=load_yaml(
            ROOT / "config/engine/fractal_reaggregation_v1.yaml"
        ),
        trace=TraceLedger(),
    )

    states = result.child_store.state_map()
    for node_id in ("TST::R1::A", "TST::R1::B", "TST::R2"):
        context = states[node_id].metadata["fractal_parent_context"]
        assert context["parent_node_id"] == "TST"
        assert (
            context["physical_stocks"]["available_military_personnel"]
            == 900
        )

    assert "fractal_parent_context" not in states["TST::R1"].metadata
