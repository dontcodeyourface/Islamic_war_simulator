from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_child_state import FractalChildStateStore
from .manifest import RunManifest
from .phase_transition import (
    PhaseArbitrationRecord,
    PhaseCommitRecord,
    arbitrate_phase_proposals,
    commit_phase_transition,
    retain_phase_persistence,
)
from .phases import (
    PhaseEvaluationResult,
    PhasePersistenceState,
    evaluate_national_phase,
)
from .security_regime import (
    SecurityRegimeEvaluationResult,
    SecurityRegimePersistenceState,
    evaluate_security_regime,
)
from .security_regime_recovery import (
    SecurityRegimeRecoveryEvaluationResult,
    SecurityRegimeRecoveryPersistenceState,
    evaluate_security_regime_recovery,
)
from .security_regime_recovery_transition import (
    SecurityRegimeRecoveryCommitRecord,
    commit_security_regime_recovery,
    retain_security_regime_recovery_persistence,
)
from .security_regime_transition import (
    SecurityRegimeCommitRecord,
    commit_security_regime_transition,
    retain_security_regime_persistence,
)
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalRegionalRegimeStore:
    last_committed_day: int
    phase_persistence: tuple[PhasePersistenceState, ...]
    security_persistence: tuple[SecurityRegimePersistenceState, ...]
    security_recovery_persistence: tuple[
        SecurityRegimeRecoveryPersistenceState, ...
    ]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRegionalRegimeStore.to_dict day=%s nodes=%s",
            self.last_committed_day,
            len(self.phase_persistence),
        )
        return {
            "last_committed_day": self.last_committed_day,
            "phase_persistence": [
                item.to_dict()
                for item in sorted(
                    self.phase_persistence,
                    key=lambda value: value.node_id,
                )
            ],
            "security_persistence": [
                item.to_dict()
                for item in sorted(
                    self.security_persistence,
                    key=lambda value: value.node_id,
                )
            ],
            "security_recovery_persistence": [
                item.to_dict()
                for item in sorted(
                    self.security_recovery_persistence,
                    key=lambda value: value.node_id,
                )
            ],
        }

    def store_hash(self) -> str:
        logger.info(
            "FractalRegionalRegimeStore.store_hash day=%s",
            self.last_committed_day,
        )
        return canonical_hash(self.to_dict())

    def phase_map(self) -> dict[str, PhasePersistenceState]:
        logger.info(
            "FractalRegionalRegimeStore.phase_map nodes=%s",
            len(self.phase_persistence),
        )
        return {
            item.node_id: item
            for item in self.phase_persistence
        }

    def security_map(self) -> dict[str, SecurityRegimePersistenceState]:
        logger.info(
            "FractalRegionalRegimeStore.security_map nodes=%s",
            len(self.security_persistence),
        )
        return {
            item.node_id: item
            for item in self.security_persistence
        }

    def recovery_map(
        self,
    ) -> dict[str, SecurityRegimeRecoveryPersistenceState]:
        logger.info(
            "FractalRegionalRegimeStore.recovery_map nodes=%s",
            len(self.security_recovery_persistence),
        )
        return {
            item.node_id: item
            for item in self.security_recovery_persistence
        }


@dataclass(frozen=True)
class FractalCategoricalDivergenceAudit:
    audit_id: str
    parent_node_id: str
    day: int
    child_node_ids: tuple[str, ...]
    national_phases: tuple[tuple[str, str], ...]
    security_force_regimes: tuple[tuple[str, str], ...]
    prison_regimes: tuple[tuple[str, str], ...]
    organized_crime_regimes: tuple[tuple[str, str], ...]
    phase_divergent: bool
    security_regime_divergent: bool
    static_regimes_consistent: bool
    collapse_consensus_ready: bool
    aggregation_policy_id: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalCategoricalDivergenceAudit.to_dict parent=%s day=%s",
            self.parent_node_id,
            self.day,
        )
        return {
            "audit_id": self.audit_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "child_node_ids": list(self.child_node_ids),
            "national_phases": dict(self.national_phases),
            "security_force_regimes": dict(
                self.security_force_regimes
            ),
            "prison_regimes": dict(self.prison_regimes),
            "organized_crime_regimes": dict(
                self.organized_crime_regimes
            ),
            "phase_divergent": self.phase_divergent,
            "security_regime_divergent": (
                self.security_regime_divergent
            ),
            "static_regimes_consistent": (
                self.static_regimes_consistent
            ),
            "collapse_consensus_ready": (
                self.collapse_consensus_ready
            ),
            "aggregation_policy_id": self.aggregation_policy_id,
        }


