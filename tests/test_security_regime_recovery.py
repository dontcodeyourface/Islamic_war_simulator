from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.manifest import build_manifest
from iwsim.security_regime_recovery import (
    SecurityRegimeRecoveryPersistenceState,
    evaluate_security_regime_recovery,
)
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture(
    *,
    regime: str = "STRAINED",
    day: int = 1,
) -> tuple[EngineState, dict, dict, object]:
    logger.info("_fixture regime=%s day=%s", regime, day)
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    recovery_config = load_yaml(
        ROOT / "config/engine/security_regime_recovery_v1.yaml"
    )
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
        run_id="security-regime-recovery-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.18.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-SECURITY-RECOVERY-TEST",
        scenario_hash=canonical_hash({"scenario": "security-regime-recovery-test"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=1,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=60,
        enabled_modules=("security_regime_recovery_evaluator",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state, parameters, recovery_config, manifest


def _set_strained_recovery_state(state: EngineState) -> None:
    logger.info("_set_strained_recovery_state node=%s", state.node_id)
    state.latents["security_chain_cohesion"] = 0.85
    state.latents["command_cohesion"] = 0.85
    state.latents["operational_fatigue"] = 0.20


def test_strained_to_cohesive_requires_thirteen_consecutive_days() -> None:
    logger.info(
        "test_strained_to_cohesive_requires_thirteen_consecutive_days"
    )
    state, parameters, config, manifest = _fixture()
    _set_strained_recovery_state(state)
    persistence: SecurityRegimeRecoveryPersistenceState | None = None

    for day in range(1, 14):
        state.day = day
        result = evaluate_security_regime_recovery(
            state=state,
            persistence=persistence,
            context_flags={},
            recovery_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence
        assert result.evaluations[0].persistence_required == 13
        assert result.evaluations[0].persistence_observed == day
        if day < 13:
            assert result.proposals == ()
        else:
            assert len(result.proposals) == 1
            proposal = result.proposals[0]
            assert proposal.from_regime == "STRAINED"
            assert proposal.to_regime == "COHESIVE"
            assert proposal.apply_status == "PROPOSED_NOT_APPLIED"

    assert state.regimes["security_force_regime"] == "STRAINED"


def test_failed_recovery_condition_resets_streak() -> None:
    logger.info("test_failed_recovery_condition_resets_streak")
    state, parameters, config, manifest = _fixture()
    _set_strained_recovery_state(state)
    persistence: SecurityRegimeRecoveryPersistenceState | None = None

    for day in range(1, 4):
        state.day = day
        result = evaluate_security_regime_recovery(
            state=state,
            persistence=persistence,
            context_flags={},
            recovery_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence

    state.day = 4
    state.latents["operational_fatigue"] = 0.60
    failed = evaluate_security_regime_recovery(
        state=state,
        persistence=persistence,
        context_flags={},
        recovery_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert failed.evaluations[0].conditions_passed is False
    assert failed.evaluations[0].persistence_observed == 0

    state.day = 5
    state.latents["operational_fatigue"] = 0.20
    restarted = evaluate_security_regime_recovery(
        state=state,
        persistence=failed.persistence,
        context_flags={},
        recovery_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert restarted.evaluations[0].persistence_observed == 1


def test_same_day_escalation_suppresses_recovery_and_resets_streak() -> None:
    logger.info(
        "test_same_day_escalation_suppresses_recovery_and_resets_streak"
    )
    state, parameters, config, manifest = _fixture(day=2)
    _set_strained_recovery_state(state)
    persistence = SecurityRegimeRecoveryPersistenceState(
        node_id="TST",
        current_regime="STRAINED",
        last_evaluated_day=1,
        streaks=(("SECURITY_RECOVERY_STRAINED_COHESIVE_V1", 7),),
    )

    result = evaluate_security_regime_recovery(
        state=state,
        persistence=persistence,
        context_flags={},
        recovery_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
        same_day_escalation_committed=True,
    )

    assert result.evaluations[0].conditions_passed is True
    assert result.evaluations[0].suppressed_by_same_day_escalation is True
    assert result.evaluations[0].persistence_observed == 0
    assert result.evaluations[0].matured is False
    assert result.proposals == ()


def test_recovery_hysteresis_overlap_fails_closed() -> None:
    logger.info("test_recovery_hysteresis_overlap_fails_closed")
    state, parameters, config, manifest = _fixture()
    _set_strained_recovery_state(state)
    broken = copy.deepcopy(parameters)
    broken["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "SECURITY_REGIME_RECOVERY_SYN_V1"
    ]["value"]["transitions"]["strained_to_cohesive"]["all"][
        "security_chain_cohesion_gte"
    ] = 0.70

    with pytest.raises(ValueError, match="hysteresis gap must be positive"):
        evaluate_security_regime_recovery(
            state=state,
            persistence=None,
            context_flags={},
            recovery_config=config,
            parameter_registry=broken,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_multiple_commands_recovery_requires_authority_fragmentation_to_clear() -> None:
    logger.info(
        "test_multiple_commands_recovery_requires_authority_fragmentation_to_clear"
    )
    state, parameters, config, manifest = _fixture(
        regime="MULTIPLE_COMMANDS",
    )
    state.latents["command_cohesion"] = 0.50
    state.latents["state_cohesion"] = 0.55

    blocked = evaluate_security_regime_recovery(
        state=state,
        persistence=None,
        context_flags={"multiple_authority_nodes_present": True},
        recovery_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert blocked.evaluations[0].conditions_passed is False

    allowed = evaluate_security_regime_recovery(
        state=state,
        persistence=None,
        context_flags={"multiple_authority_nodes_present": False},
        recovery_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert allowed.evaluations[0].conditions_passed is True
    assert allowed.evaluations[0].persistence_required == 34


def test_calibrated_recovery_profile_fails_closed() -> None:
    logger.info("test_calibrated_recovery_profile_fails_closed")
    state, parameters, config, manifest = _fixture()
    _set_strained_recovery_state(state)

    with pytest.raises(
        ValueError,
        match="Missing security-regime recovery parameter",
    ):
        evaluate_security_regime_recovery(
            state=state,
            persistence=None,
            context_flags={},
            recovery_config=config,
            parameter_registry=parameters,
            profile="calibrated_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
