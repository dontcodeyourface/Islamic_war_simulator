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


def _force_only_spain_morocco_interstate_event(parameters: dict) -> dict:
    logger.info("_force_only_spain_morocco_interstate_event")
    patched = copy.deepcopy(parameters)
    hazards = patched["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_WEIGHTS_SYN_V1"
    ]["value"]
    interstate = hazards["INTERSTATE_INCIDENT_V1"]
    interstate["base_score"] = 0.0
    interstate["generated_threshold"] = 0.9
    interstate["weights"] = {
        "external_conflict_pressure_mean": 1.0,
        "geographic_proximity": 0.0,
        "land_border": 0.0,
        "alliance_deterrence": 0.0,
    }
    hazards["MASS_PROTEST_TRIGGER_V1"]["generated_threshold"] = 2.0
    probability = patched["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0
    return patched


def _set_reciprocal_test_state(states: dict) -> None:
    logger.info("_set_reciprocal_test_state")
    for state in states.values():
        state.latents["violent_islamist_pressure"] = 0.0
        state.latents["violent_ultranationalist_pressure"] = 0.0
        state.latents["revolutionary_extremist_pressure"] = 0.0
        state.latents["communal_fear"] = 0.0
        state.latents["civilizational_narrative_strength"] = 0.0
        state.latents["polarization"] = 0.0
        state.latents["foreign_support_nonstate"] = 0.0
        state.latents["prison_control"] = 1.0
        state.latents["social_cohesion"] = 0.0
        state.latents["government_legitimacy"] = 0.0
        state.latents["police_effective_capacity"] = 0.0
        state.latents["intelligence_effectiveness"] = 0.0

    states["ESP"].latents["violent_islamist_pressure"] = 0.8
    states["ESP"].latents["violent_ultranationalist_pressure"] = 0.2
    states["ESP"].latents["communal_fear"] = 1.0



def _set_security_chain_test_state(states: dict) -> None:
    logger.info("_set_security_chain_test_state")
    for state in states.values():
        state.latents["public_order_stress"] = 0.0
        state.latents["external_conflict_pressure"] = 0.0
        state.latents["organized_armed_actor_capacity"] = 0.0
        state.latents["salary_payment_continuity"] = 1.0
        state.latents["government_legitimacy"] = 1.0
        state.latents["transport_logistics_functionality"] = 1.0
        state.latents["police_effective_capacity"] = 1.0
        state.latents["intelligence_effectiveness"] = 1.0
        state.latents["administrative_capacity"] = 1.0
        state.latents["social_cohesion"] = 1.0
        state.latents["security_chain_cohesion"] = 1.0
        state.latents["command_cohesion"] = 1.0
        state.latents["constitutional_loyalty"] = 1.0
        state.latents["operational_fatigue"] = 0.0

    esp = states["ESP"]
    esp.latents["public_order_stress"] = 1.0
    esp.latents["external_conflict_pressure"] = 1.0
    esp.latents["organized_armed_actor_capacity"] = 1.0
    esp.latents["salary_payment_continuity"] = 0.0
    esp.latents["government_legitimacy"] = 0.0
    esp.latents["transport_logistics_functionality"] = 0.0
    esp.latents["police_effective_capacity"] = 0.0
    esp.latents["intelligence_effectiveness"] = 0.0
    esp.latents["administrative_capacity"] = 0.0
    esp.latents["social_cohesion"] = 0.0
    esp.latents["security_chain_cohesion"] = 0.8
    esp.latents["command_cohesion"] = 0.8
    esp.latents["constitutional_loyalty"] = 0.8
    esp.latents["operational_fatigue"] = 0.2

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
    latencies = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "GRAPH_LATENCIES_SYN_V1"
    ]["value"]
    latencies["geographic_proximity"] = [1, 1]
    latencies["land_border"] = [1, 1]
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



