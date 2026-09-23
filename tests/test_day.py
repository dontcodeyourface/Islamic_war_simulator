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
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 2026):
    logger.info("_runtime seed=%s", seed)
    graph_config = load_yaml(ROOT / "config/graph/country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    day_config = load_yaml(ROOT / "config/engine/day_transaction_v1.yaml")

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
    states = {}
    for iso3 in sorted(snapshots):
        states[iso3] = initialize_hybrid_state(
            snapshot=snapshots[iso3],
            engine_state_registry=state_registry,
            normalization_registry=normalization,
            parameter_registry=parameters,
            feature_map=feature_map,
            rng=rng,
            trace=TraceLedger(),
            profile="synthetic_smoke_v1",
        )

    manifest = build_manifest(
        run_id="day-test-run",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.7.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={
            iso3: canonical_hash(snapshot)
            for iso3, snapshot in sorted(snapshots.items())
        },
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-DAY-TEST",
        scenario_hash=canonical_hash({"scenario": "day-test"}),
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
            "typed_graph",
            "event_engine",
            "event_effects",
            "owner_resolver",
            "day_transaction",
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


def _force_spain_morocco_and_spain_protest(states: dict) -> None:
    logger.info("_force_spain_morocco_and_spain_protest")
    for state in states.values():
        state.latents["external_conflict_pressure"] = 0.0
        state.latents["polarization"] = 0.0
        state.latents["inflation_pressure"] = 0.0
        state.latents["unemployment_pressure"] = 0.0
        state.latents["government_legitimacy"] = 1.0
        state.latents["social_cohesion"] = 1.0
        state.latents["public_order_stress"] = 0.10

    states["ESP"].latents["external_conflict_pressure"] = 1.0
    states["MAR"].latents["external_conflict_pressure"] = 1.0

    states["ESP"].latents["polarization"] = 1.0
    states["ESP"].latents["inflation_pressure"] = 1.0
    states["ESP"].latents["unemployment_pressure"] = 1.0
    states["ESP"].latents["government_legitimacy"] = 0.0
    states["ESP"].latents["social_cohesion"] = 0.0
    states["ESP"].latents["public_order_stress"] = 0.40


def test_no_event_day_advances_all_nodes_once_without_mutating_inputs() -> None:
    logger.info("test_no_event_day_advances_all_nodes_once_without_mutating_inputs")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime()
    parameters = _disable_all_events(parameters)
    before = {
        node_id: state.to_dict()
        for node_id, state in sorted(states.items())
    }
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
    )

    assert result.day_from == 0
    assert result.day_to == 1
    assert len(result.events) == 0
    assert len(result.proposals) == 0
    assert len(result.resolutions) == 0
    assert set(result.states) == set(states)

    for node_id in sorted(states):
        assert states[node_id].to_dict() == before[node_id]
        assert result.states[node_id].day == 1
        assert result.states[node_id].latents == states[node_id].latents

    checkpoints = [
        item for item in trace.records
        if item["record_type"] == "daily_checkpoint"
    ]
    assert len(checkpoints) == 5
    assert trace.records[0]["record_type"] == "day_transaction_started"
    assert trace.records[-1]["record_type"] == "day_transaction_committed"


def test_generated_events_resolve_atomically_from_common_beginning_state() -> None:
    logger.info("test_generated_events_resolve_atomically_from_common_beginning_state")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime()
    _force_spain_morocco_and_spain_protest(states)
    before_spain_public_order = states["ESP"].latents["public_order_stress"]
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
    )

    event_types = sorted(event.event_type for event in result.events)
    assert event_types == [
        "INTERSTATE_INCIDENT_V1",
        "MASS_PROTEST_TRIGGER_V1",
    ]
    assert all(event.provenance_class == "GENERATED" for event in result.events)

    public_order_proposals = [
        proposal
        for proposal in result.proposals
        if proposal.target_node == "ESP"
        and proposal.variable == "public_order_stress"
    ]
    assert len(public_order_proposals) == 2
    assert all(
        proposal.value_before == pytest.approx(before_spain_public_order)
        for proposal in public_order_proposals
    )

    public_order_resolution = next(
        record
        for record in result.resolutions
        if record.target_node == "ESP"
        and record.variable == "public_order_stress"
    )
    assert public_order_resolution.raw_sum_delta == pytest.approx(0.085)
    assert public_order_resolution.value_before == pytest.approx(0.40)
    assert public_order_resolution.value_after == pytest.approx(0.485)
    assert result.states["ESP"].latents["public_order_stress"] == pytest.approx(
        0.485
    )
    assert states["ESP"].latents["public_order_stress"] == pytest.approx(0.40)


