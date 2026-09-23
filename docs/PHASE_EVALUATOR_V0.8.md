# Read-Only Phase Evaluator v0.8

**Status:** implementation milestone  
**Version:** 0.8.0  
**Date:** 2026-09-23  
**Phase mutation:** disabled  
**De-escalation:** disabled  
**Active numeric profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.8 implements the national escalation-state classifier as a read-only evaluator.

The evaluator answers:

> Given the committed end-of-day EngineState and the recent persistence history, which phase-transition rules are currently satisfied?

It does **not** change `EngineState.regimes.national_phase`.

This separates:

- classification;
- persistence;
- transition proposal;
- eventual transition commit.

## 2. State machine

Canonical phases remain:

```text
STABLE
TENSION
EMERGENCY
MASS_UNREST
ORGANIZED_POLITICAL_VIOLENCE
INSURGENCY
DUAL_AUTHORITY
CIVIL_WAR
STATE_FRAGMENTATION
```

The phase is still an output classifier of underlying system state.

No phase itself creates tactical behavior.

## 3. Contract

Machine-readable configuration:

`config/engine/phase_evaluator_v1.yaml`

Implementation:

`src/iwsim/phases.py`

The evaluator consumes:

- one EngineState;
- previous PhasePersistenceState, if any;
- explicit context flags;
- phase configuration;
- parameter registry;
- active parameter profile;
- run manifest;
- trace ledger.

It returns:

- updated persistence state;
- every applicable rule evaluation;
- zero or more read-only PhaseTransitionProposal objects.

## 4. Persistence

Phase changes require consecutive days.

For each applicable rule:

```text
conditions pass today
    +
previous consecutive streak
    ↓
new persistence streak
```

If a condition fails:

```text
streak -> 0
```

When the current national phase changes externally:

```text
old phase streaks -> discarded
```

This prevents obsolete evidence from carrying into another phase.

## 5. Consecutive-day integrity

The evaluator requires:

```text
current_day = previous_evaluated_day + 1
```

Therefore:

- evaluating the same day twice fails closed;
- skipping a day fails closed.

A future persistence-recovery mechanism can be introduced explicitly, but v0.8 never guesses missing phase history.

## 6. Parameter source

Thresholds and persistence durations come from the existing authoritative parameter registry.

Examples:

```text
PHASE_STABLE_TENSION_SYN_V1
PHASE_TENSION_EMERGENCY_SYN_V1
PHASE_EMERGENCY_MASS_UNREST_SYN_V1
PHASE_MASS_UNREST_OPV_SYN_V1
PHASE_OPV_INSURGENCY_SYN_V1
PHASE_INSURGENCY_DUAL_AUTHORITY_SYN_V1
PHASE_CIVIL_WAR_SYN_V1
PHASE_FRAGMENTATION_SYN_V1
```

No phase threshold is duplicated as a numeric literal in evaluator code.

The calibrated profile remains unpopulated and fails closed.

## 7. Condition language

Synthetic phase parameters currently use two condition groups:

```text
all
any
```

Latent comparisons use versioned suffix semantics:

```text
_gte -> >=
_lte -> <=
_gt  -> >
_lt  -> <
```

Example:

```text
public_order_stress_gte: 0.50
```

is resolved against:

`EngineState.latents["public_order_stress"]`.

## 8. Context flags

Some structural transitions require facts that should not be inferred from a scalar alone.

v0.8 supports explicit boolean context flags:

```text
competing_authority_present
multiple_authority_nodes_present
```

Example:

`INSURGENCY -> DUAL_AUTHORITY`

cannot mature merely because state cohesion is low.

It also requires:

```text
competing_authority_present = true
```

This prevents the classifier from inventing a rival authority.

## 9. STABLE -> TENSION

Synthetic engineering rule:

- any configured tension condition may be sufficient;
- the condition must persist for the registered number of days.

Candidate inputs include:

- external conflict pressure;
- polarization;
- public-order stress.

No demographic identity variable participates directly.

## 10. TENSION -> EMERGENCY

Requires the configured conjunction, currently including:

- public-order stress;
- reduced government legitimacy;
- persistence.

## 11. EMERGENCY -> MASS_UNREST

Requires combined:

- stronger public-order stress;
- polarization;
- reduced social cohesion;
- persistence.

## 12. MASS_UNREST -> ORGANIZED_POLITICAL_VIOLENCE

Requires material organized armed actor capacity plus severe public-order stress.

Large demonstrations alone are insufficient.

## 13. ORGANIZED_POLITICAL_VIOLENCE -> INSURGENCY

Requires persistent combination of:

