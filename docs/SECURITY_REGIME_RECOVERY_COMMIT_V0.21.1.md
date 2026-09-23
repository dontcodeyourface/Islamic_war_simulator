# Security Regime Recovery Commit v0.21.1

**Status:** implementation milestone  
**Version:** 0.21.1  
**Date:** 2026-09-23

## Purpose

v0.21.1 commits matured recovery proposals produced by the v0.18 evaluator.

It changes only `EngineState.regimes.security_force_regime` and only one level downward at a time.

## Atomic recovery path

```text
security escalation evaluation
-> escalation commit
-> recovery evaluation
-> matured recovery proposal
-> recovery commit
-> national phase evaluation
-> checkpoint
```

Escalation keeps same-day precedence because v0.18 suppresses recovery on nodes that escalated that day.

## Persistence reset

A committed recovery transition resets both:

- escalation persistence;
- recovery persistence.

Both memories are rewritten to the new regime with empty streaks.

This prevents stale streaks from producing an immediate rebound after a regime change.

## One-level rule

Only the immediate previous canonical regime is eligible:

```text
MULTIPLE_COMMANDS -> LOCALIZED_DEFECTION
LOCALIZED_DEFECTION -> COMMAND_FRACTURE
COMMAND_FRACTURE -> SELECTIVE_NONCOMPLIANCE
SELECTIVE_NONCOMPLIANCE -> STRAINED
STRAINED -> COHESIVE
```

## Fractal relevance

Security-force regime is one of the documented institutional/security refinement triggers.

v0.21.1 closes the hysteretic regime loop before that classifier is consumed by adaptive fractal refinement. This avoids permanently sticky high-stress classifications and reduces refine/collapse oscillation risk.

## Scope

No refinement nodes are created in v0.21.1.

No tactical target selection, route planning, weapon employment or operational instruction is introduced.
