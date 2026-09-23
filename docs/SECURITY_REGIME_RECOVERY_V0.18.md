# Security Regime Recovery Evaluator v0.18

**Status:** implementation milestone  
**Version:** 0.18.0  
**Date:** 2026-09-23  
**State mutation:** disabled

## Purpose

v0.18 adds read-only de-escalation evaluation for the committed security-force regime.

Recovery is deliberately separated from v0.17 escalation commit. A matured recovery condition produces evidence only; it does not mutate the regime.

## One-step recovery

```text
MULTIPLE_COMMANDS
  -> LOCALIZED_DEFECTION
  -> COMMAND_FRACTURE
  -> SELECTIVE_NONCOMPLIANCE
  -> STRAINED
  -> COHESIVE
```

Only one level may be proposed at a time.

## Hysteresis

Recovery thresholds are deliberately separated from escalation thresholds.

Examples:

- COHESIVE recovery requires security-chain and command cohesion above the escalation boundary and fatigue below the STRAINED boundary;
- recovery from severe regimes requires restored command/state cohesion and explicit disappearance of competing/multiple-authority context where relevant;
- recovery persistence is longer than a one-day fluctuation.

All v0.18 thresholds are synthetic engineering parameters under `SECURITY_REGIME_RECOVERY_SYN_V1`, not calibrated causal estimates.

## Same-day precedence

Escalation has precedence.

If a node commits an upward security-regime transition on day T, recovery evaluation for that node on day T is suppressed and its recovery streak resets.

This prevents contradictory up/down proposals in the same atomic day.

## Persistence

Recovery streak state is independent from escalation persistence.

After day zero, enabling recovery evaluation requires a persistence object for every node. Missing or skipped history fails closed.

## Scope

v0.18 is read-only. The next step may commit matured recovery proposals under a separate atomic transition contract.

The regime remains a classifier, not an operational instruction.
