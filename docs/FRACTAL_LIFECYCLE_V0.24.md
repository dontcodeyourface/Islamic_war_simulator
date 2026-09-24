# Fractal Topology Lifecycle Generations v0.24

**Status:** implementation milestone  
**Version:** 0.24.0  
**Date:** 2026-09-24

## Purpose

v0.24 makes repeated adaptive-resolution cycles provenance-safe.

After v0.23, a collapsed L2 lineage remains in topology as inactive history. A later high-stress period may legitimately refine the same country again, but reusing or mutating the closed runtime nodes would destroy episode history.

v0.24 separates:

- **catalog identity** — the stable regional identity from the explicit L2 catalog;
- **runtime lineage identity** — one immutable materialization episode.

## Generation rule

For a catalog child such as:

```text
ESP::R1
```

runtime lineage IDs are:

```text
generation 1 -> ESP::R1
generation 2 -> ESP::R1::g2
generation 3 -> ESP::R1::g3
...
```

Generation 1 keeps existing IDs for backwards compatibility.

Every topology node stores:

- `catalog_child_id`;
- `lineage_generation`;
- `lineage_policy_id`.

## Immutable episode history

A closed runtime node is never reactivated or overwritten.

After collapse:

```text
ESP::R1       active=false de_refinement_day=35 generation=1
```

A later refinement creates:

```text
ESP::R1::g2   active=true  generation=2
```

The generation-1 node remains unchanged.

## Sibling generation integrity

All children in one parent materialization share the same generation.

Before allocating a later generation, v0.24 requires:

- no active child lineage for the parent;
- the current catalog child set to match the historical catalog child set;
- every historical sibling to have the same contiguous generation history;
- every inactive historical node to have a `de_refinement_day`;
- no generated runtime ID collision.

A catalog topology change therefore fails closed and requires an explicit topology-migration PR rather than silently remapping historical regions.

## Reserved suffix

Explicit catalog child IDs may not themselves end in `::gN`.

That suffix namespace is reserved for runtime lineage generations.

## Child-state lineage

Newly initialized child EngineState metadata records:

- stable catalog child ID;
- runtime node ID;
- lineage generation;
- lifecycle policy ID.

The child-store continues to contain only active runtime lineage instances.

## Replay

Materialization commit identity includes:

- runtime child IDs;
- stable catalog child IDs;
- lineage generation;
- lifecycle policy ID.

The materialization config hash already participates in day transaction identity.

## Scope

v0.24 changes topology lifecycle identity only.

It does not change stress thresholds, uncertainty distributions, child dynamics, graph activation, tactical targeting, route planning, weapon selection or operational execution.
