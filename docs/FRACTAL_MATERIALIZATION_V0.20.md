# Fractal L2 Materialization v0.20

**Status:** implementation milestone  
**Version:** 0.20.0  
**Date:** 2026-09-23  
**Child EngineState activation:** disabled  
**CountryGraph child activation:** disabled

## Purpose

v0.20 commits a matured v0.19 `EXPAND` action into an explicit L2 topology and immutable lineage records.

It deliberately does not initialize child state variables yet.

The separation is intentional:

- v0.20 answers **which child nodes exist and why**;
- v0.21 will answer **how parent quantities are distributed into them**.

## No invented geography

The materializer requires an explicit regional catalog.

If an EXPAND action matures for a parent without a catalog entry, the transaction fails closed.

Python never creates anonymous or guessed regions.

The repository includes an empty catalog scaffold only. Real regional catalogs should be added through dedicated data/provenance PRs.

## Topology node contract

Every materialized L2 node records:

- child node ID;
- human-readable label;
- parent node ID;
- level;
- creation day;
- source refinement action ID;
- refinement reason;
- source variables;
- initialization weight;
- initialization-weight policy ID;
- inherited-uncertainty policy ID;
- aggregation-rule ID;
- catalog provenance/source ID;
- de-refinement day;
- active flag.

This implements the lineage requirements from the adaptive fractal architecture before child state exists.

## Catalog weights

Each parent's explicit child catalog supplies `initialization_weight` values.

v0.20 validates:

- positive finite weights;
- unique child IDs;
- parent-namespaced child IDs;
- configured child-count bounds;
- sum(weights) = 1.

These weights are metadata only in v0.20.

v0.21 will use them for conservation-aware state initialization.

## Separate topology store

Materialized L2 nodes are stored in `FractalTopologyState`.

They are not inserted into:

- the L1 `CountryGraph`;
- the L1 `states` mapping;
- event candidate passes;
- graph spillover;
- owner resolution.

This prevents partially initialized child nodes from entering dynamics.

## Expansion commit

A commit requires:

- a matured v0.19 `EXPAND` proposal;
- L1 -> L2 transition;
- matching parent persistence;
- persistence requirement already satisfied;
- topology committed through the prior day;
- no active children already present;
- an explicit valid regional catalog.

On success:

- L2 topology nodes are created;
- lineage records are emitted;
- parent fractal persistence advances to `L2_REGION`;
- expansion/collapse streaks reset.

## Collapse

v0.20 does not commit COLLAPSE.

A COLLAPSE action fails closed if passed to this materializer.

Conservation-aware L2 -> L1 reaggregation remains scheduled for v0.23.

## Trace

Adds:

- `fractal_materialization_committed`;
- `fractal_lineage_created`;
- `fractal_topology_retained`.

The materialization commit stores topology hashes before and after plus the region-catalog hash.

## Next steps

- v0.21 — conservation-aware parent -> child state initialization;
- v0.22 — uncertainty widening at finer scales;
- v0.23 — collapse and conservative reaggregation;
- later — L3/L4/L5 using the same topology/lineage interfaces.
