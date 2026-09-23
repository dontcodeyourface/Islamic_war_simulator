from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .manifest import RunManifest
from .phases import PhasePersistenceState, PhaseTransitionProposal
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PhaseArbitrationRecord:
    arbitration_id: str
    node_id: str
    day: int
    from_phase: str
    proposal_ids: tuple[str, ...]
    selected_proposal_id: str
    rejected_proposal_ids: tuple[str, ...]
    rule_id: str
    policy: str
    target_phase_ranks: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseArbitrationRecord.to_dict arbitration_id=%s node_id=%s",
            self.arbitration_id,
            self.node_id,
        )
        return {
            "arbitration_id": self.arbitration_id,
            "node_id": self.node_id,
            "day": self.day,
            "from_phase": self.from_phase,
            "proposal_ids": list(self.proposal_ids),
            "selected_proposal_id": self.selected_proposal_id,
            "rejected_proposal_ids": list(self.rejected_proposal_ids),
            "rule_id": self.rule_id,
            "policy": self.policy,
            "target_phase_ranks": dict(self.target_phase_ranks),
        }


@dataclass(frozen=True)
class PhaseCommitRecord:
    commit_id: str
    arbitration_id: str
    proposal_id: str
    node_id: str
    day: int
    from_phase: str
    to_phase: str
    rule_id: str
    transition_rule_id: str
    parameter_id: str
    state_hash_before: str
    state_hash_after: str
    apply_status: str = "COMMITTED"

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseCommitRecord.to_dict commit_id=%s node_id=%s",
            self.commit_id,
            self.node_id,
        )
        return {
            "commit_id": self.commit_id,
            "arbitration_id": self.arbitration_id,
            "proposal_id": self.proposal_id,
            "node_id": self.node_id,
            "day": self.day,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "rule_id": self.rule_id,
            "transition_rule_id": self.transition_rule_id,
            "parameter_id": self.parameter_id,
            "state_hash_before": self.state_hash_before,
            "state_hash_after": self.state_hash_after,
            "apply_status": self.apply_status,
        }


def _phase_ranks(phase_config: dict[str, Any]) -> dict[str, int]:
    logger.info("_phase_ranks")
    order = tuple(str(item) for item in phase_config["phase_order"])
    if len(order) != len(set(order)):
        raise ValueError("phase_order contains duplicates")
    return {phase: index for index, phase in enumerate(order)}


def _validate_transition_config(transition_config: dict[str, Any]) -> None:
    logger.info("_validate_transition_config")
    mode = transition_config.get("mode", {})
    if not bool(mode.get("enabled", False)):
        raise ValueError("Phase transition commit is disabled")
    if int(mode.get("max_commits_per_node_per_day", 0)) != 1:
        raise ValueError("v0.9 requires exactly one phase commit per node/day")
    if bool(mode.get("deescalation_enabled", True)):
        raise ValueError("v0.9 de-escalation must remain disabled")
    arbitration = transition_config.get("arbitration", {})
    if arbitration.get("policy") != "highest_target_phase_order":
        raise ValueError("Unsupported phase arbitration policy")
    if arbitration.get("tie_breaker") != "proposal_id_ascending":
        raise ValueError("Unsupported phase arbitration tie breaker")


def arbitrate_phase_proposals(
    *,
    proposals: tuple[PhaseTransitionProposal, ...],
    phase_config: dict[str, Any],
    transition_config: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> PhaseArbitrationRecord | None:
    """Choose at most one matured outgoing phase proposal deterministically."""
    logger.info("arbitrate_phase_proposals proposals=%s", len(proposals))
    _validate_transition_config(transition_config)
    if not proposals:
        return None

    node_ids = {proposal.node_id for proposal in proposals}
    days = {proposal.day for proposal in proposals}
    from_phases = {proposal.from_phase for proposal in proposals}
    if len(node_ids) != 1 or len(days) != 1 or len(from_phases) != 1:
        raise ValueError("Phase arbitration requires one node/day/from_phase group")

    node_id = next(iter(node_ids))
    day = next(iter(days))
    from_phase = next(iter(from_phases))
    ranks = _phase_ranks(phase_config)
    if from_phase not in ranks:
        raise ValueError(f"Unknown current phase {from_phase}")

    ranked: list[tuple[int, str, PhaseTransitionProposal]] = []
    for proposal in proposals:
        if proposal.to_phase not in ranks:
            raise ValueError(f"Unknown target phase {proposal.to_phase}")
        if ranks[proposal.to_phase] <= ranks[from_phase]:
            raise ValueError(
                f"v0.9 only permits escalation: {from_phase}->{proposal.to_phase}"
            )
        ranked.append((ranks[proposal.to_phase], proposal.proposal_id, proposal))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = ranked[0][2]
    proposal_ids = tuple(sorted(proposal.proposal_id for proposal in proposals))
    rejected = tuple(
        proposal_id for proposal_id in proposal_ids
        if proposal_id != selected.proposal_id
    )
    rule_id = str(transition_config["arbitration"]["rule_id"])
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "node_id": node_id,
            "day": day,
            "from_phase": from_phase,
            "proposal_ids": proposal_ids,
            "selected_proposal_id": selected.proposal_id,
            "rule_id": rule_id,
        }
    )
    record = PhaseArbitrationRecord(
        arbitration_id=f"phasearb-{digest[:24]}",
        node_id=node_id,
        day=day,
        from_phase=from_phase,
        proposal_ids=proposal_ids,
        selected_proposal_id=selected.proposal_id,
        rejected_proposal_ids=rejected,
        rule_id=rule_id,
        policy=str(transition_config["arbitration"]["policy"]),
        target_phase_ranks=tuple(
            sorted((proposal.to_phase, ranks[proposal.to_phase]) for proposal in proposals)
        ),
    )
    trace.append("phase_arbitration", **record.to_dict())
    return record


