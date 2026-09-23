from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.day import run_day_transaction
from iwsim.graph import build_country_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.phases import PhasePersistenceState
from iwsim.rng import RNGManager
from iwsim.state import EngineState
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 909):
    logger.info("_runtime seed=%s", seed)
    graph_config = load_yaml(ROOT / "config/graph/country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    day_config = load_yaml(ROOT / "config/engine/day_transaction_v1.yaml")
    phase_config = load_yaml(ROOT / "config/engine/phase_evaluator_v1.yaml")
    transition_config = load_yaml(ROOT / "config/engine/phase_transition_v1.yaml")

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
        run_id="phase-day-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.9.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={
            iso3: canonical_hash(snapshot)
            for iso3, snapshot in sorted(snapshots.items())
        },
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-PHASE-DAY-TEST",
        scenario_hash=canonical_hash({"scenario": "phase-day-test"}),
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
        enabled_modules=(
            "initializer",
            "typed_graph",
            "event_engine",
            "event_effects",
            "owner_resolver",
            "day_transaction",
            "phase_evaluator",
            "phase_arbitration",
            "phase_commit",
            "trace",
        ),
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
        phase_config,
        transition_config,
    )


def _disable_all_events(parameters: dict) -> dict:
    logger.info("_disable_all_events")
    patched = copy.deepcopy(parameters)
    hazard = patched["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_WEIGHTS_SYN_V1"
    ]["value"]
    for config in hazard.values():
        config["generated_threshold"] = 2.0
    probability = patched["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0
    return patched


def _state_at_day(
    state: EngineState,
    *,
    day: int,
    phase: str | None = None,
) -> EngineState:
    logger.info("_state_at_day node_id=%s day=%s phase=%s", state.node_id, day, phase)
    return EngineState(
        node_id=state.node_id,
        day=day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes={
            **state.regimes,
            "national_phase": phase or state.regimes["national_phase"],
        },
        metadata=dict(state.metadata),
    )


def _quiet_states(states: dict[str, EngineState], day: int) -> dict[str, EngineState]:
    logger.info("_quiet_states day=%s", day)
    result = {}
    for node_id, state in sorted(states.items()):
        next_state = _state_at_day(state, day=day)
        next_state.latents["external_conflict_pressure"] = 0.0
        next_state.latents["polarization"] = 0.0
        next_state.latents["public_order_stress"] = 0.0
        next_state.latents["government_legitimacy"] = 1.0
        next_state.latents["social_cohesion"] = 1.0
        result[node_id] = next_state
    return result


def _persistence_for(
    states: dict[str, EngineState],
    *,
    last_day: int,
    overrides: dict[str, tuple[tuple[str, int], ...]] | None = None,
) -> dict[str, PhasePersistenceState]:
    logger.info("_persistence_for last_day=%s", last_day)
    overrides = overrides or {}
    return {
        node_id: PhasePersistenceState(
            node_id=node_id,
            current_phase=state.regimes["national_phase"],
            last_evaluated_day=last_day,
            streaks=overrides.get(node_id, ()),
        )
        for node_id, state in sorted(states.items())
    }


def test_atomic_day_commits_matured_stable_to_tension_transition() -> None:
    logger.info("test_atomic_day_commits_matured_stable_to_tension_transition")
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
        phase_config,
        transition_config,
    ) = _runtime()
    parameters = _disable_all_events(parameters)
    states = _quiet_states(states, 2)
    states["ESP"].latents["external_conflict_pressure"] = 0.40
    persistence = _persistence_for(
        states,
        last_day=2,
        overrides={"ESP": (("PHASE_STABLE_TENSION_V1", 2),)},
    )
    original_spain_hash = states["ESP"].state_hash()
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
        enable_phase_transitions=True,
        phase_config=phase_config,
        phase_transition_config=transition_config,
        phase_persistence=persistence,
    )

    assert states["ESP"].state_hash() == original_spain_hash
    assert result.states["ESP"].day == 3
    assert result.states["ESP"].regimes["national_phase"] == "TENSION"
    assert len(result.phase_commits) == 1
    commit = result.phase_commits[0]
    assert commit.node_id == "ESP"
    assert commit.from_phase == "STABLE"
    assert commit.to_phase == "TENSION"
    assert result.phase_persistence["ESP"].current_phase == "TENSION"
    assert result.phase_persistence["ESP"].streaks == ()
    assert result.phase_persistence["ESP"].last_evaluated_day == 3

    checkpoint = next(
        record for record in trace.records
        if record["record_type"] == "daily_checkpoint"
        and record["node_id"] == "ESP"
    )
    assert checkpoint["phase_transition_ids"] == [commit.commit_id]


