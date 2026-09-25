# Recursive Fractal Runtime v0.34b

**Status:** implementation milestone  
**Version:** 0.34b  
**Date:** 2026-09-25  
**Depends on:** v0.34a recursive topology

## Purpose

v0.34b generalizes dynamic authority from a fixed L1/L2 model to the deepest active spatial descendants currently supported by the engine.

The canonical invariant remains:

> resolution follows stress, and dynamic authority follows active resolution.

If an active L2 node is refined into L3 children, that L2 node remains materialized as a parent/context state but no longer executes the same delegated regionalizable dynamics in parallel.

## Deepest-active authority

For:

`L1 country -> L2 region -> L3 metro/logistics children`

runtime authority is:

- L1: national-only authority;
- refined L2: parent/context state, no delegated regionalizable execution;
- active L3 leaves: regionalizable dynamic authority.

The legacy `active_regional_node_ids` field now represents the active spatial execution leaves. At v0.34b those leaves may be L2 or L3.

## Child-state initialization

The child-state initializer now supports recursive parentage.

A newly materialized L3 child is initialized from the live L2 parent state after that parent state has been advanced to the current topology day. Existing additive conservation rules remain unchanged:

- additive integer stocks are split exactly;
- intensive stocks inherit according to the existing policy;
- parent-only L1 stocks remain null in descendants;
- latents/regimes inherit the live parent state;
- lineage metadata records the actual child level and runtime/catalog identity.

The active child-state store may therefore contain both a refined parent context state and its active descendants.

## Runtime plan

`build_fractal_runtime_plan()` now:

- validates parent references across L1 and topology nodes;
- rejects active descendants whose topology parent is inactive;
- requires exact EngineState coverage for every active topology node;
- identifies active leaves deterministically;
- gives regionalizable authority only to those leaves;
- keeps refined intermediate nodes as `PARENT_CONTEXT`;
- supports autonomous execution on L2 and L3 leaves;
- fails closed for unsupported deeper dynamic levels.

Execution statuses:

- `L1_FULL_AUTHORITY`
- `L1_NATIONAL_ONLY_AUTHORITY`
- `L2_REGIONAL_AUTHORITY_ACTIVE_V0_29`
- `L3_REGIONAL_AUTHORITY_ACTIVE_V0_34B`
- `FRACTAL_PARENT_CONTEXT_NO_DUPLICATE_EXECUTION`
- `INACTIVE_HISTORY_EXCLUDED`

## Autonomous dynamics

The existing `execute_autonomous_l2_dynamics()` function name is retained for compatibility, but its execution set is now the runtime plan's deepest active children.

Only leaf states are passed to proposal generation and owner resolution. Refined parent-context states remain in the child store unchanged.

This prevents duplicate causal execution while preserving the state required for aggregation, traceability and later collapse.

## Tests

`tests/test_fractal_recursive_runtime.py` validates:

- L3 initialization from a live L2 state;
- exact additive conservation across the L2 -> L3 split;
- L2 parent retention in the child-state store;
- L2 parent demotion to `PARENT_CONTEXT`;
- L3 leaf acquisition of regionalizable authority;
- autonomous execution only on L3 leaves;
- unchanged refined L2 context state during leaf execution.

Existing L2 runtime tests remain authoritative for backward compatibility.

## Deferred to v0.34c

v0.34b does not yet generalize every L2 subsystem to L3.

The next increment must extend:

- projected graph node/edge classification to L3;
- regional phase/security persistence to deepest active leaves;
- event/spillover execution at L3;
- parent-child coupling through L2/L3;
- conservative L3 -> L2 reaggregation;
- end-to-end L2 -> L3 -> L2 lifecycle validation.

L4 actor networks and L5 event clusters remain deferred until L3 completes this lifecycle.

## Safety and abstraction boundary

L3 is a strategic aggregate metro/logistics domain. It does not represent individual tactical routes, facilities, targets, weapon choices or operational execution.
