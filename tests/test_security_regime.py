from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.manifest import build_manifest
from iwsim.security_regime import (
    SecurityRegimePersistenceState,
    evaluate_security_regime,
)
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture(
    *,
    regime: str = "COHESIVE",
    day: int = 1,
) -> tuple[EngineState, dict, dict, object]:
    logger.info("_fixture regime=%s day=%s", regime, day)
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    config = load_yaml(ROOT / "config/engine/security_regime_evaluator_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=day,
        physical_stocks={},
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": regime,
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={},
    )
    manifest = build_manifest(
        run_id="security-regime-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.16.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-SECURITY-REGIME-TEST",
        scenario_hash=canonical_hash({"scenario": "security-regime-test"}),
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
        enabled_modules=("security_regime_evaluator",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state, parameters, config, manifest


def test_cohesive_to_strained_matures_immediately_and_is_read_only() -> None:
    logger.info("test_cohesive_to_strained_matures_immediately_and_is_read_only")
    state, parameters, config, manifest = _fixture()
    state.latents["security_chain_cohesion"] = 0.70
    state.latents["operational_fatigue"] = 0.50
    before = state.state_hash()
    trace = TraceLedger()

    result = evaluate_security_regime(
        state=state,
        persistence=None,
        context_flags={},
        regime_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=trace,
    )

    assert len(result.evaluations) == 1
    evaluation = result.evaluations[0]
    assert evaluation.from_regime == "COHESIVE"
    assert evaluation.to_regime == "STRAINED"
    assert evaluation.persistence_required == 1
    assert evaluation.persistence_observed == 1
    assert evaluation.matured is True
    assert len(result.proposals) == 1
    assert result.proposals[0].apply_status == "PROPOSED_NOT_APPLIED"
    assert state.state_hash() == before
    assert state.regimes["security_force_regime"] == "COHESIVE"


def test_selective_noncompliance_requires_eight_consecutive_days() -> None:
    logger.info("test_selective_noncompliance_requires_eight_consecutive_days")
    state, parameters, config, manifest = _fixture(
        regime="STRAINED",
        day=1,
    )
    persistence: SecurityRegimePersistenceState | None = None

    for day in range(1, 9):
        state.day = day
        state.latents["security_chain_cohesion"] = 0.55
        state.latents["constitutional_loyalty"] = 0.65
        result = evaluate_security_regime(
            state=state,
            persistence=persistence,
            context_flags={},
            regime_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence
        assert result.evaluations[0].persistence_observed == day
        assert result.evaluations[0].persistence_required == 8
        if day < 8:
            assert result.proposals == ()
        else:
            assert len(result.proposals) == 1
            assert result.proposals[0].to_regime == "SELECTIVE_NONCOMPLIANCE"


def test_failed_condition_resets_security_regime_streak() -> None:
    logger.info("test_failed_condition_resets_security_regime_streak")
    state, parameters, config, manifest = _fixture(
        regime="STRAINED",
        day=1,
    )
    persistence: SecurityRegimePersistenceState | None = None

    for day in range(1, 4):
        state.day = day
        state.latents["security_chain_cohesion"] = 0.55
        state.latents["constitutional_loyalty"] = 0.65
        result = evaluate_security_regime(
            state=state,
            persistence=persistence,
            context_flags={},
            regime_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence

    state.day = 4
    state.latents["constitutional_loyalty"] = 0.90
    failed = evaluate_security_regime(
        state=state,
        persistence=persistence,
        context_flags={},
        regime_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert failed.evaluations[0].conditions_passed is False
    assert failed.evaluations[0].persistence_observed == 0

    state.day = 5
    state.latents["constitutional_loyalty"] = 0.65
    restarted = evaluate_security_regime(
        state=state,
        persistence=failed.persistence,
        context_flags={},
        regime_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert restarted.evaluations[0].persistence_observed == 1


def test_localized_defection_requires_explicit_authority_context() -> None:
    logger.info("test_localized_defection_requires_explicit_authority_context")
    state, parameters, config, manifest = _fixture(
        regime="COMMAND_FRACTURE",
        day=1,
    )
    state.latents["command_cohesion"] = 0.35
    state.latents["center_region_cohesion"] = 0.40

    without_flag = evaluate_security_regime(
        state=state,
        persistence=None,
        context_flags={},
        regime_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert without_flag.evaluations[0].conditions_passed is False

    with_flag = evaluate_security_regime(
        state=state,
        persistence=None,
        context_flags={"competing_authority_present": True},
        regime_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert with_flag.evaluations[0].conditions_passed is True
    assert with_flag.evaluations[0].persistence_observed == 1
    assert with_flag.evaluations[0].persistence_required == 13


def test_skipped_day_persistence_fails_closed() -> None:
    logger.info("test_skipped_day_persistence_fails_closed")
    state, parameters, config, manifest = _fixture(
        regime="STRAINED",
        day=3,
    )
    persistence = SecurityRegimePersistenceState(
        node_id="TST",
        current_regime="STRAINED",
        last_evaluated_day=1,
        streaks=(("SECURITY_STRAINED_SELECTIVE_NONCOMPLIANCE_V1", 1),),
    )

    with pytest.raises(ValueError, match="requires consecutive days"):
        evaluate_security_regime(
            state=state,
            persistence=persistence,
            context_flags={},
            regime_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_security_regime_config_cannot_reorder_transition_contract() -> None:
    logger.info("test_security_regime_config_cannot_reorder_transition_contract")
    state, parameters, config, manifest = _fixture()
    broken = copy.deepcopy(config)
    broken["transitions"][0]["to"] = "COMMAND_FRACTURE"

    with pytest.raises(ValueError, match="must remain canonical"):
        evaluate_security_regime(
            state=state,
            persistence=None,
            context_flags={},
            regime_config=broken,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_calibrated_security_regime_profile_fails_closed() -> None:
    logger.info("test_calibrated_security_regime_profile_fails_closed")
    state, parameters, config, manifest = _fixture()
    state.latents["security_chain_cohesion"] = 0.70
    state.latents["operational_fatigue"] = 0.50

    with pytest.raises(ValueError, match="Missing security-regime parameter"):
        evaluate_security_regime(
            state=state,
            persistence=None,
            context_flags={},
            regime_config=config,
            parameter_registry=parameters,
            profile="calibrated_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
