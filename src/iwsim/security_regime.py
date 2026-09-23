from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .manifest import RunManifest
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)

CANONICAL_REGIME_ORDER = (
    "COHESIVE",
    "STRAINED",
    "SELECTIVE_NONCOMPLIANCE",
    "COMMAND_FRACTURE",
    "LOCALIZED_DEFECTION",
    "MULTIPLE_COMMANDS",
)

CANONICAL_TRANSITIONS = (
    ("COHESIVE", "STRAINED", "strained"),
    ("STRAINED", "SELECTIVE_NONCOMPLIANCE", "selective_noncompliance"),
    ("SELECTIVE_NONCOMPLIANCE", "COMMAND_FRACTURE", "command_fracture"),
    ("COMMAND_FRACTURE", "LOCALIZED_DEFECTION", "localized_defection"),
    ("LOCALIZED_DEFECTION", "MULTIPLE_COMMANDS", "multiple_commands"),
)

ALLOWED_LATENT_CONDITION_VARIABLES = frozenset(
    {
        "security_chain_cohesion",
        "operational_fatigue",
        "constitutional_loyalty",
        "command_cohesion",
        "center_region_cohesion",
        "state_cohesion",
    }
)


@dataclass(frozen=True)
class SecurityRegimeConditionResult:
    condition_key: str
    source: str
    observed: float | bool
    operator: str
    expected: float | bool
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeConditionResult.to_dict key=%s passed=%s",
            self.condition_key,
            self.passed,
        )
        return {
            "condition_key": self.condition_key,
            "source": self.source,
            "observed": self.observed,
            "operator": self.operator,
            "expected": self.expected,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class SecurityRegimeTransitionProposal:
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
            "SecurityRegimeTransitionProposal.to_dict proposal_id=%s",
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
class SecurityRegimeRuleEvaluation:
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

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeRuleEvaluation.to_dict rule_id=%s node=%s",
            self.rule_id,
            self.node_id,
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
        }


@dataclass(frozen=True)
class SecurityRegimePersistenceState:
    node_id: str
    current_regime: str
    last_evaluated_day: int
    streaks: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimePersistenceState.to_dict node=%s day=%s",
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
class SecurityRegimeEvaluationResult:
    persistence: SecurityRegimePersistenceState
    evaluations: tuple[SecurityRegimeRuleEvaluation, ...]
    proposals: tuple[SecurityRegimeTransitionProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "SecurityRegimeEvaluationResult.to_dict node=%s evaluations=%s proposals=%s",
            self.persistence.node_id,
            len(self.evaluations),
            len(self.proposals),
        )
        return {
            "persistence": self.persistence.to_dict(),
            "evaluations": [item.to_dict() for item in self.evaluations],
            "proposals": [item.to_dict() for item in self.proposals],
        }


