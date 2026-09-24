from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.manifest import build_manifest
from iwsim.security_regime import SecurityRegimePersistenceState
from iwsim.security_regime_recovery import (
    SecurityRegimeRecoveryPersistenceState,
    SecurityRegimeRecoveryProposal,
)
from iwsim.security_regime_recovery_transition import (
    commit_security_regime_recovery,
    retain_security_regime_recovery_persistence,
)
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> tuple[EngineState, dict, dict, object]:
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    transition_config = load_yaml(
        ROOT / "config/engine/security_regime_recovery_transition_v1.yaml"
    )
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=13,
        physical_stocks={},
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "STRAINED",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={},
    )
    manifest = build_manifest(
        run_id="security-recovery-commit-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.21.1",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-SECURITY-RECOVERY-COMMIT",
        scenario_hash=canonical_hash({"scenario": "security-recovery"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=1,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=30,
        enabled_modules=("security_regime_recovery_commit",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )
    return state, registry, transition_config, manifest


def _proposal(state: EngineState) -> SecurityRegimeRecoveryProposal:
    logger.info("_proposal node=%s day=%s", state.node_id, state.day)
    return SecurityRegimeRecoveryProposal(
        proposal_id="security-recovery-test",
        node_id=state.node_id,
        day=state.day,
        from_regime="STRAINED",
        to_regime="COHESIVE",
        rule_id="SECURITY_RECOVERY_STRAINED_COHESIVE_V1",
        parameter_id="SECURITY_REGIME_RECOVERY_SYN_V1",
        parameter_subkey="strained_to_cohesive",
        condition_results=(),
        persistence_required=13,
        persistence_observed=13,
    )


def test_recovery_commit_changes_only_regime_and_resets_both_memories() -> None:
    logger.info(
        "test_recovery_commit_changes_only_regime_and_resets_both_memories"
    )
    state, registry, transition_config, manifest = _fixture()
    before = state.to_dict()
    trace = TraceLedger()

    (
        committed,
        record,
        escalation_persistence,
        recovery_persistence,
    ) = commit_security_regime_recovery(
        state=state,
        proposal=_proposal(state),
        transition_config=transition_config,
        engine_state_registry=registry,
        manifest=manifest,
        trace=trace,
    )

    assert state.to_dict() == before
    assert committed.latents == state.latents
    assert committed.physical_stocks == state.physical_stocks
    assert committed.metadata == state.metadata
    assert committed.regimes["security_force_regime"] == "COHESIVE"
    assert state.regimes["security_force_regime"] == "STRAINED"

    assert record.from_regime == "STRAINED"
    assert record.to_regime == "COHESIVE"
    assert record.state_hash_before == state.state_hash()
    assert record.state_hash_after == committed.state_hash()

    assert escalation_persistence == SecurityRegimePersistenceState(
        node_id="TST",
        current_regime="COHESIVE",
        last_evaluated_day=13,
        streaks=(),
    )
    assert recovery_persistence == SecurityRegimeRecoveryPersistenceState(
        node_id="TST",
        current_regime="COHESIVE",
        last_evaluated_day=13,
        streaks=(),
    )

    assert [item["record_type"] for item in trace.records] == [
        "security_regime_recovery_committed",
        "security_regime_persistence_committed",
        "security_regime_recovery_persistence_committed",
    ]


def test_recovery_commit_rejects_non_adjacent_downward_jump() -> None:
    logger.info("test_recovery_commit_rejects_non_adjacent_downward_jump")
    state, registry, transition_config, manifest = _fixture()
    proposal = _proposal(state)
    tampered = proposal.__class__(
        proposal_id=proposal.proposal_id,
        node_id=proposal.node_id,
        day=proposal.day,
        from_regime=proposal.from_regime,
        to_regime="SELECTIVE_NONCOMPLIANCE",
        rule_id=proposal.rule_id,
        parameter_id=proposal.parameter_id,
        parameter_subkey=proposal.parameter_subkey,
        condition_results=proposal.condition_results,
        persistence_required=proposal.persistence_required,
        persistence_observed=proposal.persistence_observed,
        apply_status=proposal.apply_status,
    )

    with pytest.raises(ValueError, match="immediate previous security regime"):
        commit_security_regime_recovery(
            state=state,
            proposal=tampered,
            transition_config=transition_config,
            engine_state_registry=registry,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_recovery_commit_config_fails_closed() -> None:
    logger.info("test_recovery_commit_config_fails_closed")
    state, registry, transition_config, manifest = _fixture()
    broken = copy.deepcopy(transition_config)
    broken["mode"]["max_commits_per_node_per_day"] = 2

    with pytest.raises(
        ValueError,
        match="exactly one security-regime recovery commit",
    ):
        commit_security_regime_recovery(
            state=state,
            proposal=_proposal(state),
            transition_config=broken,
            engine_state_registry=registry,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_retain_recovery_persistence_is_identity_operation() -> None:
    logger.info("test_retain_recovery_persistence_is_identity_operation")
    persistence = SecurityRegimeRecoveryPersistenceState(
        node_id="TST",
        current_regime="STRAINED",
        last_evaluated_day=8,
        streaks=(("SECURITY_RECOVERY_STRAINED_COHESIVE_V1", 6),),
    )
    trace = TraceLedger()

    retained = retain_security_regime_recovery_persistence(
        persistence=persistence,
        trace=trace,
    )

    assert retained == persistence
    assert trace.records == [
        {
            "record_type": "security_regime_recovery_persistence_committed",
            "node_id": "TST",
            "day": 8,
            "current_regime": "STRAINED",
            "streaks": {
                "SECURITY_RECOVERY_STRAINED_COHESIVE_V1": 6,
            },
            "source": "evaluation_no_recovery_transition",
            "commit_id": None,
        }
    ]
