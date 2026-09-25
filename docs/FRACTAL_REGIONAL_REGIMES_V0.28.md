# Fractal Regional Phase and Security Runtime v0.28

**Status:** implementation milestone  
**Version:** 0.28.0  
**Date:** 2026-09-25  
**Depends on:** v0.27.1 consecutive active-L2 lifecycle gating fix

## Purpose

v0.28 makes active L2 regions persistent categorical simulation domains.

The engine now allows sibling regions under the same L1 parent to evolve independently in:

- `regimes.national_phase`;
- `regimes.security_force_regime`.

This closes the next canonical gap after autonomous L2 latent dynamics and multiscale Owner Resolver provenance.

The architectural rule remains:

> resolution follows stress, and dynamic authority follows active resolution.

## Reused state machines

v0.28 does not create regional-only transition equations.

Active L2 children reuse the existing generic L1 implementations:

- `evaluate_security_regime()`;
- `commit_security_regime_transition()`;
- `evaluate_security_regime_recovery()`;
- `commit_security_regime_recovery()`;
- `evaluate_national_phase()`;
- `arbitrate_phase_proposals()`;
- `commit_phase_transition()`.

Scale changes execution ownership and persistence scope, not the causal equations.

## Execution order

For a child active at the beginning of day `t`:

```text
child state at t
-> autonomous L2 latent dynamics
-> Owner Resolver
-> child clock advances once to t+1
-> security-regime escalation evaluation/commit
-> security-regime recovery evaluation/commit
-> phase evaluation/arbitration/commit
-> categorical divergence audit
-> committed L2 state at t+1
```

Children materialized during the current transaction do not evaluate phase or security on the same day. They receive baseline persistence at the committed day and begin categorical evaluation on the next day.

## Regional persistence store

v0.28 introduces `FractalRegionalRegimeStore`.

It stores independent typed persistence for each active child:

- `PhasePersistenceState`;
- `SecurityRegimePersistenceState`;
- `SecurityRegimeRecoveryPersistenceState`.

The store is separate from L1 persistence.

This prevents:

- parent streaks from leaking into children;
- sibling streaks from being shared;
- regional divergence from being hidden in `EngineState.metadata`;
- loss of replay identity.

The persistence store participates in day transaction identity.

## Parent suppression

When an L1 parent is refined, L1 categorical evaluation is suppressed for that parent.

Unrefined L1 nodes continue through the existing phase/security paths.

The refined parent receives zero-streak placeholder persistence at the committed day so the L1 replay contract remains structurally complete while the parent is not the regional categorical authority.

No L1 phase or security transition is generated from stale aggregate regional state while L2 is active.

## Sibling divergence

Different child state can now generate different categorical outcomes.

Valid runtime examples include:

```text
ESP::R1 national_phase = TENSION
ESP::R2 national_phase = STABLE
```

and:

```text
ESP::R1 security_force_regime = STRAINED
ESP::R2 security_force_regime = COHESIVE
```

Sibling equality is not an invariant.

Divergence is a valid simulation state and is explicitly audited.

## Categorical divergence audit

Each active sibling set produces `FractalCategoricalDivergenceAudit`.

The audit records:

- parent node;
- child IDs;
- child national phases;
- child security-force regimes;
- prison regimes;
- organized-crime regimes;
- whether phase diverged;
- whether security regime diverged;
- whether static regimes remain consistent;
- whether the sibling set is currently consensus-ready for collapse;
- categorical aggregation policy ID.

## Collapse semantics

v0.28 defines, but does not replace, the categorical collapse rule.

Until v0.32:

- dynamic categorical state uses unanimous sibling consensus;
- divergence is allowed during runtime;
- collapse with unresolved categorical divergence must fail closed;
- no majority vote, max-rank selection or silent parent overwrite is allowed.

Policy ID:

`FRACTAL_CATEGORICAL_AGGREGATION_V1`

The existing reaggregation path already requires sibling regime consensus, so v0.28 preserves that conservative behavior.

## Consecutive-day lifecycle

v0.28 incorporates the v0.27.1 gating correction.

When a day begins with active L2:

- coarse L1 parents may still be evaluated for new refinement;
- already refined parents are excluded from L1 refinement/collapse evaluation;
- their refinement streaks are reset while explicit parent-child coupling is deferred;
- topology and child state continue to advance normally.

This removes the previous second-day circular gate.

## Transaction atomicity

Regional phase/security evaluation runs inside the staged day transaction.

Partial regional trace or persistence is not published if the transaction fails.

The output includes:

- updated child store;
- updated regional persistence store;
- phase/security/recovery evaluations;
- commits;
- divergence audits.

## Determinism and replay

Transaction identity includes:

- regional runtime configuration hash;
- regional persistence state;
- regional context flags;
- phase/security configuration hashes;
- existing multiscale runtime-plan identity.

Identical inputs therefore produce identical regional transitions, persistence and audits.

## Validation

v0.28 tests cover:

- direct regional sibling phase divergence;
- direct regional security-regime divergence;
- deterministic regional runtime replay;
- new-child next-day activation;
- persistence bootstrap;
- trace atomicity on failure;
- consecutive active-L2 day traversal;
- full two-day `run_day_transaction` path:
  `L1 -> L2 materialization -> persistence bootstrap -> autonomous next day -> R1/R2 categorical divergence`.

## Deferred

Still deferred:

- v0.29 multiscale graph projection;
- v0.30 regional event and spillover execution;
- v0.31 parent-child aggregate coupling;
- v0.32 dynamic L2 -> L1 reaggregation with evolved children;
- v0.33 full lifecycle validation;
- v0.34+ recursive L3/L4/L5 runtime.

## Safety and abstraction boundary

Phase and security regimes remain aggregate classifiers.

v0.28 introduces no:

- tactical target selection;
- route planning;
- weapon selection;
- attack-method optimization;
- operational execution;
- direct transition rules based on civilian political, religious or demographic identity.

---

**v0.28 definition of done:** active sibling L2 regions can persist and transition independently through the same generic phase/security state machines used at L1, while refined L1 parents are prevented from executing duplicate categorical dynamics.
