from __future__ import annotations

import logging
from pathlib import Path

from iwsim.config import load_yaml
from iwsim.graph import build_country_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.rng import RNGManager
from iwsim.spillover import evaluate_graph_spillovers, empty_spillover_queue
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime():
    logger.info("_runtime")
    graph_config = load_yaml(ROOT / "config/graph/country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    spillover_config = load_yaml(ROOT / "config/engine/graph_spillover_v1.yaml")

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
    rng = RNGManager(12345)
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
    for state in states.values():
        state.latents["external_conflict_pressure"] = 0.50
    return states, graph, parameters, spillover_config


def test_trace_only_spillover_is_deterministic_and_non_mutating() -> None:
    logger.info("test_trace_only_spillover_is_deterministic_and_non_mutating")
    states_a, graph_a, parameters_a, config_a = _runtime()
    states_b, graph_b, parameters_b, config_b = _runtime()
    before = {
        node_id: state.state_hash()
        for node_id, state in sorted(states_a.items())
    }
    trace_a = TraceLedger()
    trace_b = TraceLedger()

    result_a = evaluate_graph_spillovers(
        day=1,
        states=states_a,
        graph=graph_a,
        spillover_config=config_a,
        parameter_registry=parameters_a,
        profile="synthetic_smoke_v1",
        queue=empty_spillover_queue(0),
        trace=trace_a,
    )
    result_b = evaluate_graph_spillovers(
        day=1,
        states=states_b,
        graph=graph_b,
        spillover_config=config_b,
        parameter_registry=parameters_b,
        profile="synthetic_smoke_v1",
        queue=empty_spillover_queue(0),
        trace=trace_b,
    )

    assert result_a.to_dict() == result_b.to_dict()
    assert trace_a.records == trace_b.records
    assert len(result_a.candidates) == 140
    assert result_a.queue.last_processed_day == 1
    assert all(item.day_effective > 1 for item in result_a.queue.pending)
    assert {
        node_id: state.state_hash()
        for node_id, state in sorted(states_a.items())
    } == before


def test_resolved_and_unresolved_channel_semantics_are_distinct() -> None:
    logger.info("test_resolved_and_unresolved_channel_semantics_are_distinct")
    states, graph, parameters, config = _runtime()
    result = evaluate_graph_spillovers(
        day=1,
        states=states,
        graph=graph,
        spillover_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        queue=empty_spillover_queue(0),
        trace=TraceLedger(),
    )

    proximity = [
        item
        for item in result.candidates
        if item.rule_id == "REGIONAL_CONFLICT_PRESSURE_TRACE_V1"
        and item.channel == "geographic_proximity"
    ]
    information = [
        item
        for item in result.candidates
        if item.rule_id == "INFORMATION_PRESSURE_TRACE_V1"
    ]

    assert len(proximity) == 20
    assert len(information) == 20
    assert all(item.status == "SCHEDULED" for item in proximity)
    assert all(item.edge_weight is not None for item in proximity)
    assert all(item.raw_effect is not None for item in proximity)

    assert all(item.status == "UNRESOLVED_CHANNEL" for item in information)
    assert all(item.edge_weight is None for item in information)
    assert all(item.raw_effect is None for item in information)
    queued_ids = {item.spillover_id for item in result.queue.pending}
    matured_ids = {item.spillover_id for item in result.matured}
    assert not any(
        item.spillover_id in queued_ids or item.spillover_id in matured_ids
        for item in information
    )


def test_latency_queue_matures_records_on_effective_day() -> None:
    logger.info("test_latency_queue_matures_records_on_effective_day")
    states, graph, parameters, config = _runtime()
    result = evaluate_graph_spillovers(
        day=1,
        states=states,
        graph=graph,
        spillover_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        queue=empty_spillover_queue(0),
        trace=TraceLedger(),
    )
    assert result.queue.pending

    chosen = min(
        result.queue.pending,
        key=lambda item: (item.day_effective, item.spillover_id),
    )
    queue = result.queue
    matured_ids: set[str] = set()

    for day in range(2, chosen.day_effective + 1):
        next_result = evaluate_graph_spillovers(
            day=day,
            states=states,
            graph=graph,
            spillover_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            queue=queue,
            trace=TraceLedger(),
        )
        matured_ids.update(item.spillover_id for item in next_result.matured)
        queue = next_result.queue

    assert chosen.spillover_id in matured_ids
    assert chosen.spillover_id not in {
        item.spillover_id for item in queue.pending
    }


def test_latency_stays_inside_channel_contract() -> None:
    logger.info("test_latency_stays_inside_channel_contract")
    states, graph, parameters, config = _runtime()
    result = evaluate_graph_spillovers(
        day=1,
        states=states,
        graph=graph,
        spillover_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        queue=empty_spillover_queue(0),
        trace=TraceLedger(),
    )
    intervals = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "GRAPH_LATENCIES_SYN_V1"
    ]["value"]

    for item in result.candidates:
        low, high = intervals[item.channel]
        assert int(low) <= item.latency_days <= int(high)


def test_calibrated_spillover_profile_fails_closed() -> None:
    logger.info("test_calibrated_spillover_profile_fails_closed")
    states, graph, parameters, config = _runtime()

    try:
        evaluate_graph_spillovers(
            day=1,
            states=states,
            graph=graph,
            spillover_config=config,
            parameter_registry=parameters,
            profile="calibrated_v1",
            queue=empty_spillover_queue(0),
            trace=TraceLedger(),
        )
    except ValueError as exc:
        assert "Missing spillover parameter" in str(exc)
    else:
        raise AssertionError("calibrated_v1 must fail closed while unpopulated")
