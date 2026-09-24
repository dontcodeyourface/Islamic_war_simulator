from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.fractal_child_state import (
    FractalChildStateStore,
    empty_fractal_child_state_store,
    initialize_fractal_child_states,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
)
from iwsim.fractal_uncertainty import apply_fractal_uncertainty
from iwsim.rng import RNGManager
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture():
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    child_config = load_yaml(
        ROOT / "config/engine/fractal_child_state_v1.yaml"
    )
    uncertainty_config = load_yaml(
        ROOT / "config/engine/fractal_uncertainty_v1.yaml"
    )
    parameters = load_yaml(
        ROOT / "config/engine/parameter_registry_v1.yaml"
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
                refinement_action_id="refine-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.5,
                initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
                inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
            FractalTopologyNode(
                node_id="TST::R2",
                label="Region 2",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="refine-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.3,
                initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
                inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
                aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
                catalog_source_id="SYNTHETIC_TEST",
            ),
            FractalTopologyNode(
                node_id="TST::R3",
                label="Region 3",
                parent_node_id="TST",
                level="L2_REGION",
                created_day=1,
                refinement_action_id="refine-test",
                refinement_reason="violence",
                source_variables=("public_order_stress",),
                initialization_weight=0.2,
                initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
                inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
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
    return parent, topology, initialized, registry, parameters, uncertainty_config


def _apply(seed: int):
    logger.info("_apply seed=%s", seed)
    parent, topology, initialized, registry, parameters, config = _fixture()
    rng = RNGManager(seed)
    trace = TraceLedger()
    result = apply_fractal_uncertainty(
        parent_states={"TST": parent},
        topology=topology,
        child_store=initialized.store,
        new_child_ids=tuple(
            item.child_node_id
            for item in initialized.initialization_records
        ),
        uncertainty_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        trace=trace,
    )
    return parent, topology, initialized, result, rng, trace


def test_l2_variation_preserves_weighted_parent_latent_means() -> None:
    logger.info(
        "test_l2_variation_preserves_weighted_parent_latent_means"
    )
    parent, topology, initialized, result, _, trace = _apply(2201)
    children = result.store.state_map()
    assert len(result.records) == 5
    assert len(result.audits) == 1
    assert result.audits[0].preserved is True
    assert result.audits[0].max_abs_error <= result.audits[0].tolerance

    before = initialized.store.state_map()
    assert children["TST::R1"].latents["polarization"] != pytest.approx(
        children["TST::R2"].latents["polarization"]
    )
    for node_id in children:
        assert (
            children[node_id].physical_stocks
            == before[node_id].physical_stocks
        )
        assert children[node_id].regimes == before[node_id].regimes
        assert children[node_id].day == before[node_id].day
        assert (
            children[node_id].metadata["fractal_uncertainty_policy_id"]
            == "FRACTAL_L2_LOCAL_VARIATION_V1"
        )
        assert (
            children[node_id].metadata["fractal_child_dynamics_active"]
            is False
        )

    varied = dict(result.audits[0].parent_values)
    weighted = dict(result.audits[0].weighted_child_values)
    for variable, parent_value in varied.items():
        assert weighted[variable] == pytest.approx(
            parent_value,
            abs=result.audits[0].tolerance,
        )
        direct = sum(
            item.initialization_weight
            * children[item.node_id].latents[variable]
            for item in topology.active_children("TST")
        )
        assert direct == pytest.approx(
            parent.latents[variable],
            abs=result.audits[0].tolerance,
        )

    assert [item["record_type"] for item in trace.records].count(
        "fractal_uncertainty_applied"
    ) == 5
    assert trace.records[-1]["record_type"] == "fractal_uncertainty_audit"


def test_l2_variation_is_seed_replayable_and_seed_sensitive() -> None:
    logger.info("test_l2_variation_is_seed_replayable_and_seed_sensitive")
    first = _apply(2202)[3]
    replay = _apply(2202)[3]
    other = _apply(2203)[3]
    assert first.store.to_dict() == replay.store.to_dict()
    assert [item.to_dict() for item in first.records] == [
        item.to_dict() for item in replay.records
    ]
    assert first.store.to_dict() != other.store.to_dict()


def test_no_new_children_consumes_no_uncertainty_rng_draws() -> None:
    logger.info("test_no_new_children_consumes_no_uncertainty_rng_draws")
    parent, topology, initialized, registry, parameters, config = _fixture()
    rng = RNGManager(2204)
    before = rng.describe()
    result = apply_fractal_uncertainty(
        parent_states={"TST": parent},
        topology=topology,
        child_store=initialized.store,
        new_child_ids=(),
        uncertainty_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=rng,
        trace=TraceLedger(),
    )
    assert result.store == initialized.store
    assert result.records == ()
    assert result.audits == ()
    assert rng.describe() == before


def test_calibrated_profile_fails_closed_without_registered_parameters() -> None:
    logger.info(
        "test_calibrated_profile_fails_closed_without_registered_parameters"
    )
    parent, topology, initialized, registry, parameters, config = _fixture()
    with pytest.raises(
        ValueError,
        match="Missing fractal uncertainty parameter",
    ):
        apply_fractal_uncertainty(
            parent_states={"TST": parent},
            topology=topology,
            child_store=initialized.store,
            new_child_ids=tuple(
                item.child_node_id
                for item in initialized.initialization_records
            ),
            uncertainty_config=config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="calibrated_v1",
            rng=RNGManager(2205),
            trace=TraceLedger(),
        )



def test_uncertainty_cannot_be_reapplied_to_same_children() -> None:
    logger.info("test_uncertainty_cannot_be_reapplied_to_same_children")
    parent, topology, initialized, registry, parameters, config = _fixture()
    child_ids = tuple(
        item.child_node_id
        for item in initialized.initialization_records
    )
    first = apply_fractal_uncertainty(
        parent_states={"TST": parent},
        topology=topology,
        child_store=initialized.store,
        new_child_ids=child_ids,
        uncertainty_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        rng=RNGManager(2206),
        trace=TraceLedger(),
    )

    with pytest.raises(
        ValueError,
        match="already applied",
    ):
        apply_fractal_uncertainty(
            parent_states={"TST": parent},
            topology=topology,
            child_store=first.store,
            new_child_ids=child_ids,
            uncertainty_config=config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            rng=RNGManager(2207),
            trace=TraceLedger(),
        )


def test_uncertainty_rejects_children_created_on_prior_day() -> None:
    logger.info("test_uncertainty_rejects_children_created_on_prior_day")
    parent, topology, initialized, registry, parameters, config = _fixture()
    day_two_parent = EngineState(
        node_id=parent.node_id,
        day=2,
        physical_stocks=dict(parent.physical_stocks),
        latents=dict(parent.latents),
        regimes=dict(parent.regimes),
        metadata=dict(parent.metadata),
    )
    day_two_children = tuple(
        EngineState(
            node_id=state.node_id,
            day=2,
            physical_stocks=dict(state.physical_stocks),
            latents=dict(state.latents),
            regimes=dict(state.regimes),
            metadata=dict(state.metadata),
        )
        for state in initialized.store.states
    )
    day_two_store = FractalChildStateStore(
        last_initialized_day=2,
        states=day_two_children,
    )
    day_two_topology = FractalTopologyState(
        last_committed_day=2,
        nodes=topology.nodes,
    )
    child_ids = tuple(
        item.child_node_id
        for item in initialized.initialization_records
    )

    with pytest.raises(
        ValueError,
        match="may only sample children created on the current day",
    ):
        apply_fractal_uncertainty(
            parent_states={"TST": day_two_parent},
            topology=day_two_topology,
            child_store=day_two_store,
            new_child_ids=child_ids,
            uncertainty_config=config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            rng=RNGManager(2208),
            trace=TraceLedger(),
        )