@dataclass(frozen=True)
class FractalRegionalRegimeResult:
    child_store: FractalChildStateStore
    persistence_store: FractalRegionalRegimeStore
    phase_evaluations: tuple[PhaseEvaluationResult, ...]
    phase_arbitrations: tuple[PhaseArbitrationRecord, ...]
    phase_commits: tuple[PhaseCommitRecord, ...]
    security_evaluations: tuple[SecurityRegimeEvaluationResult, ...]
    security_commits: tuple[SecurityRegimeCommitRecord, ...]
    recovery_evaluations: tuple[
        SecurityRegimeRecoveryEvaluationResult, ...
    ]
    recovery_commits: tuple[
        SecurityRegimeRecoveryCommitRecord, ...
    ]
    divergence_audits: tuple[
        FractalCategoricalDivergenceAudit, ...
    ]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalRegionalRegimeResult.to_dict phase_commits=%s security_commits=%s recovery_commits=%s",
            len(self.phase_commits),
            len(self.security_commits),
            len(self.recovery_commits),
        )
        return {
            "child_store": self.child_store.to_dict(),
            "persistence_store": self.persistence_store.to_dict(),
            "phase_evaluations": [
                item.to_dict() for item in self.phase_evaluations
            ],
            "phase_arbitrations": [
                item.to_dict() for item in self.phase_arbitrations
            ],
            "phase_commits": [
                item.to_dict() for item in self.phase_commits
            ],
            "security_evaluations": [
                item.to_dict() for item in self.security_evaluations
            ],
            "security_commits": [
                item.to_dict() for item in self.security_commits
            ],
            "recovery_evaluations": [
                item.to_dict() for item in self.recovery_evaluations
            ],
            "recovery_commits": [
                item.to_dict() for item in self.recovery_commits
            ],
            "divergence_audits": [
                item.to_dict() for item in self.divergence_audits
            ],
        }


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    logger.info("_validate_config")
    mode = config.get("mode", {})
    required_true = (
        "enabled",
        "evaluate_active_l2_only",
        "reuse_l1_phase_machine",
        "reuse_l1_security_regime_machine",
        "sibling_divergence_allowed",
        "new_children_start_next_day",
        "regional_persistence_separate_from_l1",
        "atomic_with_day_transaction",
    )
    for key in required_true:
        if mode.get(key) is not True:
            raise ValueError(
                f"v0.28 regional regime runtime requires {key}=true"
            )

    categorical = config.get("categorical_aggregation", {})
    policy_id = str(categorical.get("policy_id", "")).strip()
    if not policy_id:
        raise ValueError(
            "Regional categorical aggregation policy_id is required"
        )
    if (
        categorical.get("dynamic_regime_collapse_policy")
        != "unanimous_consensus_required_until_v0_32"
    ):
        raise ValueError(
            "v0.28 dynamic categorical collapse must remain consensus-only"
        )
    if categorical.get("fail_closed_on_divergence") is not True:
        raise ValueError(
            "v0.28 categorical divergence must fail closed on collapse"
        )
    dynamic = tuple(
        sorted(
            str(item)
            for item in categorical.get("dynamic_regimes", [])
        )
    )
    if dynamic != ("national_phase", "security_force_regime"):
        raise ValueError(
            "v0.28 dynamic regional regimes must be national_phase and "
            "security_force_regime"
        )
    static = tuple(
        sorted(
            str(item)
            for item in categorical.get("static_regimes", [])
        )
    )
    if static != ("organized_crime_regime", "prison_regime"):
        raise ValueError(
            "v0.28 static regional regimes must remain prison/organized-crime"
        )
    return {
        "aggregation_policy_id": policy_id,
    }