def _validate_config(config: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    logger.info("_validate_config")
    mode = config.get("mode", {})
    if mode.get("read_only") is not True:
        raise ValueError("v0.16 security regime evaluator requires read_only=true")
    if mode.get("regime_commit_allowed") is not False:
        raise ValueError("v0.16 security regime evaluator forbids regime commit")
    if mode.get("deescalation_enabled") is not False:
        raise ValueError("v0.16 security regime evaluator is escalation-only")

    order = tuple(str(item) for item in config.get("regime_order", []))
    if order != CANONICAL_REGIME_ORDER:
        raise ValueError("Security regime order must remain canonical")

    transitions_raw = config.get("transitions")
    if not isinstance(transitions_raw, list):
        raise ValueError("Security regime transitions must be a list")
    if len(transitions_raw) != len(CANONICAL_TRANSITIONS):
        raise ValueError("Security regime transition count mismatch")

    normalized: list[dict[str, Any]] = []
    observed_contract: list[tuple[str, str, str]] = []
    seen_rule_ids: set[str] = set()
    for item in transitions_raw:
        if not isinstance(item, dict):
            raise ValueError("Security regime transition must be a mapping")
        rule_id = str(item.get("rule_id", ""))
        from_regime = str(item.get("from", ""))
        to_regime = str(item.get("to", ""))
        parameter_subkey = str(item.get("parameter_subkey", ""))
        parameter_id = item.get("parameter_id")
        if (
            not rule_id
            or not from_regime
            or not to_regime
            or not parameter_subkey
            or not isinstance(parameter_id, dict)
        ):
            raise ValueError(f"Invalid security regime transition: {item}")
        if rule_id in seen_rule_ids:
            raise ValueError(f"Duplicate security regime rule_id {rule_id}")
        seen_rule_ids.add(rule_id)
        observed_contract.append(
            (from_regime, to_regime, parameter_subkey)
        )
        normalized.append(
            {
                "rule_id": rule_id,
                "from": from_regime,
                "to": to_regime,
                "parameter_subkey": parameter_subkey,
                "parameter_id": {
                    str(k): str(v) for k, v in parameter_id.items()
                },
            }
        )
    if tuple(observed_contract) != CANONICAL_TRANSITIONS:
        raise ValueError("Security regime transitions must remain canonical")

    safety = config.get("safety")
    if not isinstance(safety, dict):
        raise ValueError("Security regime safety block must be a mapping")
    for key in (
        "political_identity_direct_transition_input",
        "demographic_identity_direct_transition_input",
        "religious_identity_direct_transition_input",
    ):
        if safety.get(key) is not False:
            raise ValueError(f"Security regime safety invariant {key} must remain false")
    if safety.get("regime_is_classifier_not_operational_instruction") is not True:
        raise ValueError("Security regime must remain a classifier")

    return tuple(normalized)


def _parameter_set(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info(
        "_parameter_set profile=%s parameter_id=%s",
        profile,
        parameter_id,
    )
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(
        parameter_id
    )
    if parameter is None:
        raise ValueError(
            f"Missing security-regime parameter {parameter_id} for {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Security-regime parameter {parameter_id} must contain a mapping value"
        )
    return value


def _parse_condition_key(
    condition_key: str,
    operator_map: dict[str, str],
) -> tuple[str, str] | None:
    logger.info("_parse_condition_key condition_key=%s", condition_key)
    for suffix in sorted(operator_map, key=len, reverse=True):
        if condition_key.endswith(suffix):
            variable = condition_key[: -len(suffix)]
            if not variable:
                raise ValueError(
                    f"Invalid security regime condition key {condition_key}"
                )
            return variable, operator_map[suffix]
    return None


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
    raise ValueError(f"Unsupported security regime operator {operator}")


def _evaluate_condition(
    *,
    condition_key: str,
    expected: Any,
    state: EngineState,
    context_flags: dict[str, bool],
    config: dict[str, Any],
) -> SecurityRegimeConditionResult:
    logger.info(
        "_evaluate_condition node=%s condition_key=%s",
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
    parsed = _parse_condition_key(condition_key, operator_map)
    if parsed is None:
        raise ValueError(f"Unknown security regime condition {condition_key}")
    variable, operator = parsed
    if variable not in ALLOWED_LATENT_CONDITION_VARIABLES:
        raise ValueError(
            f"Security regime variable {variable} is not an allowed institutional input"
        )
    if variable not in state.latents:
        raise KeyError(
            f"Security regime variable {variable} missing from {state.node_id}"
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


def _outgoing_rule(
    *,
    current_regime: str,
    transitions: tuple[dict[str, Any], ...],
) -> dict[str, Any] | None:
    logger.info("_outgoing_rule current_regime=%s", current_regime)
    matches = [
        item for item in transitions if item["from"] == current_regime
    ]
    if len(matches) > 1:
        raise ValueError(
            f"Multiple outgoing security regime rules for {current_regime}"
        )
    return matches[0] if matches else None


def _initial_streaks(
    *,
    persistence: SecurityRegimePersistenceState | None,
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
        raise ValueError("Security regime persistence node mismatch")
    if state.day != persistence.last_evaluated_day + 1:
        raise ValueError(
            "Security regime persistence requires consecutive days: "
            f"last={persistence.last_evaluated_day} current={state.day}"
        )
    if persistence.current_regime != state.regimes["security_force_regime"]:
        return {}
    return dict(persistence.streaks)


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
        }
    )
    return f"security-regime-{digest[:24]}"


def evaluate_security_regime(
    *,
    state: EngineState,
    persistence: SecurityRegimePersistenceState | None,
    context_flags: dict[str, bool] | None,
    regime_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> SecurityRegimeEvaluationResult:
    """Evaluate one end-of-day security-regime transition without mutating state."""
    logger.info(
        "evaluate_security_regime node=%s day=%s regime=%s profile=%s",
        state.node_id,
        state.day,
        state.regimes.get("security_force_regime"),
        profile,
    )
    state_hash_before = state.state_hash()
    transitions = _validate_config(regime_config)
    current_regime = str(state.regimes["security_force_regime"])
    if current_regime not in CANONICAL_REGIME_ORDER:
        raise ValueError(f"Unknown security force regime {current_regime}")

    previous_streaks = _initial_streaks(
        persistence=persistence,
        state=state,
    )
    rule = _outgoing_rule(
        current_regime=current_regime,
        transitions=transitions,
    )

    evaluations: list[SecurityRegimeRuleEvaluation] = []
    proposals: list[SecurityRegimeTransitionProposal] = []
    next_streaks: dict[str, int] = {}

    if rule is not None:
        parameter_id = rule["parameter_id"].get(profile)
        if parameter_id is None:
            raise ValueError(
                f"No security regime parameter mapping for profile {profile}"
            )
        parameter_set = _parameter_set(
            parameter_registry,
            profile=profile,
            parameter_id=parameter_id,
        )
        subkey = rule["parameter_subkey"]
        raw_conditions = parameter_set.get(subkey)
        if not isinstance(raw_conditions, dict):
            raise ValueError(
                f"Missing security regime subkey {subkey} in {parameter_id}"
            )
        persistence_required = int(
            raw_conditions.get(
                "persistence_days",
                regime_config["persistence"]["default_persistence_days"],
            )
        )
        if persistence_required < 1:
            raise ValueError("Security regime persistence must be >= 1")

        conditions = {
            str(k): v
            for k, v in raw_conditions.items()
            if k != "persistence_days"
        }
        if not conditions:
            raise ValueError(
                f"Security regime subkey {subkey} has no conditions"
            )
        flags = dict(context_flags or {})
        condition_results = tuple(
            _evaluate_condition(
                condition_key=key,
                expected=value,
                state=state,
                context_flags=flags,
                config=regime_config,
            )
            for key, value in sorted(conditions.items())
        )
        conditions_passed = all(item.passed for item in condition_results)
        streak = (
            previous_streaks.get(rule["rule_id"], 0) + 1
            if conditions_passed
            else 0
        )
        next_streaks[rule["rule_id"]] = streak
        matured = conditions_passed and streak >= persistence_required

        evaluation = SecurityRegimeRuleEvaluation(
            node_id=state.node_id,
            day=state.day,
            from_regime=current_regime,
            to_regime=rule["to"],
            rule_id=rule["rule_id"],
            parameter_id=parameter_id,
            parameter_subkey=subkey,
            condition_results=condition_results,
            conditions_passed=conditions_passed,
            persistence_required=persistence_required,
            persistence_observed=streak,
            matured=matured,
        )
        evaluations.append(evaluation)
        trace.append("security_regime_evaluation", **evaluation.to_dict())

        if matured:
            proposal = SecurityRegimeTransitionProposal(
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
                parameter_subkey=subkey,
                condition_results=condition_results,
                persistence_required=persistence_required,
                persistence_observed=streak,
            )
            proposals.append(proposal)
            trace.append(
                "security_regime_transition_proposal",
                **proposal.to_dict(),
            )

    updated_persistence = SecurityRegimePersistenceState(
        node_id=state.node_id,
        current_regime=current_regime,
        last_evaluated_day=state.day,
        streaks=tuple(sorted(next_streaks.items())),
    )

    if state.state_hash() != state_hash_before:
        raise RuntimeError("Read-only security regime evaluator mutated EngineState")

    return SecurityRegimeEvaluationResult(
        persistence=updated_persistence,
        evaluations=tuple(evaluations),
        proposals=tuple(proposals),
    )
