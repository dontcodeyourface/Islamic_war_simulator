from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.events import evaluate_interstate_incident, evaluate_mass_protest
from iwsim.graph import build_structural_graph, edge_by_nodes
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _state(country_file: str, seed: int):
    logger.info("_state country_file=%s seed=%s", country_file, seed)
    snapshot = load_yaml(ROOT / country_file)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    trace = TraceLedger()
    state = initialize_hybrid_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        parameter_registry=parameters,
        feature_map=feature_map,
        rng=RNGManager(seed),
        trace=trace,
        profile="synthetic_smoke_v1",
    )
    return state


def _graph_and_parameters():
    logger.info("_graph_and_parameters")
    graph_config = load_yaml(ROOT / "config/graph/base_country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    graph = build_structural_graph(
        repo_root=ROOT,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )
    return graph, parameters


def _manifest(graph_hash: str, *, run_id: str = "event-test-run"):
    logger.info("_manifest graph_hash=%s run_id=%s", graph_hash, run_id)
    return build_manifest(
        run_id=run_id,
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.4.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"snapshots": "test"}),
        country_file_hashes={"ESP": "TEST", "MAR": "TEST"},
        graph_hash=graph_hash,
        scenario_id="SCN-EVENT-DRYRUN",
        scenario_hash=canonical_hash({"scenario": "event-dryrun"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash({"parameters": "test"}),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=123,
        rng_algorithm="python_random_mt19937",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=1,
        enabled_modules=("initializer", "structural_graph", "event_engine_dry_run"),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )


def test_interstate_incident_generated_path_does_not_consume_rng() -> None:
    logger.info("test_interstate_incident_generated_path_does_not_consume_rng")
    graph, parameters = _graph_and_parameters()
    esp = _state("config/countries/spain.yaml", 1)
    mar = _state("config/countries/morocco.yaml", 2)
    edge = edge_by_nodes(graph, "ESP", "MAR")
    esp.latents["external_conflict_pressure"] = 1.0
    mar.latents["external_conflict_pressure"] = 1.0

    before_esp = esp.state_hash()
    before_mar = mar.state_hash()
    rng = RNGManager(999)
    trace = TraceLedger()
    result = evaluate_interstate_incident(
        day=1,
        state_a=esp,
        state_b=mar,
        edge=edge,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=_manifest(graph.graph_hash()),
        trace=trace,
    )

    assert result.occurred is True
    assert result.provenance_class == "GENERATED"
    assert result.random_draw is None
    assert result.hazard_score >= result.generated_threshold
    assert result.event is not None
    assert result.event.dry_run is True
    assert result.event.rng_stream is None
    assert not any(
        stream_name.startswith("events:")
        for stream_name in rng.describe()["streams"]
    )
    assert not any(record["record_type"] == "event_rng_draw" for record in trace.records)
    assert esp.state_hash() == before_esp
    assert mar.state_hash() == before_mar


def test_interstate_incident_random_shock_path_records_rng() -> None:
    logger.info("test_interstate_incident_random_shock_path_records_rng")
    graph, parameters = _graph_and_parameters()
    parameters = copy.deepcopy(parameters)
    probability = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 1.0
    probability["score_scale"] = 0.0

    esp = _state("config/countries/spain.yaml", 3)
    mar = _state("config/countries/morocco.yaml", 4)
    edge = edge_by_nodes(graph, "ESP", "MAR")
    esp.latents["external_conflict_pressure"] = 0.0
    mar.latents["external_conflict_pressure"] = 0.0

    rng = RNGManager(123)
    trace = TraceLedger()
    result = evaluate_interstate_incident(
        day=1,
        state_a=esp,
        state_b=mar,
        edge=edge,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=_manifest(graph.graph_hash()),
        trace=trace,
    )

    assert result.hazard_score < result.generated_threshold
    assert result.occurred is True
    assert result.provenance_class == "RANDOM_SHOCK"
    assert result.random_draw is not None
    assert result.event is not None
    assert result.event.rng_stream == "events:INTERSTATE_INCIDENT_V1:ESP--MAR"

    draws = [
        record
        for record in trace.records
        if record["record_type"] == "event_rng_draw"
    ]
    assert len(draws) == 1
    assert draws[0]["draw_index"] == 0
    assert draws[0]["random_draw"] == pytest.approx(result.random_draw)


def test_interstate_incident_can_remain_absent() -> None:
    logger.info("test_interstate_incident_can_remain_absent")
    graph, parameters = _graph_and_parameters()
    parameters = copy.deepcopy(parameters)
    probability = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0

    esp = _state("config/countries/spain.yaml", 5)
    mar = _state("config/countries/morocco.yaml", 6)
    esp.latents["external_conflict_pressure"] = 0.0
    mar.latents["external_conflict_pressure"] = 0.0

    result = evaluate_interstate_incident(
        day=1,
        state_a=esp,
        state_b=mar,
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(321),
        manifest=_manifest(graph.graph_hash()),
        trace=TraceLedger(),
    )

    assert result.occurred is False
    assert result.provenance_class is None
    assert result.event is None


def test_mass_protest_generated_path() -> None:
    logger.info("test_mass_protest_generated_path")
    graph, parameters = _graph_and_parameters()
    esp = _state("config/countries/spain.yaml", 7)
    esp.latents["polarization"] = 1.0
    esp.latents["inflation_pressure"] = 1.0
    esp.latents["unemployment_pressure"] = 1.0
    esp.latents["government_legitimacy"] = 0.0
    esp.latents["social_cohesion"] = 0.0

    result = evaluate_mass_protest(
        day=1,
        state=esp,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(7),
        manifest=_manifest(graph.graph_hash()),
        trace=TraceLedger(),
    )

    assert result.occurred is True
    assert result.provenance_class == "GENERATED"
    assert result.hazard_score >= result.generated_threshold
    assert result.event is not None


def test_random_event_candidate_replays_exactly() -> None:
    logger.info("test_random_event_candidate_replays_exactly")
    graph, parameters = _graph_and_parameters()
    parameters = copy.deepcopy(parameters)
    probability = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.01

    esp_a = _state("config/countries/spain.yaml", 8)
    mar_a = _state("config/countries/morocco.yaml", 9)
    esp_b = _state("config/countries/spain.yaml", 8)
    mar_b = _state("config/countries/morocco.yaml", 9)
    esp_a.latents["external_conflict_pressure"] = 0.2
    mar_a.latents["external_conflict_pressure"] = 0.2
    esp_b.latents["external_conflict_pressure"] = 0.2
    mar_b.latents["external_conflict_pressure"] = 0.2

    manifest = _manifest(graph.graph_hash())
    trace_a = TraceLedger()
    trace_b = TraceLedger()

    a = evaluate_interstate_incident(
        day=11,
        state_a=esp_a,
        state_b=mar_a,
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(444),
        manifest=manifest,
        trace=trace_a,
    )
    b = evaluate_interstate_incident(
        day=11,
        state_a=esp_b,
        state_b=mar_b,
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(444),
        manifest=manifest,
        trace=trace_b,
    )

    assert a.to_dict() == b.to_dict()
    assert trace_a.records == trace_b.records


def test_unrelated_event_family_does_not_shift_interstate_rng() -> None:
    logger.info("test_unrelated_event_family_does_not_shift_interstate_rng")
    graph, parameters = _graph_and_parameters()
    parameters = copy.deepcopy(parameters)
    probability = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.01

    esp_a = _state("config/countries/spain.yaml", 21)
    mar_a = _state("config/countries/morocco.yaml", 22)
    esp_b = _state("config/countries/spain.yaml", 21)
    mar_b = _state("config/countries/morocco.yaml", 22)
    for state in (esp_a, mar_a, esp_b, mar_b):
        state.latents["external_conflict_pressure"] = 0.2

    manifest = _manifest(graph.graph_hash())

    rng_a = RNGManager(789)
    first = evaluate_interstate_incident(
        day=5,
        state_a=esp_a,
        state_b=mar_a,
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng_a,
        manifest=manifest,
        trace=TraceLedger(),
    )

    rng_b = RNGManager(789)
    _ = evaluate_mass_protest(
        day=5,
        state=esp_b,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng_b,
        manifest=manifest,
        trace=TraceLedger(),
    )
    second = evaluate_interstate_incident(
        day=5,
        state_a=esp_b,
        state_b=mar_b,
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng_b,
        manifest=manifest,
        trace=TraceLedger(),
    )

    assert first.random_draw == pytest.approx(second.random_draw)
    assert first.occurrence_probability == pytest.approx(
        second.occurrence_probability
    )