def _phase_baseline(state: EngineState) -> PhasePersistenceState:
    logger.info("_phase_baseline node=%s day=%s", state.node_id, state.day)
    return PhasePersistenceState(
        node_id=state.node_id,
        current_phase=str(state.regimes["national_phase"]),
        last_evaluated_day=state.day,
        streaks=(),
    )


def _security_baseline(
    state: EngineState,
) -> SecurityRegimePersistenceState:
    logger.info(
        "_security_baseline node=%s day=%s",
        state.node_id,
        state.day,
    )
    return SecurityRegimePersistenceState(
        node_id=state.node_id,
        current_regime=str(
            state.regimes["security_force_regime"]
        ),
        last_evaluated_day=state.day,
        streaks=(),
    )


def _recovery_baseline(
    state: EngineState,
) -> SecurityRegimeRecoveryPersistenceState:
    logger.info(
        "_recovery_baseline node=%s day=%s",
        state.node_id,
        state.day,
    )
    return SecurityRegimeRecoveryPersistenceState(
        node_id=state.node_id,
        current_regime=str(
            state.regimes["security_force_regime"]
        ),
        last_evaluated_day=state.day,
        streaks=(),
    )


def bootstrap_or_validate_regional_regime_store(
    *,
    child_store: FractalChildStateStore,
    active_node_ids: tuple[str, ...],
    supplied_store: FractalRegionalRegimeStore | None,
) -> FractalRegionalRegimeStore:
    logger.info(
        "bootstrap_or_validate_regional_regime_store day=%s active=%s supplied=%s",
        child_store.last_initialized_day,
        len(active_node_ids),
        supplied_store is not None,
    )
    child_map = child_store.state_map()
    expected = set(active_node_ids)
    if not expected.issubset(child_map):
        raise ValueError(
            "Regional regime bootstrap missing active child states: "
            f"{sorted(expected - set(child_map))}"
        )

    if supplied_store is None:
        already_active = [
            node_id
            for node_id in sorted(expected)
            if child_map[node_id].metadata.get(
                "fractal_regional_regime_runtime_active"
            ) is True
        ]
        if already_active:
            raise ValueError(
                "Regional regime persistence history is required for "
                f"previously evaluated children: {already_active}"
            )
        states = [child_map[node_id] for node_id in sorted(expected)]
        return FractalRegionalRegimeStore(
            last_committed_day=child_store.last_initialized_day,
            phase_persistence=tuple(
                _phase_baseline(state) for state in states
            ),
            security_persistence=tuple(
                _security_baseline(state) for state in states
            ),
            security_recovery_persistence=tuple(
                _recovery_baseline(state) for state in states
            ),
        )

    if (
        supplied_store.last_committed_day
        != child_store.last_initialized_day
    ):
        raise ValueError(
            "Regional regime persistence day mismatch: "
            f"expected {child_store.last_initialized_day}, "
            f"got {supplied_store.last_committed_day}"
        )

    phase = supplied_store.phase_map()
    security = supplied_store.security_map()
    recovery = supplied_store.recovery_map()
    for name, mapping in (
        ("phase", phase),
        ("security", security),
        ("security_recovery", recovery),
    ):
        if set(mapping) != expected:
            raise ValueError(
                f"Regional {name} persistence coverage mismatch: "
                f"missing={sorted(expected - set(mapping))} "
                f"unexpected={sorted(set(mapping) - expected)}"
            )

    for node_id in sorted(expected):
        state = child_map[node_id]
        if phase[node_id].current_phase != state.regimes["national_phase"]:
            raise ValueError(
                f"Regional phase persistence mismatch for {node_id}"
            )
        current_regime = state.regimes["security_force_regime"]
        if security[node_id].current_regime != current_regime:
            raise ValueError(
                f"Regional security persistence mismatch for {node_id}"
            )
        if recovery[node_id].current_regime != current_regime:
            raise ValueError(
                f"Regional security recovery persistence mismatch for {node_id}"
            )
        if phase[node_id].last_evaluated_day != state.day:
            raise ValueError(
                f"Regional phase persistence day mismatch for {node_id}"
            )
        if security[node_id].last_evaluated_day != state.day:
            raise ValueError(
                f"Regional security persistence day mismatch for {node_id}"
            )
        if recovery[node_id].last_evaluated_day != state.day:
            raise ValueError(
                f"Regional recovery persistence day mismatch for {node_id}"
            )
    return supplied_store


