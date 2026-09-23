from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .manifest import RunManifest
from .state import EngineState
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PhaseConditionResult:
    condition_key: str
    source: str
    observed: float | bool
    operator: str
    expected: float | bool
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseConditionResult.to_dict condition_key=%s passed=%s",
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
class PhaseTransitionProposal:
    proposal_id: str
    node_id: str
    day: int
    from_phase: str
    to_phase: str
    rule_id: str
    parameter_id: str
    condition_mode: str
    condition_results: tuple[PhaseConditionResult, ...]
    persistence_required: int
    persistence_observed: int
    apply_status: str = "PROPOSED_NOT_APPLIED"

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseTransitionProposal.to_dict proposal_id=%s",
            self.proposal_id,
        )
        return {
            "proposal_id": self.proposal_id,
            "node_id": self.node_id,
            "day": self.day,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "rule_id": self.rule_id,
            "parameter_id": self.parameter_id,
            "condition_mode": self.condition_mode,
            "condition_results": [
                item.to_dict() for item in self.condition_results
            ],
            "persistence_required": self.persistence_required,
            "persistence_observed": self.persistence_observed,
            "apply_status": self.apply_status,
        }


@dataclass(frozen=True)
class PhaseRuleEvaluation:
    node_id: str
    day: int
    from_phase: str
    to_phase: str
    rule_id: str
    parameter_id: str
    condition_mode: str
    condition_results: tuple[PhaseConditionResult, ...]
    conditions_passed: bool
    persistence_required: int
    persistence_observed: int
    matured: bool

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseRuleEvaluation.to_dict rule_id=%s node_id=%s",
            self.rule_id,
            self.node_id,
        )
        return {
            "node_id": self.node_id,
            "day": self.day,
            "from_phase": self.from_phase,
            "to_phase": self.to_phase,
            "rule_id": self.rule_id,
            "parameter_id": self.parameter_id,
            "condition_mode": self.condition_mode,
            "condition_results": [
                item.to_dict() for item in self.condition_results
            ],
            "conditions_passed": self.conditions_passed,
            "persistence_required": self.persistence_required,
            "persistence_observed": self.persistence_observed,
            "matured": self.matured,
        }


@dataclass(frozen=True)
class PhasePersistenceState:
    node_id: str
    current_phase: str
    last_evaluated_day: int
    streaks: tuple[tuple[str, int], ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhasePersistenceState.to_dict node_id=%s day=%s",
            self.node_id,
            self.last_evaluated_day,
        )
        return {
            "node_id": self.node_id,
            "current_phase": self.current_phase,
            "last_evaluated_day": self.last_evaluated_day,
            "streaks": dict(self.streaks),
        }


@dataclass(frozen=True)
class PhaseEvaluationResult:
    persistence: PhasePersistenceState
    evaluations: tuple[PhaseRuleEvaluation, ...]
    proposals: tuple[PhaseTransitionProposal, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "PhaseEvaluationResult.to_dict node_id=%s evaluations=%s proposals=%s",
            self.persistence.node_id,
            len(self.evaluations),
            len(self.proposals),
        )
        return {
            "persistence": self.persistence.to_dict(),
            "evaluations": [item.to_dict() for item in self.evaluations],
            "proposals": [item.to_dict() for item in self.proposals],
        }


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
            f"Missing phase parameter {parameter_id} for profile {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Phase parameter {parameter_id} must contain a mapping value"
        )
    return value


