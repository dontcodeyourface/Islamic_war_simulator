from __future__ import annotations

import copy
import logging
import math
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.day import run_day_transaction
from iwsim.graph import build_country_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.recovery import propose_recovery_effects
from iwsim.rng import RNGManager
from iwsim.state import EngineState
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 1010):
    logger.info("_runtime seed=%s", seed)
    graph_config = load_yaml(ROOT / "config/graph/country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    day_config = load_yaml(ROOT / "config/engine/day_transaction_v1.yaml")
    recovery_config = load_yaml(ROOT / "config/engine/recovery_v1.yaml")

    snapshots = {
        iso3: load_yaml(ROOT / node["snapshot_path"])
        for iso3, node in graph_config["nodes"].items()
    }
    graph = build_country_graph(
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        snapshots=snapshots,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )
    rng = RNGManager(seed)
    states = {
        iso3: initialize_hybrid_state(
            snapshot=snapshots[iso3],
            engine_state_registry=state_registry,
            normalization_registry=normalization,
            parameter_registry=parameters,
            feature_map=feature_map,
            rng=rng,
            trace=TraceLedger(),
            profile="synthetic_smoke_v1",
        )
        for iso3 in sorted(snapshots)
    }
    manifest = build_manifest(
        run_id="recovery-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.10.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={
            iso3: canonical_hash(snapshot)
            for iso3, snapshot in sorted(snapshots.items())
        },
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-RECOVERY-TEST",
        scenario_hash=canonical_hash({"scenario": "recovery-test"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=30,
        enabled_modules=("recovery", "owner_resolver", "day_transaction", "trace"),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return (
        states,
        graph,
        day_config,
        state_registry,
        parameters,
        rng,
        manifest,
        recovery_config,
    )


def _baseline(state: EngineState) -> dict[str, float]:
    logger.info("_baseline node_id=%s", state.node_id)
    return {
        str(key): float(value)
        for key, value in state.metadata["baseline_latents"]
    }


def _disable_random_events(parameters: dict) -> dict:
    logger.info("_disable_random_events")
    patched = copy.deepcopy(parameters)
    probability = patched["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0
    return patched


def _quiet_non_spain(states: dict[str, EngineState]) -> None:
    logger.info("_quiet_non_spain")
    for node_id, state in states.items():
        if node_id == "ESP":
            continue
        state.latents["external_conflict_pressure"] = 0.0
        state.latents["polarization"] = 0.0
        state.latents["inflation_pressure"] = 0.0
        state.latents["unemployment_pressure"] = 0.0
        state.latents["government_legitimacy"] = 1.0
        state.latents["social_cohesion"] = 1.0


def test_initializer_persists_exact_immutable_t0_baseline() -> None:
    logger.info("test_initializer_persists_exact_immutable_t0_baseline")
    states = _runtime()[0]
    state = states["ESP"]
    baseline_raw = state.metadata["baseline_latents"]
    assert isinstance(baseline_raw, tuple)
    assert len(baseline_raw) == 60
    assert dict(baseline_raw) == state.latents
    assert state.metadata["baseline_latents_version"] == "ENGINESTATE_T0_V1"


def test_recovery_uses_registered_short_half_life_and_baseline() -> None:
    logger.info("test_recovery_uses_registered_short_half_life_and_baseline")
    states, _, _, registry, parameters, _, manifest, recovery_config = _runtime()
    state = states["ESP"]
    baseline = _baseline(state)
    current = min(1.0, baseline["communal_fear"] + 0.20)
    if math.isclose(current, baseline["communal_fear"], abs_tol=1e-12):
        current = max(0.0, baseline["communal_fear"] - 0.20)
    state.latents["communal_fear"] = current
    state.latents["state_cohesion"] = max(
        0.0, baseline["state_cohesion"] - 0.25
    )
    trace = TraceLedger()

    proposals = propose_recovery_effects(
        states={"ESP": state},
        engine_state_registry=registry,
        parameter_registry=parameters,
        recovery_config=recovery_config,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=trace,
    )

    communal = next(
        proposal for proposal in proposals
        if proposal.variable == "communal_fear"
    )
    alpha = 1.0 - math.pow(2.0, -1.0 / 8.0)
    expected = (baseline["communal_fear"] - current) * alpha
    assert communal.raw_delta == pytest.approx(expected)
    assert communal.parameter_ids == ("MEM_HALF_LIVES_SYN_V1",)
    assert communal.equation_id == "RECOVERY_TO_BASELINE_V1"
    assert communal.event_type == "ENDOGENOUS_RECOVERY_V1"
    assert all(
        proposal.variable != "state_cohesion"
        for proposal in proposals
    )

    recovery_record = next(
        record for record in trace.records
        if record["record_type"] == "recovery_proposal"
        and record["variable"] == "communal_fear"
    )
    assert recovery_record["baseline_value"] == pytest.approx(
        baseline["communal_fear"]
    )
    assert recovery_record["half_life_days"] == pytest.approx(8.0)
    assert recovery_record["daily_alpha"] == pytest.approx(alpha)


def test_infrastructure_functionality_recovers_upward_to_t0() -> None:
    logger.info("test_infrastructure_functionality_recovers_upward_to_t0")
    states, _, _, registry, parameters, _, manifest, recovery_config = _runtime()
    state = states["ESP"]
    baseline = _baseline(state)
    assert baseline["electricity_functionality"] == pytest.approx(1.0)
    state.latents["electricity_functionality"] = 0.50

    proposals = propose_recovery_effects(
        states={"ESP": state},
        engine_state_registry=registry,
        parameter_registry=parameters,
        recovery_config=recovery_config,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    electricity = next(
        proposal for proposal in proposals
        if proposal.variable == "electricity_functionality"
    )
    alpha = 1.0 - math.pow(2.0, -1.0 / 34.0)
    assert electricity.raw_delta == pytest.approx(0.50 * alpha)
    assert electricity.raw_delta > 0


def test_recovery_and_event_effect_share_same_beginning_value() -> None:
    logger.info("test_recovery_and_event_effect_share_same_beginning_value")
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
        recovery_config,
    ) = _runtime(seed=1011)
    parameters = _disable_random_events(parameters)
    _quiet_non_spain(states)

    spain = states["ESP"]
    baseline = _baseline(spain)
    current = min(0.80, baseline["public_order_stress"] + 0.20)
    if current <= baseline["public_order_stress"]:
        current = max(0.20, baseline["public_order_stress"] - 0.20)
    spain.latents["public_order_stress"] = current
    spain.latents["external_conflict_pressure"] = 0.0
    spain.latents["polarization"] = 1.0
    spain.latents["inflation_pressure"] = 1.0
    spain.latents["unemployment_pressure"] = 1.0
    spain.latents["government_legitimacy"] = 0.0
    spain.latents["social_cohesion"] = 0.0

    trace = TraceLedger()
    result = run_day_transaction(
        states=states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
        enable_recovery=True,
        recovery_config=recovery_config,
    )

    proposals = [
        proposal for proposal in result.proposals
        if proposal.target_node == "ESP"
        and proposal.variable == "public_order_stress"
    ]
    assert {proposal.event_type for proposal in proposals} == {
        "MASS_PROTEST_TRIGGER_V1",
        "ENDOGENOUS_RECOVERY_V1",
    }
    assert all(proposal.value_before == pytest.approx(current) for proposal in proposals)

    recovery = next(
        proposal for proposal in proposals
        if proposal.event_type == "ENDOGENOUS_RECOVERY_V1"
    )
    event = next(
        proposal for proposal in proposals
        if proposal.event_type == "MASS_PROTEST_TRIGGER_V1"
    )
    resolution = next(
        record for record in result.resolutions
        if record.target_node == "ESP"
        and record.variable == "public_order_stress"
    )
    assert event.raw_delta == pytest.approx(0.060)
    assert resolution.raw_sum_delta == pytest.approx(
        event.raw_delta + recovery.raw_delta
    )
    assert resolution.value_before == pytest.approx(current)


def test_recovery_config_changes_transaction_identity() -> None:
    logger.info("test_recovery_config_changes_transaction_identity")
    runtime_a = _runtime(seed=1012)
    runtime_b = _runtime(seed=1012)
    config_b = copy.deepcopy(runtime_b[7])
    config_b["variables"]["communal_fear"]["memory_class"] = "medium"

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=_disable_random_events(runtime_a[4]),
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_recovery=True,
        recovery_config=runtime_a[7],
    )
    result_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=_disable_random_events(runtime_b[4]),
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_recovery=True,
        recovery_config=config_b,
    )
    assert result_a.transaction_id != result_b.transaction_id


def test_calibrated_recovery_fails_closed() -> None:
    logger.info("test_calibrated_recovery_fails_closed")
    states, _, _, registry, parameters, _, manifest, recovery_config = _runtime()
    with pytest.raises(ValueError, match="Missing recovery parameter"):
        propose_recovery_effects(
            states={"ESP": states["ESP"]},
            engine_state_registry=registry,
            parameter_registry=parameters,
            recovery_config=recovery_config,
            profile="calibrated_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_missing_t0_baseline_fails_closed() -> None:
    logger.info("test_missing_t0_baseline_fails_closed")
    states, _, _, registry, parameters, _, manifest, recovery_config = _runtime()
    state = states["ESP"]
    state.metadata.pop("baseline_latents")
    state.latents["communal_fear"] = min(
        1.0, state.latents["communal_fear"] + 0.20
    )

    with pytest.raises(ValueError, match="Missing baseline_latents"):
        propose_recovery_effects(
            states={"ESP": state},
            engine_state_registry=registry,
            parameter_registry=parameters,
            recovery_config=recovery_config,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_recovery_failure_after_event_evaluation_rolls_back_transaction() -> None:
    logger.info(
        "test_recovery_failure_after_event_evaluation_rolls_back_transaction"
    )
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
        recovery_config,
    ) = _runtime(seed=1013)
    states["ESP"].metadata.pop("baseline_latents")
    state_hashes_before = {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    }
    rng_before = rng.describe()
    trace = TraceLedger()

    with pytest.raises(ValueError, match="Missing baseline_latents"):
        run_day_transaction(
            states=states,
            graph=graph,
            day_config=day_config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            rng=rng,
            manifest=manifest,
            trace=trace,
            enable_recovery=True,
            recovery_config=recovery_config,
        )

    assert rng.describe() == rng_before
    assert trace.records == []
    assert {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    } == state_hashes_before
