from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .manifest import RunManifest
from .security_regime import (
    CANONICAL_REGIME_ORDER,
    SecurityRegimePersistenceState,
    SecurityRegimeTransitionProposal,
)
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecurityRegimeCommitRecord:
    commit_id: str
    proposal_id: str
    node_id: str
    day: int
    from_regime: str
    to_regime: str
    rule_id: str
    transition_rule_id: str
    parameter_id: str
    parameter_subkey: str
    state_hash_before: str
    state_hash_after: str
    apply_status: str = "COMMITTED"

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeCommitRecord.to_dict commit_id=%s node_id=%s",
            self.commit_id,
            self.node_id,
        )
        return {
            "commit_id": self.commit_id,
            "proposal_id": self.proposal_id,
            "node_id": self.node_id,
            "day": self.day,
            "from_regime": self.from_regime,
            "to_regime": self.to_regime,
            "rule_id": self.rule_id,
            "transition_rule_id": self.transition_rule_id,
            "parameter_id": self.parameter_id,
            "parameter_subkey": self.parameter_subkey,
            "state_hash_before": self.state_hash_before,
            "state_hash_after": self.state_hash_after,
            "apply_status": self.apply_status,
        }


def _validate_transition_config(config: dict[str, Any]) -> None:
    logger.info("_validate_transition_config")
    mode = config.get("mode", {})
    if mode.get("enabled") is not True:
        raise ValueError("Security regime commit is disabled")
    if int(mode.get("max_commits_per_node_per_day", 0)) != 1:
        raise ValueError(
            "v0.17 requires exactly one security-regime commit per node/day"
        )
    if mode.get("deescalation_enabled") is not False:
        raise ValueError("v0.17 de-escalation must remain disabled")
    if mode.get("commit_is_atomic_with_day_transaction") is not True:
        raise ValueError("Security regime commit must remain atomic with day transaction")
    if mode.get("reset_persistence_after_commit") is not True:
        raise ValueError("Security regime commit must reset persistence")

    commit = config.get("commit", {})
    if commit.get("rule_id") != "SECURITY_REGIME_COMMIT_V1":
        raise ValueError("Unsupported security regime commit rule")
    if commit.get("state_field") != "regimes.security_force_regime":
        raise ValueError("Security regime commit field must remain canonical")
    if commit.get("original_state_must_remain_unchanged") is not True:
        raise ValueError("Security regime commit must preserve original state")
    if commit.get("committed_state_must_validate") is not True:
        raise ValueError("Committed security regime state must validate")

    safety = config.get("safety", {})
    if safety.get("regime_is_classifier_not_operational_instruction") is not True:
        raise ValueError("Security regime must remain a classifier")
    if safety.get("political_identity_direct_transition_input") is not False:
        raise ValueError("Political identity cannot drive security regime commit")
    if safety.get("demographic_identity_direct_transition_input") is not False:
        raise ValueError("Demographic identity cannot drive security regime commit")
    if safety.get("religious_identity_direct_transition_input") is not False:
        raise ValueError("Religious identity cannot drive security regime commit")


def _validate_proposal_against_state(
    *,
    state: EngineState,
    proposal: SecurityRegimeTransitionProposal,
) -> None:
    logger.info(
        "_validate_proposal_against_state node_id=%s proposal_id=%s",
        state.node_id,
        proposal.proposal_id,
    )
    if proposal.apply_status != "PROPOSED_NOT_APPLIED":
        raise ValueError(
            f"Security regime proposal {proposal.proposal_id} is not commit-eligible"
        )
    if state.node_id != proposal.node_id or state.day != proposal.day:
        raise ValueError("Security regime proposal does not match state node/day")
    current_regime = str(state.regimes["security_force_regime"])
    if current_regime != proposal.from_regime:
        raise ValueError("Security regime proposal is stale against current state")
    if proposal.persistence_observed < proposal.persistence_required:
        raise ValueError("Security regime proposal has not satisfied persistence")
    if proposal.from_regime not in CANONICAL_REGIME_ORDER:
        raise ValueError(f"Unknown security regime {proposal.from_regime}")
    if proposal.to_regime not in CANONICAL_REGIME_ORDER:
        raise ValueError(f"Unknown security regime {proposal.to_regime}")

    from_rank = CANONICAL_REGIME_ORDER.index(proposal.from_regime)
    to_rank = CANONICAL_REGIME_ORDER.index(proposal.to_regime)
    if to_rank != from_rank + 1:
        raise ValueError(
            "v0.17 only permits the immediate next security regime"
        )


def commit_security_regime_transition(
    *,
    state: EngineState,
    proposal: SecurityRegimeTransitionProposal,
    transition_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    EngineState,
    SecurityRegimeCommitRecord,
    SecurityRegimePersistenceState,
]:
    """Commit one matured security-regime proposal to an immutable next state."""
    logger.info(
        "commit_security_regime_transition node_id=%s day=%s proposal_id=%s",
        state.node_id,
        state.day,
        proposal.proposal_id,
    )
    _validate_transition_config(transition_config)
    _validate_proposal_against_state(state=state, proposal=proposal)

    state_hash_before = state.state_hash()
    committed_state = EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes={
            **state.regimes,
            "security_force_regime": proposal.to_regime,
        },
        metadata=dict(state.metadata),
    )
    committed_state.validate(extract_latent_registry(engine_state_registry))
    if state.state_hash() != state_hash_before:
        raise RuntimeError("Security regime commit mutated original EngineState")

    commit_rule_id = str(transition_config["commit"]["rule_id"])
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "proposal_id": proposal.proposal_id,
            "node_id": state.node_id,
            "day": state.day,
            "from_regime": proposal.from_regime,
            "to_regime": proposal.to_regime,
            "commit_rule_id": commit_rule_id,
        }
    )
    record = SecurityRegimeCommitRecord(
        commit_id=f"securitycommit-{digest[:24]}",
        proposal_id=proposal.proposal_id,
        node_id=state.node_id,
        day=state.day,
        from_regime=proposal.from_regime,
        to_regime=proposal.to_regime,
        rule_id=commit_rule_id,
        transition_rule_id=proposal.rule_id,
        parameter_id=proposal.parameter_id,
        parameter_subkey=proposal.parameter_subkey,
        state_hash_before=state_hash_before,
        state_hash_after=committed_state.state_hash(),
    )
    persistence = SecurityRegimePersistenceState(
        node_id=state.node_id,
        current_regime=proposal.to_regime,
        last_evaluated_day=state.day,
        streaks=(),
    )
    trace.append(
        "security_regime_transition_committed",
        **record.to_dict(),
    )
    trace.append(
        "security_regime_persistence_committed",
        node_id=state.node_id,
        day=state.day,
        current_regime=proposal.to_regime,
        streaks={},
        source="committed_transition_reset",
        commit_id=record.commit_id,
    )
    return committed_state, record, persistence


def retain_security_regime_persistence(
    *,
    persistence: SecurityRegimePersistenceState,
    trace: TraceLedger,
) -> SecurityRegimePersistenceState:
    """Commit evaluator persistence when no security regime transition occurs."""
    logger.info(
        "retain_security_regime_persistence node_id=%s day=%s",
        persistence.node_id,
        persistence.last_evaluated_day,
    )
    trace.append(
        "security_regime_persistence_committed",
        node_id=persistence.node_id,
        day=persistence.last_evaluated_day,
        current_regime=persistence.current_regime,
        streaks=dict(persistence.streaks),
        source="evaluation_no_transition",
        commit_id=None,
    )
    return persistence
