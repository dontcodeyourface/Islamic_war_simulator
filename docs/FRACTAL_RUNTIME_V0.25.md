# Fractal Active Runtime Plan v0.25

**Status:** implementation milestone  
**Version:** 0.25.0  
**Date:** 2026-09-25  
**Autonomous child dynamics:** not yet enabled

## Purpose

v0.25 introduces the first executable multiscale runtime-authority contract.

The topology lifecycle through v0.24 can create, initialize, vary, collapse and re-create L2 regional children, but the existing daily engine still executes dynamic modules only against L1 country states.

v0.25 does not yet move those dynamic modules to L2. Instead it establishes the deterministic authority plan that v0.26 will execute and makes incorrect post-refinement L1 execution fail closed.

Canonical rule:

> resolution follows stress, and dynamic authority follows active resolution.

## Authority partition

The v0.25 runtime contract classifies every registered EngineState field exactly once as either:

- **regionalizable** — owned by active L2 children after refinement;
- **national-only** — retained by the L1 parent until an explicit lower-scale allocation contract exists.

The partition is machine-readable in:

```text
config/engine/fractal_runtime_v1.yaml
```

Coverage is validated against the canonical EngineState registry. Missing fields, extra fields or duplicate scale assignments fail closed.

### Physical stocks

National-only in v0.25:

- available military personnel;
- foreign reserves;
- gold reserves.

All other current physical stocks are classified as regionalizable.

### Latents

National-only in v0.25:

- aggregate military-domain effectiveness variables;
- military logistics availability;
- defence industrial capacity;
- replenishment capacity;
- AI defence maturity;
- cyber resilience;
- alliance support.

All other current latents are explicitly classified as regionalizable.

This classification is an authority policy, not an empirical claim that all regional values are already observed.

### Regimes

All four current regimes are classified as regionalizable because the documented future architecture permits sibling regional divergence. Their independent execution and aggregation semantics remain deferred to v0.28/v0.32.

## Runtime plan

For each simulation day the planner produces a deterministic `FractalRuntimePlan`.

### Unrefined parent

```text
L1 country
  owns regionalizable state = true
  owns national-only state  = true
  execution status          = L1_FULL_AUTHORITY
```

### Refined parent

```text
L1 country
  owns regionalizable state = false
  owns national-only state  = true

L2 active children
  own regionalizable state  = true
  own national-only state   = false
```

Inactive historical lineage is excluded from the runtime set.

## Beginning-of-day semantics

The beginning-of-day topology controls the current day's runtime authority.

A refinement committed during day `t` therefore affects dynamic authority from day `t+1`.

This avoids mid-transaction changes to the set of executing state nodes and preserves synchronous deterministic semantics.

## v0.25 fail-closed boundary

Autonomous L2 dynamics are not implemented in this milestone.

Therefore, if a day begins with an already-refined parent and the runtime planner is enabled, v0.25 raises an error instead of silently continuing legacy L1 regional execution.

This is intentional.

It prevents a refined country from being simulated using a state-authority model that contradicts the canonical architecture.

v0.26 must replace this guard by actually executing the active L2 runtime.

## Topology/state integrity

The planner requires exact agreement between:

- active L2 topology nodes;
- child EngineState objects in the child-state store.

It rejects:

- missing active child state;
- unexpected child state;
- inactive historical child state remaining in the active store;
- unknown parent IDs;
- non-L2 active child topology;
- parent metadata mismatch;
- runtime lineage identity mismatch;
- catalog identity mismatch;
- lineage-generation mismatch.

## Replay identity

The beginning-of-day runtime-plan hash participates in day-transaction identity.

The planner also records:

- runtime config hash;
- topology hash;
- child-state-store hash;
- policy ID;
- authority nodes;
- refined parents;
- active L2 nodes;
- inactive historical lineage;
- exact authority partition.

Identical inputs therefore produce an identical plan hash.

## Trace

The daily transaction emits runtime-plan trace records for:

1. `BEGINNING_OF_DAY`;
2. `COMMITTED_NEXT_DAY`.

The committed-next-day plan may contain newly materialized L2 children even though v0.25 does not execute them during the current day.

## Relationship to v0.26

v0.25 establishes **who should execute**.

v0.26 will implement **how active L2 nodes execute**.

The next milestone must:

- replace the refined-parent fail-closed guard with real L2 execution;
- route safe generic dynamic modules through active L2 EngineState;
- prevent L1 duplication of regionalizable dynamics;
- preserve L1 national-only authority;
- maintain transaction-wide rollback and deterministic RNG/trace semantics.

## Scope boundary

v0.25 changes runtime authority planning and replay/trace identity only.

It does not introduce:

- autonomous child dynamics;
- multiscale graph projection;
- L2 event propagation;
- regional phase/regime execution;
- parent-child causal coupling;
- dynamic categorical reaggregation;
- L3/L4/L5 execution;
- tactical targeting;
- route planning;
- weapon selection;
- operational execution.

---

**v0.25 invariant:** once refinement exists at the beginning of a day, the engine must not pretend that full L1 authority is still valid.