def test_graph_spillover_does_not_shift_event_rng_streams() -> None:
    logger.info("test_graph_spillover_does_not_shift_event_rng_streams")
    runtime_a = _runtime(seed=1004)
    runtime_b = _runtime(seed=1004)
    params_a = _disable_all_events(runtime_a[4])
    params_b = _disable_all_events(runtime_b[4])
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=params_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
    )
    result_b = run_day_transaction(
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

    assert [item.to_dict() for item in result_a.candidates] == [
        item.to_dict() for item in result_b.candidates
    ]
    assert runtime_a[5].describe() == runtime_b[5].describe()
    assert result_a.transaction_id != result_b.transaction_id



def test_matured_graph_spillover_is_resolved_on_next_day() -> None:
    logger.info("test_matured_graph_spillover_is_resolved_on_next_day")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1005)
    parameters = _disable_all_events(parameters)
    latencies = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "GRAPH_LATENCIES_SYN_V1"
    ]["value"]
    latencies["geographic_proximity"] = [1, 1]
    latencies["land_border"] = [1, 1]
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

    for state in states.values():
        state.latents["external_conflict_pressure"] = 0.0
    states["ESP"].latents["external_conflict_pressure"] = 1.0

    first = run_day_transaction(
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
    assert first.spillover_queue is not None
    assert first.spillover_proposals == ()
    assert first.states["MAR"].latents["external_conflict_pressure"] == pytest.approx(
        0.0
    )

    trace = TraceLedger()
    second = run_day_transaction(
        states=first.states,
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
        spillover_queue=first.spillover_queue,
    )

    mar_proposals = [
        proposal
        for proposal in second.spillover_proposals
        if proposal.target_node == "MAR"
        and proposal.variable == "external_conflict_pressure"
    ]
    assert mar_proposals
    expected_mar_delta = sum(item.raw_delta for item in mar_proposals)
    assert second.states["MAR"].latents[
        "external_conflict_pressure"
    ] == pytest.approx(expected_mar_delta)

    mar_resolution = next(
        record
        for record in second.resolutions
        if record.target_node == "MAR"
        and record.variable == "external_conflict_pressure"
    )
    assert mar_resolution.raw_sum_delta == pytest.approx(expected_mar_delta)

    mar_checkpoint = next(
        item
        for item in trace.records
        if item["record_type"] == "daily_checkpoint"
        and item["node_id"] == "MAR"
    )
    assert set(mar_checkpoint["spillover_ids_applied"]) == {
        proposal.event_id for proposal in mar_proposals
    }
    assert all(
        proposal.value_before == pytest.approx(0.0)
        for proposal in mar_proposals
    )



def test_matured_spillover_and_event_share_one_owner_resolution() -> None:
    logger.info("test_matured_spillover_and_event_share_one_owner_resolution")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1006)
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

    day_one_parameters = _disable_all_events(parameters)
    day_one_latencies = day_one_parameters["parameter_sets"]["synthetic_smoke_v1"][
        "parameters"
    ]["GRAPH_LATENCIES_SYN_V1"]["value"]
    day_one_latencies["geographic_proximity"] = [1, 1]
    day_one_latencies["land_border"] = [1, 1]

    for state in states.values():
        state.latents["external_conflict_pressure"] = 0.0
    states["ESP"].latents["external_conflict_pressure"] = 0.8
    states["MAR"].latents["external_conflict_pressure"] = 1.0

    first = run_day_transaction(
        states=states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=day_one_parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
    )
    assert first.spillover_queue is not None
    assert first.spillover_proposals == ()

    day_two_parameters = _force_only_spain_morocco_interstate_event(parameters)
    day_two_latencies = day_two_parameters["parameter_sets"]["synthetic_smoke_v1"][
        "parameters"
    ]["GRAPH_LATENCIES_SYN_V1"]["value"]
    day_two_latencies["geographic_proximity"] = [1, 1]
    day_two_latencies["land_border"] = [1, 1]

    second = run_day_transaction(
        states=first.states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=day_two_parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=first.spillover_queue,
    )

    esp_external = [
        proposal
        for proposal in second.proposals
        if proposal.target_node == "ESP"
        and proposal.variable == "external_conflict_pressure"
    ]
    event_proposals = [
        proposal
        for proposal in esp_external
        if proposal.event_type == "INTERSTATE_INCIDENT_V1"
    ]
    spillover_proposals = [
        proposal
        for proposal in esp_external
        if proposal.event_type == "GRAPH_SPILLOVER_V1"
    ]

    assert len(event_proposals) == 1
    assert len(spillover_proposals) == 2
    assert all(proposal.value_before == pytest.approx(0.8) for proposal in esp_external)
    assert event_proposals[0].raw_delta == pytest.approx(0.06)

    expected_delta = sum(proposal.raw_delta for proposal in esp_external)
    resolution = next(
        record
        for record in second.resolutions
        if record.target_node == "ESP"
        and record.variable == "external_conflict_pressure"
    )
    assert set(resolution.proposal_ids) == {
        proposal.proposal_id for proposal in esp_external
    }
    assert resolution.raw_sum_delta == pytest.approx(expected_delta)
    assert resolution.value_before == pytest.approx(0.8)
    assert resolution.value_after == pytest.approx(0.8 + expected_delta)



