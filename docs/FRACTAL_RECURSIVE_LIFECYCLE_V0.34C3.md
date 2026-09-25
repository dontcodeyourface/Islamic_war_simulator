# Recursive Fractal Lifecycle v0.34c3

**Status:** implementation milestone  
**Version:** 0.34c3  
**Date:** 2026-09-25  
**Depends on:** v0.34c2 deepest-active regimes and recursive coupling

## Purpose

v0.34c3 closes the first complete recursive spatial lifecycle beneath L2.

The engine can now execute:

`L1 -> L2 -> L3 -> collapse L3 -> L2 -> re-refine L3 generation 2`

without replacing the existing L1/L2 APIs and without creating a second engine for L3.

The canonical rule remains:

> resolution follows stress, and dynamic authority follows active resolution.

## Recursive refinement evaluator

The refinement evaluator now distinguishes:

- the base level of the state being evaluated;
- the current active resolution represented by its persistence.

Supported base levels are:

- `L1_COUNTRY`
- `L2_REGION`

Supported adjacent resolution transitions are:

- `L1_COUNTRY <-> L2_REGION`
- `L2_REGION <-> L3_METRO_OR_LOGISTICS_AREA`

A node may move only one adjacent level per action.

L3 is not currently a base level for further refinement. Therefore this milestone does not activate L4.

## Refinement persistence

Refinement persistence is now maintained for:

- every L1 country;
- every active L2 topology node.

L3 nodes do not own refinement persistence yet because L3 -> L4 remains disabled.

When L1 materializes L2 children, a fresh L2 refinement persistence record is created for each new child with zero streaks and the current day. New L2 nodes cannot immediately refine again on their creation day.

When a lineage is collapsed, persistence for inactive descendants is retired at transaction commit.

## Post-coupling evaluation

Refined parents are not evaluated against stale parent state.

Their refinement evaluation is deferred until parent-child coupling has reconstructed the aggregate state for the current day.

This applies to:

- an L1 country currently resolved at L2;
- an L2 region currently resolved at L3.

This also closes a pre-existing gap in the L2 -> L1 lifecycle: country collapse pressure can now mature endogenously after coupling instead of remaining permanently suppressed.

## Same-day recursive materialization

After post-coupling evaluation, a matured L2 -> L3 expansion may be committed during the same day transaction.

The sequence is:

1. materialize topology;
2. augment the already-current child-state store with new L3 states;
3. conserve additive stocks exactly;
4. optionally apply local uncertainty to the newly created L3 sibling set;
5. rebuild runtime authority for the committed next-day state.

Existing L2 states are retained without a second day increment during same-day augmentation.

## Recursive uncertainty

One-time spatial uncertainty is generalized from L2-only children to both L2 and L3 children.

For L3 initialization, the live L2 state in the child store is the parent reference.

The existing guarantees remain:

- physical stocks immutable during uncertainty;
- regimes immutable;
- parent weighted latent mean preserved;
- deterministic RNG stream names by parent/group/day;
- no inferred local fact is created from uncertainty.

## Conservative L3 -> L2 collapse

`collapse_l3_to_l2()` reuses the same conservative aggregation contract as L2 -> L1.

On commit:

- all active direct L3 siblings must be present;
- additive integer stocks are summed exactly;
- intensive stocks and latents use initialization-weighted aggregation;
- categorical regimes require unanimous sibling consensus;
- divergence fails closed;
- active L3 topology nodes become immutable historical lineage;
- the L2 parent remains active;
- the L2 parent EngineState in the child store is replaced by the live reaggregated state;
- L2 runtime authority is restored.

The existing `collapse_l2_to_l1()` wrapper remains unchanged for callers.

## Nested collapse ordering

A country-level L2 -> L1 collapse and a child L3 -> L2 resolution action must not both commit across the same branch on the same day.

If a descendant L2 node has a same-day resolution action, the ancestor L1 collapse proposal is deferred. This prevents collapsing two hierarchy levels atomically with partially updated lineage.

## Regime persistence reconciliation

A topology change may alter the deepest-active execution set after regional regimes have already run for the day.

At commit, regional regime persistence is reconciled to the final runtime plan:

- retained active leaves keep their current persistence;
- newly materialized leaves receive same-day baseline persistence;
- retired parent/context persistence is removed;
- missing active child state is a hard failure.

The returned day result is therefore directly reusable as the next day's input.

## Transactional E2E

`tests/test_fractal_regional_day.py::test_v034c3_day_transaction_l2_l3_collapse_rerefine_generation_two` covers the full committed-day path:

1. L1 ESP materializes canonical L2;
2. an L2 node reaches expansion persistence;
3. the same day transaction materializes explicit synthetic-test L3 children;
4. runtime authority moves from L2 to L3;
5. L3 collapse persistence matures;
6. conservative L3 -> L2 collapse restores L2 authority;
7. historical L3 generation 1 remains immutable;
8. later L2 re-expansion creates real L3 generation 2 runtime IDs;
9. catalog IDs remain stable;
10. generation-1 lineage is unchanged.

Core reaggregation tests separately validate live-state conservation and fail-closed categorical divergence.

## Production L3 catalog requirement

The production canonical region catalog currently defines L1 -> L2 geography only.

v0.34c3 intentionally does **not** invent production L3 metro/logistics partitions.

Recursive materialization requires an explicit child catalog entry for each L2 parent. Tests use a synthetic explicit L3 catalog solely to validate engine behavior.

The next data milestone must therefore define the canonical L3 catalog/provenance policy before production scenarios are allowed to activate L3.

## Deferred

Before enabling L4/L5:

- define evidence-backed or explicitly scenario-defined L3 catalogs;
- define corresponding L3 graph channels;
- run the canonical recursive lifecycle against real configured L3 data;
- validate deterministic replay and conservation under Monte Carlo execution.

## Safety boundary

L3 remains a strategic aggregate resolution domain. It does not encode tactical routes, individual facilities, targets, weapon selection, or operational execution.