def _commit_security_for_node(
    *,
    state: EngineState,
    persistence: SecurityRegimePersistenceState,
    context_flags: dict[str, bool],
    regime_config: dict[str, Any],
    transition_config: dict[str, Any],
    recovery_config: dict[str, Any],
    recovery_transition_config: dict[str, Any],
    recovery_persistence: SecurityRegimeRecoveryPersistenceState,
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    EngineState,
    SecurityRegimePersistenceState,
    SecurityRegimeRecoveryPersistenceState,
    SecurityRegimeEvaluationResult,
    SecurityRegimeCommitRecord | None,
    SecurityRegimeRecoveryEvaluationResult,
    SecurityRegimeRecoveryCommitRecord | None,
]:
    logger.info(
        "_commit_security_for_node node=%s day=%s",
        state.node_id,
        state.day,
    )
    evaluation = evaluate_security_regime(
        state=state,
        persistence=persistence,
        context_flags=context_flags,
        regime_config=regime_config,
        parameter_registry=parameter_registry,
        profile=profile,
        manifest=manifest,
        trace=trace,
    )
    if len(evaluation.proposals) > 1:
        raise ValueError(
            f"Multiple matured regional security proposals for {state.node_id}"
        )

    committed_state = state
    escalation_persistence = evaluation.persistence
    escalation_commit: SecurityRegimeCommitRecord | None = None
    if evaluation.proposals:
        (
            committed_state,
            escalation_commit,
            escalation_persistence,
        ) = commit_security_regime_transition(
            state=state,
            proposal=evaluation.proposals[0],
            transition_config=transition_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=trace,
        )
    else:
        escalation_persistence = retain_security_regime_persistence(
            persistence=evaluation.persistence,
            trace=trace,
        )

    recovery_evaluation = evaluate_security_regime_recovery(
        state=committed_state,
        persistence=recovery_persistence,
        context_flags=context_flags,
        recovery_config=recovery_config,
        parameter_registry=parameter_registry,
        profile=profile,
        manifest=manifest,
        trace=trace,
        same_day_escalation_committed=(
            escalation_commit is not None
        ),
    )
    if len(recovery_evaluation.proposals) > 1:
        raise ValueError(
            f"Multiple matured regional recovery proposals for {state.node_id}"
        )

    recovery_commit: SecurityRegimeRecoveryCommitRecord | None = None
    recovery_out = recovery_evaluation.persistence
    if recovery_evaluation.proposals:
        (
            committed_state,
            recovery_commit,
            escalation_persistence,
            recovery_out,
        ) = commit_security_regime_recovery(
            state=committed_state,
            proposal=recovery_evaluation.proposals[0],
            transition_config=recovery_transition_config,
            engine_state_registry=engine_state_registry,
            manifest=manifest,
            trace=trace,
        )
    else:
        recovery_out = retain_security_regime_recovery_persistence(
            persistence=recovery_evaluation.persistence,
            trace=trace,
        )

    return (
        committed_state,
        escalation_persistence,
        recovery_out,
        evaluation,
        escalation_commit,
        recovery_evaluation,
        recovery_commit,
    )


