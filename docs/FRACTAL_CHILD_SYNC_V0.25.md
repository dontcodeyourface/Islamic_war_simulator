# Fractal Refined-Child Synchronization v0.25

**Status:** implementation milestone  
**Version:** 0.25.0  
**Date:** 2026-09-24  
**Child dynamics:** disabled  
**RNG:** none

## Purpose

v0.25 keeps active L2 child states consistent with the current L1 parent while regional dynamics remain disabled.

Before v0.25, existing child states only advanced their clock. The L1 parent could continue evolving through events and state dynamics while the L2 store remained frozen. A later v0.23 collapse could therefore reaggregate stale child values back into the parent.

v0.25 closes that consistency gap before any true L2 dynamics are activated.

## Ordering

The fractal tail of the atomic day becomes:

```text
fractal refinement evaluation
-> topology materialization
-> child-state initialization / day advance
-> one-time v0.22 uncertainty for new children
-> v0.25 parent-to-child synchronization
-> v0.23 collapse/reaggregation, if matured
-> checkpoint
```

A collapse therefore consumes synchronized current-day L2 states.

## Physical stocks

The same v0.21 classification remains canonical.

### Additive integer conserved

The current parent total is redistributed by immutable topology initialization weights using deterministic largest remainder:

- population_total
- working_age_population
- dependent_population
- displaced_people
- reception_population
- available_police_personnel
- prison_population

The child sum must equal the parent exactly.

### Intensive

Every active child inherits the current parent value:

- fuel_stock_days_equivalent
- strategic_food_stock_days

### Parent-only

These remain null in L2:

- available_military_personnel
- foreign_reserves_usd
- gold_reserves_tonnes

They continue to live only in the L1 parent.

## Latent synchronization

For each latent variable:

1. compute the current weighted L2 mean;
2. derive each child's deviation from that mean;
3. recenter those deviations around the current parent value;
4. preserve the full deviation shape when bounds allow;
5. otherwise multiply all sibling deviations by one common scale `s <= 1` sufficient to keep every child inside the canonical latent bounds.

Because the deviations are weight-centered:

```text
sum(weight_i * deviation_i) = 0
```

the synchronized children satisfy:

```text
sum(weight_i * child_i) = current_parent_value
```

without random draws.

This preserves v0.22 local heterogeneity as far as the state bounds permit.

## Regimes

While child dynamics remain disabled, every child regime follows the current parent regime exactly.

Divergent regional regime evolution is reserved for the later child-dynamics activation layer.

## Lineage

Synchronization never changes:

- runtime child ID;
- catalog child ID;
- lineage generation;
- refinement action;
- uncertainty provenance.

It appends only:

- last parent-sync day;
- parent state hash at sync;
- sync policy ID.

## Atomicity

The sync layer validates that:

- topology and child-store are committed through the same current day;
- active topology IDs exactly equal child-store IDs;
- every parent has the complete sibling set;
- lineage metadata matches topology;
- weights sum to 1;
- physical and latent conservation audits pass.

Any mismatch aborts the staged day transaction.

## Replay

No RNG stream is consumed.

The sync config hash participates in `transaction_id`.

Trace adds:

- `fractal_child_sync_applied`;
- `fractal_child_sync_audit`.

## Scope

v0.25 is consistency synchronization, not child dynamics.

It does not activate L2 event generation, graph contagion, regional Owner Resolver dynamics, tactical targeting, route planning, weapon selection or operational execution.
