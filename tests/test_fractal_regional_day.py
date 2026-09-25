from __future__ import annotations

import copy
import logging
from pathlib import Path

from iwsim.config import canonical_hash, load_yaml
from iwsim.day import run_day_transaction
from iwsim.fractal import FractalRefinementPersistenceState
from iwsim.fractal_child_state import FractalChildStateStore
from iwsim.fractal_regional_regime import FractalRegionalRegimeStore
from iwsim.graph import build_country_graph
from iwsim.initializer import initialize_hybrid_state
from iwsim.manifest import build_manifest
from iwsim.phases import PhasePersistenceState
from iwsim.rng import RNGManager
from iwsim.spillover import empty_spillover_queue
from iwsim.state import EngineState
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime(seed: int = 2801):
    logger.info("_runtime seed=%s", seed)
    graph_config = load_yaml(
        ROOT / "config/graph/country_graph_v1.yaml"
    )
    distance_matrix = load_yaml(
        ROOT / graph_config["distance_matrix_path"]
    )
    registry = load_yaml(
        ROOT / "config/engine/engine_state_v1.yaml"
    )
    normalization = load_yaml(
        ROOT / "config/engine/normalization_parameters_v1.yaml"
    )
    parameters = load_yaml(
        ROOT / "config/engine/parameter_registry_v1.yaml"
    )
    feature_map = load_yaml(
        ROOT / "config/engine/snapshot_feature_map_v1.yaml"
    )
    day_config = load_yaml(
        ROOT / "config/engine/day_transaction_v1.yaml"
    )
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
            engine_state_registry=registry,
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
        run_id="fractal-regional-day-test",
        created_at="2026-09-25T00:00:00+00:00",
        engine_version="0.28.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={
            iso3: canonical_hash(snapshot)
            for iso3, snapshot in sorted(snapshots.items())
        },
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-FRACTAL-REGIONAL-DAY",
        scenario_hash=canonical_hash({"scenario": "regional-day"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-25",
        horizon_days=2,
        enabled_modules=(
            "day_transaction",
            "fractal_runtime",
            "fractal_regional_regimes",
        ),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )
    return (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
    )


def _disable_events(parameters: dict) -> dict:
    logger.info("_disable_events")
    patched = copy.deepcopy(parameters)
    hazard = patched["parameter_sets"]["synthetic_smoke_v1"][
        "parameters"
    ]["EVENT_HAZARD_WEIGHTS_SYN_V1"]["value"]
    for item in hazard.values():
        item["generated_threshold"] = 2.0
    probability = patched["parameter_sets"]["synthetic_smoke_v1"][
        "parameters"
    ]["EVENT_HAZARD_PROBABILITY_SYN_V1"]["value"]
    probability["p_floor"] = 0.0
    probability["score_scale"] = 0.0
    return patched


def _catalog() -> dict:
    logger.info("_catalog")
    return load_yaml(
        ROOT / "config/engine/fractal_region_catalog_v1.yaml"
    )


def _regional_graph_catalog() -> dict:
    logger.info("_regional_graph_catalog")
    return load_yaml(
        ROOT / "config/engine/fractal_region_graph_catalog_v1.yaml"
    )


def _force_refinement_state(state: EngineState) -> None:
    logger.info("_force_refinement_state node=%s", state.node_id)
    for variable in (
        "public_order_stress",
        "terrorism_threat_pressure",
        "organized_armed_actor_capacity",
        "regional_fragmentation_pressure",
        "criminal_network_power",
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
        "revolutionary_extremist_pressure",
        "displacement_pressure",
    ):
        state.latents[variable] = 1.0
    for variable in (
        "government_legitimacy",
        "state_cohesion",
        "electricity_functionality",
        "fuel_distribution_functionality",
        "transport_logistics_functionality",
        "telecom_internet_functionality",
        "water_resilience",
    ):
        state.latents[variable] = 0.0

    # Keep the parent security classifier stable on the materialization day.
    state.latents["security_chain_cohesion"] = 0.95
    state.latents["command_cohesion"] = 0.95
    state.latents["operational_fatigue"] = 0.05


def _set_parent_stocks(state: EngineState) -> None:
    logger.info("_set_parent_stocks node=%s", state.node_id)
    state.physical_stocks.update(
        {
            "population_total": 101,
            "working_age_population": 61,
            "dependent_population": 40,
            "displaced_people": 5,
            "reception_population": 3,
            "fuel_stock_days_equivalent": 90.0,
            "strategic_food_stock_days": 30.0,
            "available_police_personnel": 11,
            "available_military_personnel": 1000,
            "prison_population": 7,
            "foreign_reserves_usd": 5000.0,
            "gold_reserves_tonnes": 25.0,
        }
    )


def _configs() -> dict[str, dict]:
    logger.info("_configs")
    names = {
        "refinement": "fractal_refinement_v1.yaml",
        "materialization": "fractal_materialization_v1.yaml",
        "child": "fractal_child_state_v1.yaml",
        "runtime": "fractal_runtime_v1.yaml",
        "regional": "fractal_regional_regime_v1.yaml",
        "projection": "fractal_graph_projection_v1.yaml",
        "spillover": "graph_spillover_v1.yaml",
        "reaggregation": "fractal_reaggregation_v1.yaml",
        "phase": "phase_evaluator_v1.yaml",
        "phase_transition": "phase_transition_v1.yaml",
        "security": "security_regime_evaluator_v1.yaml",
        "security_transition": "security_regime_transition_v1.yaml",
        "security_recovery": "security_regime_recovery_v1.yaml",
        "security_recovery_transition": (
            "security_regime_recovery_transition_v1.yaml"
        ),
    }
    return {
        key: load_yaml(ROOT / "config/engine" / filename)
        for key, filename in names.items()
    }


def _common_regime_kwargs(configs: dict[str, dict]) -> dict:
    logger.info("_common_regime_kwargs")
    return {
        "enable_phase_transitions": True,
        "phase_config": configs["phase"],
        "phase_transition_config": configs["phase_transition"],
        "enable_security_regime_evaluator": True,
        "security_regime_config": configs["security"],
        "enable_security_regime_commits": True,
        "security_regime_transition_config": configs[
            "security_transition"
        ],
        "enable_security_regime_recovery_evaluator": True,
        "security_regime_recovery_config": configs[
            "security_recovery"
        ],
        "enable_security_regime_recovery_commits": True,
        "security_regime_recovery_transition_config": configs[
            "security_recovery_transition"
        ],
        "enable_fractal_regional_regimes": True,
        "fractal_regional_regime_config": configs["regional"],
    }


def _stressed_child(state: EngineState) -> EngineState:
    logger.info("_stressed_child node=%s", state.node_id)
    latents = dict(state.latents)
    latents.update(
        {
            "public_order_stress": 0.90,
            "polarization": 0.90,
            "external_conflict_pressure": 0.50,
            "security_chain_cohesion": 0.50,
            "operational_fatigue": 0.80,
            "command_cohesion": 0.70,
        }
    )
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=latents,
        regimes=dict(state.regimes),
        metadata=dict(state.metadata),
    )


