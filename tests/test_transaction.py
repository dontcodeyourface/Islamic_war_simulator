from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.graph import build_structural_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger
from iwsim.transaction import execute_day_transaction

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 700, run_id: str = "tx-test"):
    logger.info("_runtime seed=%s run_id=%s", seed, run_id)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    graph_config = load_yaml(ROOT / "config/graph/base_country_graph_v1.yaml")
    transaction_config = load_yaml(ROOT / "config/engine/day_transaction_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])

    graph = build_structural_graph(
        repo_root=ROOT,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )

    snapshots = {}
    for node_id, spec in sorted(graph_config["nodes"].items()):
        snapshots[node_id] = load_yaml(ROOT / spec["snapshot_path"])

    rng = RNGManager(seed)
    states = {}
    for node_id in sorted(snapshots):
        states[node_id] = initialize_hybrid_state(
            snapshot=snapshots[node_id],
            engine_state_registry=state_registry,
            normalization_registry=normalization,
            parameter_registry=parameters,
            feature_map=feature_map,
            rng=rng,
            trace=TraceLedger(),
            profile="synthetic_smoke_v1",
        )

    manifest = build_manifest(
        run_id=run_id,
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.7.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={node_id: "TEST" for node_id in sorted(snapshots)},
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-DAYTX-TEST",
        scenario_hash=canonical_hash({"scenario": "daytx-test"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=1,
        enabled_modules=(
            "initializer",
            "structural_graph",
            "event_engine",
            "event_effect_proposals",
            "owner_resolver",
            "day_transaction",
            "trace",
        ),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return (
        state_registry,
        parameters,
        graph,
        transaction_config,
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


def _force_random_events_then_effect_failure(parameters: dict) -> dict:
    logger.info("_force_random_events_then_effect_failure")
    modified = copy.deepcopy(parameters)
    hazards = modified["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_WEIGHTS_SYN_V1"
    ]["value"]
    for config in hazards.values():
        config["generated_threshold"] = 1.1
    probability = modified["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 1.0
    probability["score_scale"] = 0.0
    del modified["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_EFFECT_PROPOSALS_SYN_V1"
    ]
    return modified


def _force_spain_generated_events(states: dict) -> None:
    logger.info("_force_spain_generated_events")
    esp = states["ESP"]
    mar = states["MAR"]
    esp.latents["external_conflict_pressure"] = 0.95
    mar.latents["external_conflict_pressure"] = 0.95
    esp.latents["polarization"] = 1.0
    esp.latents["inflation_pressure"] = 1.0
    esp.latents["unemployment_pressure"] = 1.0
    esp.latents["government_legitimacy"] = 0.0
    esp.latents["social_cohesion"] = 0.0


def test_atomic_day_without_events_advances_all_nodes_once() -> None:
    logger.info("test_atomic_day_without_events_advances_all_nodes_once")
    (
        state_registry,
        parameters,
        graph,
        transaction_config,
        rng,
        states,
        manifest,
    ) = _runtime()
    parameters = _force_no_events(parameters)
    original_hashes = {
        node_id: state.state_hash()
        for node_id, state in states.items()
    }
    original_latents = {
        node_id: dict(state.latents)
        for node_id, state in states.items()
    }
    trace = TraceLedger()

    result = execute_day_transaction(
        states=states,
        graph=graph,
        transaction_config=transaction_config,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
    )

    assert result.day_from == 0
    assert result.day_to == 1
    assert len(result.candidate_results) == len(graph.edges) + len(graph.nodes)
    assert result.events == ()
    assert result.proposals == ()
    assert result.resolutions == ()
    assert set(result.states) == set(graph.nodes)
    assert all(state.day == 1 for state in result.states.values())
    for node_id in states:
        assert states[node_id].day == 0
        assert states[node_id].latents == original_latents[node_id]
        assert states[node_id].state_hash() == original_hashes[node_id]
        assert result.states[node_id].latents == original_latents[node_id]

    assert trace.records[0]["record_type"] == "day_transaction_started"
    assert trace.records[-1]["record_type"] == "day_transaction_committed"
    checkpoints = [
        record for record in trace.records
        if record["record_type"] == "daily_checkpoint"
    ]
    assert len(checkpoints) == 5


def test_generated_events_are_resolved_from_same_beginning_of_day_state() -> None:
    logger.info(
        "test_generated_events_are_resolved_from_same_beginning_of_day_state"
    )
    (
        state_registry,
        parameters,
        graph,
        transaction_config,
        rng,
        states,
        manifest,
    ) = _runtime()
    _force_spain_generated_events(states)
    before_esp = dict(states["ESP"].latents)
    before_mar = dict(states["MAR"].latents)
    trace = TraceLedger()

    result = execute_day_transaction(
        states=states,
        graph=graph,
        transaction_config=transaction_config,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
    )

    event_types = {(event.event_type, event.actors) for event in result.events}
    assert ("INTERSTATE_INCIDENT_V1", ("ESP", "MAR")) in event_types
    assert ("MASS_PROTEST_TRIGGER_V1", ("ESP",)) in event_types

    esp = result.states["ESP"]
    mar = result.states["MAR"]
    assert esp.day == 1
    assert mar.day == 1
    assert states["ESP"].day == 0
    assert states["ESP"].latents == before_esp
    assert states["MAR"].latents == before_mar

    assert esp.latents["external_conflict_pressure"] == pytest.approx(1.0)
    assert esp.latents["public_order_stress"] > before_esp["public_order_stress"]
    assert esp.latents["communal_fear"] > before_esp["communal_fear"]
    assert esp.latents["government_legitimacy"] == pytest.approx(0.0)
    assert esp.latents["social_cohesion"] == pytest.approx(0.0)
    assert mar.latents["external_conflict_pressure"] == pytest.approx(1.0)

    esp_resolutions = [
        record for record in result.resolutions
        if record.target_node == "ESP"
    ]
    assert any(
        record.variable == "public_order_stress"
        and len(record.proposal_ids) >= 2
        for record in esp_resolutions
    )
    assert any(record.clamp_amount != 0.0 for record in esp_resolutions)


def test_day_transaction_replays_exactly() -> None:
    logger.info("test_day_transaction_replays_exactly")
    runtime_a = _runtime(seed=701, run_id="replay-run")
    runtime_b = _runtime(seed=701, run_id="replay-run")
    _force_spain_generated_events(runtime_a[5])
    _force_spain_generated_events(runtime_b[5])
    trace_a = TraceLedger()
    trace_b = TraceLedger()

    result_a = execute_day_transaction(
        states=runtime_a[5],
        graph=runtime_a[2],
        transaction_config=runtime_a[3],
        engine_state_registry=runtime_a[0],
        parameter_registry=runtime_a[1],
        profile="synthetic_smoke_v1",
        rng=runtime_a[4],
        manifest=runtime_a[6],
        trace=trace_a,
    )
    result_b = execute_day_transaction(
        states=runtime_b[5],
        graph=runtime_b[2],
        transaction_config=runtime_b[3],
        engine_state_registry=runtime_b[0],
        parameter_registry=runtime_b[1],
        profile="synthetic_smoke_v1",
        rng=runtime_b[4],
        manifest=runtime_b[6],
        trace=trace_b,
    )

    assert result_a.to_dict() == result_b.to_dict()
    assert trace_a.records == trace_b.records
    assert runtime_a[4].describe() == runtime_b[4].describe()


def test_day_transaction_is_state_dict_order_independent() -> None:
    logger.info("test_day_transaction_is_state_dict_order_independent")
    runtime_a = _runtime(seed=702, run_id="order-run")
    runtime_b = _runtime(seed=702, run_id="order-run")
    _force_spain_generated_events(runtime_a[5])
    _force_spain_generated_events(runtime_b[5])

    reversed_states = dict(reversed(list(runtime_b[5].items())))
    trace_a = TraceLedger()
    trace_b = TraceLedger()
    result_a = execute_day_transaction(
        states=runtime_a[5],
        graph=runtime_a[2],
        transaction_config=runtime_a[3],
        engine_state_registry=runtime_a[0],
        parameter_registry=runtime_a[1],
        profile="synthetic_smoke_v1",
        rng=runtime_a[4],
        manifest=runtime_a[6],
        trace=trace_a,
    )
    result_b = execute_day_transaction(
        states=reversed_states,
        graph=runtime_b[2],
        transaction_config=runtime_b[3],
        engine_state_registry=runtime_b[0],
        parameter_registry=runtime_b[1],
        profile="synthetic_smoke_v1",
        rng=runtime_b[4],
        manifest=runtime_b[6],
        trace=trace_b,
    )

    assert result_a.to_dict() == result_b.to_dict()
    assert trace_a.records == trace_b.records


def test_failed_day_rolls_back_rng_trace_and_state() -> None:
    logger.info("test_failed_day_rolls_back_rng_trace_and_state")
    (
        state_registry,
        parameters,
        graph,
        transaction_config,
        rng,
        states,
        manifest,
    ) = _runtime(seed=703, run_id="rollback-run")
    broken_parameters = _force_random_events_then_effect_failure(parameters)
    before_rng = rng.describe()
    before_hashes = {
        node_id: state.state_hash()
        for node_id, state in states.items()
    }
    trace = TraceLedger()

    with pytest.raises(ValueError, match="Missing effect parameter"):
        execute_day_transaction(
            states=states,
            graph=graph,
            transaction_config=transaction_config,
            engine_state_registry=state_registry,
            parameter_registry=broken_parameters,
            profile="synthetic_smoke_v1",
            rng=rng,
            manifest=manifest,
            trace=trace,
        )

    assert rng.describe() == before_rng
    assert trace.records == []
    assert {
        node_id: state.state_hash()
        for node_id, state in states.items()
    } == before_hashes
    assert all(state.day == 0 for state in states.values())


def test_node_mismatch_fails_before_any_side_effect() -> None:
    logger.info("test_node_mismatch_fails_before_any_side_effect")
    (
        state_registry,
        parameters,
        graph,
        transaction_config,
        rng,
        states,
        manifest,
    ) = _runtime(seed=704, run_id="node-mismatch")
    reduced_states = dict(states)
    del reduced_states["GBR"]
    before_rng = rng.describe()
    trace = TraceLedger()

    with pytest.raises(ValueError, match="State/graph node mismatch"):
        execute_day_transaction(
            states=reduced_states,
            graph=graph,
            transaction_config=transaction_config,
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            rng=rng,
            manifest=manifest,
            trace=trace,
        )

    assert rng.describe() == before_rng
    assert trace.records == []
