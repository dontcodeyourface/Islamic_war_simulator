# Fractal Multiscale Graph Projection v0.29

**Status:** implementation milestone  
**Version:** 0.29.0  
**Date:** 2026-09-25  
**Depends on:** v0.28 regional phase/security runtime

## Purpose

v0.29 projects the strategic L1 graph onto the active multiscale runtime without inventing regional connectivity.

The projected graph is a separate immutable runtime object. The canonical L1 `CountryGraph` remains unchanged and continues to represent the evidence/parameter-backed country-level graph.

This milestone builds graph identity and provenance only. It does not yet execute regional spillovers or events; that activation is v0.30.

## Active node set

The projected graph contains exactly the runtime nodes that own regionalizable state:

- an unrefined country contributes its L1 country node;
- a refined country contributes its active L2 children;
- the refined L1 parent is excluded from regional graph execution;
- inactive historical lineage is excluded.

Therefore refinement changes the graph execution set in the same next-day boundary used by the runtime authority plan.

## Pair coverage versus connectivity

v0.29 creates deterministic complete pair coverage over the active regional runtime node set.

Complete pair coverage is a data structure invariant, **not** an assertion that every pair is connected.

Every canonical channel on every pair carries both a nullable value and an explicit resolution/projection status. Missing regional evidence remains `value=null`, `status=UNRESOLVED_REGIONAL_PROJECTION`; it is never converted to zero and never inferred from identity.

## L1-to-L1 behavior

When both active endpoints remain L1 countries, channel values and parameter provenance are copied exactly from the canonical `CountryGraph`. Statuses distinguish `BASE_L1_RESOLVED` and `BASE_L1_UNRESOLVED`.

A fully coarse v0.29 projected graph therefore reproduces the existing L1 graph semantics.

## Any-L2 behavior

The projection policy is channel-specific. Geographic proximity, land border, trade dependency, energy dependency, migration link, diaspora link, information link, criminal-network link and extremist-network link require explicit regional catalog evidence and are never copied automatically from a parent edge.

`alliance_link` remains national/institutional. When either endpoint is L2 its projected value is null with `PARENT_RETAINED_NOT_PROJECTED`. The regional graph catalog is forbidden from supplying alliance links; an attempted regional alliance projection fails closed.

## Stable catalog identity versus runtime lineage

Regional graph data uses stable catalog IDs such as `ESP::R1`, while runtime generations may be `ESP::R1::g2`. Projection maps runtime generation nodes to stable catalog endpoints through lineage metadata. Generation suffixes are forbidden inside the graph catalog.

## Regional graph catalog

The canonical scaffold is `config/engine/fractal_region_graph_catalog_v1.yaml`. Symmetric channels use one value; directed channels record `a_to_b` and `b_to_a` independently. Optional source IDs and parameter IDs are retained independently by direction. Numeric values must remain within `[0,1]`; null remains unresolved.

## Edge classes

Projected edges are classified as `BASE_L1`, `INTERNAL_L2`, `L2_EXTERNAL`, or `CROSS_PARENT_L2`. This classification is provenance only and does not alter channel values.

## Deterministic graph identity

`FractalProjectedGraph.graph_hash()` includes day, projection policy ID, runtime-plan hash, base graph hash, regional catalog hash, runtime lineage, all edge/channel values, directional statuses, source/parameter provenance and channel projection policy IDs.

Any regional graph catalog change also participates in day transaction identity.

## Day transaction semantics

When enabled, the transaction builds a `BEGINNING_OF_DAY` projected graph from the beginning runtime plan and a `COMMITTED_NEXT_DAY` graph from the committed next-day runtime plan.

A same-day refinement therefore keeps the L1 parent in the current-day graph and replaces it with active L2 children only in the committed next-day graph. Both graph hashes are recorded in trace and result.

## Validation

Tests cover coarse L1 equivalence, complete pair coverage, refined-parent replacement, generation-aware catalog lookup, directed orientation, internal L2 edges, null preservation, parent-retained alliance semantics, deterministic hashing, catalog sensitivity, next-day graph switching, and transaction-identity sensitivity.

## Deferred to v0.30

v0.29 deliberately does not modify `evaluate_graph_spillovers`. With beginning-of-day active L2, legacy L1 spillover remains fail-closed. v0.30 will consume the projected graph for regional event/spillover execution and preserve mixed-scale queue provenance.

---

Graph projection changes computational connectivity resolution only. It introduces no tactical routes, target selection, weapon selection or operational execution.