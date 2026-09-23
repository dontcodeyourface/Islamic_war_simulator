from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.phases import PhasePersistenceState, evaluate_national_phase
from iwsim.rng import RNGManager
from iwsim.state import EngineState
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 800):
    logger.info("_runtime seed=%s", seed)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    phase_config = load_yaml(ROOT / "config/engine/phase_evaluator_v1.yaml")
    snapshot = load_yaml(ROOT / "config/countries/spain.yaml")
    state = initialize_hybrid_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        parameter_registry=parameters,
        feature_map=feature_map,
        rng=RNGManager(seed),
        trace=TraceLedger(),
        profile="synthetic_smoke_v1",
    )
    manifest = build_manifest(
        run_id="phase-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.8.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshot),
        country_file_hashes={"ESP": "TEST"},
        graph_hash=canonical_hash({"graph": "phase-test"}),
        scenario_id="SCN-PHASE-TEST",
        scenario_hash=canonical_hash({"scenario": "phase-test"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=seed,
        rng_algorithm="python_random_mt19937",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=30,
        enabled_modules=("phase_evaluator", "trace"),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state, parameters, phase_config, manifest


def _state_for_day(
    base: EngineState,
    *,
    day: int,
    phase: str,
) -> EngineState:
    logger.info("_state_for_day day=%s phase=%s", day, phase)
    return EngineState(
        node_id=base.node_id,
        day=day,
        physical_stocks=dict(base.physical_stocks),
        latents=dict(base.latents),
        regimes={**base.regimes, "national_phase": phase},
        metadata=dict(base.metadata),
    )


def _evaluate_days(
    *,
    base: EngineState,
    days: int,
    phase: str,
    parameters: dict,
    phase_config: dict,
    manifest,
    configure,
    context_flags: dict[str, bool] | None = None,
):
    logger.info("_evaluate_days days=%s phase=%s", days, phase)
    persistence = None
    trace = TraceLedger()
    results = []
    for day in range(1, days + 1):
        state = _state_for_day(base, day=day, phase=phase)
        configure(state, day)
        result = evaluate_national_phase(
            state=state,
            persistence=persistence,
            context_flags=context_flags,
            phase_config=phase_config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=trace,
        )
        persistence = result.persistence
        results.append(result)
    return results, trace


def _configure_stable_tension(state: EngineState, day: int) -> None:
    logger.info("_configure_stable_tension day=%s", day)
    state.latents["external_conflict_pressure"] = 0.40
    state.latents["polarization"] = 0.10
    state.latents["public_order_stress"] = 0.10


def _configure_tension_emergency(state: EngineState, day: int) -> None:
    logger.info("_configure_tension_emergency day=%s", day)
    state.latents["public_order_stress"] = 0.60
    state.latents["government_legitimacy"] = 0.60


def _configure_insurgency_both(state: EngineState, day: int) -> None:
    logger.info("_configure_insurgency_both day=%s", day)
    state.latents["organized_armed_actor_capacity"] = 0.80
    state.latents["security_chain_cohesion"] = 0.30
    state.latents["territorial_control"] = 0.60
    state.latents["administrative_capacity"] = 0.50
    state.latents["center_region_cohesion"] = 0.40
    state.latents["state_cohesion"] = 0.40


def test_stable_to_tension_requires_three_consecutive_days() -> None:
    logger.info("test_stable_to_tension_requires_three_consecutive_days")
    base, parameters, phase_config, manifest = _runtime()
    results, trace = _evaluate_days(
        base=base,
        days=3,
        phase="STABLE",
        parameters=parameters,
        phase_config=phase_config,
        manifest=manifest,
        configure=_configure_stable_tension,
    )

    assert results[0].evaluations[0].persistence_observed == 1
    assert results[1].evaluations[0].persistence_observed == 2
    assert results[0].proposals == ()
    assert results[1].proposals == ()
    assert len(results[2].proposals) == 1
    proposal = results[2].proposals[0]
    assert proposal.from_phase == "STABLE"
    assert proposal.to_phase == "TENSION"
    assert proposal.persistence_required == 3
    assert proposal.persistence_observed == 3
    assert proposal.apply_status == "PROPOSED_NOT_APPLIED"

    proposal_records = [
        record for record in trace.records
        if record["record_type"] == "phase_transition_proposal"
    ]
    assert len(proposal_records) == 1


def test_failed_condition_resets_persistence_streak() -> None:
    logger.info("test_failed_condition_resets_persistence_streak")
    base, parameters, phase_config, manifest = _runtime()
    persistence: PhasePersistenceState | None = None
    trace = TraceLedger()

    for day, pressure in ((1, 0.40), (2, 0.0), (3, 0.40)):
        state = _state_for_day(base, day=day, phase="STABLE")
        state.latents["external_conflict_pressure"] = pressure
        state.latents["polarization"] = 0.0
        state.latents["public_order_stress"] = 0.0
        result = evaluate_national_phase(
            state=state,
            persistence=persistence,
            context_flags={},
            phase_config=phase_config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=trace,
        )
        persistence = result.persistence

    assert result.evaluations[0].persistence_observed == 1
    assert result.proposals == ()


def test_tension_to_emergency_uses_all_conditions() -> None:
    logger.info("test_tension_to_emergency_uses_all_conditions")
    base, parameters, phase_config, manifest = _runtime()
    results, _ = _evaluate_days(
        base=base,
        days=3,
        phase="TENSION",
        parameters=parameters,
        phase_config=phase_config,
        manifest=manifest,
        configure=_configure_tension_emergency,
    )

    assert results[-1].evaluations[0].condition_mode == "all"
    assert all(
        condition.passed
        for condition in results[-1].evaluations[0].condition_results
    )
    assert len(results[-1].proposals) == 1
    assert results[-1].proposals[0].to_phase == "EMERGENCY"


def test_insurgency_can_propose_multiple_outgoing_transitions_read_only() -> None:
    logger.info(
        "test_insurgency_can_propose_multiple_outgoing_transitions_read_only"
    )
    base, parameters, phase_config, manifest = _runtime()
    results, _ = _evaluate_days(
        base=base,
        days=21,
        phase="INSURGENCY",
        parameters=parameters,
        phase_config=phase_config,
        manifest=manifest,
        configure=_configure_insurgency_both,
        context_flags={"competing_authority_present": True},
    )

    final_targets = {proposal.to_phase for proposal in results[-1].proposals}
    assert final_targets == {"DUAL_AUTHORITY", "CIVIL_WAR"}
    assert base.regimes["national_phase"] == "STABLE"


def test_dual_authority_requires_explicit_context_flag() -> None:
    logger.info("test_dual_authority_requires_explicit_context_flag")
    base, parameters, phase_config, manifest = _runtime()
    persistence = None
    trace = TraceLedger()

    for day in range(1, 14):
        state = _state_for_day(base, day=day, phase="INSURGENCY")
        _configure_insurgency_both(state, day)
        result = evaluate_national_phase(
            state=state,
            persistence=persistence,
            context_flags={"competing_authority_present": False},
            phase_config=phase_config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=trace,
        )
        persistence = result.persistence

    dual_eval = next(
        item for item in result.evaluations
        if item.to_phase == "DUAL_AUTHORITY"
    )
    assert dual_eval.persistence_observed == 0
    assert all(
        proposal.to_phase != "DUAL_AUTHORITY"
        for proposal in result.proposals
    )


def test_phase_change_resets_old_rule_streaks() -> None:
    logger.info("test_phase_change_resets_old_rule_streaks")
    base, parameters, phase_config, manifest = _runtime()
    trace = TraceLedger()

    stable = _state_for_day(base, day=1, phase="STABLE")
    _configure_stable_tension(stable, 1)
    first = evaluate_national_phase(
        state=stable,
        persistence=None,
        context_flags={},
        phase_config=phase_config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=trace,
    )
    assert dict(first.persistence.streaks)["PHASE_STABLE_TENSION_V1"] == 1

    tension = _state_for_day(base, day=2, phase="TENSION")
    _configure_tension_emergency(tension, 2)
    second = evaluate_national_phase(
        state=tension,
        persistence=first.persistence,
        context_flags={},
        phase_config=phase_config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=trace,
    )
    streaks = dict(second.persistence.streaks)
    assert "PHASE_STABLE_TENSION_V1" not in streaks
    assert streaks["PHASE_TENSION_EMERGENCY_V1"] == 1


def test_same_day_re_evaluation_fails_closed() -> None:
    logger.info("test_same_day_re_evaluation_fails_closed")
    base, parameters, phase_config, manifest = _runtime()
    state = _state_for_day(base, day=1, phase="STABLE")
    _configure_stable_tension(state, 1)
    first = evaluate_national_phase(
        state=state,
        persistence=None,
        context_flags={},
        phase_config=phase_config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )

    with pytest.raises(ValueError, match="consecutive days"):
        evaluate_national_phase(
            state=state,
            persistence=first.persistence,
            context_flags={},
            phase_config=phase_config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_skipped_day_fails_closed() -> None:
    logger.info("test_skipped_day_fails_closed")
    base, parameters, phase_config, manifest = _runtime()
    day1 = _state_for_day(base, day=1, phase="STABLE")
    _configure_stable_tension(day1, 1)
    first = evaluate_national_phase(
        state=day1,
        persistence=None,
        context_flags={},
        phase_config=phase_config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )

    day3 = _state_for_day(base, day=3, phase="STABLE")
    _configure_stable_tension(day3, 3)
    with pytest.raises(ValueError, match="consecutive days"):
        evaluate_national_phase(
            state=day3,
            persistence=first.persistence,
            context_flags={},
            phase_config=phase_config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_phase_evaluator_is_read_only_and_replayable() -> None:
    logger.info("test_phase_evaluator_is_read_only_and_replayable")
    base_a, parameters_a, phase_config_a, manifest_a = _runtime(seed=801)
    base_b, parameters_b, phase_config_b, manifest_b = _runtime(seed=801)
    state_a = _state_for_day(base_a, day=1, phase="STABLE")
    state_b = _state_for_day(base_b, day=1, phase="STABLE")
    _configure_stable_tension(state_a, 1)
    _configure_stable_tension(state_b, 1)
    before_hash_a = state_a.state_hash()
    before_hash_b = state_b.state_hash()
    trace_a = TraceLedger()
    trace_b = TraceLedger()

    result_a = evaluate_national_phase(
        state=state_a,
        persistence=None,
        context_flags={},
        phase_config=phase_config_a,
        parameter_registry=parameters_a,
        profile="synthetic_smoke_v1",
        manifest=manifest_a,
        trace=trace_a,
    )
    result_b = evaluate_national_phase(
        state=state_b,
        persistence=None,
        context_flags={},
        phase_config=phase_config_b,
        parameter_registry=parameters_b,
        profile="synthetic_smoke_v1",
        manifest=manifest_b,
        trace=trace_b,
    )

    assert state_a.state_hash() == before_hash_a
    assert state_b.state_hash() == before_hash_b
    assert result_a.to_dict() == result_b.to_dict()
    assert trace_a.records == trace_b.records


def test_calibrated_phase_evaluator_fails_closed() -> None:
    logger.info("test_calibrated_phase_evaluator_fails_closed")
    base, parameters, phase_config, manifest = _runtime()
    state = _state_for_day(base, day=1, phase="STABLE")
    _configure_stable_tension(state, 1)

    with pytest.raises(ValueError, match="Missing phase parameter"):
        evaluate_national_phase(
            state=state,
            persistence=None,
            context_flags={},
            phase_config=phase_config,
            parameter_registry=parameters,
            profile="calibrated_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_phase_config_contains_no_identity_propensity_conditions() -> None:
    logger.info("test_phase_config_contains_no_identity_propensity_conditions")
    phase_config = load_yaml(ROOT / "config/engine/phase_evaluator_v1.yaml")
    serialized = str(phase_config).lower()
    forbidden = (
        "muslim_share",
        "christian_share",
        "mosque_count",
        "conservative_vote",
        "left_vote",
    )
    for token in forbidden:
        assert token not in serialized