def test_matured_spillover_and_event_share_single_owner_resolution() -> None:
    logger.info(
        "test_matured_spillover_and_event_share_single_owner_resolution"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1006)
    day_one_parameters = _disable_all_events(parameters)
    latencies = day_one_parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "GRAPH_LATENCIES_SYN_V1"
    ]["value"]
    latencies["geographic_proximity"] = [1, 1]
    latencies["land_border"] = [1, 1]
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

    for state in states.values():
        state.latents["external_conflict_pressure"] = 0.0
    states["ESP"].latents["external_conflict_pressure"] = 1.0

    first = run_day_transaction(
        states=states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=day_one_parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
    )
    assert first.spillover_queue is not None

    day_two_parameters = copy.deepcopy(day_one_parameters)
    day_two_parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_WEIGHTS_SYN_V1"
    ]["value"]["INTERSTATE_INCIDENT_V1"]["generated_threshold"] = 0.0

    mar_before = float(first.states["MAR"].latents["external_conflict_pressure"])
    trace = TraceLedger()
    second = run_day_transaction(
        states=first.states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=day_two_parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=first.spillover_queue,
    )

    mar_proposals = [
        proposal
        for proposal in second.proposals
        if proposal.target_node == "MAR"
        and proposal.variable == "external_conflict_pressure"
    ]
    assert any(
        proposal.event_type == "GRAPH_SPILLOVER_V1"
        for proposal in mar_proposals
    )
    assert any(
        proposal.event_type == "INTERSTATE_INCIDENT_V1"
        for proposal in mar_proposals
    )
    assert all(
        proposal.value_before == pytest.approx(mar_before)
        for proposal in mar_proposals
    )

    resolution = next(
        record
        for record in second.resolutions
        if record.target_node == "MAR"
        and record.variable == "external_conflict_pressure"
    )
    expected_delta = sum(proposal.raw_delta for proposal in mar_proposals)
    assert resolution.raw_sum_delta == pytest.approx(expected_delta)
    assert set(resolution.proposal_ids) == {
        proposal.proposal_id for proposal in mar_proposals
    }
    assert second.states["MAR"].latents[
        "external_conflict_pressure"
    ] == pytest.approx(min(1.0, mar_before + expected_delta))



