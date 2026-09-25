# L3 Regimes and Recursive Coupling v0.34c2

**Status:** implementation milestone  
**Version:** 0.34c2  
**Date:** 2026-09-25  
**Depends on:** v0.34c1 projected graph

## Purpose

v0.34c2 generalizes persistent phase/security execution and parent-child coupling from a flat L1/L2 hierarchy to deepest-active L2/L3 execution leaves.

The invariant remains:

> only nodes with current regionalizable authority execute regional categorical dynamics.

Refined intermediate nodes remain materialized for context, aggregation and lineage but do not evaluate the same phase/security mechanisms in parallel.

## Regional regime persistence

The persistence layer now supports authority handoff across refinement.

On the materialization day:

- the previously active parent may still have prior persistence;
- newly materialized children receive baseline persistence and do not evaluate until the following day.

On the next day:

- deepest-active descendants are evaluated;
- the retired parent-context persistence is pruned;
- the parent EngineState remains in the child store;
- unrelated stale persistence remains a hard failure.

The bootstrap path may temporarily accept extra persistence only when that node is a real ancestor of a currently active execution leaf. Arbitrary inactive/orphan persistence is rejected.

Divergence audits are produced only for currently authoritative nodes plus children initialized for next-day authority. Parent-context states are not reintroduced as independent categorical actors.

## Bottom-up parent-child coupling

Recursive coupling is evaluated from fine to coarse resolution.

For:

`L1 -> L2 R1 -> L3 A/B`

with another unrefined sibling `L2 R2`:

1. L3 A/B are aggregated into the live L2 R1 context state using their local initialization weights.
2. The reconstructed L2 R1 state is then aggregated with L2 R2 using the L2 sibling weights.
3. The resulting aggregate view is published on L1.
4. L1 national-only context is propagated directly to deepest active execution leaves.

This avoids multiplying incompatible local weights directly at L1 and preserves the same conservative aggregation policy used by v0.31/v0.32.

## Day-transaction integration

The daily transaction now builds event/spillover state coverage from:

- unrefined L1 runtime nodes;
- deepest-active child execution leaves.

Refined parent-context child states remain in the child store but are excluded from the projected graph/event/spillover execution set.

This guarantees state-node coverage equality with the projected graph and prevents duplicate event evaluation on both L2 and L3.

## Tests

### Regional regimes

`tests/test_fractal_regional_regime.py` adds:

- persistence handoff from L2 parent authority to L3 leaves;
- pruning of the retired L2 persistence while retaining its EngineState;
- bootstrap acceptance of transitional ancestors;
- rejection of orphan/non-ancestor persistence.

### Coupling

`tests/test_fractal_recursive_coupling.py` validates:

- L3 -> L2 aggregate reconstruction;
- L2 -> L1 aggregate reconstruction in the same pass;
- exact additive stock recovery;
- nested weighted latent aggregation;
- separate audits for the L3/L2 and L2/L1 coupling boundaries;
- direct national-context propagation to deepest active leaves only.

## Compatibility

Flat L1/L2 behavior remains supported. Existing v0.28/v0.31 tests continue to exercise the original hierarchy.

## Deferred to v0.34c3

The remaining recursive lifecycle work is:

- conservative L3 -> L2 collapse/reaggregation;
- lineage closure at L3;
- restoration of L2 authority after collapse;
- actual L3 generation-2 re-refinement;
- canonical L2 -> L3 -> L2 -> L3(g2) end-to-end test.

L4/L5 remain disabled until this lifecycle is complete.

## Safety boundary

This milestone changes computational resolution and aggregate state ownership only. It does not introduce tactical routing, facility targeting, weapon selection or operational execution.