def test_day_transaction_exposes_clamp_in_checkpoint() -> None:
    logger.info("test_day_transaction_exposes_clamp_in_checkpoint")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime()
    _force_spain_morocco_and_spain_protest(states)
    states["ESP"].latents["external_conflict_pressure"] = 0.97
    states["MAR"].latents["external_conflict_pressure"] = 1.0
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
    )

    record = next(
        item
        for item in result.resolutions
        if item.target_node == "ESP"
        and item.variable == "external_conflict_pressure"
    )
    assert record.proposed_unbounded_value == pytest.approx(1.03)
    assert record.value_after == pytest.approx(1.0)
    assert record.clamp_amount == pytest.approx(0.03)

    checkpoint = next(
        item
        for item in trace.records
        if item["record_type"] == "daily_checkpoint"
        and item["node_id"] == "ESP"
    )
    assert record.resolution_id in checkpoint["constraint_clamps"]


def test_day_transaction_replays_exactly() -> None:
    logger.info("test_day_transaction_replays_exactly")
    runtime_a = _runtime(seed=444)
    runtime_b = _runtime(seed=444)
    _force_spain_morocco_and_spain_protest(runtime_a[0])
    _force_spain_morocco_and_spain_protest(runtime_b[0])
    trace_a = TraceLedger()
    trace_b = TraceLedger()

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=runtime_a[4],
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=trace_a,
    )
    result_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=runtime_b[4],
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=trace_b,
    )

    assert result_a.to_dict() == result_b.to_dict()
    assert trace_a.records == trace_b.records
    assert runtime_a[5].describe() == runtime_b[5].describe()


def test_day_transaction_is_state_dict_order_independent() -> None:
    logger.info("test_day_transaction_is_state_dict_order_independent")
    runtime_a = _runtime(seed=555)
    runtime_b = _runtime(seed=555)
    _force_spain_morocco_and_spain_protest(runtime_a[0])
    _force_spain_morocco_and_spain_protest(runtime_b[0])
    reversed_states = dict(reversed(list(runtime_b[0].items())))

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=runtime_a[4],
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
    )
    result_b = run_day_transaction(
        states=reversed_states,
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=runtime_b[4],
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
    )

    assert result_a.to_dict() == result_b.to_dict()


def test_node_mismatch_fails_before_rng_or_trace_side_effects() -> None:
    logger.info("test_node_mismatch_fails_before_rng_or_trace_side_effects")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime()
    states.pop("GBR")
    rng_before = rng.describe()
    trace = TraceLedger()

    with pytest.raises(ValueError, match="State/graph node mismatch"):
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
        )

    assert rng.describe() == rng_before
    assert trace.records == []


def test_failure_after_event_rng_consumption_rolls_back_rng_trace_and_state() -> None:
    logger.info(
        "test_failure_after_event_rng_consumption_rolls_back_rng_trace_and_state"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=909)
    state_hashes_before = {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    }
    rng_before = rng.describe()
    trace = TraceLedger()

    broken_parameters = copy.deepcopy(parameters)
    broken_parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "OWNER_RESOLVER_POLICY_SYN_V1"
    ] = None

    with pytest.raises(ValueError, match="Missing owner resolver parameter"):
        run_day_transaction(
            states=states,
            graph=graph,
            day_config=day_config,
            engine_state_registry=registry,
            parameter_registry=broken_parameters,
            profile="synthetic_smoke_v1",
            rng=rng,
            manifest=manifest,
            trace=trace,
        )

    assert rng.describe() == rng_before
    assert trace.records == []
    assert {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    } == state_hashes_before