def test_extremist_network_dynamics_resolve_atomically() -> None:
    logger.info("test_extremist_network_dynamics_resolve_atomically")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1010)
    parameters = _disable_all_events(parameters)
    network_config = load_yaml(
        ROOT / "config/engine/extremist_network_dynamics_v1.yaml"
    )

    esp = states["ESP"]
    esp.latents["polarization"] = 1.0
    esp.latents["communal_fear"] = 1.0
    esp.latents["civilizational_narrative_strength"] = 1.0
    esp.latents["foreign_support_nonstate"] = 1.0
    esp.latents["prison_control"] = 0.0
    esp.latents["police_effective_capacity"] = 0.0
    esp.latents["intelligence_effectiveness"] = 0.0
    esp.latents["government_legitimacy"] = 0.0
    esp.latents["social_cohesion"] = 0.0
    network_variables = (
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
        "revolutionary_extremist_pressure",
    )
    for variable in network_variables:
        esp.latents[variable] = 0.25

    before = esp.to_dict()
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
        enable_extremist_network_dynamics=True,
        extremist_network_config=network_config,
    )

    esp_network_proposals = [
        proposal
        for proposal in result.network_proposals
        if proposal.target_node == "ESP"
    ]
    assert len(esp_network_proposals) == 3
    assert all(
        proposal.raw_delta == pytest.approx(0.009)
        for proposal in esp_network_proposals
    )
    assert all(
        proposal.value_before == pytest.approx(0.25)
        for proposal in esp_network_proposals
    )

    for variable in network_variables:
        resolution = next(
            record
            for record in result.resolutions
            if record.target_node == "ESP"
            and record.variable == variable
        )
        assert resolution.raw_sum_delta == pytest.approx(0.009)
        assert result.states["ESP"].latents[variable] == pytest.approx(0.259)
        assert esp.latents[variable] == pytest.approx(0.25)

    assert esp.to_dict() == before
    assert any(
        item["record_type"] == "extremist_network_dynamics_proposal"
        for item in trace.records
    )


def test_same_day_event_does_not_feed_network_dynamics_until_next_tick() -> None:
    logger.info(
        "test_same_day_event_does_not_feed_network_dynamics_until_next_tick"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(seed=1011)
    network_config = load_yaml(
        ROOT / "config/engine/extremist_network_dynamics_v1.yaml"
    )
    _force_spain_morocco_and_spain_protest(states)

    esp = states["ESP"]
    esp.latents["communal_fear"] = 0.20
    esp.latents["civilizational_narrative_strength"] = 0.40
    esp.latents["foreign_support_nonstate"] = 0.30
    esp.latents["prison_control"] = 0.80
    esp.latents["police_effective_capacity"] = 0.70
    esp.latents["intelligence_effectiveness"] = 0.70
    for variable in (
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
        "revolutionary_extremist_pressure",
    ):
        esp.latents[variable] = 0.25

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
        enable_extremist_network_dynamics=True,
        extremist_network_config=network_config,
    )

    interstate = [
        event
        for event in result.events
        if event.event_type == "INTERSTATE_INCIDENT_V1"
        and "ESP" in event.actors
    ]
    assert interstate
    assert result.states["ESP"].latents["communal_fear"] > 0.20

    esp_network_trace = next(
        item
        for item in trace.records
        if item["record_type"] == "extremist_network_dynamics_proposal"
        and item["target_node"] == "ESP"
    )
    assert esp_network_trace["driver_inputs"]["communal_fear"] == pytest.approx(0.20)



def test_extremist_network_config_changes_transaction_identity() -> None:
    logger.info("test_extremist_network_config_changes_transaction_identity")
    runtime_a = _runtime(seed=1012)
    runtime_b = _runtime(seed=1012)
    params_a = _disable_all_events(runtime_a[4])
    params_b = _disable_all_events(runtime_b[4])
    config_a = load_yaml(ROOT / "config/engine/extremist_network_dynamics_v1.yaml")
    config_b = copy.deepcopy(config_a)
    config_b["status"] = "identity-test-variant"

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=params_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_extremist_network_dynamics=True,
        extremist_network_config=config_a,
    )
    result_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=params_b,
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_extremist_network_dynamics=True,
        extremist_network_config=config_b,
    )

    assert result_a.transaction_id != result_b.transaction_id
    assert result_a.states == result_b.states



