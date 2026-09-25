from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal import (
    FractalRefinementActionProposal,
    FractalRefinementPersistenceState,
)
from iwsim.fractal_child_state import (
    FractalChildStateStore,
    empty_fractal_child_state_store,
    initialize_fractal_child_states,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from iwsim.fractal_reaggregation import collapse_l2_to_l1
from iwsim.fractal_uncertainty import apply_fractal_uncertainty
from iwsim.manifest import build_manifest
from iwsim.rng import RNGManager
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _manifest(parameters: dict) -> object:
    logger.info("_manifest")
    return build_manifest(
        run_id="fractal-reaggregation-test",
        created_at="2026-09-24T00:00:00+00:00",
        engine_version="0.23.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-FRACTAL-REAGGREGATION",
        scenario_hash=canonical_hash({"scenario": "fractal-reaggregation"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=2301,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-24",
        horizon_days=60,
        enabled_modules=("fractal_collapse_reaggregation",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )


def _fixture():
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    child_config = load_yaml(
        ROOT / "config/engine/fractal_child_state_v1.yaml"
    )
    uncertainty_config = load_yaml(
        ROOT / "config/engine/fractal_uncertainty_v1.yaml"
    )
    reaggregation_config = load_yaml(
        ROOT / "config/engine/fractal_reaggregation_v1.yaml"
    )
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    parent = EngineState(
        node_id="TST",
        day=1,
        physical_stocks={
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
        },
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={"country_name": "Testland"},
    )
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(
            FractalTopologyNode(
                node_id="TST::R1",
                label="Region 1",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="expand-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.5,
                initialization_weight_policy_id=(
                    "FRACTAL_CHILD_INIT_WEIGHTS_V1"
                ),
                inherited_uncertainty_policy_id=(
                    "FRACTAL_UNCERTAINTY_WIDENING_V1"
                ),
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
            FractalTopologyNode(
                node_id="TST::R2",
                label="Region 2",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="expand-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.3,
                initialization_weight_policy_id=(
                    "FRACTAL_CHILD_INIT_WEIGHTS_V1"
                ),
                inherited_uncertainty_policy_id=(
                    "FRACTAL_UNCERTAINTY_WIDENING_V1"
                ),
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
            FractalTopologyNode(
                node_id="TST::R3",
                label="Region 3",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="expand-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.2,
                initialization_weight_policy_id=(
                    "FRACTAL_CHILD_INIT_WEIGHTS_V1"
                ),
                inherited_uncertainty_policy_id=(
                    "FRACTAL_UNCERTAINTY_WIDENING_V1"
                ),
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
        ),
    )
    initialized = initialize_fractal_child_states(
        parent_states={"TST": parent},
        topology=topology,
        child_store=empty_fractal_child_state_store(0),
        initialization_config=child_config,
        engine_state_registry=registry,
        trace=TraceLedger(),
    )
    uncertain = apply_fractal_uncertainty(
        parent_states={"TST": parent},
        topology=topology,
        child_store=initialized.store,
        new_child_ids=tuple(
            item.child_node_id
            for item in initialized.initialization_records
        ),
        uncertainty_config=uncertainty_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(2301),
        trace=TraceLedger(),
    )
    persistence = FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L2_REGION",
        last_evaluated_day=1,
        expand_streak=0,
        collapse_streak=34,
    )
    action = FractalRefinementActionProposal(
        action_id="collapse-test",
        node_id="TST",
        day=1,
        action="COLLAPSE",
        from_level="L2_REGION",
        to_level="L1_COUNTRY",
        refinement_pressure=0.1,
        threshold=0.38,
        persistence_required=34,
        persistence_observed=34,
        refinement_reason="institutional_stress",
        component_scores=(),
        source_variables=("state_cohesion",),
        equation_id="REFINEMENT_TRIGGER_V1",
        parameter_id="FRACTAL_REFINEMENT_SYN_V1",
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
    )
    return (
        parent,
        topology,
        uncertain.store,
        persistence,
        action,
        registry,
        parameters,
        reaggregation_config,
        _manifest(parameters),
    )


def _collapse(
    *,
    parent: EngineState,
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    persistence: FractalRefinementPersistenceState,
    action: FractalRefinementActionProposal,
    registry: dict,
    config: dict,
    manifest: object,
):
    logger.info("_collapse")
    trace = TraceLedger()
    result = collapse_l2_to_l1(
        parent_state=parent,
        action=action,
        persistence=persistence,
        topology=topology,
        child_store=child_store,
        reaggregation_config=config,
        engine_state_registry=registry,
        manifest=manifest,
        trace=trace,
    )
    return (*result, trace)


def test_collapse_reaggregates_conservatively_and_closes_lineage() -> None:
    logger.info(
        "test_collapse_reaggregates_conservatively_and_closes_lineage"
    )
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    parent_before = parent.to_dict()
    topology_before = topology.to_dict()
    store_before = child_store.to_dict()

    (
        parent_after,
        topology_after,
        store_after,
        persistence_after,
        commit,
        audit,
        trace,
    ) = _collapse(
        parent=parent,
        topology=topology,
        child_store=child_store,
        persistence=persistence,
        action=action,
        registry=registry,
        config=config,
        manifest=manifest,
    )

    assert parent.to_dict() == parent_before
    assert topology.to_dict() == topology_before
    assert child_store.to_dict() == store_before

    assert parent_after.physical_stocks["population_total"] == 101
    assert parent_after.physical_stocks["working_age_population"] == 61
    assert parent_after.physical_stocks["dependent_population"] == 40
    assert parent_after.physical_stocks[
        "fuel_stock_days_equivalent"
    ] == pytest.approx(90.0)
    assert parent_after.physical_stocks[
        "strategic_food_stock_days"
    ] == pytest.approx(30.0)
    assert parent_after.physical_stocks[
        "available_military_personnel"
    ] == 1000
    assert parent_after.physical_stocks["foreign_reserves_usd"] == 5000.0
    assert parent_after.physical_stocks["gold_reserves_tonnes"] == 25.0

    for variable, value in parent.latents.items():
        assert parent_after.latents[variable] == pytest.approx(
            value,
            abs=audit.tolerance,
        )
    assert parent_after.regimes == parent.regimes
    assert parent_after.metadata[
        "fractal_last_collapse_action_id"
    ] == action.action_id
    assert parent_after.metadata[
        "fractal_last_reaggregation_audit_id"
    ] == audit.audit_id

    assert topology_after.active_children("TST") == ()
    assert all(
        item.active is False and item.de_refinement_day == 1
        for item in topology_after.nodes
    )
    assert store_after.states == ()
    assert persistence_after == FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L1_COUNTRY",
        last_evaluated_day=1,
        expand_streak=0,
        collapse_streak=0,
    )

    assert audit.conserved is True
    assert audit.max_abs_latent_error <= audit.tolerance
    assert commit.audit_id == audit.audit_id
    assert commit.parent_state_hash_before == parent.state_hash()
    assert commit.parent_state_hash_after == parent_after.state_hash()
    assert commit.topology_hash_before == topology.topology_hash()
    assert commit.topology_hash_after == topology_after.topology_hash()
    assert commit.child_store_hash_before == child_store.store_hash()
    assert commit.child_store_hash_after == store_after.store_hash()

    record_types = [item["record_type"] for item in trace.records]
    assert record_types[:2] == [
        "fractal_reaggregation_audit",
        "fractal_collapse_committed",
    ]
    assert record_types.count("fractal_lineage_closed") == 3


def test_collapse_uses_current_child_additive_totals() -> None:
    logger.info("test_collapse_uses_current_child_additive_totals")
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    states = child_store.state_map()
    first = states["TST::R1"]
    changed = EngineState(
        node_id=first.node_id,
        day=first.day,
        physical_stocks={
            **first.physical_stocks,
            "population_total": int(
                first.physical_stocks["population_total"]
            ) + 2,
        },
        latents=dict(first.latents),
        regimes=dict(first.regimes),
        metadata=dict(first.metadata),
    )
    modified_store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(
            changed if item.node_id == changed.node_id else item
            for item in child_store.states
        ),
    )

    parent_after, _, _, _, _, audit, _ = _collapse(
        parent=parent,
        topology=topology,
        child_store=modified_store,
        persistence=persistence,
        action=action,
        registry=registry,
        config=config,
        manifest=manifest,
    )

    assert parent_after.physical_stocks["population_total"] == 103
    assert dict(audit.additive_child_sums)["population_total"] == 103


def test_collapse_rejects_divergent_child_regimes() -> None:
    logger.info("test_collapse_rejects_divergent_child_regimes")
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    states = child_store.state_map()
    first = states["TST::R1"]
    changed = EngineState(
        node_id=first.node_id,
        day=first.day,
        physical_stocks=dict(first.physical_stocks),
        latents=dict(first.latents),
        regimes={
            **first.regimes,
            "security_force_regime": "STRAINED",
        },
        metadata=dict(first.metadata),
    )
    modified_store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(
            changed if item.node_id == changed.node_id else item
            for item in child_store.states
        ),
    )

    with pytest.raises(ValueError, match="unanimous sibling consensus"):
        _collapse(
            parent=parent,
            topology=topology,
            child_store=modified_store,
            persistence=persistence,
            action=action,
            registry=registry,
            config=config,
            manifest=manifest,
        )


def test_collapse_rejects_mixed_null_additive_children() -> None:
    logger.info("test_collapse_rejects_mixed_null_additive_children")
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    states = child_store.state_map()
    first = states["TST::R1"]
    changed = EngineState(
        node_id=first.node_id,
        day=first.day,
        physical_stocks={
            **first.physical_stocks,
            "working_age_population": None,
        },
        latents=dict(first.latents),
        regimes=dict(first.regimes),
        metadata=dict(first.metadata),
    )
    modified_store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(
            changed if item.node_id == changed.node_id else item
            for item in child_store.states
        ),
    )

    with pytest.raises(ValueError, match="mixed null/numeric"):
        _collapse(
            parent=parent,
            topology=topology,
            child_store=modified_store,
            persistence=persistence,
            action=action,
            registry=registry,
            config=config,
            manifest=manifest,
        )


def test_collapse_rejects_incomplete_child_store() -> None:
    logger.info("test_collapse_rejects_incomplete_child_store")
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    incomplete = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=child_store.states[:-1],
    )
    with pytest.raises(ValueError, match="child store is incomplete"):
        _collapse(
            parent=parent,
            topology=topology,
            child_store=incomplete,
            persistence=persistence,
            action=action,
            registry=registry,
            config=config,
            manifest=manifest,
        )