def _outgoing_rules(
    *,
    phase: str,
    phase_config: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    logger.info("_outgoing_rules phase=%s", phase)
    return tuple(
        rule
        for rule in phase_config["transitions"]
        if phase in tuple(str(item) for item in rule["from"])
    )


def _condition_group(
    parameter_value: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    logger.info("_condition_group keys=%s", sorted(parameter_value))
    present = [
        key for key in ("all", "any")
        if key in parameter_value
    ]
    if len(present) != 1:
        raise ValueError(
            f"Phase parameter must define exactly one condition group: {present}"
        )
    mode = present[0]
    conditions = parameter_value[mode]
    if not isinstance(conditions, dict) or not conditions:
        raise ValueError("Phase condition group must be a non-empty mapping")
    return mode, conditions


def _parse_latent_condition(
    condition_key: str,
    operator_map: dict[str, str],
) -> tuple[str, str] | None:
    logger.info("_parse_latent_condition condition_key=%s", condition_key)
    suffixes = sorted(operator_map, key=len, reverse=True)
    for suffix in suffixes:
        if condition_key.endswith(suffix):
            variable = condition_key[: -len(suffix)]
            if not variable:
                raise ValueError(f"Invalid phase condition key {condition_key}")
            return variable, str(operator_map[suffix])
    return None


def _compare(
    *,
    observed: float,
    operator: str,
    expected: float,
) -> bool:
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
    raise ValueError(f"Unsupported phase comparison operator {operator}")


def _evaluate_condition(
    *,
    condition_key: str,
    expected: Any,
    state: EngineState,
    context_flags: dict[str, bool],
    phase_config: dict[str, Any],
) -> PhaseConditionResult:
    logger.info(
        "_evaluate_condition node_id=%s condition_key=%s",
        state.node_id,
        condition_key,
    )
    boolean_flags = set(
        str(item)
        for item in phase_config["condition_language"]["boolean_context_flags"]
    )
    if condition_key in boolean_flags:
        observed = bool(context_flags.get(condition_key, False))
        expected_bool = bool(expected)
        return PhaseConditionResult(
            condition_key=condition_key,
            source="context_flag",
            observed=observed,
            operator="==",
            expected=expected_bool,
            passed=observed == expected_bool,
        )

    parsed = _parse_latent_condition(
        condition_key,
        {
            str(key): str(value)
            for key, value in phase_config["condition_language"][
                "latent_suffix_operators"
            ].items()
        },
    )
    if parsed is None:
        raise ValueError(f"Unknown phase condition key {condition_key}")
    variable, operator = parsed
    if variable not in state.latents:
        raise KeyError(
            f"Phase condition variable {variable} missing from {state.node_id}"
        )
    observed_value = float(state.latents[variable])
    expected_value = float(expected)
    return PhaseConditionResult(
        condition_key=condition_key,
        source="latent",
        observed=observed_value,
        operator=operator,
        expected=expected_value,
        passed=_compare(
            observed=observed_value,
            operator=operator,
            expected=expected_value,
        ),
    )


def _proposal_id(
    *,
    manifest: RunManifest,
    state: EngineState,
    rule_id: str,
    to_phase: str,
) -> str:
    logger.info(
        "_proposal_id node_id=%s day=%s rule_id=%s",
        state.node_id,
        state.day,
        rule_id,
    )
    digest = canonical_hash(
        {
            "replay_key": manifest.replay_key,
            "node_id": state.node_id,
            "day": state.day,
            "from_phase": state.regimes["national_phase"],
            "to_phase": to_phase,
            "rule_id": rule_id,
        }
    )
    return f"phase-{digest[:24]}"


def _initial_streaks(
    *,
    persistence: PhasePersistenceState | None,
    state: EngineState,
) -> dict[str, int]:
    logger.info(
        "_initial_streaks node_id=%s day=%s has_persistence=%s",
        state.node_id,
        state.day,
        persistence is not None,
    )
    if persistence is None:
        return {}

    if persistence.node_id != state.node_id:
        raise ValueError(
            f"Persistence node {persistence.node_id} does not match {state.node_id}"
        )
    if state.day != persistence.last_evaluated_day + 1:
        raise ValueError(
            f"Phase persistence requires consecutive days: "
            f"last={persistence.last_evaluated_day} current={state.day}"
        )
    if persistence.current_phase != state.regimes["national_phase"]:
        return {}
    return dict(persistence.streaks)


def evaluate_national_phase(
    *,
    state: EngineState,
    persistence: PhasePersistenceState | None,
    context_flags: dict[str, bool] | None,
    phase_config: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    manifest: RunManifest,
    trace: TraceLedger,
) -> PhaseEvaluationResult:
    """Evaluate outgoing national-phase transitions without mutating EngineState."""
    logger.info(
        "evaluate_national_phase node_id=%s day=%s phase=%s profile=%s",
        state.node_id,
        state.day,
        state.regimes.get("national_phase"),
        profile,
    )
    state_hash_before = state.state_hash()
    phase = str(state.regimes["national_phase"])
    flags = dict(context_flags or {})
    previous_streaks = _initial_streaks(
        persistence=persistence,
        state=state,
    )

    evaluations: list[PhaseRuleEvaluation] = []
    proposals: list[PhaseTransitionProposal] = []
    next_streaks: dict[str, int] = {}

    for rule in _outgoing_rules(phase=phase, phase_config=phase_config):
        rule_id = str(rule["rule_id"])
        to_phase = str(rule["to"])
        parameter_id = str(rule["parameter_id"][profile])
        parameter_value = _parameter_value(
            parameter_registry,
            profile=profile,
            parameter_id=parameter_id,
        )
        persistence_required = int(parameter_value["persistence_days"])
        if persistence_required < 1:
            raise ValueError(
                f"Invalid persistence_days for {parameter_id}: "
                f"{persistence_required}"
            )

        condition_mode, conditions = _condition_group(parameter_value)
        condition_results = tuple(
            _evaluate_condition(
                condition_key=str(condition_key),
                expected=expected,
                state=state,
                context_flags=flags,
                phase_config=phase_config,
            )
            for condition_key, expected in sorted(conditions.items())
        )
        if condition_mode == "all":
            conditions_passed = all(item.passed for item in condition_results)
        elif condition_mode == "any":
            conditions_passed = any(item.passed for item in condition_results)
        else:
            raise ValueError(f"Unsupported condition mode {condition_mode}")

        streak = (
            previous_streaks.get(rule_id, 0) + 1
            if conditions_passed
            else 0
        )
        next_streaks[rule_id] = streak
        matured = conditions_passed and streak >= persistence_required

        evaluation = PhaseRuleEvaluation(
            node_id=state.node_id,
            day=state.day,
            from_phase=phase,
            to_phase=to_phase,
            rule_id=rule_id,
            parameter_id=parameter_id,
            condition_mode=condition_mode,
            condition_results=condition_results,
            conditions_passed=conditions_passed,
            persistence_required=persistence_required,
            persistence_observed=streak,
            matured=matured,
        )
        evaluations.append(evaluation)
        trace.append(
            "phase_evaluation",
            **evaluation.to_dict(),
        )

        if matured:
            proposal = PhaseTransitionProposal(
                proposal_id=_proposal_id(
                    manifest=manifest,
                    state=state,
                    rule_id=rule_id,
                    to_phase=to_phase,
                ),
                node_id=state.node_id,
                day=state.day,
                from_phase=phase,
                to_phase=to_phase,
                rule_id=rule_id,
                parameter_id=parameter_id,
                condition_mode=condition_mode,
                condition_results=condition_results,
                persistence_required=persistence_required,
                persistence_observed=streak,
            )
            proposals.append(proposal)
            trace.append(
                "phase_transition_proposal",
                **proposal.to_dict(),
            )

    updated_persistence = PhasePersistenceState(
        node_id=state.node_id,
        current_phase=phase,
        last_evaluated_day=state.day,
        streaks=tuple(sorted(next_streaks.items())),
    )

    if state.state_hash() != state_hash_before:
        raise RuntimeError("Read-only phase evaluator mutated EngineState")

    return PhaseEvaluationResult(
        persistence=updated_persistence,
        evaluations=tuple(evaluations),
        proposals=tuple(proposals),
    )
