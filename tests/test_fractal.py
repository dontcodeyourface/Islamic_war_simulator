from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal import (
    FractalRefinementPersistenceState,
    evaluate_fractal_refinement,
)
from iwsim.manifest import build_manifest
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture(
    *,
    day: int = 1,
) -> tuple[EngineState, dict, dict, object]:
    logger.info("_fixture day=%s", day)
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    config = load_yaml(ROOT / "config/engine/fractal_refinement_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=day,
        physical_stocks={},
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={},
    )
    manifest = build_manifest(
        run_id="fractal-refinement-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.19.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-FRACTAL-TEST",
        scenario_hash=canonical_hash({"scenario": "fractal-test"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=1,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=90,
        enabled_modules=("fractal_refinement_evaluator",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state, parameters, config, manifest


def _set_high_refinement_pressure(state: EngineState) -> None:
    logger.info("_set_high_refinement_pressure node=%s", state.node_id)
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
        "security_chain_cohesion",
        "electricity_functionality",
        "fuel_distribution_functionality",
        "transport_logistics_functionality",
        "telecom_internet_functionality",
        "water_resilience",
    ):
        state.latents[variable] = 0.0


def _set_low_refinement_pressure(state: EngineState) -> None:
    logger.info("_set_low_refinement_pressure node=%s", state.node_id)
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
        state.latents[variable] = 0.0
    for variable in (
        "government_legitimacy",
        "state_cohesion",
        "security_chain_cohesion",
        "electricity_functionality",
        "fuel_distribution_functionality",
        "transport_logistics_functionality",
        "telecom_internet_functionality",
        "water_resilience",
    ):
        state.latents[variable] = 1.0


def test_l1_expansion_requires_eight_consecutive_high_pressure_days() -> None:
    logger.info(
        "test_l1_expansion_requires_eight_consecutive_high_pressure_days"
    )
    state, parameters, config, manifest = _fixture()
    _set_high_refinement_pressure(state)
    persistence: FractalRefinementPersistenceState | None = None

    for day in range(1, 9):
        state.day = day
        result = evaluate_fractal_refinement(
            state=state,
            persistence=persistence,
            refinement_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence
        assert result.refinement_pressure == pytest.approx(1.0)
        assert persistence.current_level == "L1_COUNTRY"
        assert persistence.expand_streak == day
        assert persistence.collapse_streak == 0
        if day < 8:
            assert result.proposals == ()
        else:
            assert len(result.proposals) == 1
            proposal = result.proposals[0]
            assert proposal.action == "EXPAND"
            assert proposal.from_level == "L1_COUNTRY"
            assert proposal.to_level == "L2_REGION"
            assert proposal.persistence_required == 8
            assert proposal.persistence_observed == 8
            assert proposal.apply_status == "PROPOSED_NOT_APPLIED"
            assert proposal.equation_id == "REFINEMENT_TRIGGER_V1"
            assert proposal.parameter_id == "FRACTAL_REFINEMENT_SYN_V1"
            assert proposal.initialization_weight_policy_id == (
                "FRACTAL_CHILD_INIT_WEIGHTS_V1"
            )
            assert proposal.inherited_uncertainty_policy_id == (
                "FRACTAL_UNCERTAINTY_WIDENING_V1"
            )
            assert proposal.aggregation_rule_id == (
                "FRACTAL_PARENT_REAGGREGATION_V1"
            )


def test_l2_collapse_requires_thirty_four_consecutive_low_pressure_days() -> None:
    logger.info(
        "test_l2_collapse_requires_thirty_four_consecutive_low_pressure_days"
    )
    state, parameters, config, manifest = _fixture()
    _set_low_refinement_pressure(state)
    persistence: FractalRefinementPersistenceState | None = (
        FractalRefinementPersistenceState(
            node_id="TST",
            current_level="L2_REGION",
            last_evaluated_day=0,
            expand_streak=0,
            collapse_streak=0,
        )
    )

    for day in range(1, 35):
        state.day = day
        result = evaluate_fractal_refinement(
            state=state,
            persistence=persistence,
            refinement_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence
        assert result.refinement_pressure == pytest.approx(0.0)
        assert persistence.current_level == "L2_REGION"
        assert persistence.expand_streak == 0
        assert persistence.collapse_streak == day
        if day < 34:
            assert result.proposals == ()
        else:
            assert len(result.proposals) == 1
            proposal = result.proposals[0]
            assert proposal.action == "COLLAPSE"
            assert proposal.from_level == "L2_REGION"
            assert proposal.to_level == "L1_COUNTRY"
            assert proposal.persistence_required == 34
            assert proposal.persistence_observed == 34


def test_refinement_pressure_components_are_traceable_and_read_only() -> None:
    logger.info(
        "test_refinement_pressure_components_are_traceable_and_read_only"
    )
    state, parameters, config, manifest = _fixture()
    _set_high_refinement_pressure(state)
    before = state.state_hash()
    trace = TraceLedger()

    result = evaluate_fractal_refinement(
        state=state,
        persistence=None,
        refinement_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=trace,
    )

    assert state.state_hash() == before
    assert {
        item.component: item.score
        for item in result.component_scores
    } == {
        "violence": pytest.approx(1.0),
        "institutional_stress": pytest.approx(1.0),
        "infrastructure_stress": pytest.approx(1.0),
        "network_activity": pytest.approx(1.0),
        "displacement": pytest.approx(1.0),
    }
    evaluation = next(
        item
        for item in trace.records
        if item["record_type"] == "fractal_refinement_evaluation"
    )
    assert evaluation["equation_id"] == "REFINEMENT_TRIGGER_V1"
    assert evaluation["parameter_id"] == "FRACTAL_REFINEMENT_SYN_V1"
    assert evaluation["refinement_reason"] in {
        "violence",
        "institutional_stress",
        "infrastructure_stress",
        "network_activity",
        "displacement",
    }


def test_refinement_streak_resets_inside_hysteresis_band() -> None:
    logger.info("test_refinement_streak_resets_inside_hysteresis_band")
    state, parameters, config, manifest = _fixture(day=2)
    persistence = FractalRefinementPersistenceState(
        node_id="TST",
        current_level="L1_COUNTRY",
        last_evaluated_day=1,
        expand_streak=4,
        collapse_streak=0,
    )
    for variable in state.latents:
        state.latents[variable] = 0.5

    result = evaluate_fractal_refinement(
        state=state,
        persistence=persistence,
        refinement_config=config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert result.persistence.expand_streak == 0
    assert result.proposals == ()


def test_refinement_hysteresis_thresholds_fail_closed_when_overlapping() -> None:
    logger.info(
        "test_refinement_hysteresis_thresholds_fail_closed_when_overlapping"
    )
    state, parameters, config, manifest = _fixture()
    broken = copy.deepcopy(parameters)
    refinement = broken["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "FRACTAL_REFINEMENT_SYN_V1"
    ]["value"]
    refinement["collapse_threshold"] = refinement["expand_threshold"]

    with pytest.raises(ValueError, match="collapse_threshold < expand_threshold"):
        evaluate_fractal_refinement(
            state=state,
            persistence=None,
            refinement_config=config,
            parameter_registry=broken,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_refinement_weights_must_match_components_and_sum_to_one() -> None:
    logger.info(
        "test_refinement_weights_must_match_components_and_sum_to_one"
    )
    state, parameters, config, manifest = _fixture()
    broken = copy.deepcopy(parameters)
    weights = broken["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "FRACTAL_REFINEMENT_SYN_V1"
    ]["value"]["weights"]
    weights["violence"] = 0.40

    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        evaluate_fractal_refinement(
            state=state,
            persistence=None,
            refinement_config=config,
            parameter_registry=broken,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_calibrated_fractal_profile_fails_closed() -> None:
    logger.info("test_calibrated_fractal_profile_fails_closed")
    state, parameters, config, manifest = _fixture()

    with pytest.raises(ValueError, match="Missing fractal-refinement parameter"):
        evaluate_fractal_refinement(
            state=state,
            persistence=None,
            refinement_config=config,
            parameter_registry=parameters,
            profile="calibrated_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )



def _as_l2_state(state: EngineState) -> EngineState:
    logger.info("_as_l2_state")
    return EngineState(
        node_id="TST::R1",
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes=dict(state.regimes),
        metadata={
            **state.metadata,
            "fractal_level": "L2_REGION",
            "fractal_parent_node_id": "TST",
            "fractal_runtime_node_id": "TST::R1",
        },
    )


def test_l2_base_expansion_requires_high_pressure_and_targets_l3() -> None:
    logger.info(
        "test_l2_base_expansion_requires_high_pressure_and_targets_l3"
    )
    state, parameters, config, manifest = _fixture()
    state = _as_l2_state(state)
    _set_high_refinement_pressure(state)
    persistence: FractalRefinementPersistenceState | None = None

    for day in range(1, 9):
        state.day = day
        result = evaluate_fractal_refinement(
            state=state,
            persistence=persistence,
            refinement_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence
        assert persistence.current_level == "L2_REGION"
        if day < 8:
            assert result.proposals == ()
        else:
            assert len(result.proposals) == 1
            proposal = result.proposals[0]
            assert proposal.action == "EXPAND"
            assert proposal.from_level == "L2_REGION"
            assert proposal.to_level == "L3_METRO_OR_LOGISTICS_AREA"


def test_l2_base_refined_resolution_collapses_l3_back_to_l2() -> None:
    logger.info(
        "test_l2_base_refined_resolution_collapses_l3_back_to_l2"
    )
    state, parameters, config, manifest = _fixture()
    state = _as_l2_state(state)
    _set_low_refinement_pressure(state)
    persistence = FractalRefinementPersistenceState(
        node_id="TST::R1",
        current_level="L3_METRO_OR_LOGISTICS_AREA",
        last_evaluated_day=0,
        expand_streak=0,
        collapse_streak=0,
    )

    for day in range(1, 35):
        state.day = day
        result = evaluate_fractal_refinement(
            state=state,
            persistence=persistence,
            refinement_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
        persistence = result.persistence
        assert persistence.current_level == "L3_METRO_OR_LOGISTICS_AREA"
        if day < 34:
            assert result.proposals == ()
        else:
            assert len(result.proposals) == 1
            proposal = result.proposals[0]
            assert proposal.action == "COLLAPSE"
            assert proposal.from_level == "L3_METRO_OR_LOGISTICS_AREA"
            assert proposal.to_level == "L2_REGION"


def test_l2_base_rejects_non_adjacent_persistence_level() -> None:
    logger.info(
        "test_l2_base_rejects_non_adjacent_persistence_level"
    )
    state, parameters, config, manifest = _fixture(day=2)
    state = _as_l2_state(state)
    persistence = FractalRefinementPersistenceState(
        node_id="TST::R1",
        current_level="L1_COUNTRY",
        last_evaluated_day=1,
        expand_streak=0,
        collapse_streak=0,
    )

    with pytest.raises(ValueError, match="not adjacent"):
        evaluate_fractal_refinement(
            state=state,
            persistence=persistence,
            refinement_config=config,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            manifest=manifest,
            trace=TraceLedger(),
        )
