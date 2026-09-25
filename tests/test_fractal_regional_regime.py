from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal_child_state import FractalChildStateStore
from iwsim.fractal_regional_regime import (
    FractalRegionalRegimeStore,
    bootstrap_or_validate_regional_regime_store,
    execute_regional_regime_runtime,
)
from iwsim.manifest import build_manifest
from iwsim.phases import PhasePersistenceState
from iwsim.rng import RNGManager
from iwsim.security_regime import SecurityRegimePersistenceState
from iwsim.security_regime_recovery import (
    SecurityRegimeRecoveryPersistenceState,
)
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


def _latents() -> dict[str, float]:
    logger.info("_latents")
    return {
        variable: (low + high) / 2.0
        for variable, (low, high) in extract_latent_registry(
            _registry()
        ).items()
    }


def _state(
    node_id: str,
    *,
    day: int,
    stressed: bool,
) -> EngineState:
    logger.info(
        "_state node=%s day=%s stressed=%s",
        node_id,
        day,
        stressed,
    )
    latents = _latents()
    if stressed:
        latents.update(
            {
                "public_order_stress": 0.90,
                "polarization": 0.90,
                "external_conflict_pressure": 0.50,
                "security_chain_cohesion": 0.50,
                "operational_fatigue": 0.80,
                "command_cohesion": 0.70,
            }
        )
    else:
        latents.update(
            {
                "public_order_stress": 0.10,
                "polarization": 0.10,
                "external_conflict_pressure": 0.10,
                "security_chain_cohesion": 0.90,
                "operational_fatigue": 0.10,
                "command_cohesion": 0.90,
            }
        )
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
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={
            "fractal_parent_node_id": "TST",
            "fractal_level": "L2_REGION",
            "fractal_runtime_node_id": node_id,
            "fractal_catalog_child_id": node_id,
            "fractal_lineage_generation": 1,
        },
    )