def _calm_child(state: EngineState) -> EngineState:
    logger.info("_calm_child node=%s", state.node_id)
    latents = dict(state.latents)
    latents.update(
        {
            "public_order_stress": 0.10,
            "polarization": 0.10,
            "external_conflict_pressure": 0.10,
            "security_chain_cohesion": 0.90,
            "operational_fatigue": 0.10,
            "command_cohesion": 0.90,
        }
    )
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=latents,
        regimes=dict(state.regimes),
        metadata=dict(state.metadata),
    )


def test_day_transaction_allows_regional_phase_and_security_divergence() -> None:
    logger.info(
        "test_day_transaction_allows_regional_phase_and_security_divergence"
    )
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
    ) = _runtime()
    parameters = _disable_events(parameters)
    configs = _configs()
    latencies = parameters["parameter_sets"]["synthetic_smoke_v1"][
        "parameters"
    ]["GRAPH_LATENCIES_SYN_V1"]["value"]
    latencies["geographic_proximity"] = [0, 0]
    latencies["land_border"] = [0, 0]

    for state in states.values():
        for variable in state.latents:
            state.latents[variable] = 0.5
    _force_refinement_state(states["ESP"])
    _set_parent_stocks(states["ESP"])

    refinement_persistence = {
        node_id: FractalRefinementPersistenceState(
            node_id=node_id,
            current_level="L1_COUNTRY",
            last_evaluated_day=0,
            expand_streak=7 if node_id == "ESP" else 0,
            collapse_streak=0,
        )
        for node_id in states
    }

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
        phase_persistence=None,
        security_regime_persistence=None,
        security_regime_recovery_persistence=None,
        enable_fractal_refinement_evaluator=True,
        fractal_refinement_config=configs["refinement"],
        fractal_refinement_persistence=refinement_persistence,
        enable_fractal_materialization=True,
        fractal_materialization_config=configs["materialization"],
        fractal_region_catalog=_catalog(),
        fractal_topology=None,
        enable_fractal_child_state_initialization=True,
        fractal_child_state_config=configs["child"],
        fractal_child_state_store=None,
        enable_fractal_runtime_plan=True,
        fractal_runtime_config=configs["runtime"],
        **_common_regime_kwargs(configs),
    )

    assert first.fractal_child_state_store is not None
    assert first.fractal_topology is not None
    assert first.fractal_regional_regime_result is not None
    first_regional_store = (
        first.fractal_regional_regime_result.persistence_store
    )
    assert first_regional_store.last_committed_day == 1

    stressed_id = "ESP::CT"
    calm_id = "ESP::AN"
    second_child_store = FractalChildStateStore(
        last_initialized_day=1,
        states=tuple(
            _stressed_child(child)
            if child.node_id == stressed_id
            else _calm_child(child)
            for child in first.fractal_child_state_store.states
        ),
    )

    phase_map = first_regional_store.phase_map()
    regional_store = FractalRegionalRegimeStore(
        last_committed_day=1,
        phase_persistence=tuple(
            PhasePersistenceState(
                node_id=item.node_id,
                current_phase=item.current_phase,
                last_evaluated_day=1,
                streaks=(("PHASE_STABLE_TENSION_V1", 2),),
            )
            if item.node_id == stressed_id
            else item
            for item in first_regional_store.phase_persistence
        ),
        security_persistence=first_regional_store.security_persistence,
        security_recovery_persistence=(
            first_regional_store.security_recovery_persistence
        ),
    )

    parent_phase_before = first.states["ESP"].regimes["national_phase"]
    parent_security_before = first.states["ESP"].regimes[
        "security_force_regime"
    ]
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
        phase_persistence=first.phase_persistence,
        security_regime_persistence=first.security_regime_persistence,
        security_regime_recovery_persistence=(
            first.security_regime_recovery_persistence
        ),
        enable_fractal_refinement_evaluator=True,
        fractal_refinement_config=configs["refinement"],
        fractal_refinement_persistence=(
            first.fractal_refinement_persistence
        ),
        enable_fractal_materialization=True,
        fractal_materialization_config=configs["materialization"],
        fractal_region_catalog=_catalog(),
        fractal_topology=first.fractal_topology,
        enable_fractal_child_state_initialization=True,
        fractal_child_state_config=configs["child"],
        fractal_child_state_store=second_child_store,
        enable_fractal_runtime_plan=True,
        fractal_runtime_config=configs["runtime"],
        enable_fractal_graph_projection=True,
        fractal_graph_projection_config=configs["projection"],
        fractal_region_graph_catalog=_regional_graph_catalog(),
        enable_graph_spillover=True,
        spillover_config=configs["spillover"],
        spillover_queue=empty_spillover_queue(1),
        enable_fractal_parent_child_coupling=True,
        fractal_parent_child_coupling_config=configs["reaggregation"],
        fractal_regional_regime_store=regional_store,
        **_common_regime_kwargs(configs),
    )

    assert second.fractal_regional_regime_result is not None
    assert second.fractal_parent_child_coupling_result is not None
    assert len(second.fractal_parent_child_coupling_result.audits) == 1
    coupled_children = (
        second.fractal_parent_child_coupling_result.child_store.state_map()
    )
    assert all(
        "fractal_parent_context" in child.metadata
        for child in coupled_children.values()
    )
    assert second.fractal_projected_graph_before is not None
    assert any(
        item.target_node == stressed_id
        and item.runtime_level == "L2_REGION"
        for item in second.resolutions
    )
    assert any(
        item.target_node == "FRA"
        and item.runtime_level == "L1_COUNTRY"
        for item in second.resolutions
    )
    children = second.fractal_child_state_store.state_map()
    assert children[stressed_id].regimes["national_phase"] == "TENSION"
    assert children[calm_id].regimes["national_phase"] == "STABLE"
    assert (
        children[stressed_id].regimes["security_force_regime"]
        == "STRAINED"
    )
    assert (
        children[calm_id].regimes["security_force_regime"]
        == "COHESIVE"
    )

    regional = second.fractal_regional_regime_result
    assert len(regional.phase_commits) == 1
    assert regional.phase_commits[0].node_id == stressed_id
    assert len(regional.security_commits) == 1
    assert regional.security_commits[0].node_id == stressed_id
    assert regional.divergence_audits[0].collapse_consensus_ready is False

    assert second.states["ESP"].regimes["national_phase"] == (
        parent_phase_before
    )
    assert second.states["ESP"].regimes["security_force_regime"] == (
        parent_security_before
    )
    assert all(
        item.node_id != "ESP"
        for item in second.phase_commits
    )
    assert all(
        item.node_id != "ESP"
        for item in second.security_regime_commits
    )
    assert second.phase_persistence["ESP"].streaks == ()
    assert second.security_regime_persistence["ESP"].streaks == ()

    assert any(
        item["record_type"]
        == "fractal_categorical_divergence_audit"
        and item["parent_node_id"] == "ESP"
        and item["collapse_consensus_ready"] is False
        for item in trace.records
    )