def _commit_phase_for_node(
    *,
    state: EngineState,
    persistence: PhasePersistenceState,
    context_flags: dict[str, bool],
    phase_config: dict[str, Any],
    transition_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> tuple[
    EngineState,
    PhasePersistenceState,
    PhaseEvaluationResult,
    PhaseArbitrationRecord | None,
    PhaseCommitRecord | None,
]:
    logger.info(
        "_commit_phase_for_node node=%s day=%s",
        state.node_id,
        state.day,
    )
    evaluation = evaluate_national_phase(
        state=state,
        persistence=persistence,
        context_flags=context_flags,
        phase_config=phase_config,
        parameter_registry=parameter_registry,
        profile=profile,
        manifest=manifest,
        trace=trace,
    )
    arbitration = arbitrate_phase_proposals(
        proposals=evaluation.proposals,
        phase_config=phase_config,
        transition_config=transition_config,
        manifest=manifest,
        trace=trace,
    )
    if arbitration is None:
        return (
            state,
            retain_phase_persistence(
                persistence=evaluation.persistence,
                trace=trace,
            ),
            evaluation,
            None,
            None,
        )

    committed, commit, persistence_out = commit_phase_transition(
        state=state,
        proposals=evaluation.proposals,
        arbitration=arbitration,
        transition_config=transition_config,
        engine_state_registry=engine_state_registry,
        manifest=manifest,
        trace=trace,
    )
    return (
        committed,
        persistence_out,
        evaluation,
        arbitration,
        commit,
    )


def _divergence_audits(
    *,
    states: dict[str, EngineState],
    policy_id: str,
) -> tuple[FractalCategoricalDivergenceAudit, ...]:
    logger.info("_divergence_audits states=%s", len(states))
    by_parent: dict[str, list[EngineState]] = {}
    for state in states.values():
        parent = state.metadata.get("fractal_parent_node_id")
        if parent is None:
            raise ValueError(
                f"Regional state {state.node_id} missing parent lineage"
            )
        by_parent.setdefault(str(parent), []).append(state)

    audits: list[FractalCategoricalDivergenceAudit] = []
    for parent_id in sorted(by_parent):
        siblings = sorted(
            by_parent[parent_id],
            key=lambda item: item.node_id,
        )
        phases = tuple(
            (item.node_id, str(item.regimes["national_phase"]))
            for item in siblings
        )
        security = tuple(
            (
                item.node_id,
                str(item.regimes["security_force_regime"]),
            )
            for item in siblings
        )
        prison = tuple(
            (item.node_id, str(item.regimes["prison_regime"]))
            for item in siblings
        )
        crime = tuple(
            (
                item.node_id,
                str(item.regimes["organized_crime_regime"]),
            )
            for item in siblings
        )
        phase_divergent = len({value for _, value in phases}) > 1
        security_divergent = (
            len({value for _, value in security}) > 1
        )
        static_consistent = (
            len({value for _, value in prison}) == 1
            and len({value for _, value in crime}) == 1
        )
        collapse_ready = (
            not phase_divergent
            and not security_divergent
            and static_consistent
        )
        day = siblings[0].day
        if any(item.day != day for item in siblings):
            raise ValueError(
                f"Sibling regional regime day mismatch for {parent_id}"
            )
        payload = {
            "parent_node_id": parent_id,
            "day": day,
            "child_node_ids": [item.node_id for item in siblings],
            "national_phases": dict(phases),
            "security_force_regimes": dict(security),
            "prison_regimes": dict(prison),
            "organized_crime_regimes": dict(crime),
            "aggregation_policy_id": policy_id,
        }
        audit = FractalCategoricalDivergenceAudit(
            audit_id=f"fractal-categorical-{canonical_hash(payload)[:24]}",
            parent_node_id=parent_id,
            day=day,
            child_node_ids=tuple(
                item.node_id for item in siblings
            ),
            national_phases=phases,
            security_force_regimes=security,
            prison_regimes=prison,
            organized_crime_regimes=crime,
            phase_divergent=phase_divergent,
            security_regime_divergent=security_divergent,
            static_regimes_consistent=static_consistent,
            collapse_consensus_ready=collapse_ready,
            aggregation_policy_id=policy_id,
        )
        audits.append(audit)
    return tuple(audits)


def execute_regional_regime_runtime(
    *,
    child_store: FractalChildStateStore,
    beginning_active_node_ids: tuple[str, ...],
    persistence_store: FractalRegionalRegimeStore,
    context_flags: dict[str, dict[str, bool]] | None,
    regional_config: dict[str, Any],
    phase_config: dict[str, Any],
    phase_transition_config: dict[str, Any],
    security_regime_config: dict[str, Any],
    security_transition_config: dict[str, Any],
    security_recovery_config: dict[str, Any],
    security_recovery_transition_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> FractalRegionalRegimeResult:
    logger.info(
        "execute_regional_regime_runtime day=%s beginning_active=%s total_children=%s",
        child_store.last_initialized_day,
        len(beginning_active_node_ids),
        len(child_store.states),
    )
    policy = _validate_config(regional_config)
    state_map = child_store.state_map()
    beginning = set(beginning_active_node_ids)
    if not beginning.issubset(state_map):
        raise ValueError(
            "Regional regime runtime missing beginning-active children: "
            f"{sorted(beginning - set(state_map))}"
        )
    expected_prior_day = child_store.last_initialized_day - 1
    if persistence_store.last_committed_day != expected_prior_day:
        raise ValueError(
            "Regional regime runtime persistence must precede child store by "
            f"one day: store={persistence_store.last_committed_day} "
            f"child={child_store.last_initialized_day}"
        )

    supplied_flags = dict(context_flags or {})
    unknown_flags = set(supplied_flags) - beginning
    if unknown_flags:
        raise ValueError(
            "Regional context flags contain non-beginning-active nodes: "
            f"{sorted(unknown_flags)}"
        )

    phase_prior = persistence_store.phase_map()
    security_prior = persistence_store.security_map()
    recovery_prior = persistence_store.recovery_map()
    for name, mapping in (
        ("phase", phase_prior),
        ("security", security_prior),
        ("recovery", recovery_prior),
    ):
        if set(mapping) != beginning:
            raise ValueError(
                f"Regional {name} prior persistence coverage mismatch"
            )

    expected_prior_day = child_store.last_initialized_day - 1
    for node_id in sorted(beginning):
        state = state_map[node_id]
        if phase_prior[node_id].last_evaluated_day != expected_prior_day:
            raise ValueError(
                f"Regional phase prior day mismatch for {node_id}"
            )
        if security_prior[node_id].last_evaluated_day != expected_prior_day:
            raise ValueError(
                f"Regional security prior day mismatch for {node_id}"
            )
        if recovery_prior[node_id].last_evaluated_day != expected_prior_day:
            raise ValueError(
                f"Regional recovery prior day mismatch for {node_id}"
            )
        if (
            phase_prior[node_id].current_phase
            != state.regimes["national_phase"]
        ):
            raise ValueError(
                f"Regional phase prior state mismatch for {node_id}"
            )
        current_security = state.regimes["security_force_regime"]
        if security_prior[node_id].current_regime != current_security:
            raise ValueError(
                f"Regional security prior state mismatch for {node_id}"
            )
        if recovery_prior[node_id].current_regime != current_security:
            raise ValueError(
                f"Regional recovery prior state mismatch for {node_id}"
            )

    staged_trace = TraceLedger()
    next_states = dict(state_map)
    phase_out: dict[str, PhasePersistenceState] = {}
    security_out: dict[str, SecurityRegimePersistenceState] = {}
    recovery_out: dict[
        str, SecurityRegimeRecoveryPersistenceState
    ] = {}

    phase_evaluations: list[PhaseEvaluationResult] = []
    phase_arbitrations: list[PhaseArbitrationRecord] = []
    phase_commits: list[PhaseCommitRecord] = []
    security_evaluations: list[
        SecurityRegimeEvaluationResult
    ] = []
    security_commits: list[SecurityRegimeCommitRecord] = []
    recovery_evaluations: list[
        SecurityRegimeRecoveryEvaluationResult
    ] = []
    recovery_commits: list[
        SecurityRegimeRecoveryCommitRecord
    ] = []

    for node_id in sorted(beginning):
        state = state_map[node_id]
        flags = supplied_flags.get(node_id, {})
        (
            secured_state,
            security_persistence,
            recovery_persistence,
            security_evaluation,
            security_commit,
            recovery_evaluation,
            recovery_commit,
        ) = _commit_security_for_node(
            state=state,
            persistence=security_prior[node_id],
            context_flags=flags,
            regime_config=security_regime_config,
            transition_config=security_transition_config,
            recovery_config=security_recovery_config,
            recovery_transition_config=(
                security_recovery_transition_config
            ),
            recovery_persistence=recovery_prior[node_id],
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=staged_trace,
        )
        (
            final_state,
            phase_persistence,
            phase_evaluation,
            phase_arbitration,
            phase_commit,
        ) = _commit_phase_for_node(
            state=secured_state,
            persistence=phase_prior[node_id],
            context_flags=flags,
            phase_config=phase_config,
            transition_config=phase_transition_config,
            engine_state_registry=engine_state_registry,
            parameter_registry=parameter_registry,
            profile=profile,
            manifest=manifest,
            trace=staged_trace,
        )

        metadata = dict(final_state.metadata)
        metadata.update(
            {
                "fractal_regional_regime_runtime_active": True,
                "fractal_regional_regime_runtime_day": final_state.day,
                "fractal_categorical_aggregation_policy_id": (
                    policy["aggregation_policy_id"]
                ),
            }
        )
        next_states[node_id] = EngineState(
            node_id=final_state.node_id,
            day=final_state.day,
            physical_stocks=dict(final_state.physical_stocks),
            latents=dict(final_state.latents),
            regimes=dict(final_state.regimes),
            metadata=metadata,
        )
        phase_out[node_id] = phase_persistence
        security_out[node_id] = security_persistence
        recovery_out[node_id] = recovery_persistence
        phase_evaluations.append(phase_evaluation)
        security_evaluations.append(security_evaluation)
        recovery_evaluations.append(recovery_evaluation)
        if phase_arbitration is not None:
            phase_arbitrations.append(phase_arbitration)
        if phase_commit is not None:
            phase_commits.append(phase_commit)
        if security_commit is not None:
            security_commits.append(security_commit)
        if recovery_commit is not None:
            recovery_commits.append(recovery_commit)

    new_node_ids = set(state_map) - beginning
    for node_id in sorted(new_node_ids):
        state = state_map[node_id]
        phase_out[node_id] = _phase_baseline(state)
        security_out[node_id] = _security_baseline(state)
        recovery_out[node_id] = _recovery_baseline(state)
        staged_trace.append(
            "fractal_regional_regime_persistence_initialized",
            node_id=node_id,
            day=state.day,
            source="new_child_starts_next_day",
        )

    updated_store = FractalRegionalRegimeStore(
        last_committed_day=child_store.last_initialized_day,
        phase_persistence=tuple(
            phase_out[node_id] for node_id in sorted(phase_out)
        ),
        security_persistence=tuple(
            security_out[node_id]
            for node_id in sorted(security_out)
        ),
        security_recovery_persistence=tuple(
            recovery_out[node_id]
            for node_id in sorted(recovery_out)
        ),
    )
    updated_child_store = FractalChildStateStore(
        last_initialized_day=child_store.last_initialized_day,
        states=tuple(
            next_states[node_id]
            for node_id in sorted(next_states)
        ),
    )
    audits = _divergence_audits(
        states=next_states,
        policy_id=policy["aggregation_policy_id"],
    )
    for audit in audits:
        staged_trace.append(
            "fractal_categorical_divergence_audit",
            **audit.to_dict(),
        )

    staged_trace.append(
        "fractal_regional_regime_runtime_committed",
        day=child_store.last_initialized_day,
        evaluated_node_ids=list(sorted(beginning)),
        initialized_node_ids=list(sorted(new_node_ids)),
        phase_commit_ids=[
            item.commit_id
            for item in sorted(
                phase_commits,
                key=lambda value: value.commit_id,
            )
        ],
        security_commit_ids=[
            item.commit_id
            for item in sorted(
                security_commits,
                key=lambda value: value.commit_id,
            )
        ],
        recovery_commit_ids=[
            item.commit_id
            for item in sorted(
                recovery_commits,
                key=lambda value: value.commit_id,
            )
        ],
        persistence_store_hash=updated_store.store_hash(),
        child_store_hash=updated_child_store.store_hash(),
        aggregation_policy_id=policy["aggregation_policy_id"],
    )
    trace.extend_from(staged_trace)

    return FractalRegionalRegimeResult(
        child_store=updated_child_store,
        persistence_store=updated_store,
        phase_evaluations=tuple(phase_evaluations),
        phase_arbitrations=tuple(phase_arbitrations),
        phase_commits=tuple(
            sorted(phase_commits, key=lambda item: item.commit_id)
        ),
        security_evaluations=tuple(security_evaluations),
        security_commits=tuple(
            sorted(security_commits, key=lambda item: item.commit_id)
        ),
        recovery_evaluations=tuple(recovery_evaluations),
        recovery_commits=tuple(
            sorted(recovery_commits, key=lambda item: item.commit_id)
        ),
        divergence_audits=audits,
    )