- organized armed actor capacity;
- weakened security-chain cohesion;
- some loss of territorial control.

## 14. INSURGENCY outgoing rules

v0.8 deliberately permits multiple simultaneous read-only proposals.

### INSURGENCY -> DUAL_AUTHORITY

Requires:

- territorial-control deterioration;
- weakened center-region cohesion;
- weakened state cohesion;
- explicit competing-authority context;
- persistence.

### INSURGENCY -> CIVIL_WAR

Uses the synthetic civil-war classifier requiring:

- durable organized armed actor capacity;
- security-chain deterioration;
- territorial-control deterioration;
- administrative degradation;
- persistence.

If both mature, v0.8 emits both proposals.

It does **not** decide which transition wins.

That arbitration belongs to a later transition resolver.

## 15. DUAL_AUTHORITY -> CIVIL_WAR

The same civil-war threshold set may be evaluated when the current phase is DUAL_AUTHORITY.

## 16. CIVIL_WAR -> STATE_FRAGMENTATION

Requires sustained deeper simultaneous degradation of:

- territorial control;
- administrative capacity;
- state cohesion;
- command cohesion;
- salary-payment continuity.

## 17. Proposal object

A matured rule emits:

`PhaseTransitionProposal`

with:

```text
proposal_id
node_id
day
from_phase
to_phase
rule_id
parameter_id
condition_mode
condition_results
persistence_required
persistence_observed
apply_status
```

The apply status is always:

```text
PROPOSED_NOT_APPLIED
```

in v0.8.

## 18. Deterministic proposal identity

The proposal ID is derived from:

- replay key;
- node;
- day;
- current phase;
- target phase;
- rule ID.

An exact replay therefore emits the same proposal ID.

## 19. Condition trace

Every individual condition records:

```text
condition_key
source
observed
operator
expected
passed
```

Source is either:

- `latent`; or
- `context_flag`.

Therefore a proposal can be explained without reconstructing condition parsing later.

## 20. Read-only guarantee

The evaluator hashes the EngineState before evaluation and verifies the same hash afterward.

Any accidental mutation raises an error.

Tests also verify this externally.

## 21. Trace records

Every applicable rule emits:

```text
phase_evaluation
```

A matured rule additionally emits:

```text
phase_transition_proposal
```

The evaluator does not emit a committed transition record.

## 22. Persistence state is separate

`PhasePersistenceState` contains:

```text
node_id
current_phase
last_evaluated_day
streaks{rule_id -> consecutive_days}
```

It is intentionally separate from EngineState v1.

This avoids turning classifier bookkeeping into another country latent.

A future transaction integration layer can persist it alongside run state.

## 23. Identity safeguards

Phase conditions must not directly use:

- Muslim population share;
- Christian population share;
- mosque count;
- conservative vote share;
- left-wing vote share.

Identity/demographic variables can affect other modeled mechanisms only through explicitly justified dynamics.

They are not phase-transition shortcuts.

## 24. Calibration status

All active phase thresholds are currently:

```text
synthetic_smoke_v1
```

They exist to test:

- persistence;
- state-machine plumbing;
- replay;
- multi-variable requirements;
- absence of one-variable collapse.

They are not empirical definitions of civil war, insurgency or state fragmentation.

`calibrated_v1` remains fail-closed.

## 25. Tests

v0.8 tests cover:

- STABLE -> TENSION three-day persistence;
- failed-condition streak reset;
- TENSION -> EMERGENCY all-condition semantics;
- simultaneous INSURGENCY outgoing proposals;
- explicit competing-authority requirement;
- phase-change streak reset;
- same-day evaluation rejection;
- skipped-day rejection;
- exact replay;
- read-only state hash;
- calibrated-profile fail-closed;
- absence of identity-propensity condition shortcuts.

## 26. Integration status

The atomic day transaction v0.7 still ends after state commit and checkpoint.

v0.8 phase evaluation is currently a separate read-only layer.

This is intentional.

The transaction should not commit phase changes until proposal arbitration and transition atomicity are defined.

## 27. Next milestone

Recommended v0.9:

> phase-transition arbitration and transaction integration.

It should:

1. evaluate phase proposals after end-of-day state commit;
2. persist PhasePersistenceState for every node;
3. define deterministic arbitration when multiple outgoing proposals mature;
4. stage proposed phase changes;
5. commit phase changes atomically with phase-persistence state;
6. preserve reversible traceability;
7. keep de-escalation disabled until explicit recovery thresholds are defined.

---

**Phase Evaluator v0.8 classifies and proposes; it never decides or mutates.**