def _recursive_test_catalog() -> dict:
    logger.info("_recursive_test_catalog")
    catalog = copy.deepcopy(_catalog())
    catalog["parents"]["ESP::CT"] = {
        "source_id": "SYNTHETIC_L3_E2E",
        "children": [
            {
                "child_id": "ESP::CT::METRO_A",
                "label": "Metro A",
                "initialization_weight": 0.6,
            },
            {
                "child_id": "ESP::CT::LOGISTICS_B",
                "label": "Logistics B",
                "initialization_weight": 0.4,
            },
        ],
    }
    return catalog


def _with_refinement_pressure(
    state: EngineState,
    *,
    high: bool,
) -> EngineState:
    logger.info(
        "_with_refinement_pressure node=%s high=%s",
        state.node_id,
        high,
    )
    latents = dict(state.latents)
    positive = (
        "public_order_stress",
        "terrorism_threat_pressure",
        "organized_armed_actor_capacity",
        "regional_fragmentation_pressure",
        "criminal_network_power",
        "violent_islamist_pressure",
        "violent_ultranationalist_pressure",
        "revolutionary_extremist_pressure",
        "displacement_pressure",
    )
    inverse = (
        "government_legitimacy",
        "state_cohesion",
        "security_chain_cohesion",
        "electricity_functionality",
        "fuel_distribution_functionality",
        "transport_logistics_functionality",
        "telecom_internet_functionality",
        "water_resilience",
    )
    for variable in positive:
        latents[variable] = 1.0 if high else 0.0
    for variable in inverse:
        latents[variable] = 0.0 if high else 1.0
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=latents,
        regimes=dict(state.regimes),
        metadata=dict(state.metadata),
    )


