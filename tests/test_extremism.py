from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.extremism import propose_extremist_network_dynamics
from iwsim.resolver import resolve_delta_proposals
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]

NETWORK_VARIABLES = (
    "violent_islamist_pressure",
    "violent_ultranationalist_pressure",
    "revolutionary_extremist_pressure",
)


def _fixture() -> tuple[EngineState, dict, dict, dict]:
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    config = load_yaml(ROOT / "config/engine/extremist_network_dynamics_v1.yaml")
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


def _set_high_drivers_low_damping(state: EngineState) -> None:
    logger.info("_set_high_drivers_low_damping")
    state.latents["polarization"] = 1.0
    state.latents["communal_fear"] = 1.0
    state.latents["civilizational_narrative_strength"] = 1.0
    state.latents["foreign_support_nonstate"] = 1.0
    state.latents["prison_control"] = 0.0
    state.latents["police_effective_capacity"] = 0.0
    state.latents["intelligence_effectiveness"] = 0.0
    state.latents["government_legitimacy"] = 0.0
    state.latents["social_cohesion"] = 0.0


def _set_low_drivers_high_damping(state: EngineState) -> None:
    logger.info("_set_low_drivers_high_damping")
    state.latents["polarization"] = 0.0
    state.latents["communal_fear"] = 0.0
    state.latents["civilizational_narrative_strength"] = 0.0
    state.latents["foreign_support_nonstate"] = 0.0
    state.latents["prison_control"] = 1.0
    state.latents["police_effective_capacity"] = 1.0
    state.latents["intelligence_effectiveness"] = 1.0
    state.latents["government_legitimacy"] = 1.0
    state.latents["social_cohesion"] = 1.0


def test_parallel_families_share_identical_equation_and_positive_delta() -> None:
    logger.info(
        "test_parallel_families_share_identical_equation_and_positive_delta"
    )
    state, registry, parameters, config = _fixture()
    _set_high_drivers_low_damping(state)
    for variable in NETWORK_VARIABLES:
        state.latents[variable] = 0.25

    before = state.state_hash()
    trace = TraceLedger()
    proposals = propose_extremist_network_dynamics(
        states={"TST": state},
        network_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
    )

    assert len(proposals) == 3
    assert {item.variable for item in proposals} == set(NETWORK_VARIABLES)
    assert all(item.raw_delta == pytest.approx(0.009) for item in proposals)
    assert all(
        item.equation_id == "EXTREMIST_NETWORK_PRESSURE_V1"
        for item in proposals
    )
    assert all(
        item.owner_module == "non_state_networks"
        for item in proposals
    )
    assert all(
        item.parameter_ids
        == (
            "EXTREMIST_NETWORK_DYNAMICS_SYN_V1",
            "DYNAMIC_GAINS_SYN_V1",
        )
        for item in proposals
    )
    assert state.state_hash() == before

    dynamics_records = [
        item
        for item in trace.records
        if item["record_type"] == "extremist_network_dynamics_proposal"
    ]
    assert len(dynamics_records) == 3
    assert all(item["driver_score"] == pytest.approx(1.0) for item in dynamics_records)
    assert all(item["damping_score"] == pytest.approx(0.0) for item in dynamics_records)


def test_strong_damping_produces_symmetric_decay() -> None:
    logger.info("test_strong_damping_produces_symmetric_decay")
    state, registry, parameters, config = _fixture()
    _set_low_drivers_high_damping(state)
    for variable in NETWORK_VARIABLES:
        state.latents[variable] = 0.50

    proposals = propose_extremist_network_dynamics(
        states={"TST": state},
        network_config=config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )

    assert len(proposals) == 3
    assert all(item.raw_delta == pytest.approx(-0.006) for item in proposals)

    result = resolve_delta_proposals(
        states={"TST": state},
        proposals=proposals,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    for variable in NETWORK_VARIABLES:
        assert result.states["TST"].latents[variable] == pytest.approx(0.494)


def test_network_dynamics_replay_is_exact() -> None:
    logger.info("test_network_dynamics_replay_is_exact")
    state_a, registry_a, parameters_a, config_a = _fixture()
    state_b, registry_b, parameters_b, config_b = _fixture()
    _set_high_drivers_low_damping(state_a)
    _set_high_drivers_low_damping(state_b)
    for variable in NETWORK_VARIABLES:
        state_a.latents[variable] = 0.33
        state_b.latents[variable] = 0.33

    trace_a = TraceLedger()
    trace_b = TraceLedger()
    a = propose_extremist_network_dynamics(
        states={"TST": state_a},
        network_config=config_a,
        engine_state_registry=registry_a,
        parameter_registry=parameters_a,
        profile="synthetic_smoke_v1",
        trace=trace_a,
    )
    b = propose_extremist_network_dynamics(
        states={"TST": state_b},
        network_config=config_b,
        engine_state_registry=registry_b,
        parameter_registry=parameters_b,
        profile="synthetic_smoke_v1",
        trace=trace_b,
    )

    assert [item.to_dict() for item in a] == [item.to_dict() for item in b]
    assert trace_a.records == trace_b.records


def test_forbidden_identity_input_fails_closed() -> None:
    logger.info("test_forbidden_identity_input_fails_closed")
    state, registry, parameters, config = _fixture()
    broken = copy.deepcopy(config)
    broken["forbidden_direct_inputs"] = []
    broken["driver_inputs"][0]["variable"] = "religious_fraction_muslim"

    with pytest.raises(ValueError, match="Forbidden direct extremist-network inputs"):
        propose_extremist_network_dynamics(
            states={"TST": state},
            network_config=broken,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_invalid_weight_sum_fails_closed() -> None:
    logger.info("test_invalid_weight_sum_fails_closed")
    state, registry, parameters, config = _fixture()
    broken = copy.deepcopy(parameters)
    broken["parameter_sets"]["synthetic_smoke_v1"]["parameters"][
        "EXTREMIST_NETWORK_DYNAMICS_SYN_V1"
    ]["value"]["driver_weights"]["polarization"] = 0.50

    with pytest.raises(ValueError, match="driver weights must sum to 1.0"):
        propose_extremist_network_dynamics(
            states={"TST": state},
            network_config=config,
            engine_state_registry=registry,
            parameter_registry=broken,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_calibrated_network_profile_fails_closed() -> None:
    logger.info("test_calibrated_network_profile_fails_closed")
    state, registry, parameters, config = _fixture()

    with pytest.raises(ValueError, match="Missing extremist-network parameter"):
        propose_extremist_network_dynamics(
            states={"TST": state},
            network_config=config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="calibrated_v1",
            trace=TraceLedger(),
        )