def test_reciprocal_radicalization_resolves_from_common_beginning_state() -> None:
    logger.info(
        "test_reciprocal_radicalization_resolves_from_common_beginning_state"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(
        seed=1013
    )
    parameters = _disable_all_events(parameters)
    feedback_config = load_yaml(
        ROOT / "config/engine/reciprocal_radicalization_v1.yaml"
    )
    _set_reciprocal_test_state(states)
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
        enable_reciprocal_radicalization=True,
        reciprocal_radicalization_config=feedback_config,
    )

    assert result.events == ()
    assert len(result.reciprocal_radicalization_proposals) == 2
    by_variable = {
        item.variable: item
        for item in result.reciprocal_radicalization_proposals
    }
    islamist = by_variable["violent_islamist_pressure"]
    ultranationalist = by_variable["violent_ultranationalist_pressure"]
    assert islamist.value_before == pytest.approx(0.8)
    assert ultranationalist.value_before == pytest.approx(0.2)
    assert islamist.raw_delta == pytest.approx(0.0008)
    assert ultranationalist.raw_delta == pytest.approx(0.0128)

    islamist_resolution = next(
        item
        for item in result.resolutions
        if item.target_node == "ESP"
        and item.variable == "violent_islamist_pressure"
    )
    ultra_resolution = next(
        item
        for item in result.resolutions
        if item.target_node == "ESP"
        and item.variable == "violent_ultranationalist_pressure"
    )
    assert islamist_resolution.value_after == pytest.approx(0.8008)
    assert ultra_resolution.value_after == pytest.approx(0.2128)
    for node_id in sorted(states):
        assert states[node_id].to_dict() == before[node_id]

    evaluations = [
        item
        for item in trace.records
        if item["record_type"] == "reciprocal_radicalization_evaluation"
    ]
    assert len(evaluations) == 10
    assert set(
        trace.records[-1]["reciprocal_radicalization_proposal_ids"]
    ) == {
        item.proposal_id
        for item in result.reciprocal_radicalization_proposals
    }