def test_insurgency_arbitration_prefers_highest_mature_target() -> None:
    logger.info("test_insurgency_arbitration_prefers_highest_mature_target")
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
        phase_config,
        transition_config,
    ) = _runtime(seed=910)
    parameters = _disable_all_events(parameters)
    states = _quiet_states(states, 20)
    spain = _state_at_day(states["ESP"], day=20, phase="INSURGENCY")
    spain.latents["organized_armed_actor_capacity"] = 0.80
    spain.latents["security_chain_cohesion"] = 0.30
    spain.latents["territorial_control"] = 0.60
    spain.latents["administrative_capacity"] = 0.50
    spain.latents["center_region_cohesion"] = 0.40
    spain.latents["state_cohesion"] = 0.40
    states["ESP"] = spain

    persistence = _persistence_for(
        states,
        last_day=20,
        overrides={
            "ESP": (
                ("PHASE_INSURGENCY_DUAL_AUTHORITY_V1", 12),
                ("PHASE_INSURGENCY_CIVIL_WAR_V1", 20),
            )
        },
    )
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
        enable_phase_transitions=True,
        phase_config=phase_config,
        phase_transition_config=transition_config,
        phase_persistence=persistence,
        phase_context_flags={"ESP": {"competing_authority_present": True}},
    )

    esp_eval = next(
        item for item in result.phase_evaluations
        if item.persistence.node_id == "ESP"
    )
    assert {proposal.to_phase for proposal in esp_eval.proposals} == {
        "DUAL_AUTHORITY",
        "CIVIL_WAR",
    }
    assert len(result.phase_arbitrations) == 1
    arbitration = result.phase_arbitrations[0]
    selected = next(
        proposal for proposal in esp_eval.proposals
        if proposal.proposal_id == arbitration.selected_proposal_id
    )
    assert selected.to_phase == "CIVIL_WAR"
    assert len(arbitration.rejected_proposal_ids) == 1
    assert result.states["ESP"].regimes["national_phase"] == "CIVIL_WAR"
    assert result.phase_persistence["ESP"].current_phase == "CIVIL_WAR"
    assert result.phase_persistence["ESP"].streaks == ()


def test_transaction_identity_includes_phase_persistence_history() -> None:
    logger.info("test_transaction_identity_includes_phase_persistence_history")
    runtime_a = _runtime(seed=911)
    runtime_b = _runtime(seed=911)

    def prepare(runtime, streak: int):
        logger.info("prepare streak=%s", streak)
        states = _quiet_states(runtime[0], 2)
        states["ESP"].latents["external_conflict_pressure"] = 0.40
        persistence = _persistence_for(
            states,
            last_day=2,
            overrides={"ESP": (("PHASE_STABLE_TENSION_V1", streak),)},
        )
        return states, persistence

    states_a, persistence_a = prepare(runtime_a, 1)
    states_b, persistence_b = prepare(runtime_b, 2)

    result_a = run_day_transaction(
        states=states_a,
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=_disable_all_events(runtime_a[4]),
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_phase_transitions=True,
        phase_config=runtime_a[7],
        phase_transition_config=runtime_a[8],
        phase_persistence=persistence_a,
    )
    result_b = run_day_transaction(
        states=states_b,
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=_disable_all_events(runtime_b[4]),
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_phase_transitions=True,
        phase_config=runtime_b[7],
        phase_transition_config=runtime_b[8],
        phase_persistence=persistence_b,
    )

    assert result_a.transaction_id != result_b.transaction_id


def test_phase_history_is_required_after_day_zero() -> None:
    logger.info("test_phase_history_is_required_after_day_zero")
    runtime = _runtime(seed=912)
    states = _quiet_states(runtime[0], 1)
    rng_before = runtime[5].describe()
    trace = TraceLedger()

    with pytest.raises(ValueError, match="Phase persistence is required"):
        run_day_transaction(
            states=states,
            graph=runtime[1],
            day_config=runtime[2],
            engine_state_registry=runtime[3],
            parameter_registry=_disable_all_events(runtime[4]),
            profile="synthetic_smoke_v1",
            rng=runtime[5],
            manifest=runtime[6],
            trace=trace,
            enable_phase_transitions=True,
            phase_config=runtime[7],
            phase_transition_config=runtime[8],
            phase_persistence=None,
        )

    assert runtime[5].describe() == rng_before
    assert trace.records == []


def test_invalid_phase_arbitration_rolls_back_rng_trace_and_states() -> None:
    logger.info("test_invalid_phase_arbitration_rolls_back_rng_trace_and_states")
    runtime = _runtime(seed=913)
    states = _quiet_states(runtime[0], 0)
    state_hashes_before = {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    }
    rng_before = runtime[5].describe()
    trace = TraceLedger()
    broken_transition = copy.deepcopy(runtime[8])
    broken_transition["arbitration"]["policy"] = "UNSUPPORTED"

    with pytest.raises(ValueError, match="Unsupported phase arbitration policy"):
        run_day_transaction(
            states=states,
            graph=runtime[1],
            day_config=runtime[2],
            engine_state_registry=runtime[3],
            parameter_registry=runtime[4],
            profile="synthetic_smoke_v1",
            rng=runtime[5],
            manifest=runtime[6],
            trace=trace,
            enable_phase_transitions=True,
            phase_config=runtime[7],
            phase_transition_config=broken_transition,
            phase_persistence=None,
        )

    assert runtime[5].describe() == rng_before
    assert trace.records == []
    assert {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    } == state_hashes_before
