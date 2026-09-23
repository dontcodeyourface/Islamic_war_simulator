from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.effects import propose_event_effects
from iwsim.events import evaluate_interstate_incident, evaluate_mass_protest
from iwsim.graph import build_structural_graph, edge_by_nodes
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime_fixture():
    logger.info("_runtime_fixture")
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
        ("ESP", "config/countries/spain.yaml", 101),
        ("MAR", "config/countries/morocco.yaml", 102),
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

    manifest = build_manifest(
        run_id="effect-test-run",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.5.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"snapshot": "test"}),
        country_file_hashes={"ESP": "TEST", "MAR": "TEST"},
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-EFFECT-DRYRUN",
        scenario_hash=canonical_hash({"scenario": "effect-dryrun"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=999,
        rng_algorithm="python_random_mt19937",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=1,
        enabled_modules=(
            "initializer",
            "structural_graph",
            "event_engine_dry_run",
            "effect_proposals_dry_run",
        ),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state_registry, parameters, graph, states, manifest


def test_interstate_event_proposes_six_deltas_without_mutation() -> None:
    logger.info("test_interstate_event_proposes_six_deltas_without_mutation")
    state_registry, parameters, graph, states, manifest = _runtime_fixture()
    states["ESP"].latents["external_conflict_pressure"] = 1.0
    states["MAR"].latents["external_conflict_pressure"] = 1.0

    before = {node: state.state_hash() for node, state in states.items()}
    event_trace = TraceLedger()
    result = evaluate_interstate_incident(
        day=1,
        state_a=states["ESP"],
        state_b=states["MAR"],
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(123),
        manifest=manifest,
        trace=event_trace,
    )
    assert result.event is not None

    proposal_trace = TraceLedger()
    proposals = propose_event_effects(
        event=result.event,
        states=states,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=proposal_trace,
    )

    assert len(proposals) == 6
    assert {proposal.target_node for proposal in proposals} == {"ESP", "MAR"}
    assert {proposal.variable for proposal in proposals} == {
        "external_conflict_pressure",
        "public_order_stress",
        "communal_fear",
    }
    assert all(proposal.apply_status == "PROPOSED_NOT_APPLIED" for proposal in proposals)
    assert all(proposal.dry_run is True for proposal in proposals)
    assert all(
        proposal.parameter_ids == ("EVENT_EFFECT_PROPOSALS_SYN_V1",)
        for proposal in proposals
    )

    owners = {proposal.variable: proposal.owner_module for proposal in proposals}
    assert owners["external_conflict_pressure"] == "external_system"
    assert owners["public_order_stress"] == "security"
    assert owners["communal_fear"] == "demographics"

    after = {node: state.state_hash() for node, state in states.items()}
    assert before == after
    assert len(
        [
            record
            for record in proposal_trace.records
            if record["record_type"] == "delta_proposal"
        ]
    ) == 6


def test_mass_protest_proposals_preserve_signs_and_state() -> None:
    logger.info("test_mass_protest_proposals_preserve_signs_and_state")
    state_registry, parameters, graph, states, manifest = _runtime_fixture()
    esp = states["ESP"]
    esp.latents["polarization"] = 1.0
    esp.latents["inflation_pressure"] = 1.0
    esp.latents["unemployment_pressure"] = 1.0
    esp.latents["government_legitimacy"] = 0.0
    esp.latents["social_cohesion"] = 0.0

    before = esp.state_hash()
    result = evaluate_mass_protest(
        day=1,
        state=esp,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(456),
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert result.event is not None

    proposals = propose_event_effects(
        event=result.event,
        states=states,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    by_variable = {proposal.variable: proposal for proposal in proposals}

    assert by_variable["public_order_stress"].raw_delta == pytest.approx(0.060)
    assert by_variable["government_legitimacy"].raw_delta == pytest.approx(-0.030)
    assert by_variable["social_cohesion"].raw_delta == pytest.approx(-0.020)
    assert esp.state_hash() == before


def test_delta_proposal_ids_are_replay_stable() -> None:
    logger.info("test_delta_proposal_ids_are_replay_stable")
    state_registry, parameters, graph, states, manifest = _runtime_fixture()
    states["ESP"].latents["external_conflict_pressure"] = 1.0
    states["MAR"].latents["external_conflict_pressure"] = 1.0

    event = evaluate_interstate_incident(
        day=3,
        state_a=states["ESP"],
        state_b=states["MAR"],
        edge=edge_by_nodes(graph, "ESP", "MAR"),
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(1),
        manifest=manifest,
        trace=TraceLedger(),
    ).event
    assert event is not None

    a = propose_event_effects(
        event=event,
        states=states,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    b = propose_event_effects(
        event=event,
        states=states,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )

    assert [item.to_dict() for item in a] == [item.to_dict() for item in b]
    assert len({item.proposal_id for item in a}) == len(a)