def test_network_dynamics_and_reciprocal_feedback_share_owner_resolution() -> None:
    logger.info(
        "test_network_dynamics_and_reciprocal_feedback_share_owner_resolution"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(
        seed=1014
    )
    parameters = _disable_all_events(parameters)
    network_config = load_yaml(
        ROOT / "config/engine/extremist_network_dynamics_v1.yaml"
    )
    feedback_config = load_yaml(
        ROOT / "config/engine/reciprocal_radicalization_v1.yaml"
    )
    _set_reciprocal_test_state(states)

    result = run_day_transaction(
        states=states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        enable_extremist_network_dynamics=True,
        extremist_network_config=network_config,
        enable_reciprocal_radicalization=True,
        reciprocal_radicalization_config=feedback_config,
    )

    assert len(result.network_proposals) == 3
    assert len(result.reciprocal_radicalization_proposals) == 2

    esp_islamist = [
        item
        for item in result.proposals
        if item.target_node == "ESP"
        and item.variable == "violent_islamist_pressure"
    ]
    esp_ultra = [
        item
        for item in result.proposals
        if item.target_node == "ESP"
        and item.variable == "violent_ultranationalist_pressure"
    ]
    esp_revolutionary = [
        item
        for item in result.proposals
        if item.target_node == "ESP"
        and item.variable == "revolutionary_extremist_pressure"
    ]

    assert len(esp_islamist) == 2
    assert len(esp_ultra) == 2
    assert len(esp_revolutionary) == 1
    assert all(item.value_before == pytest.approx(0.8) for item in esp_islamist)
    assert all(item.value_before == pytest.approx(0.2) for item in esp_ultra)
    assert esp_revolutionary[0].value_before == pytest.approx(0.0)

    islamist_network = next(
        item
        for item in esp_islamist
        if item.event_type == "ENDOGENOUS_EXTREMIST_NETWORK_V1"
    )
    islamist_feedback = next(
        item
        for item in esp_islamist
        if item.event_type == "RECIPROCAL_RADICALIZATION_V1"
    )
    ultra_network = next(
        item
        for item in esp_ultra
        if item.event_type == "ENDOGENOUS_EXTREMIST_NETWORK_V1"
    )
    ultra_feedback = next(
        item
        for item in esp_ultra
        if item.event_type == "RECIPROCAL_RADICALIZATION_V1"
    )

    assert islamist_network.raw_delta == pytest.approx(0.00048)
    assert islamist_feedback.raw_delta == pytest.approx(0.0008)
    assert ultra_network.raw_delta == pytest.approx(0.00192)
    assert ultra_feedback.raw_delta == pytest.approx(0.0128)
    assert esp_revolutionary[0].raw_delta == pytest.approx(0.0024)

    islamist_resolution = next(
        item
        for item in result.resolutions
        if item.target_node == "ESP"
        and item.variable == "violent_islamist_pressure"
    )
    ultra_resolution = next(
        item
        for item in result.resolutions
        if item.target_node == "ESP"
        and item.variable == "violent_ultranationalist_pressure"
    )
    revolutionary_resolution = next(
        item
        for item in result.resolutions
        if item.target_node == "ESP"
        and item.variable == "revolutionary_extremist_pressure"
    )

    assert islamist_resolution.raw_sum_delta == pytest.approx(0.00128)
    assert ultra_resolution.raw_sum_delta == pytest.approx(0.01472)
    assert revolutionary_resolution.raw_sum_delta == pytest.approx(0.0024)
    assert result.states["ESP"].latents[
        "violent_islamist_pressure"
    ] == pytest.approx(0.80128)
    assert result.states["ESP"].latents[
        "violent_ultranationalist_pressure"
    ] == pytest.approx(0.21472)
    assert result.states["ESP"].latents[
        "revolutionary_extremist_pressure"
    ] == pytest.approx(0.0024)


def test_reciprocal_config_changes_transaction_identity() -> None:
    logger.info("test_reciprocal_config_changes_transaction_identity")
    runtime_a = _runtime(seed=1015)
    runtime_b = _runtime(seed=1015)
    params_a = _disable_all_events(runtime_a[4])
    params_b = _disable_all_events(runtime_b[4])
    _set_reciprocal_test_state(runtime_a[0])
    _set_reciprocal_test_state(runtime_b[0])

    config_a = load_yaml(
        ROOT / "config/engine/reciprocal_radicalization_v1.yaml"
    )
    config_b = copy.deepcopy(config_a)
    config_b["status"] = "identity-test-variant"

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=params_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_reciprocal_radicalization=True,
        reciprocal_radicalization_config=config_a,
    )
    result_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=params_b,
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_reciprocal_radicalization=True,
        reciprocal_radicalization_config=config_b,
    )

    assert result_a.transaction_id != result_b.transaction_id
    assert result_a.states == result_b.states



def test_security_chain_dynamics_resolve_atomically() -> None:
    logger.info("test_security_chain_dynamics_resolve_atomically")
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(
        seed=1016
    )
    parameters = _disable_all_events(parameters)
    security_config = load_yaml(
        ROOT / "config/engine/security_chain_dynamics_v1.yaml"
    )
    _set_security_chain_test_state(states)
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
        enable_security_chain_dynamics=True,
        security_chain_config=security_config,
    )

    assert result.events == ()
    esp_proposals = [
        item
        for item in result.security_chain_proposals
        if item.target_node == "ESP"
    ]
    assert len(esp_proposals) == 4
    assert {
        item.variable for item in esp_proposals
    } == {
        "security_chain_cohesion",
        "command_cohesion",
        "constitutional_loyalty",
        "operational_fatigue",
    }
    assert all(
        item.value_before == pytest.approx(0.8)
        for item in esp_proposals
        if item.variable != "operational_fatigue"
    )
    fatigue = next(
        item
        for item in esp_proposals
        if item.variable == "operational_fatigue"
    )
    assert fatigue.value_before == pytest.approx(0.2)

    assert result.states["ESP"].latents[
        "security_chain_cohesion"
    ] == pytest.approx(0.7904)
    assert result.states["ESP"].latents[
        "command_cohesion"
    ] == pytest.approx(0.7904)
    assert result.states["ESP"].latents[
        "constitutional_loyalty"
    ] == pytest.approx(0.7976)
    assert result.states["ESP"].latents[
        "operational_fatigue"
    ] == pytest.approx(0.2096)

    for node_id in sorted(states):
        assert states[node_id].to_dict() == before[node_id]

    assert set(
        trace.records[-1]["security_chain_proposal_ids"]
    ) == {
        item.proposal_id for item in result.security_chain_proposals
    }


