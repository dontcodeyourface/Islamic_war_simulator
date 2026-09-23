from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.day import run_atomic_day
from iwsim.graph import build_structural_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture(*, force_generated: bool = True):
    logger.info("_fixture force_generated=%s", force_generated)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    graph_config = load_yaml(ROOT / "config/graph/base_country_graph_v1.yaml")
    distance_matrix = load_yaml(ROOT / graph_config["distance_matrix_path"])

    graph = build_structural_graph(
        repo_root=ROOT,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
    )

    states = {}
    for node_id, country_file, seed in (
        ("ESP", "config/countries/spain.yaml", 701),
        ("MAR", "config/countries/morocco.yaml", 702),
    ):
        snapshot = load_yaml(ROOT / country_file)
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
        states[node_id] = state

    if force_generated:
        for state in states.values():
            state.latents["external_conflict_pressure"] = 1.0
            state.latents["polarization"] = 1.0
            state.latents["inflation_pressure"] = 1.0
            state.latents["unemployment_pressure"] = 1.0
            state.latents["government_legitimacy"] = 0.0
            state.latents["social_cohesion"] = 0.0
            state.latents["public_order_stress"] = 0.40
            state.latents["communal_fear"] = 0.20

    manifest = build_manifest(
        run_id="atomic-day-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.7.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"snapshots": ["ESP", "MAR"]}),
        country_file_hashes={"ESP": "TEST", "MAR": "TEST"},
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-ATOMIC-DAY-TEST",
        scenario_hash=canonical_hash({"scenario": "atomic-day"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=707,
        rng_algorithm="python_random_mt19937",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=1,
        enabled_modules=(
            "initializer",
            "structural_graph",
            "event_engine",
            "effect_proposals",
            "owner_resolver",
            "atomic_day",
        ),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state_registry, parameters, graph, states, manifest


def test_atomic_day_commits_simultaneous_events_from_same_pre_state() -> None:
    logger.info("test_atomic_day_commits_simultaneous_events_from_same_pre_state")
    state_registry, parameters, graph, states, manifest = _fixture()
    original_hashes = {node: state.state_hash() for node, state in states.items()}

    trace = TraceLedger()
    result = run_atomic_day(
        states=states,
        graph=graph,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(707),
        manifest=manifest,
        trace=trace,
    )

    assert result.transaction_day == 1
    assert len(result.candidates) == 3
    assert len(result.events) == 3
    assert len(result.proposals) == 12
    assert len(result.resolutions) == 10

    assert {event.event_type for event in result.events} == {
        "INTERSTATE_INCIDENT_V1",
        "MASS_PROTEST_TRIGGER_V1",
    }
    assert all(event.dry_run is False for event in result.events)
    assert all(proposal.dry_run is False for proposal in result.proposals)

    esp_public_order = [
        proposal
        for proposal in result.proposals
        if proposal.target_node == "ESP"
        and proposal.variable == "public_order_stress"
    ]
    assert len(esp_public_order) == 2
    assert {proposal.value_before for proposal in esp_public_order} == {0.40}
    assert sorted(proposal.raw_delta for proposal in esp_public_order) == pytest.approx(
        [0.025, 0.060]
    )

    esp_public_resolution = [
        record
        for record in result.resolutions
        if record.target_node == "ESP"
        and record.variable == "public_order_stress"
    ]
    assert len(esp_public_resolution) == 1
    assert esp_public_resolution[0].raw_sum_delta == pytest.approx(0.085)
    assert esp_public_resolution[0].value_after == pytest.approx(0.485)

    interstate = [
        event for event in result.events if event.event_type == "INTERSTATE_INCIDENT_V1"
    ]
    assert len(interstate) == 1
    assert dict(interstate[0].feature_values)["external_conflict_pressure_mean"] == pytest.approx(1.0)

    for node_id, state in states.items():
        assert state.state_hash() == original_hashes[node_id]
        assert state.day == 0
        assert result.states[node_id].day == 1

    checkpoints = [
        record for record in trace.records if record["record_type"] == "daily_checkpoint"
    ]
    assert len(checkpoints) == 2
    for checkpoint in checkpoints:
        assert checkpoint["day"] == 1
        assert checkpoint["candidate_count"] == 2
        assert len(checkpoint["event_ids_applied"]) == 2
        assert len(checkpoint["proposal_ids"]) == 6
        assert len(checkpoint["resolution_ids"]) == 5

    transactions = [
        record for record in trace.records if record["record_type"] == "daily_transaction"
    ]
    assert len(transactions) == 1
    assert transactions[0]["candidate_count"] == 3
    assert transactions[0]["phase_transitions_enabled"] is False


def test_atomic_day_no_event_path_only_advances_clock() -> None:
    logger.info("test_atomic_day_no_event_path_only_advances_clock")
    state_registry, parameters, graph, states, manifest = _fixture(
        force_generated=False
    )
    parameters = copy.deepcopy(parameters)
    probability = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EVENT_HAZARD_PROBABILITY_SYN_V1"
    ]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0

    for state in states.values():
        state.latents["external_conflict_pressure"] = 0.0
        state.latents["polarization"] = 0.0
        state.latents["inflation_pressure"] = 0.0
        state.latents["unemployment_pressure"] = 0.0
        state.latents["government_legitimacy"] = 1.0
        state.latents["social_cohesion"] = 1.0

    before_latents = {
        node: dict(state.latents)
        for node, state in states.items()
    }

    result = run_atomic_day(
        states=states,
        graph=graph,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(708),
        manifest=manifest,
        trace=TraceLedger(),
    )

    assert len(result.candidates) == 3
    assert len(result.events) == 0
    assert len(result.proposals) == 0
    assert len(result.resolutions) == 0
    for node_id in states:
        assert result.states[node_id].day == 1
        assert result.states[node_id].latents == before_latents[node_id]


def test_atomic_day_replays_exactly_and_ignores_input_dict_order() -> None:
    logger.info("test_atomic_day_replays_exactly_and_ignores_input_dict_order")
    state_registry, parameters, graph, states_a, manifest = _fixture()
    _, _, _, states_b, _ = _fixture()

    trace_a = TraceLedger()
    trace_b = TraceLedger()
    result_a = run_atomic_day(
        states={"ESP": states_a["ESP"], "MAR": states_a["MAR"]},
        graph=graph,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(709),
        manifest=manifest,
        trace=trace_a,
    )
    result_b = run_atomic_day(
        states={"MAR": states_b["MAR"], "ESP": states_b["ESP"]},
        graph=graph,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(709),
        manifest=manifest,
        trace=trace_b,
    )

    assert result_a.to_dict() == result_b.to_dict()
    assert trace_a.records == trace_b.records


def test_atomic_day_rejects_unsynchronized_state_days() -> None:
    logger.info("test_atomic_day_rejects_unsynchronized_state_days")
    state_registry, parameters, graph, states, manifest = _fixture()
    states["MAR"].day = 1

    with pytest.raises(ValueError, match="synchronized state days"):
        run_atomic_day(
            states=states,
            graph=graph,
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            rng=RNGManager(710),
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_atomic_day_candidate_hazards_are_precommit_values() -> None:
    logger.info("test_atomic_day_candidate_hazards_are_precommit_values")
    state_registry, parameters, graph, states, manifest = _fixture()

    result = run_atomic_day(
        states=states,
        graph=graph,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(711),
        manifest=manifest,
        trace=TraceLedger(),
    )

    mass_candidates = [
        candidate
        for candidate in result.candidates
        if candidate.result.event_type == "MASS_PROTEST_TRIGGER_V1"
    ]
    assert len(mass_candidates) == 2
    for candidate in mass_candidates:
        features = dict(candidate.result.feature_values)
        assert features["government_legitimacy_inverse"] == pytest.approx(1.0)
        assert features["social_cohesion"] == pytest.approx(0.0)

    for node_id in ("ESP", "MAR"):
        assert result.states[node_id].latents["government_legitimacy"] == pytest.approx(0.0)
        assert result.states[node_id].latents["social_cohesion"] == pytest.approx(0.0)