def commit_phase_transition(
    *,
    state: EngineState,
    proposals: tuple[PhaseTransitionProposal, ...],
    arbitration: PhaseArbitrationRecord,
    transition_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[EngineState, PhaseCommitRecord, PhasePersistenceState]:
    """Commit the selected phase to a new EngineState and reset persistence."""
    logger.info(
        "commit_phase_transition node_id=%s day=%s selected=%s",
        state.node_id,
        state.day,
        arbitration.selected_proposal_id,
    )
    _validate_transition_config(transition_config)
    matches = [
        proposal for proposal in proposals
        if proposal.proposal_id == arbitration.selected_proposal_id
    ]
    if len(matches) != 1:
        raise ValueError("Selected phase proposal is missing or duplicated")
    proposal = matches[0]
    if state.node_id != proposal.node_id or state.day != proposal.day:
        raise ValueError("Phase proposal does not match state node/day")
    if state.regimes["national_phase"] != proposal.from_phase:
        raise ValueError("Phase proposal is stale against current state")

    state_hash_before = state.state_hash()
    committed_state = EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes={**state.regimes, "national_phase": proposal.to_phase},
        metadata=dict(state.metadata),
    )
    committed_state.validate(extract_latent_registry(engine_state_registry))
    if state.state_hash() != state_hash_before:
        raise RuntimeError("Phase commit mutated original EngineState")

    commit_rule_id = str(transition_config["commit"]["rule_id"])
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "arbitration_id": arbitration.arbitration_id,
            "proposal_id": proposal.proposal_id,
            "node_id": state.node_id,
            "day": state.day,
            "from_phase": proposal.from_phase,
            "to_phase": proposal.to_phase,
            "rule_id": commit_rule_id,
        }
    )
    record = PhaseCommitRecord(
        commit_id=f"phasecommit-{digest[:24]}",
        arbitration_id=arbitration.arbitration_id,
        proposal_id=proposal.proposal_id,
        node_id=state.node_id,
        day=state.day,
        from_phase=proposal.from_phase,
        to_phase=proposal.to_phase,
        rule_id=commit_rule_id,
        transition_rule_id=proposal.rule_id,
        parameter_id=proposal.parameter_id,
        state_hash_before=state_hash_before,
        state_hash_after=committed_state.state_hash(),
    )
    persistence = PhasePersistenceState(
        node_id=state.node_id,
        current_phase=proposal.to_phase,
        last_evaluated_day=state.day,
        streaks=(),
    )
    trace.append("phase_transition_committed", **record.to_dict())
    trace.append(
        "phase_persistence_committed",
        node_id=state.node_id,
        day=state.day,
        current_phase=proposal.to_phase,
        streaks={},
        source="committed_transition_reset",
        commit_id=record.commit_id,
    )
    return committed_state, record, persistence


def retain_phase_persistence(
    *,
    persistence: PhasePersistenceState,
    trace: TraceLedger,
) -> PhasePersistenceState:
    """Persist evaluator history when no phase transition is committed."""
    logger.info(
        "retain_phase_persistence node_id=%s day=%s",
        persistence.node_id,
        persistence.last_evaluated_day,
    )
    trace.append(
        "phase_persistence_committed",
        node_id=persistence.node_id,
        day=persistence.last_evaluated_day,
        current_phase=persistence.current_phase,
        streaks=dict(persistence.streaks),
        source="evaluation_no_transition",
        commit_id=None,
    )
    return persistence