def test_recovery_is_aggregated_with_event_effects_in_single_resolution_pass() -> None:
    logger.info(
        "test_recovery_is_aggregated_with_event_effects_in_single_resolution_pass"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=818)
    recovery_config = load_yaml(ROOT / "config/engine/recovery_v1.yaml")
    _force_spain_morocco_and_spain_protest(states)

    baseline = float(states["ESP"].metadata["initial_latents"]["public_order_stress"])
    current = float(states["ESP"].latents["public_order_stress"])
    assert current == pytest.approx(0.40)
    expected_recovery = (baseline - current) * parameters["parameter_sets"][
        "synthetic_smoke_v1"
    ]["parameters"]["DYNAMIC_GAINS_SYN_V1"]["value"]["fast_recovery"]

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
        proposal
        for proposal in result.proposals
        if proposal.target_node == "ESP"
        and proposal.variable == "public_order_stress"
    ]
    assert len(proposals) == 3
    assert all(proposal.value_before == pytest.approx(current) for proposal in proposals)

    event_delta = sum(
        proposal.raw_delta
        for proposal in proposals
        if proposal.event_type != "ENDOGENOUS_RECOVERY_V1"
    )
    recovery_delta = next(
        proposal.raw_delta
        for proposal in proposals
        if proposal.event_type == "ENDOGENOUS_RECOVERY_V1"
    )
    assert event_delta == pytest.approx(0.085)
    assert recovery_delta == pytest.approx(expected_recovery)

    resolution = next(
        record
        for record in result.resolutions
        if record.target_node == "ESP"
        and record.variable == "public_order_stress"
    )
    assert len(resolution.proposal_ids) == 3
    assert resolution.raw_sum_delta == pytest.approx(event_delta + recovery_delta)
    assert resolution.value_after == pytest.approx(
        current + event_delta + recovery_delta
    )


def test_recovery_config_changes_transaction_identity() -> None:
    logger.info("test_recovery_config_changes_transaction_identity")
    runtime_a = _runtime(seed=919)
    runtime_b = _runtime(seed=919)
    parameters_a = _disable_all_events(runtime_a[4])
    parameters_b = _disable_all_events(runtime_b[4])
    recovery_a = load_yaml(ROOT / "config/engine/recovery_v1.yaml")
    recovery_b = copy.deepcopy(recovery_a)
    recovery_b["status"] = "identity-test-variant"

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=parameters_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_recovery=True,
        recovery_config=recovery_a,
    )
    result_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=parameters_b,
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_recovery=True,
        recovery_config=recovery_b,
    )

    assert result_a.transaction_id != result_b.transaction_id
    assert result_a.states == result_b.states



def test_graph_spillover_trace_integrates_without_state_mutation() -> None:
    logger.info("test_graph_spillover_trace_integrates_without_state_mutation")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1001)
    parameters = _disable_all_events(parameters)
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")
    before = {
        node_id: dict(state.latents)
        for node_id, state in sorted(states.items())
    }
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
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
    )

    assert result.spillover_queue is not None
    assert result.spillover_queue.last_processed_day == 1
    assert len(result.spillover_candidates) == 140
    assert len(result.events) == 0
    assert len(result.proposals) == 0
    assert len(result.resolutions) == 0

    for node_id in sorted(states):
        assert result.states[node_id].latents == before[node_id]
        assert result.states[node_id].day == 1

    record_types = [item["record_type"] for item in trace.records]
    assert "graph_spillover_candidate" in record_types
    assert "graph_spillover_queue_committed" in record_types
    assert record_types.index("graph_spillover_candidate") < record_types.index(
        "event_candidate"
    )


def test_graph_spillover_queue_is_required_after_day_zero() -> None:
    logger.info("test_graph_spillover_queue_is_required_after_day_zero")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1002)
    parameters = _disable_all_events(parameters)
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

    day_one = run_day_transaction(
        states=states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
    )
    assert day_one.spillover_queue is not None

    rng_before = rng.describe()
    trace = TraceLedger()
    with pytest.raises(ValueError, match="Spillover queue is required after day zero"):
        run_day_transaction(
            states=day_one.states,
            graph=graph,
            day_config=day_config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            rng=rng,
            manifest=manifest,
            trace=trace,
            enable_graph_spillover=True,
            spillover_config=spillover_config,
            spillover_queue=None,
        )

    assert rng.describe() == rng_before
    assert trace.records == []


def test_graph_spillover_queue_supports_consecutive_day_replay() -> None:
    logger.info("test_graph_spillover_queue_supports_consecutive_day_replay")
    runtime_a = _runtime(seed=1003)
    runtime_b = _runtime(seed=1003)
    params_a = _disable_all_events(runtime_a[4])
    params_b = _disable_all_events(runtime_b[4])
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

    first_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=params_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
    )
    first_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=params_b,
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
    )
    assert first_a.spillover_queue is not None
    assert first_b.spillover_queue is not None

    second_a = run_day_transaction(
        states=first_a.states,
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=params_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=first_a.spillover_queue,
    )
    second_b = run_day_transaction(
        states=first_b.states,
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=params_b,
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=first_b.spillover_queue,
    )

    assert second_a.to_dict() == second_b.to_dict()
    assert second_a.spillover_queue is not None
    assert second_a.spillover_queue.last_processed_day == 2
