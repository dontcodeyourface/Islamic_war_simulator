# Security Regime Evaluator v0.16

**Status:** implementation milestone  
**Version:** 0.16.0  
**Date:** 2026-09-23  
**State mutation:** disabled

## Purpose

v0.16 evaluates the ordered security-force regime using the already versioned `SECURITY_REGIMES_*` thresholds.

The evaluator is read-only. It can emit a matured transition proposal but cannot commit `EngineState.regimes.security_force_regime`.

## Ordered escalation

```text
COHESIVE
  -> STRAINED
  -> SELECTIVE_NONCOMPLIANCE
  -> COMMAND_FRACTURE
  -> LOCALIZED_DEFECTION
  -> MULTIPLE_COMMANDS
```

No de-escalation is enabled in v0.16.

## Persistence

`STRAINED` has no explicit persistence in the parameter registry and therefore uses the evaluator default of one day.

The more severe classifications preserve the existing thresholds:

- selective noncompliance: 8 consecutive days;
- command fracture: 13 consecutive days;
- localized defection: 13 consecutive days plus `competing_authority_present`;
- multiple commands: 21 consecutive days plus `multiple_authority_nodes_present`.

A failed condition resets that rule's streak.

## Inputs

Only the existing institutional/security latents referenced by the registry are accepted:

- security-chain cohesion;
- operational fatigue;
- constitutional loyalty;
- command cohesion;
- center-region cohesion;
- state cohesion.

Boolean authority conditions are explicit context flags.

Political, demographic and religious identity are not transition inputs.

## Next milestone

A following PR can add deterministic arbitration/commit and persistence-reset semantics for the matured security-regime proposal, analogous to national phase v0.9.