def test_collapse_rejects_invalid_action_and_rule() -> None:
    logger.info("test_collapse_rejects_invalid_action_and_rule")
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    wrong_level = copy.copy(action)
    object.__setattr__(wrong_level, "to_level", "L2_REGION")
    with pytest.raises(ValueError, match="L2_REGION -> L1_COUNTRY"):
        _collapse(
            parent=parent,
            topology=topology,
            child_store=child_store,
            persistence=persistence,
            action=wrong_level,
            registry=registry,
            config=config,
            manifest=manifest,
        )

    wrong_rule = copy.copy(action)
    object.__setattr__(wrong_rule, "aggregation_rule_id", "OTHER_RULE")
    with pytest.raises(ValueError, match="aggregation rule mismatch"):
        _collapse(
            parent=parent,
            topology=topology,
            child_store=child_store,
            persistence=persistence,
            action=wrong_rule,
            registry=registry,
            config=config,
            manifest=manifest,
        )


def test_collapse_accepts_autonomous_child_dynamics_and_uses_live_state() -> None:
    logger.info(
        "test_collapse_accepts_autonomous_child_dynamics_and_uses_live_state"
    )
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    states = child_store.state_map()
    first = states["TST::R1"]
    changed = EngineState(
        node_id=first.node_id,
        day=first.day,
        physical_stocks={
            **first.physical_stocks,
            "population_total": int(
                first.physical_stocks["population_total"]
            ) + 4,
        },
        latents={
            **first.latents,
            "public_order_stress": min(
                1.0,
                float(first.latents["public_order_stress"]) + 0.2,
            ),
        },
        regimes=dict(first.regimes),
        metadata={
            **first.metadata,
            "fractal_child_dynamics_active": True,
        },
    )
    autonomous_store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(
            changed if item.node_id == changed.node_id else item
            for item in child_store.states
        ),
    )

    parent_after, _, store_after, _, _, audit, trace = _collapse(
        parent=parent,
        topology=topology,
        child_store=autonomous_store,
        persistence=persistence,
        action=action,
        registry=registry,
        config=config,
        manifest=manifest,
    )

    assert parent_after.physical_stocks["population_total"] == 105
    assert dict(audit.additive_child_sums)["population_total"] == 105
    assert parent_after.latents["public_order_stress"] > parent.latents[
        "public_order_stress"
    ]
    assert audit.conserved is True
    assert store_after.states == ()
    assert "fractal_reaggregation_audit" in [
        item["record_type"] for item in trace.records
    ]


