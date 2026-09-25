# Recursive Fractal Topology v0.34a

**Status:** implementation milestone  
**Version:** 0.34a  
**Date:** 2026-09-25  
**Depends on:** canonical v0.33 L1/L2 lifecycle validation

## Purpose

v0.34a begins recursive fractal refinement by generalizing topology materialization and lineage identity from the fixed L1 -> L2 transition to adjacent lower levels.

The first newly enabled recursive transition is:

`L2_REGION -> L3_METRO_OR_LOGISTICS_AREA`

This milestone changes topology and lineage only. It does **not** yet grant autonomous L3 dynamic authority. Runtime authority generalization is v0.34b.

## Canonical level order

The engine now exposes one ordered hierarchy:

`L0_SYSTEM -> L1_COUNTRY -> L2_REGION -> L3_METRO_OR_LOGISTICS_AREA -> L4_ACTOR_NETWORK -> L5_EVENT_CLUSTER`

Materialization is adjacent-only. A refinement action may not skip a level.

v0.34a enables L1 -> L2 and L2 -> L3. L3 -> L4 and L4 -> L5 remain explicitly deferred until their state-authority semantics are implemented.

## Stable catalog identity and runtime identity

Recursive refinement distinguishes two identities:

- **catalog identity:** stable evidence/data identity independent of runtime generation;
- **runtime identity:** immutable execution lineage identity.

For a first-generation L2 parent:

`TST::R1 -> TST::R1::METRO_A`

the L3 runtime ID and catalog ID may coincide.

If the L2 parent itself is a later generation:

`TST::R1::g2`

the same stable L3 catalog child:

`TST::R1::METRO_A`

materializes as:

`TST::R1::g2::METRO_A`

This prevents collision with historical descendants of an earlier parent generation while preserving stable catalog provenance.

If the same active parent later collapses and re-refines its L3 children, the child-local lineage generation advances:

`TST::R1::METRO_A::g2`

The ancestor generation and local child generation are therefore both encoded in runtime identity without contaminating catalog identity.

## Materialization contract

`materialize_next_level()` is the generic adjacent-level materializer.

The existing `materialize_l1_to_l2()` entry point remains as a backward-compatible wrapper. Existing L1/L2 tests and callers therefore retain their public contract while deeper levels use the generalized path.

Every recursive materialization requires:

- an explicit child catalog;
- parent-namespaced stable catalog IDs;
- positive finite initialization weights summing to 1;
- one active runtime parent at the declared `from_level`;
- persistence matured on the same day as the action;
- no already-active sibling generation;
- immutable closed lineage before generation N+1;
- no reserved `::gN` suffix in catalog IDs.

## Scope boundary

v0.34a does not yet:

- execute autonomous L3 endogenous dynamics;
- project the runtime graph through L3;
- resolve L3 events/spillovers;
- reaggregate L3 -> L2;
- enable L4/L5 materialization;
- introduce city-level tactical routes, targets, facilities or military operations.

L3 remains a strategic aggregate domain such as a metropolitan/logistics area, not an operational map.

## Tests

`tests/test_fractal_recursive_materialization.py` covers:

- L2 -> L3 adjacent materialization;
- correct level and parent topology;
- stable catalog IDs;
- runtime IDs beneath a generation-2 L2 parent;
- local generation-2 re-refinement for L3 children;
- fail-closed rejection of level skipping.

Existing `tests/test_fractal_materialization.py` continues to protect backward compatibility of L1 -> L2 behavior.

## Next milestone — v0.34b

Generalize runtime authority from the hard-coded active-L2 model to a deepest-active-descendant model.

The invariant remains:

> resolution follows stress, and dynamic authority follows active resolution.

When an L2 node is refined to L3, the L2 node must cease executing the regionalizable mechanisms delegated to its active L3 children, while retaining the state scopes explicitly owned at L2.
