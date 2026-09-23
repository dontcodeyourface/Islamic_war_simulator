# Security Regime Commit v0.17

**Status:** implementation milestone  
**Version:** 0.17.0  
**Date:** 2026-09-23

## Purpose

v0.17 turns a matured read-only security-regime proposal from v0.16 into an atomic state commit.

The commit changes exactly one field:

`EngineState.regimes.security_force_regime`

It never mutates latents, physical stocks or the caller's original state.

## Commit eligibility

A proposal is eligible only when:

- it is `PROPOSED_NOT_APPLIED`;
- node and day match the evaluated state;
- `from_regime` matches current state;
- observed persistence is at least required persistence;
- target is exactly the next entry in the canonical security-regime order.

Because v0.16 permits one outgoing rule per regime, v0.17 rejects multiple matured proposals rather than arbitrating them.

## Persistence

After a committed transition:

- current regime becomes the target regime;
- last evaluated day remains the committed day;
- streaks reset to empty.

When no proposal matures, the evaluator's persistence is retained unchanged.

## Atomic placement

The daily order becomes:

```text
beginning state
  -> state-delta proposal layers
  -> one Owner Resolver
  -> clock advance
  -> security regime evaluation
  -> security regime commit/reset
  -> national phase evaluation/commit
  -> checkpoint
```

A security-regime commit is therefore based on resolved end-of-day latents.

## Traceability

Each commit records:

- proposal ID;
- node/day;
- from/to regime;
- evaluator transition rule;
- threshold parameter ID/subkey;
- state hash before/after;
- deterministic commit ID.

Daily checkpoints include security-regime commit IDs.

## Scope boundary

v0.17 remains escalation-only. De-escalation/hysteresis requires a later explicit contract.

The regime is a classifier, not an operational instruction. No tactical target selection, weapon selection, route planning or operational execution is introduced.