def test_same_day_event_does_not_feed_security_chain_until_next_tick() -> None:
    logger.info(
        "test_same_day_event_does_not_feed_security_chain_until_next_tick"
    )
    states, graph, day_config, registry, parameters, rng, manifest = _runtime(
        seed=1017
    )
    security_config = load_yaml(
        ROOT / "config/engine/security_chain_dynamics_v1.yaml"
    )
    _force_spain_morocco_and_spain_protest(states)

    esp = states["ESP"]
    esp.latents["public_order_stress"] = 0.40
    esp.latents["organized_armed_actor_capacity"] = 0.0
    esp.latents["salary_payment_continuity"] = 1.0
    esp.latents["transport_logistics_functionality"] = 1.0
    esp.latents["police_effective_capacity"] = 1.0
    esp.latents["intelligence_effectiveness"] = 1.0
    esp.latents["administrative_capacity"] = 1.0
    esp.latents["security_chain_cohesion"] = 0.8
    esp.latents["command_cohesion"] = 0.8
    esp.latents["constitutional_loyalty"] = 0.8
    esp.latents["operational_fatigue"] = 0.2

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
        enable_security_chain_dynamics=True,
        security_chain_config=security_config,
    )

    protest = [
        event
        for event in result.events
        if event.event_type == "MASS_PROTEST_TRIGGER_V1"
        and event.actors == ("ESP",)
    ]
    assert protest
    assert result.states["ESP"].latents["public_order_stress"] > 0.40

    security_eval = next(
        item
        for item in trace.records
        if item["record_type"] == "security_chain_dynamics_evaluation"
        and item["node_id"] == "ESP"
        and item["variable"] == "security_chain_cohesion"
    )
    assert security_eval["stress_inputs"]["public_order_stress"] == pytest.approx(
        0.40
    )


def test_security_chain_config_changes_transaction_identity() -> None:
    logger.info("test_security_chain_config_changes_transaction_identity")
    runtime_a = _runtime(seed=1018)
    runtime_b = _runtime(seed=1018)
    params_a = _disable_all_events(runtime_a[4])
    params_b = _disable_all_events(runtime_b[4])
    _set_security_chain_test_state(runtime_a[0])
    _set_security_chain_test_state(runtime_b[0])
    config_a = load_yaml(
        ROOT / "config/engine/security_chain_dynamics_v1.yaml"
    )
    config_b = copy.deepcopy(config_a)
    config_b["status"] = "identity-test-variant"

    result_a = run_day_transaction(
        states=runtime_a[0],
        graph=runtime_a[1],
        day_config=runtime_a[2],
        engine_state_registry=runtime_a[3],
        parameter_registry=params_a,
        profile="synthetic_smoke_v1",
        rng=runtime_a[5],
        manifest=runtime_a[6],
        trace=TraceLedger(),
        enable_security_chain_dynamics=True,
        security_chain_config=config_a,
    )
    result_b = run_day_transaction(
        states=runtime_b[0],
        graph=runtime_b[1],
        day_config=runtime_b[2],
        engine_state_registry=runtime_b[3],
        parameter_registry=params_b,
        profile="synthetic_smoke_v1",
        rng=runtime_b[5],
        manifest=runtime_b[6],
        trace=TraceLedger(),
        enable_security_chain_dynamics=True,
        security_chain_config=config_b,
    )

    assert result_a.transaction_id != result_b.transaction_id
    assert result_a.states == result_b.states
