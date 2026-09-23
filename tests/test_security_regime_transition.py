from __future__ import annotations

import copy
import logging
from pathlib import Path

import pytest

from iwsim.config import canonical_hash, load_yaml
from iwsim.manifest import build_manifest
from iwsim.security_regime import (
    SecurityRegimePersistenceState,
    evaluate_security_regime,
)
from iwsim.security_regime_transition import (
    commit_security_regime_transition,
    retain_security_regime_persistence,
)
from iwsim.state import EngineState, extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> tuple[EngineState, dict, dict, dict, object]:
    logger.info("_fixture")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    evaluator_config = load_yaml(
        ROOT / "config/engine/security_regime_evaluator_v1.yaml"
    )
    transition_config = load_yaml(
        ROOT / "config/engine/security_regime_transition_v1.yaml"
    )
    latent_registry = extract_latent_registry(registry)
    latents = {
        variable: (low + high) / 2.0
        for variable, (low, high) in latent_registry.items()
    }
    state = EngineState(
        node_id="TST",
        day=1,
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
    state.latents["security_chain_cohesion"] = 0.70
    state.latents["operational_fatigue"] = 0.50
    manifest = build_manifest(
        run_id="security-regime-commit-test",
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.17.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"TST": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-SECURITY-REGIME-COMMIT-TEST",
        scenario_hash=canonical_hash({"scenario": "security-regime-commit-test"}),
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
        enabled_modules=("security_regime_evaluator", "security_regime_commit"),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )
    return (
        state,
        registry,
        parameters,
        evaluator_config,
        transition_config,
        manifest,
    )


def _matured_proposal(
    state: EngineState,
    parameters: dict,
    evaluator_config: dict,
    manifest: object,
):
    logger.info("_matured_proposal node_id=%s day=%s", state.node_id, state.day)
    result = evaluate_security_regime(
        state=state,
        persistence=None,
        context_flags={},
        regime_config=evaluator_config,
        parameter_registry=parameters,
        profile="synthetic_smoke_v1",
        manifest=manifest,
        trace=TraceLedger(),
    )
    assert len(result.proposals) == 1
    return result.proposals[0], result.persistence


def test_security_regime_commit_changes_only_regime_and_resets_persistence() -> None:
    logger.info(
        "test_security_regime_commit_changes_only_regime_and_resets_persistence"
    )
    (
        state,
        registry,
        parameters,
        evaluator_config,
        transition_config,
        manifest,
    ) = _fixture()
    proposal, evaluator_persistence = _matured_proposal(
        state,
        parameters,
        evaluator_config,
        manifest,
    )
    before = state.to_dict()
    trace = TraceLedger()

    committed, record, persistence = commit_security_regime_transition(
        state=state,
        proposal=proposal,
        transition_config=transition_config,
        engine_state_registry=registry,
        manifest=manifest,
        trace=trace,
    )

    assert state.to_dict() == before
    assert committed.node_id == state.node_id
    assert committed.day == state.day
    assert committed.physical_stocks == state.physical_stocks
    assert committed.latents == state.latents
    assert committed.metadata == state.metadata
    assert committed.regimes["security_force_regime"] == "STRAINED"
    assert state.regimes["security_force_regime"] == "COHESIVE"

    assert record.from_regime == "COHESIVE"
    assert record.to_regime == "STRAINED"
    assert record.proposal_id == proposal.proposal_id
    assert record.state_hash_before == state.state_hash()
    assert record.state_hash_after == committed.state_hash()

    assert evaluator_persistence.streaks
    assert persistence.current_regime == "STRAINED"
    assert persistence.last_evaluated_day == state.day
    assert persistence.streaks == ()

    record_types = [item["record_type"] for item in trace.records]
    assert record_types == [
        "security_regime_transition_committed",
        "security_regime_persistence_committed",
    ]


def test_security_regime_commit_rejects_non_adjacent_target() -> None:
    logger.info("test_security_regime_commit_rejects_non_adjacent_target")
    (
        state,
        registry,
        parameters,
        evaluator_config,
        transition_config,
        manifest,
    ) = _fixture()
    proposal, _ = _matured_proposal(
        state,
        parameters,
        evaluator_config,
        manifest,
    )
    tampered = proposal.__class__(
        proposal_id=proposal.proposal_id,
        node_id=proposal.node_id,
        day=proposal.day,
        from_regime=proposal.from_regime,
        to_regime="COMMAND_FRACTURE",
        rule_id=proposal.rule_id,
        parameter_id=proposal.parameter_id,
        parameter_subkey=proposal.parameter_subkey,
        condition_results=proposal.condition_results,
        persistence_required=proposal.persistence_required,
        persistence_observed=proposal.persistence_observed,
        apply_status=proposal.apply_status,
    )

    with pytest.raises(ValueError, match="immediate next security regime"):
        commit_security_regime_transition(
            state=state,
            proposal=tampered,
            transition_config=transition_config,
            engine_state_registry=registry,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_security_regime_commit_config_fails_closed() -> None:
    logger.info("test_security_regime_commit_config_fails_closed")
    (
        state,
        registry,
        parameters,
        evaluator_config,
        transition_config,
        manifest,
    ) = _fixture()
    proposal, _ = _matured_proposal(
        state,
        parameters,
        evaluator_config,
        manifest,
    )
    broken = copy.deepcopy(transition_config)
    broken["mode"]["deescalation_enabled"] = True

    with pytest.raises(ValueError, match="de-escalation must remain disabled"):
        commit_security_regime_transition(
            state=state,
            proposal=proposal,
            transition_config=broken,
            engine_state_registry=registry,
            manifest=manifest,
            trace=TraceLedger(),
        )


def test_retain_security_regime_persistence_is_identity_operation() -> None:
    logger.info("test_retain_security_regime_persistence_is_identity_operation")
    persistence = SecurityRegimePersistenceState(
        node_id="TST",
        current_regime="STRAINED",
        last_evaluated_day=7,
        streaks=(("SECURITY_STRAINED_SELECTIVE_NONCOMPLIANCE_V1", 4),),
    )
    trace = TraceLedger()

    retained = retain_security_regime_persistence(
        persistence=persistence,
        trace=trace,
    )

    assert retained == persistence
    assert trace.records == [
        {
            "record_type": "security_regime_persistence_committed",
            "node_id": "TST",
            "day": 7,
            "current_regime": "STRAINED",
            "streaks": {
                "SECURITY_STRAINED_SELECTIVE_NONCOMPLIANCE_V1": 4,
            },
            "source": "evaluation_no_transition",
            "commit_id": None,
        }
    ]