def test_dynamic_collapse_then_rerefine_preserves_generation_lineage() -> None:
    logger.info(
        "test_dynamic_collapse_then_rerefine_preserves_generation_lineage"
    )
    (
        parent,
        topology,
        child_store,
        persistence,
        action,
        registry,
        _,
        config,
        manifest,
    ) = _fixture()
    states = child_store.state_map()
    evolved_states = []
    for item in child_store.states:
        evolved_states.append(
            EngineState(
                node_id=item.node_id,
                day=item.day,
                physical_stocks=dict(item.physical_stocks),
                latents=dict(item.latents),
                regimes=dict(item.regimes),
                metadata={
                    **item.metadata,
                    "fractal_child_dynamics_active": True,
                },
            )
        )
    evolved_store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(evolved_states),
    )

    parent_after, topology_after, store_after, persistence_after, _, audit, _ = (
        _collapse(
            parent=parent,
            topology=topology,
            child_store=evolved_store,
            persistence=persistence,
            action=action,
            registry=registry,
            config=config,
            manifest=manifest,
        )
    )

    assert audit.conserved is True
    assert store_after.states == ()
    assert persistence_after.current_level == "L1_COUNTRY"
    assert all(item.active is False for item in topology_after.nodes)
    assert all(item.de_refinement_day == 1 for item in topology_after.nodes)
    assert parent_after.metadata["fractal_last_collapse_action_id"] == (
        action.action_id
    )

    historical_ids = {item.node_id for item in topology_after.nodes}
    historical_generations = {
        item.lineage_generation for item in topology_after.nodes
    }
    assert historical_generations == {1}

    # Generation 2 identity is required to be disjoint from immutable history.
    generation_two_ids = {
        f"{item.catalog_child_id or item.node_id}::G2"
        for item in topology_after.nodes
    }
    assert historical_ids.isdisjoint(generation_two_ids)
    assert len(generation_two_ids) == len(historical_ids)
