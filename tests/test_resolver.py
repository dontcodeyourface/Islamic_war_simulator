from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.effects import DeltaProposal
from iwsim.initializer import initialize_hybrid_state
from iwsim.resolver import resolve_delta_proposals
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _runtime():
    logger.info("_runtime")
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    snapshot = load_yaml(ROOT / "config/countries/spain.yaml")

    state = initialize_hybrid_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        parameter_registry=parameters,
        feature_map=feature_map,
        rng=RNGManager(1234),
        trace=TraceLedger(),
        profile="synthetic_smoke_v1",
    )
    return state_registry, parameters, state


def _proposal(
    *,
    proposal_id: str,
    variable: str,
    owner_module: str,
    value_before: float,
    raw_delta: float,
) -> DeltaProposal:
    logger.info(
        "_proposal proposal_id=%s variable=%s owner_module=%s",
        proposal_id,
        variable,
        owner_module,
    )
    return DeltaProposal(
        proposal_id=proposal_id,
        event_id="evt-test",
        event_type="TEST_EVENT_V1",
        target_node="ESP",
        variable=variable,
        owner_module=owner_module,
        value_before=value_before,
        raw_delta=raw_delta,
        proposed_unbounded_value=value_before + raw_delta,
        equation_id="EVENT_EFFECT_PROPOSAL_V1",
        parameter_ids=("EVENT_EFFECT_PROPOSALS_SYN_V1",),
        apply_status="PROPOSED_NOT_APPLIED",
        dry_run=True,
    )


def test_resolver_aggregates_same_variable_and_preserves_original_state() -> None:
    logger.info("test_resolver_aggregates_same_variable_and_preserves_original_state")
    state_registry, parameters, state = _runtime()
    state.latents["public_order_stress"] = 0.40
    original_hash = state.state_hash()

    proposals = (
        _proposal(
            proposal_id="p-a",
            variable="public_order_stress",
            owner_module="security",
            value_before=0.40,
            raw_delta=0.08,
        ),
        _proposal(
            proposal_id="p-b",
            variable="public_order_stress",
            owner_module="security",
            value_before=0.40,
            raw_delta=0.05,
        ),
    )
    trace = TraceLedger()
    result = resolve_delta_proposals(
        states={"ESP": state},
        proposals=proposals,
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
    )

    assert len(result.records) == 1
    record = result.records[0]
    assert record.raw_sum_delta == pytest.approx(0.13)
    assert record.value_before == pytest.approx(0.40)
    assert record.value_after == pytest.approx(0.53)
    assert record.bounded_delta == pytest.approx(0.13)
    assert record.clamp_amount == pytest.approx(0.0)
    assert record.proposal_ids == ("p-a", "p-b")
    assert result.states["ESP"].latents["public_order_stress"] == pytest.approx(0.53)
    assert result.states["ESP"].day == state.day

    assert state.latents["public_order_stress"] == pytest.approx(0.40)
    assert state.state_hash() == original_hash
    assert result.states["ESP"] is not state
    assert len(
        [item for item in trace.records if item["record_type"] == "owner_resolution"]
    ) == 1


def test_resolver_applies_upper_bound_and_exposes_clamp_amount() -> None:
    logger.info("test_resolver_applies_upper_bound_and_exposes_clamp_amount")
    state_registry, parameters, state = _runtime()
    state.latents["external_conflict_pressure"] = 0.97

    proposal = _proposal(
        proposal_id="p-clamp-high",
        variable="external_conflict_pressure",
        owner_module="external_system",
        value_before=0.97,
        raw_delta=0.06,
    )
    record = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(proposal,),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    ).records[0]

    assert record.proposed_unbounded_value == pytest.approx(1.03)
    assert record.value_after == pytest.approx(1.0)
    assert record.bounded_delta == pytest.approx(0.03)
    assert record.clamp_amount == pytest.approx(0.03)