def _replace_child_pressure(
    store: FractalChildStateStore,
    *,
    node_ids: set[str],
    high: bool,
) -> FractalChildStateStore:
    logger.info(
        "_replace_child_pressure nodes=%s high=%s",
        len(node_ids),
        high,
    )
    return FractalChildStateStore(
        last_initialized_day=store.last_initialized_day,
        states=tuple(
            _with_refinement_pressure(state, high=high)
            if state.node_id in node_ids
            else state
            for state in store.states
        ),
    )


def _recursive_core_kwargs(configs: dict[str, dict]) -> dict:
    logger.info("_recursive_core_kwargs")
    return {
        "enable_fractal_refinement_evaluator": True,
        "fractal_refinement_config": configs["refinement"],
        "enable_fractal_materialization": True,
        "fractal_materialization_config": configs["materialization"],
        "fractal_region_catalog": _recursive_test_catalog(),
        "enable_fractal_child_state_initialization": True,
        "fractal_child_state_config": configs["child"],
        "enable_fractal_runtime_plan": True,
        "fractal_runtime_config": configs["runtime"],
        "enable_fractal_reaggregation": True,
        "fractal_reaggregation_config": configs["reaggregation"],
    }


def test_v034c3_day_transaction_l2_l3_collapse_rerefine_generation_two() -> None:
    logger.info(
        "test_v034c3_day_transaction_l2_l3_collapse_rerefine_generation_two"
    )
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
    ) = _runtime(seed=3433)
    parameters = _disable_events(parameters)
    configs = _configs()

    for state in states.values():
        for variable in state.latents:
            state.latents[variable] = 0.5
    _force_refinement_state(states["ESP"])
    _set_parent_stocks(states["ESP"])

    initial_persistence = {
        node_id: FractalRefinementPersistenceState(
            node_id=node_id,
            current_level="L1_COUNTRY",
            last_evaluated_day=0,
            expand_streak=7 if node_id == "ESP" else 0,
            collapse_streak=0,
        )
        for node_id in states
    }

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
        fractal_refinement_persistence=initial_persistence,
        fractal_topology=None,
        fractal_child_state_store=None,
        **_recursive_core_kwargs(configs),
    )

    assert first.fractal_topology is not None
    assert first.fractal_child_state_store is not None
    assert first.fractal_runtime_plan_after is not None
    target = "ESP::CT"
    assert target in first.fractal_child_state_store.state_map()
    assert target in first.fractal_refinement_persistence
    assert (
        first.fractal_refinement_persistence[target].current_level
        == "L2_REGION"
    )

    second_persistence = dict(first.fractal_refinement_persistence)
    second_persistence[target] = FractalRefinementPersistenceState(
        node_id=target,
        current_level="L2_REGION",
        last_evaluated_day=1,
        expand_streak=7,
        collapse_streak=0,
    )
    second_store = _replace_child_pressure(
        first.fractal_child_state_store,
        node_ids={target},
        high=True,
    )

    second = run_day_transaction(
        states=first.states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        fractal_refinement_persistence=second_persistence,
        fractal_topology=first.fractal_topology,
        fractal_child_state_store=second_store,
        **_recursive_core_kwargs(configs),
    )

    assert second.fractal_topology is not None
    assert second.fractal_child_state_store is not None
    assert second.fractal_runtime_plan_after is not None
    l3_gen1 = second.fractal_topology.active_children(target)
    assert {item.node_id for item in l3_gen1} == {
        "ESP::CT::METRO_A",
        "ESP::CT::LOGISTICS_B",
    }
    assert {item.lineage_generation for item in l3_gen1} == {1}
    assert (
        second.fractal_refinement_persistence[target].current_level
        == "L3_METRO_OR_LOGISTICS_AREA"
    )
    assert target not in second.fractal_runtime_plan_after.active_regional_node_ids
    assert {
        "ESP::CT::METRO_A",
        "ESP::CT::LOGISTICS_B",
    }.issubset(
        set(second.fractal_runtime_plan_after.active_regional_node_ids)
    )
    assert any(
        item.parent_node_id == target
        and item.to_level == "L3_METRO_OR_LOGISTICS_AREA"
        for item in second.fractal_materialization_commits
    )

    third_persistence = dict(second.fractal_refinement_persistence)
    third_persistence[target] = FractalRefinementPersistenceState(
        node_id=target,
        current_level="L3_METRO_OR_LOGISTICS_AREA",
        last_evaluated_day=2,
        expand_streak=0,
        collapse_streak=33,
    )
    third_store = _replace_child_pressure(
        second.fractal_child_state_store,
        node_ids={
            target,
            "ESP::CT::METRO_A",
            "ESP::CT::LOGISTICS_B",
        },
        high=False,
    )

    third = run_day_transaction(
        states=second.states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        fractal_refinement_persistence=third_persistence,
        fractal_topology=second.fractal_topology,
        fractal_child_state_store=third_store,
        **_recursive_core_kwargs(configs),
    )

    assert third.fractal_topology is not None
    assert third.fractal_child_state_store is not None
    assert third.fractal_runtime_plan_after is not None
    assert third.fractal_topology.active_children(target) == ()
    assert (
        third.fractal_refinement_persistence[target].current_level
        == "L2_REGION"
    )
    assert target in third.fractal_runtime_plan_after.active_regional_node_ids
    assert all(
        item.from_level == "L3_METRO_OR_LOGISTICS_AREA"
        and item.to_level == "L2_REGION"
        for item in third.fractal_collapse_commits
        if item.parent_node_id == target
    )
    historical_gen1 = {
        item.node_id: item.to_dict()
        for item in third.fractal_topology.nodes
        if item.parent_node_id == target
    }
    assert set(historical_gen1) == {
        "ESP::CT::METRO_A",
        "ESP::CT::LOGISTICS_B",
    }
    assert all(
        item["active"] is False and item["de_refinement_day"] == 3
        for item in historical_gen1.values()
    )

    fourth_persistence = dict(third.fractal_refinement_persistence)
    fourth_persistence[target] = FractalRefinementPersistenceState(
        node_id=target,
        current_level="L2_REGION",
        last_evaluated_day=3,
        expand_streak=7,
        collapse_streak=0,
    )
    fourth_store = _replace_child_pressure(
        third.fractal_child_state_store,
        node_ids={target},
        high=True,
    )

    fourth = run_day_transaction(
        states=third.states,
        graph=graph,
        day_config=day_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=TraceLedger(),
        fractal_refinement_persistence=fourth_persistence,
        fractal_topology=third.fractal_topology,
        fractal_child_state_store=fourth_store,
        **_recursive_core_kwargs(configs),
    )

    assert fourth.fractal_topology is not None
    assert fourth.fractal_child_state_store is not None
    assert fourth.fractal_runtime_plan_after is not None
    l3_gen2 = fourth.fractal_topology.active_children(target)
    assert {item.node_id for item in l3_gen2} == {
        "ESP::CT::METRO_A::g2",
        "ESP::CT::LOGISTICS_B::g2",
    }
    assert {item.catalog_child_id for item in l3_gen2} == {
        "ESP::CT::METRO_A",
        "ESP::CT::LOGISTICS_B",
    }
    assert {item.lineage_generation for item in l3_gen2} == {2}
    assert set(historical_gen1).isdisjoint(
        {item.node_id for item in l3_gen2}
    )

    for node_id, before in historical_gen1.items():
        after = next(
            item
            for item in fourth.fractal_topology.nodes
            if item.node_id == node_id
        )
        assert after.to_dict() == before

    active_ids = set(
        fourth.fractal_runtime_plan_after.active_regional_node_ids
    )
    assert target not in active_ids
    assert {
        "ESP::CT::METRO_A::g2",
        "ESP::CT::LOGISTICS_B::g2",
    }.issubset(active_ids)



