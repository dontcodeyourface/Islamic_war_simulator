from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .manifest import RunManifest
from .security_regime import (
    CANONICAL_REGIME_ORDER,
    SecurityRegimeConditionResult,
)
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)

CANONICAL_RECOVERY_TRANSITIONS = (
    ("STRAINED", "COHESIVE", "strained_to_cohesive"),
    (
        "SELECTIVE_NONCOMPLIANCE",
        "STRAINED",
        "selective_noncompliance_to_strained",
    ),
    (
        "COMMAND_FRACTURE",
        "SELECTIVE_NONCOMPLIANCE",
        "command_fracture_to_selective_noncompliance",
    ),
    (
        "LOCALIZED_DEFECTION",
        "COMMAND_FRACTURE",
        "localized_defection_to_command_fracture",
    ),
    (
        "MULTIPLE_COMMANDS",
        "LOCALIZED_DEFECTION",
        "multiple_commands_to_localized_defection",
    ),
)

ALLOWED_LATENT_INPUTS = frozenset(
    {
        "security_chain_cohesion",
        "command_cohesion",
        "constitutional_loyalty",
        "operational_fatigue",
        "center_region_cohesion",
        "state_cohesion",
    }
)


@dataclass(frozen=True)
class SecurityRegimeRecoveryRuleEvaluation:
    node_id: str
    day: int
    from_regime: str
    to_regime: str
    rule_id: str
    parameter_id: str
    parameter_subkey: str
    condition_results: tuple[SecurityRegimeConditionResult, ...]
    conditions_passed: bool
    persistence_required: int
    persistence_observed: int
    matured: bool
    suppressed_by_same_day_escalation: bool = False

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeRecoveryRuleEvaluation.to_dict node=%s rule=%s matured=%s",
            self.node_id,
            self.rule_id,
            self.matured,
        )
        return {
            "node_id": self.node_id,
            "day": self.day,
            "from_regime": self.from_regime,
            "to_regime": self.to_regime,
            "rule_id": self.rule_id,
            "parameter_id": self.parameter_id,
            "parameter_subkey": self.parameter_subkey,
            "condition_results": [
                item.to_dict() for item in self.condition_results
            ],
            "conditions_passed": self.conditions_passed,
            "persistence_required": self.persistence_required,
            "persistence_observed": self.persistence_observed,
            "matured": self.matured,
            "suppressed_by_same_day_escalation": (
                self.suppressed_by_same_day_escalation
            ),
        }


@dataclass(frozen=True)
class SecurityRegimeRecoveryProposal:
    proposal_id: str
    node_id: str
    day: int
    from_regime: str
    to_regime: str
    rule_id: str
    parameter_id: str
    parameter_subkey: str
    condition_results: tuple[SecurityRegimeConditionResult, ...]
    persistence_required: int
    persistence_observed: int
    apply_status: str = "PROPOSED_NOT_APPLIED"

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeRecoveryProposal.to_dict proposal_id=%s",
            self.proposal_id,
        )
        return {
            "proposal_id": self.proposal_id,
            "node_id": self.node_id,
            "day": self.day,
            "from_regime": self.from_regime,
            "to_regime": self.to_regime,
            "rule_id": self.rule_id,
            "parameter_id": self.parameter_id,
            "parameter_subkey": self.parameter_subkey,
            "condition_results": [
                item.to_dict() for item in self.condition_results
            ],
            "persistence_required": self.persistence_required,
            "persistence_observed": self.persistence_observed,
            "apply_status": self.apply_status,
        }


@dataclass(frozen=True)
class SecurityRegimeRecoveryPersistenceState:
    node_id: str
    current_regime: str
    last_evaluated_day: int
    streaks: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeRecoveryPersistenceState.to_dict node=%s day=%s",
            self.node_id,
            self.last_evaluated_day,
        )
        return {
            "node_id": self.node_id,
            "current_regime": self.current_regime,
            "last_evaluated_day": self.last_evaluated_day,
            "streaks": dict(self.streaks),
        }


@dataclass(frozen=True)
class SecurityRegimeRecoveryEvaluationResult:
    persistence: SecurityRegimeRecoveryPersistenceState
    evaluations: tuple[SecurityRegimeRecoveryRuleEvaluation, ...]
    proposals: tuple[SecurityRegimeRecoveryProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeRecoveryEvaluationResult.to_dict node=%s evaluations=%s proposals=%s",
            self.persistence.node_id,
            len(self.evaluations),
            len(self.proposals),
        )
        return {
            "persistence": self.persistence.to_dict(),
            "evaluations": [item.to_dict() for item in self.evaluations],
            "proposals": [item.to_dict() for item in self.proposals],
        }


