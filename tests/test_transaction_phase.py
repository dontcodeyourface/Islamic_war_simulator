from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.graph import build_structural_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.phases import PhasePersistenceState
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger
from iwsim.transaction import execute_day_transaction

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 950, run_id: str = "phase-tx"):
    logger.info("_runtime seed=%s run_id=%s", seed, run_id)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    graph_config = load_yaml(ROOT / "config/graph/base_country_graph_v1.yaml")
    transaction_config = load_yaml(ROOT / "config/engine/day_transaction_v2.yaml")
    phase_config = load_yaml(ROOT / "config/engine/phase_evaluator_v1.yaml")
    phase_resolver_config = load_yaml(
        ROOT / "config/engine/phase_transition_resolver_v1.yaml"
    )
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])

    graph = build_structural_graph(
        repo_root=ROOT,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )
    snapshots = {
        node_id: load_yaml(ROOT / spec["snapshot_path"])
        for node_id, spec in sorted(graph_config["nodes"].items())
    }
    rng = RNGManager(seed)
    states = {
        node_id: initialize_hybrid_state(
            snapshot=snapshots[node_id],
            engine_state_registry=state_registry,
            normalization_registry=normalization,
            parameter_registry=parameters,
            feature_map=feature_map,
            rng=rng,
            trace=TraceLedger(),
            profile="synthetic_smoke_v1",
        )
        for node_id in sorted(snapshots)
    }
    manifest = build_manifest(
        run_id=run_id,
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.9.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={node_id: "TEST" for node_id in sorted(snapshots)},
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-PHASE-TX",
        scenario_hash=canonical_hash({"scenario": "phase-tx"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=10,
        enabled_modules=("day_transaction", "phase_evaluator", "phase_resolver"),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return (
        state_registry,
        parameters,
        graph,
        transaction_config,
        phase_config,
        phase_resolver_config,
        rng,
        states,
        manifest,
    )


def _force_no_events(parameters: dict) -> dict:
    logger.info("_force_no_events")
    modified = copy.deepcopy(parameters)
    hazards = modified["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_WEIGHTS_SYN_V1"
    ]["value"]
    for config in hazards.values():
        config["generated_threshold"] = 1.1
    probability = modified["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0
    return modified


def _configure_esp_tension_signal(states: dict) -> None:
    logger.info("_configure_esp_tension_signal")
    states["ESP"].latents["external_conflict_pressure"] = 0.40
    states["ESP"].latents["polarization"] = 0.10
    states["ESP"].latents["public_order_stress"] = 0.10


def _run_day(
    runtime,
    *,
    states,
    persistence,
    trace,
    resolver_config=None,
):
    logger.info("_run_day state_day=%s", next(iter(states.values())).day)
    (
        state_registry,
        parameters,
        graph,
        transaction_config,
        phase_config,
        phase_resolver_config,
        rng,
        _,
        manifest,
    ) = runtime
    return execute_day_transaction(
        states=states,
        graph=graph,
        transaction_config=transaction_config,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
        phase_config=phase_config,
        phase_resolver_config=resolver_config or phase_resolver_config,
        phase_persistence=persistence,
        phase_context_flags={},
    )


def test_three_day_transaction_commits_stable_to_tension() -> None:
    logger.info("test_three_day_transaction_commits_stable_to_tension")
    runtime = list(_runtime())
    runtime[1] = _force_no_events(runtime[1])
    states = runtime[7]
    _configure_esp_tension_signal(states)
    persistence = {node_id: None for node_id in states}
    trace = TraceLedger()

    day1 = _run_day(
        tuple(runtime),
        states=states,
        persistence=persistence,
        trace=trace,
    )
    assert day1.states["ESP"].regimes["national_phase"] == "STABLE"
    assert dict(day1.phase_persistence["ESP"].streaks)[
        "PHASE_STABLE_TENSION_V1"
    ] == 1

    day2 = _run_day(
        tuple(runtime),
        states=day1.states,
        persistence=day1.phase_persistence,
        trace=trace,
    )
    assert day2.states["ESP"].regimes["national_phase"] == "STABLE"
    assert dict(day2.phase_persistence["ESP"].streaks)[
        "PHASE_STABLE_TENSION_V1"
    ] == 2

    day3 = _run_day(
        tuple(runtime),
        states=day2.states,
        persistence=day2.phase_persistence,
        trace=trace,
    )
    assert day3.states["ESP"].regimes["national_phase"] == "TENSION"
    assert day3.phase_persistence["ESP"].current_phase == "TENSION"
    assert day3.phase_persistence["ESP"].streaks == ()
    esp_commits = [
        commit for commit in day3.phase_commits
        if commit.node_id == "ESP"
    ]
    assert len(esp_commits) == 1
    assert esp_commits[0].from_phase == "STABLE"
    assert esp_commits[0].to_phase == "TENSION"

    checkpoint = next(
        record for record in trace.records
        if record["record_type"] == "daily_checkpoint"
        and record["day"] == 3
        and record["node_id"] == "ESP"
    )
    assert checkpoint["phase_transition_ids"] == [esp_commits[0].commit_id]


def test_v2_transaction_persists_phase_memory_for_all_nodes() -> None:
    logger.info("test_v2_transaction_persists_phase_memory_for_all_nodes")
    runtime = list(_runtime(seed=951))
    runtime[1] = _force_no_events(runtime[1])
    states = runtime[7]
    persistence = {node_id: None for node_id in states}
    result = _run_day(
        tuple(runtime),
        states=states,
        persistence=persistence,
        trace=TraceLedger(),
    )
    assert set(result.phase_persistence) == set(states)
    assert len(result.phase_evaluations) == len(states)


def test_phase_runtime_memory_changes_transaction_identity() -> None:
    logger.info("test_phase_runtime_memory_changes_transaction_identity")
    runtime_a = list(_runtime(seed=952, run_id="same-run"))
    runtime_b = list(_runtime(seed=952, run_id="same-run"))
    runtime_a[1] = _force_no_events(runtime_a[1])
    runtime_b[1] = _force_no_events(runtime_b[1])
    states_a = runtime_a[7]
    states_b = runtime_b[7]

    persistence_a = {node_id: None for node_id in states_a}
    persistence_b = {node_id: None for node_id in states_b}
    persistence_b["ESP"] = PhasePersistenceState(
        node_id="ESP",
        current_phase="STABLE",
        last_evaluated_day=0,
        streaks=(("PHASE_STABLE_TENSION_V1", 2),),
    )

    result_a = _run_day(
        tuple(runtime_a),
        states=states_a,
        persistence=persistence_a,
        trace=TraceLedger(),
    )
    result_b = _run_day(
        tuple(runtime_b),
        states=states_b,
        persistence=persistence_b,
        trace=TraceLedger(),
    )
    assert result_a.transaction_id != result_b.transaction_id


def test_phase_failure_rolls_back_whole_day() -> None:
    logger.info("test_phase_failure_rolls_back_whole_day")
    runtime = list(_runtime(seed=953, run_id="rollback-phase"))
    runtime[1] = _force_no_events(runtime[1])
    states = runtime[7]
    _configure_esp_tension_signal(states)

    persistence = {node_id: None for node_id in states}
    persistence["ESP"] = PhasePersistenceState(
        node_id="ESP",
        current_phase="STABLE",
        last_evaluated_day=0,
        streaks=(("PHASE_STABLE_TENSION_V1", 2),),
    )
    broken_resolver = copy.deepcopy(runtime[5])
    broken_resolver["arbitration"]["policy"] = "unsupported"

    rng_before = runtime[6].describe()
    hashes_before = {
        node_id: state.state_hash()
        for node_id, state in states.items()
    }
    trace = TraceLedger()

    with pytest.raises(ValueError, match="Unsupported phase arbitration policy"):
        _run_day(
            tuple(runtime),
            states=states,
            persistence=persistence,
            trace=trace,
            resolver_config=broken_resolver,
        )

    assert runtime[6].describe() == rng_before
    assert trace.records == []
    assert {
        node_id: state.state_hash()
        for node_id, state in states.items()
    } == hashes_before
    assert all(state.day == 0 for state in states.values())


def test_three_day_phase_transaction_replays_exactly() -> None:
    logger.info("test_three_day_phase_transaction_replays_exactly")
    def run(seed: int):
        logger.info("run replay seed=%s", seed)
        runtime = list(_runtime(seed=seed, run_id="phase-replay"))
        runtime[1] = _force_no_events(runtime[1])
        states = runtime[7]
        _configure_esp_tension_signal(states)
        persistence = {node_id: None for node_id in states}
        trace = TraceLedger()
        results = []
        for _ in range(3):
            result = _run_day(
                tuple(runtime),
                states=states,
                persistence=persistence,
                trace=trace,
            )
            results.append(result.to_dict())
            states = result.states
            persistence = result.phase_persistence
        return results, trace.records, runtime[6].describe()

    a = run(954)
    b = run(954)
    assert a == b