def test_resolver_applies_lower_bound() -> None:
    logger.info("test_resolver_applies_lower_bound")
    state_registry, parameters, state = _runtime()
    state.latents["government_legitimacy"] = 0.01

    proposal = _proposal(
        proposal_id="p-clamp-low",
        variable="government_legitimacy",
        owner_module="institutions",
        value_before=0.01,
        raw_delta=-0.03,
    )
    record = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(proposal,),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
    ).records[0]

    assert record.proposed_unbounded_value == pytest.approx(-0.02)
    assert record.value_after == pytest.approx(0.0)
    assert record.bounded_delta == pytest.approx(-0.01)
    assert record.clamp_amount == pytest.approx(-0.02)


def test_resolver_rejects_stale_proposal() -> None:
    logger.info("test_resolver_rejects_stale_proposal")
    state_registry, parameters, state = _runtime()
    state.latents["public_order_stress"] = 0.40
    proposal = _proposal(
        proposal_id="p-stale",
        variable="public_order_stress",
        owner_module="security",
        value_before=0.39,
        raw_delta=0.02,
    )
    with pytest.raises(ValueError, match="Stale proposal"):
        resolve_delta_proposals(
            states={"ESP": state},
            proposals=(proposal,),
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_resolver_rejects_owner_mismatch() -> None:
    logger.info("test_resolver_rejects_owner_mismatch")
    state_registry, parameters, state = _runtime()
    value = state.latents["public_order_stress"]
    proposal = _proposal(
        proposal_id="p-owner",
        variable="public_order_stress",
        owner_module="institutions",
        value_before=value,
        raw_delta=0.02,
    )
    with pytest.raises(ValueError, match="Owner mismatch"):
        resolve_delta_proposals(
            states={"ESP": state},
            proposals=(proposal,),
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_resolver_rejects_duplicate_proposal_ids() -> None:
    logger.info("test_resolver_rejects_duplicate_proposal_ids")
    state_registry, parameters, state = _runtime()
    value = state.latents["public_order_stress"]
    a = _proposal(
        proposal_id="p-duplicate",
        variable="public_order_stress",
        owner_module="security",
        value_before=value,
        raw_delta=0.01,
    )
    b = _proposal(
        proposal_id="p-duplicate",
        variable="public_order_stress",
        owner_module="security",
        value_before=value,
        raw_delta=0.02,
    )
    with pytest.raises(ValueError, match="Duplicate proposal_id"):
        resolve_delta_proposals(
            states={"ESP": state},
            proposals=(a, b),
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
        )


def test_resolver_is_input_order_independent() -> None:
    logger.info("test_resolver_is_input_order_independent")
    state_registry, parameters, state = _runtime()
    state.latents["communal_fear"] = 0.20
    a = _proposal(
        proposal_id="p-a",
        variable="communal_fear",
        owner_module="demographics",
        value_before=0.20,
        raw_delta=0.01,
    )
    b = _proposal(
        proposal_id="p-b",
        variable="communal_fear",
        owner_module="demographics",
        value_before=0.20,
        raw_delta=0.02,
    )
    trace_a = TraceLedger()
    trace_b = TraceLedger()
    first = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(a, b),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace_a,
    )
    second = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(b, a),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace_b,
    )

    assert first.to_dict() == second.to_dict()
    assert trace_a.records == trace_b.records


def test_calibrated_resolver_fails_closed_while_unpopulated() -> None:
    logger.info("test_calibrated_resolver_fails_closed_while_unpopulated")
    state_registry, parameters, state = _runtime()
    proposal = _proposal(
        proposal_id="p-cal",
        variable="public_order_stress",
        owner_module="security",
        value_before=state.latents["public_order_stress"],
        raw_delta=0.01,
    )
    with pytest.raises(ValueError, match="Missing owner resolver parameter"):
        resolve_delta_proposals(
            states={"ESP": state},
            proposals=(proposal,),
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="calibrated_v1",
            trace=TraceLedger(),
        )


