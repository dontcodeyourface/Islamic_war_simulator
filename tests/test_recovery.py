from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.recovery import propose_recovery_effects
from iwsim.resolver import resolve_delta_proposals
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _state_fixture() -> tuple[EngineState, dict, dict, dict]:
    logger.info("_state_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    recovery_config = load_yaml(ROOT / "config/engine/recovery_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    latents["communal_fear"] = 0.60
    latents["public_order_stress"] = 0.50
    latents["electricity_functionality"] = 0.50
    latents["telecom_internet_functionality"] = 0.50

    baselines = dict(latents)
    baselines["communal_fear"] = 0.20
    baselines["public_order_stress"] = 0.10
    baselines["electricity_functionality"] = 1.00
    baselines["telecom_internet_functionality"] = 1.00

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
        metadata={"initial_latents": baselines},
    )
    state.validate(latent_registry)
    return state, registry, parameters, recovery_config


def test_recovery_proposals_are_bounded_traceable_and_non_mutating() -> None:
    logger.info("test_recovery_proposals_are_bounded_traceable_and_non_mutating")
    state, registry, parameters, recovery_config = _state_fixture()
    before = state.state_hash()
    trace = TraceLedger()

    proposals = propose_recovery_effects(
        states={"TST": state},
        recovery_config=recovery_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
    )

    assert len(proposals) == 4
    by_variable = {proposal.variable: proposal for proposal in proposals}
    assert by_variable["communal_fear"].raw_delta == pytest.approx(-0.010)
    assert by_variable["public_order_stress"].raw_delta == pytest.approx(-0.010)
    assert by_variable["electricity_functionality"].raw_delta == pytest.approx(0.004)
    assert by_variable["telecom_internet_functionality"].raw_delta == pytest.approx(0.004)
    assert all(
        proposal.event_type == "ENDOGENOUS_RECOVERY_V1"
        for proposal in proposals
    )
    assert all(
        proposal.apply_status == "PROPOSED_NOT_APPLIED"
        for proposal in proposals
    )
    assert all(
        proposal.parameter_ids == ("DYNAMIC_GAINS_SYN_V1",)
        for proposal in proposals
    )
    assert state.state_hash() == before

    recovery_records = [
        item for item in trace.records
        if item["record_type"] == "recovery_proposal"
    ]
    delta_records = [
        item for item in trace.records
        if item["record_type"] == "delta_proposal"
    ]
    assert len(recovery_records) == 4
    assert len(delta_records) == 4


def test_recovery_proposals_flow_through_owner_resolver() -> None:
    logger.info("test_recovery_proposals_flow_through_owner_resolver")
    state, registry, parameters, recovery_config = _state_fixture()
    proposals = propose_recovery_effects(
        states={"TST": state},
        recovery_config=recovery_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )

    result = resolve_delta_proposals(
        states={"TST": state},
        proposals=proposals,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )

    assert result.states["TST"].latents["communal_fear"] == pytest.approx(0.59)
    assert result.states["TST"].latents["public_order_stress"] == pytest.approx(0.49)
    assert result.states["TST"].latents["electricity_functionality"] == pytest.approx(
        0.504
    )
    assert result.states["TST"].latents[
        "telecom_internet_functionality"
    ] == pytest.approx(0.504)
    assert state.latents["communal_fear"] == pytest.approx(0.60)


def test_recovery_at_baseline_emits_no_proposal() -> None:
    logger.info("test_recovery_at_baseline_emits_no_proposal")
    state, registry, parameters, recovery_config = _state_fixture()
    for variable in (
        "communal_fear",
        "public_order_stress",
        "electricity_functionality",
        "telecom_internet_functionality",
    ):
        state.latents[variable] = state.metadata["initial_latents"][variable]

    proposals = propose_recovery_effects(
        states={"TST": state},
        recovery_config=recovery_config,
        engine_state_registry=registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    )
    assert proposals == ()


def test_missing_recovery_memory_fails_closed() -> None:
    logger.info("test_missing_recovery_memory_fails_closed")
    state, registry, parameters, recovery_config = _state_fixture()
    state.metadata.pop("initial_latents")

    with pytest.raises(ValueError, match="Recovery baseline memory missing"):
        propose_recovery_effects(
            states={"TST": state},
            recovery_config=recovery_config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_calibrated_recovery_profile_fails_closed() -> None:
    logger.info("test_calibrated_recovery_profile_fails_closed")
    state, registry, parameters, recovery_config = _state_fixture()

    with pytest.raises(ValueError, match="Missing recovery parameter"):
        propose_recovery_effects(
            states={"TST": state},
            recovery_config=recovery_config,
            engine_state_registry=registry,
            parameter_registry=parameters,
            profile="calibrated_v1",
            trace=TraceLedger(),
        )
