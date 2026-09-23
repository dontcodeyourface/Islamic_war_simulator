from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.reciprocal import propose_reciprocal_radicalization_effects
from iwsim.resolver import resolve_delta_proposals
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _state_fixture() -> tuple[EngineState, dict, dict, dict]:
    logger.info("_state_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feedback_config = load_yaml(
        ROOT / "config/engine/reciprocal_radicalization_v1.yaml"
    )
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=7,
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
    state.validate(latent_registry)
    return state, registry, parameters, feedback_config


def _set_feedback_state(
    state: EngineState,
    *,
    islamist: float,
    ultranationalist: float,
    fear: float,
    narrative: float,
    damping: float,
) -> None:
    logger.info(
        "_set_feedback_state node=%s islamist=%s ultra=%s fear=%s narrative=%s damping=%s",
        state.node_id,
        islamist,
        ultranationalist,
        fear,
        narrative,
        damping,
    )
    state.latents["violent_islamist_pressure"] = islamist
    state.latents["violent_ultranationalist_pressure"] = ultranationalist
    state.latents["communal_fear"] = fear
    state.latents["civilizational_narrative_strength"] = narrative
    for variable in (
        "social_cohesion",
        "government_legitimacy",
        "police_effective_capacity",
        "intelligence_effectiveness",
    ):
        state.latents[variable] = damping


def test_reciprocal_feedback_is_symmetric_traceable_and_non_mutating() -> None:
    logger.info(
        "test_reciprocal_feedback_is_symmetric_traceable_and_non_mutating"
    )
    state, registry, parameters, feedback_config = _state_fixture()
    _set_feedback_state(
        state,
        islamist=0.8,
        ultranationalist=0.2,
        fear=1.0,
        narrative=0.0,
        damping=0.0,
    )
    before = state.state_hash()
    trace = TraceLedger()

    proposals = propose_reciprocal_radicalization_effects(
        states={"TST": state},
        feedback_config=feedback_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
    )

    assert len(proposals) == 2
    by_variable = {item.variable: item for item in proposals}
    assert by_variable["violent_ultranationalist_pressure"].raw_delta == pytest.approx(
        0.016
    )
    assert by_variable["violent_islamist_pressure"].raw_delta == pytest.approx(
        0.004
    )
    assert by_variable["violent_ultranationalist_pressure"].value_before == pytest.approx(
        0.2
    )
    assert by_variable["violent_islamist_pressure"].value_before == pytest.approx(
        0.8
    )
    assert all(
        item.event_type == "RECIPROCAL_RADICALIZATION_V1"
        for item in proposals
    )
    assert all(
        item.parameter_ids == ("RECIPROCAL_RADICALIZATION_SYN_V1",)
        for item in proposals
    )
    assert state.state_hash() == before

    evaluations = [
        item
        for item in trace.records
        if item["record_type"] == "reciprocal_radicalization_evaluation"
    ]
    delta_records = [
        item
        for item in trace.records
        if item["record_type"] == "reciprocal_radicalization_delta_proposal"
    ]
    assert len(evaluations) == 2
    assert len(delta_records) == 2


def test_institutional_damping_can_reverse_feedback_delta() -> None:
    logger.info("test_institutional_damping_can_reverse_feedback_delta")
    state, registry, parameters, feedback_config = _state_fixture()
    _set_feedback_state(
        state,
        islamist=0.4,
        ultranationalist=0.4,
        fear=0.5,
        narrative=0.2,
        damping=1.0,
    )

    proposals = propose_reciprocal_radicalization_effects(
        states={"TST": state},
        feedback_config=feedback_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    assert len(proposals) == 2
    expected = (0.020 * 0.4 * 0.5) + (0.012 * 0.2 * 0.4) - (0.025 * 1.0 * 0.4)
    assert expected < 0.0
    assert all(item.raw_delta == pytest.approx(expected) for item in proposals)

    result = resolve_delta_proposals(
        states={"TST": state},
        proposals=proposals,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    assert result.states["TST"].latents[
        "violent_islamist_pressure"
    ] == pytest.approx(0.4 + expected)
    assert result.states["TST"].latents[
        "violent_ultranationalist_pressure"
    ] == pytest.approx(0.4 + expected)


def test_zero_network_pressures_emit_evaluations_but_no_deltas() -> None:
    logger.info("test_zero_network_pressures_emit_evaluations_but_no_deltas")
    state, registry, parameters, feedback_config = _state_fixture()
    _set_feedback_state(
        state,
        islamist=0.0,
        ultranationalist=0.0,
        fear=1.0,
        narrative=1.0,
        damping=0.0,
    )
    trace = TraceLedger()

    proposals = propose_reciprocal_radicalization_effects(
        states={"TST": state},
        feedback_config=feedback_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
    )

    assert proposals == ()
    evaluations = [
        item
        for item in trace.records
        if item["record_type"] == "reciprocal_radicalization_evaluation"
    ]
    assert len(evaluations) == 2
    assert all(item["raw_delta"] == pytest.approx(0.0) for item in evaluations)


def test_reciprocal_direction_contract_must_be_exactly_mirrored() -> None:
    logger.info("test_reciprocal_direction_contract_must_be_exactly_mirrored")
    state, registry, parameters, feedback_config = _state_fixture()
    broken = copy.deepcopy(feedback_config)
    broken["directions"][1]["source_variable"] = "revolutionary_extremist_pressure"

    with pytest.raises(ValueError, match="exact mirrors"):
        propose_reciprocal_radicalization_effects(
            states={"TST": state},
            feedback_config=broken,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_calibrated_reciprocal_profile_fails_closed() -> None:
    logger.info("test_calibrated_reciprocal_profile_fails_closed")
    state, registry, parameters, feedback_config = _state_fixture()

    with pytest.raises(
        ValueError,
        match="Missing reciprocal-radicalization parameter",
    ):
        propose_reciprocal_radicalization_effects(
            states={"TST": state},
            feedback_config=feedback_config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="calibrated_v1",
            trace=TraceLedger(),
        )


def test_feedback_config_has_no_civilian_identity_propensity_inputs() -> None:
    logger.info("test_feedback_config_has_no_civilian_identity_propensity_inputs")
    _, _, _, feedback_config = _state_fixture()
    serialized = str(feedback_config).lower()
    forbidden = (
        "muslim_share",
        "christian_share",
        "religious_share",
        "party_vote",
        "nationality_share",
        "mosque_count",
    )
    assert not any(item in serialized for item in forbidden)
