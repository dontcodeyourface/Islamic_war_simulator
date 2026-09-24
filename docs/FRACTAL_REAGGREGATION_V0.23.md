# Fractal L2 -> L1 Collapse/Reaggregation v0.23

**Status:** implementation milestone  
**Version:** 0.23.0  
**Date:** 2026-09-24  
**Child dynamics:** disabled

## Purpose

v0.23 closes the first adaptive-resolution loop by committing a matured `COLLAPSE` action from L2 regional resolution back to the L1 country representation.

A collapse is not a topology-only toggle. The current L2 sibling states are conservatively reaggregated into the existing L1 parent before regional children are deactivated.

## Ordering

The canonical fractal portion of one day becomes:

```text
fractal refinement evaluation
-> EXPAND materialization, if any
-> child-state initialization / frozen-day advance
-> one-time v0.22 uncertainty for newly created children
-> v0.23 COLLAPSE reaggregation, if any
-> checkpoint
```

A parent cannot EXPAND and COLLAPSE in the same day because the v0.19 evaluator emits at most one action from its current resolution level.

## Physical-stock reaggregation

v0.23 uses the exact v0.21 physical-stock classification.

### Additive integer stocks

The current child values are summed exactly:

- population_total
- working_age_population
- dependent_population
- displaced_people
- reception_population
- available_police_personnel
- prison_population

All-null children aggregate to null. Mixed null/numeric siblings fail closed.

### Intensive stocks

These use the topology initialization weights:

- fuel_stock_days_equivalent
- strategic_food_stock_days

All-null children aggregate to null. Mixed null/numeric siblings fail closed.

### Parent-only national stocks

These remain on the continuously existing L1 parent and are not reconstructed from regional nulls:

- available_military_personnel
- foreign_reserves_usd
- gold_reserves_tonnes

## Latents

Every latent is aggregated with the same L2 initialization weights recorded in topology lineage.

This is compatible with v0.22, which preserves the weighted parent mean when introducing synthetic L2 heterogeneity.

## Regimes

v0.23 requires unanimous sibling consensus for every categorical regime.

If regional regime values differ, collapse fails closed rather than inventing an ordering or majority rule. A future child-dynamics milestone must define an explicit categorical aggregation policy before divergent regimes can collapse.

## Topology and child store

After a successful collapse:

- all active children of the parent are marked `active=false`;
- each receives `de_refinement_day=day`;
- lineage nodes remain in topology for provenance;
- collapsed child EngineState objects are removed from the active child-state store;
- refinement persistence becomes `L1_COUNTRY`;
- expansion and collapse streaks reset to zero.

The L1 CountryGraph is unchanged.

## Atomicity and trace

A collapse emits:

- `fractal_reaggregation_audit`;
- `fractal_collapse_committed`;
- one `fractal_lineage_closed` record per child.

The commit records parent/topology/child-store hashes before and after, the source action, aggregation rule, audit ID and persistence transition.

Any validation or conservation failure aborts the staged day transaction.

## Lifecycle boundary

v0.23 preserves inactive topology lineage after collapse.

Re-expanding the same catalog regions after a later stress recurrence requires an explicit lifecycle policy so historical lineage is not overwritten. That follow-up is implemented by [FRACTAL_LIFECYCLE_V0.24.md](FRACTAL_LIFECYCLE_V0.24.md), which creates immutable runtime generations instead of reopening closed lineage instances.

## Safety boundary

Collapse is a computational-resolution operation, not a political or military outcome.

No tactical targeting, route planning, weapon selection or operational execution is introduced.
