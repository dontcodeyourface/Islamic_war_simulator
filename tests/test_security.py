from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.resolver import resolve_delta_proposals
from iwsim.security import propose_security_chain_dynamics
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _state_fixture() -> tuple[EngineState, dict, dict, dict]:
    logger.info("_state_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    config = load_yaml(ROOT / "config/engine/security_chain_dynamics_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=4,
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
    return state, registry, parameters, config


def _set_scores(
    state: EngineState,
    *,
    stress: float,
    resilience: float,
) -> None:
    logger.info(
        "_set_scores node=%s stress=%s resilience=%s",
        state.node_id,
        stress,
        resilience,
    )
    state.latents["public_order_stress"] = stress
    state.latents["external_conflict_pressure"] = stress
    state.latents["organized_armed_actor_capacity"] = stress
    state.latents["salary_payment_continuity"] = resilience
    state.latents["government_legitimacy"] = resilience
    state.latents["transport_logistics_functionality"] = resilience
    state.latents["police_effective_capacity"] = resilience
    state.latents["intelligence_effectiveness"] = resilience
    state.latents["administrative_capacity"] = resilience
    state.latents["social_cohesion"] = resilience


def test_high_stress_erodes_cohesion_and_accumulates_fatigue() -> None:
    logger.info("test_high_stress_erodes_cohesion_and_accumulates_fatigue")
    state, registry, parameters, config = _state_fixture()
    _set_scores(state, stress=1.0, resilience=0.0)
    state.latents["security_chain_cohesion"] = 0.8
    state.latents["command_cohesion"] = 0.8
    state.latents["constitutional_loyalty"] = 0.8
    state.latents["operational_fatigue"] = 0.2
    before = state.state_hash()
    trace = TraceLedger()

    proposals = propose_security_chain_dynamics(
        states={"TST": state},
        security_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
    )
    by_variable = {item.variable: item for item in proposals}

    assert set(by_variable) == {
        "security_chain_cohesion",
        "command_cohesion",
        "constitutional_loyalty",
        "operational_fatigue",
    }
    assert by_variable["security_chain_cohesion"].raw_delta == pytest.approx(-0.0096)
    assert by_variable["command_cohesion"].raw_delta == pytest.approx(-0.0096)
    assert by_variable["constitutional_loyalty"].raw_delta == pytest.approx(-0.0024)
    assert by_variable["operational_fatigue"].raw_delta == pytest.approx(0.0096)
    assert all(item.owner_module == "security" for item in proposals)
    assert all(
        item.parameter_ids == (
            "SECURITY_CHAIN_DYNAMICS_SYN_V1",
            "DYNAMIC_GAINS_SYN_V1",
        )
        for item in proposals
    )
    assert state.state_hash() == before

    evaluations = [
        item
        for item in trace.records
        if item["record_type"] == "security_chain_dynamics_evaluation"
    ]
    assert len(evaluations) == 4
    assert all(item["stress_score"] == pytest.approx(1.0) for item in evaluations)
    assert all(item["resilience_score"] == pytest.approx(0.0) for item in evaluations)


def test_high_resilience_recovers_cohesion_and_reduces_fatigue() -> None:
    logger.info("test_high_resilience_recovers_cohesion_and_reduces_fatigue")
    state, registry, parameters, config = _state_fixture()
    _set_scores(state, stress=0.0, resilience=1.0)
    state.latents["security_chain_cohesion"] = 0.2
    state.latents["command_cohesion"] = 0.2
    state.latents["constitutional_loyalty"] = 0.2
    state.latents["operational_fatigue"] = 0.8

    proposals = propose_security_chain_dynamics(
        states={"TST": state},
        security_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    by_variable = {item.variable: item for item in proposals}
    assert by_variable["security_chain_cohesion"].raw_delta == pytest.approx(0.0096)
    assert by_variable["command_cohesion"].raw_delta == pytest.approx(0.0096)
    assert by_variable["constitutional_loyalty"].raw_delta == pytest.approx(0.0024)
    assert by_variable["operational_fatigue"].raw_delta == pytest.approx(-0.0096)

    resolved = resolve_delta_proposals(
        states={"TST": state},
        proposals=proposals,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    assert resolved.states["TST"].latents["security_chain_cohesion"] == pytest.approx(
        0.2096
    )
    assert resolved.states["TST"].latents["operational_fatigue"] == pytest.approx(
        0.7904
    )


def test_security_chain_weight_sets_fail_closed_when_not_normalized() -> None:
    logger.info("test_security_chain_weight_sets_fail_closed_when_not_normalized")
    state, registry, parameters, config = _state_fixture()
    broken = copy.deepcopy(parameters)
    broken["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "SECURITY_CHAIN_DYNAMICS_SYN_V1"
    ]["value"]["stress_weights"]["public_order_stress"] = 0.40

    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        propose_security_chain_dynamics(
            states={"TST": state},
            security_config=config,
            engine_state_registry=registry,
            parameter_registry=broken,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_security_chain_safety_flags_fail_closed() -> None:
    logger.info("test_security_chain_safety_flags_fail_closed")
    state, registry, parameters, config = _state_fixture()
    broken = copy.deepcopy(config)
    broken["safety_and_integrity"][
        "political_party_preference_as_fracture_input"
    ] = True

    with pytest.raises(ValueError, match="safety invariant"):
        propose_security_chain_dynamics(
            states={"TST": state},
            security_config=broken,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_security_chain_canonical_targets_cannot_be_replaced() -> None:
    logger.info("test_security_chain_canonical_targets_cannot_be_replaced")
    state, registry, parameters, config = _state_fixture()
    broken = copy.deepcopy(config)
    broken["targets"][0]["variable"] = "government_legitimacy"

    with pytest.raises(ValueError, match="canonical security variables"):
        propose_security_chain_dynamics(
            states={"TST": state},
            security_config=broken,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_calibrated_security_chain_profile_fails_closed() -> None:
    logger.info("test_calibrated_security_chain_profile_fails_closed")
    state, registry, parameters, config = _state_fixture()

    with pytest.raises(ValueError, match="Missing security-chain parameter"):
        propose_security_chain_dynamics(
            states={"TST": state},
            security_config=config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="calibrated_v1",
            trace=TraceLedger(),
        )
