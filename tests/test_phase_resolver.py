from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.initializer import initialize_hybrid_state
from iwsim.phase_resolver import resolve_phase_transition
from iwsim.phases import (
    PhaseEvaluationResult,
    PhasePersistenceState,
    PhaseTransitionProposal,
)
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
    phase_config = load_yaml(ROOT / "config/engine/phase_evaluator_v1.yaml")
    resolver_config = load_yaml(
        ROOT / "config/engine/phase_transition_resolver_v1.yaml"
    )
    snapshot = load_yaml(ROOT / "config/countries/spain.yaml")
    state = initialize_hybrid_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        parameter_registry=parameters,
        feature_map=feature_map,
        rng=RNGManager(900),
        trace=TraceLedger(),
        profile="synthetic_smoke_v1",
    )
    state.day = 21
    state.regimes["national_phase"] = "INSURGENCY"
    return state, phase_config, resolver_config


def _proposal(
    *,
    proposal_id: str,
    to_phase: str,
    day: int = 21,
    node_id: str = "ESP",
    from_phase: str = "INSURGENCY",
    apply_status: str = "PROPOSED_NOT_APPLIED",
) -> PhaseTransitionProposal:
    logger.info(
        "_proposal proposal_id=%s from=%s to=%s",
        proposal_id,
        from_phase,
        to_phase,
    )
    return PhaseTransitionProposal(
        proposal_id=proposal_id,
        node_id=node_id,
        day=day,
        from_phase=from_phase,
        to_phase=to_phase,
        rule_id=f"RULE_{to_phase}",
        parameter_id=f"PARAM_{to_phase}",
        condition_mode="all",
        condition_results=(),
        persistence_required=1,
        persistence_observed=1,
        apply_status=apply_status,
    )


def _evaluation(
    proposals: tuple[PhaseTransitionProposal, ...],
    *,
    day: int = 21,
    phase: str = "INSURGENCY",
) -> PhaseEvaluationResult:
    logger.info("_evaluation proposals=%s day=%s", len(proposals), day)
    return PhaseEvaluationResult(
        persistence=PhasePersistenceState(
            node_id="ESP",
            current_phase=phase,
            last_evaluated_day=day,
            streaks=(("test", 1),),
        ),
        evaluations=(),
        proposals=proposals,
    )


def test_resolver_selects_highest_target_severity() -> None:
    logger.info("test_resolver_selects_highest_target_severity")
    state, phase_config, resolver_config = _runtime()
    before_hash = state.state_hash()
    evaluation = _evaluation(
        (
            _proposal(proposal_id="p-dual", to_phase="DUAL_AUTHORITY"),
            _proposal(proposal_id="p-civil", to_phase="CIVIL_WAR"),
        )
    )
    trace = TraceLedger()

    result = resolve_phase_transition(
        state=state,
        evaluation=evaluation,
        phase_config=phase_config,
        resolver_config=resolver_config,
        trace=trace,
    )

    assert state.state_hash() == before_hash
    assert state.regimes["national_phase"] == "INSURGENCY"
    assert result.state.regimes["national_phase"] == "CIVIL_WAR"
    assert result.commit is not None
    assert result.commit.selected_proposal_id == "p-civil"
    assert result.commit.competing_proposal_ids == ("p-civil", "p-dual")
    assert result.persistence.current_phase == "CIVIL_WAR"
    assert result.persistence.streaks == ()
    assert [
        record["record_type"] for record in trace.records
    ] == ["phase_transition_committed"]


def test_no_proposal_preserves_state_and_persistence() -> None:
    logger.info("test_no_proposal_preserves_state_and_persistence")
    state, phase_config, resolver_config = _runtime()
    evaluation = _evaluation(())
    result = resolve_phase_transition(
        state=state,
        evaluation=evaluation,
        phase_config=phase_config,
        resolver_config=resolver_config,
        trace=TraceLedger(),
    )
    assert result.state is state
    assert result.commit is None
    assert result.persistence == evaluation.persistence


@pytest.mark.parametrize(
    ("proposal", "message"),
    [
        (_proposal(proposal_id="p-node", to_phase="CIVIL_WAR", node_id="FRA"), "node mismatch"),
        (_proposal(proposal_id="p-day", to_phase="CIVIL_WAR", day=20), "day mismatch"),
        (_proposal(proposal_id="p-from", to_phase="CIVIL_WAR", from_phase="DUAL_AUTHORITY"), "from mismatch"),
        (_proposal(proposal_id="p-status", to_phase="CIVIL_WAR", apply_status="COMMITTED"), "not eligible"),
        (_proposal(proposal_id="p-down", to_phase="MASS_UNREST"), "Non-escalating"),
    ],
)
def test_resolver_rejects_invalid_proposals(
    proposal: PhaseTransitionProposal,
    message: str,
) -> None:
    logger.info(
        "test_resolver_rejects_invalid_proposals proposal_id=%s",
        proposal.proposal_id,
    )
    state, phase_config, resolver_config = _runtime()
    with pytest.raises(ValueError, match=message):
        resolve_phase_transition(
            state=state,
            evaluation=_evaluation((proposal,)),
            phase_config=phase_config,
            resolver_config=resolver_config,
            trace=TraceLedger(),
        )


def test_resolver_rejects_duplicate_proposal_ids() -> None:
    logger.info("test_resolver_rejects_duplicate_proposal_ids")
    state, phase_config, resolver_config = _runtime()
    a = _proposal(proposal_id="same", to_phase="DUAL_AUTHORITY")
    b = _proposal(proposal_id="same", to_phase="CIVIL_WAR")
    with pytest.raises(ValueError, match="Duplicate phase proposal_id"):
        resolve_phase_transition(
            state=state,
            evaluation=_evaluation((a, b)),
            phase_config=phase_config,
            resolver_config=resolver_config,
            trace=TraceLedger(),
        )


def test_same_target_tie_breaks_by_proposal_id() -> None:
    logger.info("test_same_target_tie_breaks_by_proposal_id")
    state, phase_config, resolver_config = _runtime()
    a = _proposal(proposal_id="p-z", to_phase="CIVIL_WAR")
    b = _proposal(proposal_id="p-a", to_phase="CIVIL_WAR")
    result = resolve_phase_transition(
        state=state,
        evaluation=_evaluation((a, b)),
        phase_config=phase_config,
        resolver_config=resolver_config,
        trace=TraceLedger(),
    )
    assert result.commit is not None
    assert result.commit.selected_proposal_id == "p-a"


def test_unknown_arbitration_policy_fails_closed() -> None:
    logger.info("test_unknown_arbitration_policy_fails_closed")
    state, phase_config, resolver_config = _runtime()
    resolver_config = {
        **resolver_config,
        "arbitration": {
            **resolver_config["arbitration"],
            "policy": "unsupported",
        },
    }
    with pytest.raises(ValueError, match="Unsupported phase arbitration policy"):
        resolve_phase_transition(
            state=state,
            evaluation=_evaluation(
                (_proposal(proposal_id="p", to_phase="CIVIL_WAR"),)
            ),
            phase_config=phase_config,
            resolver_config=resolver_config,
            trace=TraceLedger(),
        )