def test_v034d_missing_l3_catalog_blocks_refinement_without_aborting_day() -> None:
    logger.info(
        "test_v034d_missing_l3_catalog_blocks_refinement_without_aborting_day"
    )
    (
        states,
        graph,
        day_config,
        registry,
        parameters,
        rng,
        manifest,
    ) = _runtime(seed=3435)
    parameters = _disable_events(parameters)
    configs = _configs()

    for state in states.values():
        for variable in state.latents:
            state.latents[variable] = 0.5
    _force_refinement_state(states["ESP"])
    _set_parent_stocks(states["ESP"])

    initial_persistence = {
        node_id: FractalRefinementPersistenceState(
            node_id=node_id,
            current_level="L1_COUNTRY",
            last_evaluated_day=0,
            expand_streak=7 if node_id == "ESP" else 0,
            collapse_streak=0,
        )
        for node_id in states
    }

    common = {
        "enable_fractal_refinement_evaluator": True,
        "fractal_refinement_config": configs["refinement"],
        "enable_fractal_materialization": True,
        "fractal_materialization_config": configs["materialization"],
        "fractal_region_catalog": _catalog(),
        "enable_fractal_child_state_initialization": True,
        "fractal_child_state_config": configs["child"],
        "enable_fractal_runtime_plan": True,
        "fractal_runtime_config": configs["runtime"],
        "enable_fractal_reaggregation": True,
        "fractal_reaggregation_config": configs["reaggregation"],
    }

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
        fractal_refinement_persistence=initial_persistence,
        fractal_topology=None,
        fractal_child_state_store=None,
        **common,
    )

    target = "ESP::MD"
    assert first.fractal_child_state_store is not None
    assert first.fractal_topology is not None

    persistence = dict(first.fractal_refinement_persistence)
    persistence[target] = FractalRefinementPersistenceState(
        node_id=target,
        current_level="L2_REGION",
        last_evaluated_day=1,
        expand_streak=7,
        collapse_streak=0,
    )
    child_store = _replace_child_pressure(
        first.fractal_child_state_store,
        node_ids={target},
        high=True,
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
        fractal_refinement_persistence=persistence,
        fractal_topology=first.fractal_topology,
        fractal_child_state_store=child_store,
        **common,
    )

    assert second.fractal_topology is not None
    assert second.fractal_runtime_plan_after is not None
    assert second.fractal_topology.active_children(target) == ()
    assert target in second.fractal_runtime_plan_after.active_regional_node_ids
    assert (
        second.fractal_refinement_persistence[target].current_level
        == "L2_REGION"
    )
    assert second.fractal_refinement_persistence[target].expand_streak >= 8
    assert not any(
        item.parent_node_id == target
        for item in second.fractal_materialization_commits
    )

    blocked = [
        item
        for item in trace.records
        if item["record_type"]
        == "fractal_refinement_blocked_missing_catalog"
    ]
    assert len(blocked) == 1
    assert blocked[0]["node_id"] == target
    assert blocked[0]["catalog_parent_id"] == target
    assert blocked[0]["from_level"] == "L2_REGION"
    assert blocked[0]["to_level"] == "L3_METRO_OR_LOGISTICS_AREA"
    assert blocked[0]["apply_status"] == "BLOCKED_NOT_APPLIED"