def _parameter_id(profile: str) -> str:
    logger.info("_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "SECURITY_REGIME_RECOVERY_SYN_V1"
    if profile == "calibrated_v1":
        return "SECURITY_REGIME_RECOVERY_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _escalation_parameter_id(profile: str) -> str:
    logger.info("_escalation_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "SECURITY_REGIMES_SYN_V1"
    if profile == "calibrated_v1":
        return "SECURITY_REGIMES_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _escalation_parameter_value(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info(
        "_escalation_parameter_value profile=%s parameter_id=%s",
        profile,
        parameter_id,
    )
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing security-regime escalation parameter {parameter_id} for {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Security-regime escalation parameter {parameter_id} "
            "must contain a mapping value"
        )
    return value


def _validate_hysteresis(
    *,
    recovery_rules: dict[str, Any],
    escalation_rules: dict[str, Any],
) -> None:
    logger.info("_validate_hysteresis")
    numeric_guards = (
        (
            "strained_to_cohesive",
            "security_chain_cohesion_gte",
            "strained",
            "security_chain_cohesion_lt",
            "gt",
        ),
        (
            "strained_to_cohesive",
            "operational_fatigue_lte",
            "strained",
            "operational_fatigue_gte",
            "lt",
        ),
        (
            "selective_noncompliance_to_strained",
            "security_chain_cohesion_gte",
            "selective_noncompliance",
            "security_chain_cohesion_lte",
            "gt",
        ),
        (
            "selective_noncompliance_to_strained",
            "constitutional_loyalty_gte",
            "selective_noncompliance",
            "constitutional_loyalty_lte",
            "gt",
        ),
        (
            "command_fracture_to_selective_noncompliance",
            "command_cohesion_gte",
            "command_fracture",
            "command_cohesion_lte",
            "gt",
        ),
        (
            "command_fracture_to_selective_noncompliance",
            "security_chain_cohesion_gte",
            "command_fracture",
            "security_chain_cohesion_lte",
            "gt",
        ),
        (
            "localized_defection_to_command_fracture",
            "command_cohesion_gte",
            "localized_defection",
            "command_cohesion_lte",
            "gt",
        ),
        (
            "localized_defection_to_command_fracture",
            "center_region_cohesion_gte",
            "localized_defection",
            "center_region_cohesion_lte",
            "gt",
        ),
        (
            "multiple_commands_to_localized_defection",
            "command_cohesion_gte",
            "multiple_commands",
            "command_cohesion_lte",
            "gt",
        ),
        (
            "multiple_commands_to_localized_defection",
            "state_cohesion_gte",
            "multiple_commands",
            "state_cohesion_lte",
            "gt",
        ),
    )

    for (
        recovery_subkey,
        recovery_condition,
        escalation_subkey,
        escalation_condition,
        relation,
    ) in numeric_guards:
        recovery_entry = recovery_rules.get(recovery_subkey)
        escalation_entry = escalation_rules.get(escalation_subkey)
        if not isinstance(recovery_entry, dict) or not isinstance(
            escalation_entry, dict
        ):
            raise ValueError("Security recovery hysteresis mapping is incomplete")
        recovery_conditions = recovery_entry.get("all")
        if not isinstance(recovery_conditions, dict):
            raise ValueError(
                f"Security recovery {recovery_subkey} must define all conditions"
            )
        if recovery_condition not in recovery_conditions:
            raise ValueError(
                f"Security recovery hysteresis condition missing: "
                f"{recovery_subkey}.{recovery_condition}"
            )
        if escalation_condition not in escalation_entry:
            raise ValueError(
                f"Security escalation hysteresis condition missing: "
                f"{escalation_subkey}.{escalation_condition}"
            )
        recovery_value = float(recovery_conditions[recovery_condition])
        escalation_value = float(escalation_entry[escalation_condition])
        if relation == "gt" and not recovery_value > escalation_value:
            raise ValueError(
                f"Security recovery hysteresis gap must be positive for "
                f"{recovery_subkey}.{recovery_condition}"
            )
        if relation == "lt" and not recovery_value < escalation_value:
            raise ValueError(
                f"Security recovery hysteresis gap must be positive for "
                f"{recovery_subkey}.{recovery_condition}"
            )

    boolean_guards = (
        (
            "localized_defection_to_command_fracture",
            "competing_authority_present",
            "localized_defection",
        ),
        (
            "multiple_commands_to_localized_defection",
            "multiple_authority_nodes_present",
            "multiple_commands",
        ),
    )
    for recovery_subkey, condition_key, escalation_subkey in boolean_guards:
        recovery_conditions = recovery_rules[recovery_subkey]["all"]
        escalation_conditions = escalation_rules[escalation_subkey]
        if recovery_conditions.get(condition_key) is not False:
            raise ValueError(
                f"Security recovery {condition_key} must require false"
            )
        if escalation_conditions.get(condition_key) is not True:
            raise ValueError(
                f"Security escalation {condition_key} must require true"
            )


def _parameter_value(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info(
        "_parameter_value profile=%s parameter_id=%s",
        profile,
        parameter_id,
    )
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing security-regime recovery parameter {parameter_id} for {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Security-regime recovery parameter {parameter_id} "
            "must contain a mapping value"
        )
    return value


def _validate_config(config: dict[str, Any]) -> tuple[dict[str, str], ...]:
    logger.info("_validate_config")
    mode = config.get("mode", {})
    if mode.get("read_only") is not True:
        raise ValueError("v0.18 security recovery requires read_only=true")
    if mode.get("recovery_commit_allowed") is not False:
        raise ValueError("v0.18 security recovery commit must remain disabled")
    if mode.get("one_level_per_transition") is not True:
        raise ValueError("v0.18 recovery must remain one-level-per-transition")
    if mode.get("suppress_after_same_day_escalation") is not True:
        raise ValueError(
            "v0.18 recovery must suppress evaluation after same-day escalation"
        )

    transitions = config.get("transitions")
    if not isinstance(transitions, list):
        raise ValueError("Security recovery transitions must be a list")
    observed: list[tuple[str, str, str]] = []
    normalized: list[dict[str, str]] = []
    seen_rule_ids: set[str] = set()
    for item in transitions:
        if not isinstance(item, dict):
            raise ValueError("Security recovery transition must be a mapping")
        rule_id = str(item.get("rule_id", ""))
        from_regime = str(item.get("from", ""))
        to_regime = str(item.get("to", ""))
        parameter_subkey = str(item.get("parameter_subkey", ""))
        if not all((rule_id, from_regime, to_regime, parameter_subkey)):
            raise ValueError(f"Invalid security recovery transition: {item}")
        if rule_id in seen_rule_ids:
            raise ValueError(f"Duplicate security recovery rule_id {rule_id}")
        seen_rule_ids.add(rule_id)
        observed.append((from_regime, to_regime, parameter_subkey))
        normalized.append(
            {
                "rule_id": rule_id,
                "from": from_regime,
                "to": to_regime,
                "parameter_subkey": parameter_subkey,
            }
        )
    if tuple(observed) != CANONICAL_RECOVERY_TRANSITIONS:
        raise ValueError("Security recovery transitions must remain canonical")

    safety = config.get("safety", {})
    for key in (
        "political_identity_direct_transition_input",
        "demographic_identity_direct_transition_input",
        "religious_identity_direct_transition_input",
    ):
        if safety.get(key) is not False:
            raise ValueError(
                f"Security recovery safety invariant {key} must remain false"
            )
    if safety.get("regime_is_classifier_not_operational_instruction") is not True:
        raise ValueError("Security regime recovery must remain classifier-only")
    return tuple(normalized)


def _compare(observed: float, operator: str, expected: float) -> bool:
    logger.info(
        "_compare observed=%s operator=%s expected=%s",
        observed,
        operator,
        expected,
    )
    if operator == ">=":
        return observed >= expected
    if operator == "<=":
        return observed <= expected
    if operator == ">":
        return observed > expected
    if operator == "<":
        return observed < expected
    raise ValueError(f"Unsupported security recovery operator {operator}")


def _parse_condition(
    condition_key: str,
    operator_map: dict[str, str],
) -> tuple[str, str] | None:
    logger.info("_parse_condition condition_key=%s", condition_key)
    for suffix in sorted(operator_map, key=len, reverse=True):
        if condition_key.endswith(suffix):
            variable = condition_key[: -len(suffix)]
            if not variable:
                raise ValueError(
                    f"Invalid security recovery condition {condition_key}"
                )
            return variable, operator_map[suffix]
    return None


def _evaluate_condition(
    *,
    condition_key: str,
    expected: Any,
    state: EngineState,
    context_flags: dict[str, bool],
    config: dict[str, Any],
) -> SecurityRegimeConditionResult:
    logger.info(
        "_evaluate_condition node=%s key=%s",
        state.node_id,
        condition_key,
    )
    boolean_flags = set(
        str(item)
        for item in config["condition_language"]["boolean_context_flags"]
    )
    if condition_key in boolean_flags:
        observed = bool(context_flags.get(condition_key, False))
        expected_bool = bool(expected)
        return SecurityRegimeConditionResult(
            condition_key=condition_key,
            source="context_flag",
            observed=observed,
            operator="==",
            expected=expected_bool,
            passed=observed == expected_bool,
        )

    operator_map = {
        str(k): str(v)
        for k, v in config["condition_language"][
            "latent_suffix_operators"
        ].items()
    }
    parsed = _parse_condition(condition_key, operator_map)
    if parsed is None:
        raise ValueError(f"Unknown security recovery condition {condition_key}")
    variable, operator = parsed
    if variable not in ALLOWED_LATENT_INPUTS:
        raise ValueError(
            f"Security recovery variable {variable} is not an allowed input"
        )
    if variable not in state.latents:
        raise KeyError(
            f"Security recovery variable {variable} missing from {state.node_id}"
        )
    observed = float(state.latents[variable])
    expected_value = float(expected)
    return SecurityRegimeConditionResult(
        condition_key=condition_key,
        source="latent",
        observed=observed,
        operator=operator,
        expected=expected_value,
        passed=_compare(observed, operator, expected_value),
    )


def _initial_streaks(
    *,
    persistence: SecurityRegimeRecoveryPersistenceState | None,
    state: EngineState,
) -> dict[str, int]:
    logger.info(
        "_initial_streaks node=%s day=%s supplied=%s",
        state.node_id,
        state.day,
        persistence is not None,
    )
    if persistence is None:
        return {}
    if persistence.node_id != state.node_id:
        raise ValueError("Security recovery persistence node mismatch")
    if state.day != persistence.last_evaluated_day + 1:
        raise ValueError(
            "Security recovery persistence requires consecutive days: "
            f"last={persistence.last_evaluated_day} current={state.day}"
        )
    if persistence.current_regime != state.regimes["security_force_regime"]:
        return {}
    return dict(persistence.streaks)


def _outgoing_rule(
    current_regime: str,
    transitions: tuple[dict[str, str], ...],
) -> dict[str, str] | None:
    logger.info("_outgoing_rule current_regime=%s", current_regime)
    matches = [item for item in transitions if item["from"] == current_regime]
    if len(matches) > 1:
        raise ValueError(
            f"Multiple security recovery rules from {current_regime}"
        )
    return matches[0] if matches else None


def _proposal_id(
    *,
    manifest: RunManifest,
    state: EngineState,
    rule_id: str,
    to_regime: str,
) -> str:
    logger.info(
        "_proposal_id node=%s day=%s rule=%s",
        state.node_id,
        state.day,
        rule_id,
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "node_id": state.node_id,
            "day": state.day,
            "from_regime": state.regimes["security_force_regime"],
            "to_regime": to_regime,
            "rule_id": rule_id,
            "proposal_contract": "SECURITY_REGIME_RECOVERY_V1",
        }
    )
    return f"security-recovery-{digest[:24]}"


def evaluate_security_regime_recovery(
    *,
    state: EngineState,
    persistence: SecurityRegimeRecoveryPersistenceState | None,
    context_flags: dict[str, bool] | None,
    recovery_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
    same_day_escalation_committed: bool = False,
) -> SecurityRegimeRecoveryEvaluationResult:
    """Evaluate one read-only, one-step security-regime recovery transition."""
    logger.info(
        "evaluate_security_regime_recovery node=%s day=%s regime=%s profile=%s escalated=%s",
        state.node_id,
        state.day,
        state.regimes.get("security_force_regime"),
        profile,
        same_day_escalation_committed,
    )
    state_hash_before = state.state_hash()
    transitions = _validate_config(recovery_config)
    current_regime = str(state.regimes["security_force_regime"])
    if current_regime not in CANONICAL_REGIME_ORDER:
        raise ValueError(f"Unknown security force regime {current_regime}")

    parameter_id = _parameter_id(profile)
    parameter_value = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    rules = parameter_value.get("transitions")
    if not isinstance(rules, dict):
        raise ValueError(
            f"Security recovery parameter {parameter_id} must define transitions"
        )
    escalation_parameter_id = _escalation_parameter_id(profile)
    escalation_rules = _escalation_parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=escalation_parameter_id,
    )
    _validate_hysteresis(
        recovery_rules=rules,
        escalation_rules=escalation_rules,
    )

    previous_streaks = _initial_streaks(
        persistence=persistence,
        state=state,
    )
    rule = _outgoing_rule(current_regime, transitions)
    evaluations: list[SecurityRegimeRecoveryRuleEvaluation] = []
    proposals: list[SecurityRegimeRecoveryProposal] = []
    next_streaks: dict[str, int] = {}

    if rule is not None:
        parameter_subkey = rule["parameter_subkey"]
        rule_parameters = rules.get(parameter_subkey)
        if not isinstance(rule_parameters, dict):
            raise ValueError(
                f"Missing security recovery transition parameters {parameter_subkey}"
            )
        persistence_required = int(rule_parameters.get("persistence_days", 0))
        if persistence_required < 1:
            raise ValueError(
                f"Invalid recovery persistence for {parameter_subkey}"
            )
        conditions = rule_parameters.get("all")
        if not isinstance(conditions, dict) or not conditions:
            raise ValueError(
                f"Security recovery transition {parameter_subkey} "
                "must define non-empty all conditions"
            )

        flags = dict(context_flags or {})
        condition_results = tuple(
            _evaluate_condition(
                condition_key=str(key),
                expected=value,
                state=state,
                context_flags=flags,
                config=recovery_config,
            )
            for key, value in sorted(conditions.items())
        )
        conditions_passed = all(item.passed for item in condition_results)
        streak = (
            previous_streaks.get(rule["rule_id"], 0) + 1
            if conditions_passed and not same_day_escalation_committed
            else 0
        )
        next_streaks[rule["rule_id"]] = streak
        matured = (
            conditions_passed
            and not same_day_escalation_committed
            and streak >= persistence_required
        )

        evaluation = SecurityRegimeRecoveryRuleEvaluation(
            node_id=state.node_id,
            day=state.day,
            from_regime=current_regime,
            to_regime=rule["to"],
            rule_id=rule["rule_id"],
            parameter_id=parameter_id,
            parameter_subkey=parameter_subkey,
            condition_results=condition_results,
            conditions_passed=conditions_passed,
            persistence_required=persistence_required,
            persistence_observed=streak,
            matured=matured,
            suppressed_by_same_day_escalation=same_day_escalation_committed,
        )
        evaluations.append(evaluation)
        trace.append(
            "security_regime_recovery_evaluation",
            **evaluation.to_dict(),
        )

        if matured:
            proposal = SecurityRegimeRecoveryProposal(
                proposal_id=_proposal_id(
                    manifest=manifest,
                    state=state,
                    rule_id=rule["rule_id"],
                    to_regime=rule["to"],
                ),
                node_id=state.node_id,
                day=state.day,
                from_regime=current_regime,
                to_regime=rule["to"],
                rule_id=rule["rule_id"],
                parameter_id=parameter_id,
                parameter_subkey=parameter_subkey,
                condition_results=condition_results,
                persistence_required=persistence_required,
                persistence_observed=streak,
            )
            proposals.append(proposal)
            trace.append(
                "security_regime_recovery_proposal",
                **proposal.to_dict(),
            )

    updated_persistence = SecurityRegimeRecoveryPersistenceState(
        node_id=state.node_id,
        current_regime=current_regime,
        last_evaluated_day=state.day,
        streaks=tuple(sorted(next_streaks.items())),
    )

    if state.state_hash() != state_hash_before:
        raise RuntimeError(
            "Read-only security regime recovery evaluator mutated EngineState"
        )

    return SecurityRegimeRecoveryEvaluationResult(
        persistence=updated_persistence,
        evaluations=tuple(evaluations),
        proposals=tuple(proposals),
    )
