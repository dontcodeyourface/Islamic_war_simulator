from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .phases import (
    PhaseEvaluationResult,
    PhasePersistenceState,
    PhaseTransitionProposal,
)
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PhaseTransitionCommit:
    commit_id: str
    node_id: str
    day: int
    from_phase: str
    to_phase: str
    selected_proposal_id: str
    competing_proposal_ids: tuple[str, ...]
    arbitration_policy: str
    rule_id: str
    parameter_id: str
    apply_status: str = "COMMITTED"

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseTransitionCommit.to_dict commit_id=%s",
            self.commit_id,
        )
        return {
            "commit_id": self.commit_id,
            "node_id": self.node_id,
            "day": self.day,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "selected_proposal_id": self.selected_proposal_id,
            "competing_proposal_ids": list(self.competing_proposal_ids),
            "arbitration_policy": self.arbitration_policy,
            "rule_id": self.rule_id,
            "parameter_id": self.parameter_id,
            "apply_status": self.apply_status,
        }


@dataclass(frozen=True)
class PhaseTransitionResolution:
    state: EngineState
    persistence: PhasePersistenceState
    commit: PhaseTransitionCommit | None

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseTransitionResolution.to_dict node_id=%s committed=%s",
            self.state.node_id,
            self.commit is not None,
        )
        return {
            "state": self.state.to_dict(),
            "persistence": self.persistence.to_dict(),
            "commit": self.commit.to_dict() if self.commit is not None else None,
        }


def _clone_state(state: EngineState) -> EngineState:
    logger.info("_clone_state node_id=%s day=%s", state.node_id, state.day)
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes=dict(state.regimes),
        metadata=dict(state.metadata),
    )


def _phase_index_map(phase_config: dict[str, Any]) -> dict[str, int]:
    logger.info("_phase_index_map")
    phases = [str(item) for item in phase_config["phase_order"]]
    if len(phases) != len(set(phases)):
        raise ValueError("Duplicate phase in phase_order")
    return {phase: index for index, phase in enumerate(phases)}


def _validate_proposals(
    *,
    state: EngineState,
    proposals: tuple[PhaseTransitionProposal, ...],
    phase_index: dict[str, int],
    resolver_config: dict[str, Any],
) -> None:
    logger.info(
        "_validate_proposals node_id=%s proposals=%s",
        state.node_id,
        len(proposals),
    )
    ids = [proposal.proposal_id for proposal in proposals]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate phase proposal_id detected")

    current_phase = str(state.regimes["national_phase"])
    if current_phase not in phase_index:
        raise ValueError(f"Unknown current phase {current_phase}")

    for proposal in proposals:
        if proposal.apply_status != "PROPOSED_NOT_APPLIED":
            raise ValueError(
                f"Phase proposal {proposal.proposal_id} is not eligible for commit"
            )
        if proposal.node_id != state.node_id:
            raise ValueError(
                f"Phase proposal node mismatch {proposal.node_id} != {state.node_id}"
            )
        if proposal.day != state.day:
            raise ValueError(
                f"Phase proposal day mismatch {proposal.day} != {state.day}"
            )
        if proposal.from_phase != current_phase:
            raise ValueError(
                f"Phase proposal from mismatch {proposal.from_phase} != "
                f"{current_phase}"
            )
        if proposal.to_phase not in phase_index:
            raise ValueError(f"Unknown target phase {proposal.to_phase}")
        if bool(
            resolver_config["arbitration"]["require_target_above_current_phase"]
        ):
            if phase_index[proposal.to_phase] <= phase_index[current_phase]:
                raise ValueError(
                    f"Non-escalating proposal forbidden in v0.9: "
                    f"{current_phase}->{proposal.to_phase}"
                )


def _select_proposal(
    *,
    proposals: tuple[PhaseTransitionProposal, ...],
    phase_index: dict[str, int],
    resolver_config: dict[str, Any],
) -> PhaseTransitionProposal:
    logger.info("_select_proposal proposals=%s", len(proposals))
    policy = str(resolver_config["arbitration"]["policy"])
    if policy != "highest_target_severity":
        raise ValueError(f"Unsupported phase arbitration policy {policy}")

    ordered = sorted(
        proposals,
        key=lambda proposal: (
            -phase_index[proposal.to_phase],
            proposal.proposal_id,
        ),
    )
    return ordered[0]


def _commit_id(
    *,
    state: EngineState,
    selected: PhaseTransitionProposal,
    proposals: tuple[PhaseTransitionProposal, ...],
    arbitration_policy: str,
) -> str:
    logger.info(
        "_commit_id node_id=%s day=%s selected=%s",
        state.node_id,
        state.day,
        selected.proposal_id,
    )
    digest = canonical_hash(
        {
            "node_id": state.node_id,
            "day": state.day,
            "from_phase": state.regimes["national_phase"],
            "to_phase": selected.to_phase,
            "selected_proposal_id": selected.proposal_id,
            "competing_proposal_ids": sorted(
                proposal.proposal_id for proposal in proposals
            ),
            "arbitration_policy": arbitration_policy,
        }
    )
    return f"phasecommit-{digest[:24]}"


def resolve_phase_transition(
    *,
    state: EngineState,
    evaluation: PhaseEvaluationResult,
    phase_config: dict[str, Any],
    resolver_config: dict[str, Any],
    trace: TraceLedger,
) -> PhaseTransitionResolution:
    """Commit at most one matured phase proposal into a new state object."""
    logger.info(
        "resolve_phase_transition node_id=%s day=%s proposals=%s",
        state.node_id,
        state.day,
        len(evaluation.proposals),
    )
    if evaluation.persistence.node_id != state.node_id:
        raise ValueError("Phase evaluation persistence node mismatch")
    if evaluation.persistence.last_evaluated_day != state.day:
        raise ValueError("Phase evaluation persistence day mismatch")
    if evaluation.persistence.current_phase != state.regimes["national_phase"]:
        raise ValueError(
            "Phase evaluation persistence phase does not match EngineState"
        )

    proposals = tuple(evaluation.proposals)
    if not proposals:
        return PhaseTransitionResolution(
            state=state,
            persistence=evaluation.persistence,
            commit=None,
        )

    phase_index = _phase_index_map(phase_config)
    _validate_proposals(
        state=state,
        proposals=proposals,
        phase_index=phase_index,
        resolver_config=resolver_config,
    )
    selected = _select_proposal(
        proposals=proposals,
        phase_index=phase_index,
        resolver_config=resolver_config,
    )
    policy = str(resolver_config["arbitration"]["policy"])

    next_state = _clone_state(state)
    from_phase = str(state.regimes["national_phase"])
    next_state.regimes["national_phase"] = selected.to_phase

    updated_persistence = PhasePersistenceState(
        node_id=state.node_id,
        current_phase=selected.to_phase,
        last_evaluated_day=state.day,
        streaks=(),
    )
    commit = PhaseTransitionCommit(
        commit_id=_commit_id(
            state=state,
            selected=selected,
            proposals=proposals,
            arbitration_policy=policy,
        ),
        node_id=state.node_id,
        day=state.day,
        from_phase=from_phase,
        to_phase=selected.to_phase,
        selected_proposal_id=selected.proposal_id,
        competing_proposal_ids=tuple(
            sorted(proposal.proposal_id for proposal in proposals)
        ),
        arbitration_policy=policy,
        rule_id=selected.rule_id,
        parameter_id=selected.parameter_id,
    )
    trace.append(
        "phase_transition_committed",
        **commit.to_dict(),
    )
    return PhaseTransitionResolution(
        state=next_state,
        persistence=updated_persistence,
        commit=commit,
    )