def _manifest():
    logger.info("_manifest")
    rng = RNGManager(2800)
    return build_manifest(
        run_id="regional-regime-test",
        created_at="2026-09-25T00:00:00+00:00",
        engine_version="0.28.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"tst": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-REGIONAL-REGIME",
        scenario_hash=canonical_hash({"scenario": "regional"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            _parameters()["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=2800,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-25",
        horizon_days=1,
        enabled_modules=("fractal_regional_regimes",),
    )


def _persistence_store() -> FractalRegionalRegimeStore:
    logger.info("_persistence_store")
    phase_rule = "PHASE_STABLE_TENSION_V1"
    return FractalRegionalRegimeStore(
        last_committed_day=1,
        phase_persistence=(
            PhasePersistenceState(
                node_id="TST::R1",
                current_phase="STABLE",
                last_evaluated_day=1,
                streaks=((phase_rule, 2),),
            ),
            PhasePersistenceState(
                node_id="TST::R2",
                current_phase="STABLE",
                last_evaluated_day=1,
                streaks=(),
            ),
        ),
        security_persistence=(
            SecurityRegimePersistenceState(
                node_id="TST::R1",
                current_regime="COHESIVE",
                last_evaluated_day=1,
                streaks=(),
            ),
            SecurityRegimePersistenceState(
                node_id="TST::R2",
                current_regime="COHESIVE",
                last_evaluated_day=1,
                streaks=(),
            ),
        ),
        security_recovery_persistence=(
            SecurityRegimeRecoveryPersistenceState(
                node_id="TST::R1",
                current_regime="COHESIVE",
                last_evaluated_day=1,
                streaks=(),
            ),
            SecurityRegimeRecoveryPersistenceState(
                node_id="TST::R2",
                current_regime="COHESIVE",
                last_evaluated_day=1,
                streaks=(),
            ),
        ),
    )


def _run(trace: TraceLedger | None = None):
    logger.info("_run")
    child_store = FractalChildStateStore(
        last_initialized_day=2,
        states=(
            _state("TST::R1", day=2, stressed=True),
            _state("TST::R2", day=2, stressed=False),
        ),
    )
    return execute_regional_regime_runtime(
        child_store=child_store,
        beginning_active_node_ids=("TST::R1", "TST::R2"),
        persistence_store=_persistence_store(),
        context_flags=None,
        regional_config=load_yaml(
            ROOT / "config/engine/fractal_regional_regime_v1.yaml"
        ),
        phase_config=load_yaml(
            ROOT / "config/engine/phase_evaluator_v1.yaml"
        ),
        phase_transition_config=load_yaml(
            ROOT / "config/engine/phase_transition_v1.yaml"
        ),
        security_regime_config=load_yaml(
            ROOT / "config/engine/security_regime_evaluator_v1.yaml"
        ),
        security_transition_config=load_yaml(
            ROOT / "config/engine/security_regime_transition_v1.yaml"
        ),
        security_recovery_config=load_yaml(
            ROOT / "config/engine/security_regime_recovery_v1.yaml"
        ),
        security_recovery_transition_config=load_yaml(
            ROOT
            / "config/engine/security_regime_recovery_transition_v1.yaml"
        ),
        engine_state_registry=_registry(),
        parameter_registry=_parameters(),
        profile="synthetic_smoke_v1",
        manifest=_manifest(),
        trace=trace or TraceLedger(),
    )


def test_regional_siblings_can_diverge_in_phase_and_security() -> None:
    logger.info(
        "test_regional_siblings_can_diverge_in_phase_and_security"
    )
    result = _run()
    states = result.child_store.state_map()

    assert states["TST::R1"].regimes["national_phase"] == "TENSION"
    assert states["TST::R2"].regimes["national_phase"] == "STABLE"
    assert (
        states["TST::R1"].regimes["security_force_regime"]
        == "STRAINED"
    )
    assert (
        states["TST::R2"].regimes["security_force_regime"]
        == "COHESIVE"
    )

    assert len(result.phase_commits) == 1
    assert result.phase_commits[0].node_id == "TST::R1"
    assert len(result.security_commits) == 1
    assert result.security_commits[0].node_id == "TST::R1"
    assert result.recovery_commits == ()

    assert len(result.divergence_audits) == 1
    audit = result.divergence_audits[0]
    assert audit.parent_node_id == "TST"
    assert audit.phase_divergent is True
    assert audit.security_regime_divergent is True
    assert audit.static_regimes_consistent is True
    assert audit.collapse_consensus_ready is False


def test_regional_regime_runtime_is_deterministic() -> None:
    logger.info("test_regional_regime_runtime_is_deterministic")
    trace_a = TraceLedger()
    trace_b = TraceLedger()
    first = _run(trace_a)
    second = _run(trace_b)

    assert first.to_dict() == second.to_dict()
    assert trace_a.records == trace_b.records


def test_new_child_is_initialized_but_not_evaluated_same_day() -> None:
    logger.info(
        "test_new_child_is_initialized_but_not_evaluated_same_day"
    )
    base = _run()
    states = tuple(base.child_store.states) + (
        _state("TST::R3", day=2, stressed=True),
    )
    child_store = FractalChildStateStore(
        last_initialized_day=2,
        states=states,
    )
    trace = TraceLedger()
    result = execute_regional_regime_runtime(
        child_store=child_store,
        beginning_active_node_ids=("TST::R1", "TST::R2"),
        persistence_store=_persistence_store(),
        context_flags=None,
        regional_config=load_yaml(
            ROOT / "config/engine/fractal_regional_regime_v1.yaml"
        ),
        phase_config=load_yaml(
            ROOT / "config/engine/phase_evaluator_v1.yaml"
        ),
        phase_transition_config=load_yaml(
            ROOT / "config/engine/phase_transition_v1.yaml"
        ),
        security_regime_config=load_yaml(
            ROOT / "config/engine/security_regime_evaluator_v1.yaml"
        ),
        security_transition_config=load_yaml(
            ROOT / "config/engine/security_regime_transition_v1.yaml"
        ),
        security_recovery_config=load_yaml(
            ROOT / "config/engine/security_regime_recovery_v1.yaml"
        ),
        security_recovery_transition_config=load_yaml(
            ROOT
            / "config/engine/security_regime_recovery_transition_v1.yaml"
        ),
        engine_state_registry=_registry(),
        parameter_registry=_parameters(),
        profile="synthetic_smoke_v1",
        manifest=_manifest(),
        trace=trace,
    )

    r3 = result.child_store.state_map()["TST::R3"]
    assert r3.regimes["national_phase"] == "STABLE"
    assert r3.regimes["security_force_regime"] == "COHESIVE"
    assert result.persistence_store.phase_map()["TST::R3"].streaks == ()
    assert any(
        item["record_type"]
        == "fractal_regional_regime_persistence_initialized"
        and item["node_id"] == "TST::R3"
        for item in trace.records
    )


def test_regional_store_bootstrap_uses_current_child_regimes() -> None:
    logger.info(
        "test_regional_store_bootstrap_uses_current_child_regimes"
    )
    child_store = FractalChildStateStore(
        last_initialized_day=4,
        states=(
            _state("TST::R1", day=4, stressed=False),
            _state("TST::R2", day=4, stressed=False),
        ),
    )
    store = bootstrap_or_validate_regional_regime_store(
        child_store=child_store,
        active_node_ids=("TST::R1", "TST::R2"),
        supplied_store=None,
    )
    assert store.last_committed_day == 4
    assert set(store.phase_map()) == {"TST::R1", "TST::R2"}
    assert all(
        item.current_phase == "STABLE"
        for item in store.phase_persistence
    )


def test_regional_runtime_failure_does_not_publish_partial_trace() -> None:
    logger.info(
        "test_regional_runtime_failure_does_not_publish_partial_trace"
    )
    child_store = FractalChildStateStore(
        last_initialized_day=2,
        states=(
            _state("TST::R1", day=2, stressed=True),
            _state("TST::R2", day=2, stressed=False),
        ),
    )
    broken = _persistence_store()
    broken = FractalRegionalRegimeStore(
        last_committed_day=broken.last_committed_day,
        phase_persistence=broken.phase_persistence,
        security_persistence=broken.security_persistence,
        security_recovery_persistence=(
            SecurityRegimeRecoveryPersistenceState(
                node_id="TST::R1",
                current_regime="MULTIPLE_COMMANDS",
                last_evaluated_day=1,
                streaks=(),
            ),
            broken.security_recovery_persistence[1],
        ),
    )
    trace = TraceLedger()
    with pytest.raises(ValueError):
        execute_regional_regime_runtime(
            child_store=child_store,
            beginning_active_node_ids=("TST::R1", "TST::R2"),
            persistence_store=broken,
            context_flags=None,
            regional_config=load_yaml(
                ROOT
                / "config/engine/fractal_regional_regime_v1.yaml"
            ),
            phase_config=load_yaml(
                ROOT / "config/engine/phase_evaluator_v1.yaml"
            ),
            phase_transition_config=load_yaml(
                ROOT / "config/engine/phase_transition_v1.yaml"
            ),
            security_regime_config=load_yaml(
                ROOT
                / "config/engine/security_regime_evaluator_v1.yaml"
            ),
            security_transition_config=load_yaml(
                ROOT
                / "config/engine/security_regime_transition_v1.yaml"
            ),
            security_recovery_config=load_yaml(
                ROOT
                / "config/engine/security_regime_recovery_v1.yaml"
            ),
            security_recovery_transition_config=load_yaml(
                ROOT
                / "config/engine/security_regime_recovery_transition_v1.yaml"
            ),
            engine_state_registry=_registry(),
            parameter_registry=_parameters(),
            profile="synthetic_smoke_v1",
            manifest=_manifest(),
            trace=trace,
        )
    assert trace.records == []
