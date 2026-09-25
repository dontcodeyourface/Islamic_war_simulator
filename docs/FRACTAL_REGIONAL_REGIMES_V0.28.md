# Fractal Regional Phase and Security Runtime v0.28

**Status:** implementation milestone  
**Version:** 0.28.0  
**Date:** 2026-09-25  
**Depends on:** v0.27.1 active-L2 day gating fix

## Purpose

v0.28 enables persistent categorical divergence between active L2 siblings for:

- `national_phase`;
- `security_force_regime`.

The implementation reuses the existing L1 phase/security state machines. It does not introduce a second regional rule set or country-specific transition logic.

## Runtime ordering

Regional categorical execution follows the same end-of-day semantics as L1:

```text
day t active L2 state
-> autonomous latent proposals/resolution
-> child clock advances to t+1
-> security-regime escalation evaluation/commit
-> security-regime recovery evaluation/commit
-> phase evaluation/arbitration/commit
-> categorical divergence audit
```

New children materialized during the current transaction do not evaluate phase/security immediately. Their persistence baselines are initialized at day `t+1`, and their first regional evaluation begins on the next day.

## Persistent regional history

`FractalRegionalRegimeStore` stores independent per-child persistence for:

- phase transition streaks;
- security-regime escalation streaks;
- security-regime recovery streaks.

The store is separate from L1 persistence and from `EngineState.metadata`.

A one-time bootstrap with empty streaks is allowed when v0.28 is first introduced to already-active L2 children. Once a child has executed the regional runtime, missing persistence history fails closed instead of silently resetting streaks.

## Refined L1 parent behavior

A refined L1 parent no longer executes regional phase/security classification while its active children own regionalizable state.

For transaction continuity, the parent's L1 phase/security persistence record is carried to the committed day with empty streaks and an explicit trace record:

`fractal_parent_regime_persistence_suppressed`

The parent regime value itself is not mutated by child commits in v0.28. Parent-child aggregation/coupling remains deferred to v0.31.

## Sibling divergence

Active children may legitimately diverge, for example:

```text
ESP::R1 national_phase = TENSION
ESP::R2 national_phase = STABLE

ESP::R1 security_force_regime = STRAINED
ESP::R2 security_force_regime = COHESIVE
```

Sibling equality is not enforced.

## Categorical aggregation contract

v0.28 defines the pre-v0.32 collapse contract:

- `national_phase` and `security_force_regime` are dynamic regional regimes;
- `prison_regime` and `organized_crime_regime` remain static/inherited in this milestone;
- sibling divergence is a valid runtime state;
- collapse is consensus-only until v0.32;
- divergent dynamic categorical state must fail closed rather than being silently discarded.

Each parent receives a `fractal_categorical_divergence_audit` containing the observed sibling values and `collapse_consensus_ready`.

The existing v0.23 reaggregation consensus rule therefore remains conservative and compatible with v0.28.

## Atomicity

Regional phase/security evaluation uses a staged trace and immutable EngineState commits.

A failed regional transition does not publish partial regional trace or mutate the caller child store.

The outer day transaction remains the final commit boundary for:

- L1 state;
- L2 state;
- persistence;
- topology;
- RNG;
- trace.

## Replay identity

Regional runtime inputs participate in day transaction identity:

- regional runtime config hash;
- regional persistence store;
- child context flags;
- phase config hash;
- phase transition config hash;
- security-regime config/transition hashes;
- security-recovery config/transition hashes.

Identical state, persistence, configs and manifest therefore produce identical regional results.

## Validation

v0.28 includes tests for:

- sibling phase divergence;
- sibling security-regime divergence;
- deterministic regional replay;
- one-day delay for newly materialized children;
- persistence bootstrap;
- persistence-history fail-closed behavior;
- regional trace atomicity;
- end-to-end L1 -> L2 -> next-day divergence;
- refined-parent phase/security suppression;
- categorical collapse-readiness audit.

## Deferred

Still deferred:

- multiscale graph projection — v0.29;
- regional event and spillover execution — v0.30;
- parent-child aggregate coupling — v0.31;
- dynamic categorical L2 -> L1 aggregation — v0.32;
- complete lifecycle validation — v0.33.

---

Regional phase/security labels are analytical classifiers. No tactical targeting, route planning, weapon selection or operational execution is introduced.