def test_resolver_records_explicit_multiscale_runtime_provenance() -> None:
    logger.info(
        "test_resolver_records_explicit_multiscale_runtime_provenance"
    )
    state_registry, parameters, state = _runtime()
    state.latents["public_order_stress"] = 0.40
    proposal = _proposal(
        proposal_id="p-runtime-context",
        variable="public_order_stress",
        owner_module="security",
        value_before=0.40,
        raw_delta=0.02,
    )
    context = {
        "ESP": {
            "runtime_level": "L2_REGION",
            "runtime_parent_node_id": "PARENT",
            "runtime_authority_scope": "REGIONALIZABLE",
            "runtime_plan_hash": "plan-test",
            "runtime_policy_id": "FRACTAL_RUNTIME_AUTHORITY_V1",
        }
    }
    trace = TraceLedger()
    record = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(proposal,),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=trace,
        runtime_context_by_node=context,
    ).records[0]

    assert record.runtime_level == "L2_REGION"
    assert record.runtime_parent_node_id == "PARENT"
    assert record.runtime_authority_scope == "REGIONALIZABLE"
    assert record.runtime_plan_hash == "plan-test"
    assert record.runtime_policy_id == "FRACTAL_RUNTIME_AUTHORITY_V1"
    owner_trace = next(
        item
        for item in trace.records
        if item["record_type"] == "owner_resolution"
    )
    assert owner_trace["runtime_level"] == "L2_REGION"
    assert owner_trace["runtime_plan_hash"] == "plan-test"


def test_multiscale_context_participates_in_resolution_identity() -> None:
    logger.info(
        "test_multiscale_context_participates_in_resolution_identity"
    )
    state_registry, parameters, state = _runtime()
    state.latents["public_order_stress"] = 0.40
    proposal = _proposal(
        proposal_id="p-scale-identity",
        variable="public_order_stress",
        owner_module="security",
        value_before=0.40,
        raw_delta=0.02,
    )
    l1 = {
        "ESP": {
            "runtime_level": "L1_COUNTRY",
            "runtime_parent_node_id": None,
            "runtime_authority_scope": "FULL",
            "runtime_plan_hash": "plan-l1",
            "runtime_policy_id": "FRACTAL_RUNTIME_AUTHORITY_V1",
        }
    }
    l2 = {
        "ESP": {
            "runtime_level": "L2_REGION",
            "runtime_parent_node_id": "PARENT",
            "runtime_authority_scope": "REGIONALIZABLE",
            "runtime_plan_hash": "plan-l2",
            "runtime_policy_id": "FRACTAL_RUNTIME_AUTHORITY_V1",
        }
    }

    record_l1 = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(proposal,),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
        runtime_context_by_node=l1,
    ).records[0]
    record_l2 = resolve_delta_proposals(
        states={"ESP": state},
        proposals=(proposal,),
        engine_state_registry=state_registry,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        trace=TraceLedger(),
        runtime_context_by_node=l2,
    ).records[0]

    assert record_l1.resolution_id != record_l2.resolution_id


def test_resolver_fails_closed_when_runtime_context_is_incomplete() -> None:
    logger.info(
        "test_resolver_fails_closed_when_runtime_context_is_incomplete"
    )
    state_registry, parameters, state = _runtime()
    proposal = _proposal(
        proposal_id="p-missing-context",
        variable="public_order_stress",
        owner_module="security",
        value_before=state.latents["public_order_stress"],
        raw_delta=0.01,
    )
    with pytest.raises(
        ValueError,
        match="Missing runtime resolver context",
    ):
        resolve_delta_proposals(
            states={"ESP": state},
            proposals=(proposal,),
            engine_state_registry=state_registry,
            parameter_registry=parameters,
            profile="synthetic_smoke_v1",
            trace=TraceLedger(),
            runtime_context_by_node={},
        )
