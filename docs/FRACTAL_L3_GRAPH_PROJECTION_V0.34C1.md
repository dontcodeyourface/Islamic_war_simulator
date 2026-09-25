# L3 Graph Projection v0.34c1

**Status:** implementation milestone  
**Version:** 0.34c1  
**Date:** 2026-09-25  
**Depends on:** v0.34b deepest-active runtime authority

## Purpose

This milestone generalizes the deterministic projected strategic graph from active L1/L2 nodes to deepest-active L1/L2/L3 runtime leaves.

The graph continues to obey the same rule used since v0.29:

> no regional or local edge is inferred by cloning a parent-country edge.

When L3 is active, the refined L2 parent remains runtime context but is not emitted as a projected graph node because it no longer owns regionalizable execution.

## Runtime ancestry validation

Every projected subnational node must resolve through the runtime authority tree to one valid L1 country present in the base country graph.

For example:

`ESP::CT::METRO_A -> ESP::CT -> ESP`

If that ancestry is broken, cyclic, or terminates outside the base graph, projection fails closed.

## Projected node set

The projected graph contains only runtime nodes with regionalizable authority:

- coarse L1 nodes;
- unrefined active L2 leaves;
- active L3 leaves beneath refined L2 nodes.

Intermediate parent/context nodes are deliberately omitted.

This preserves one graph node per active execution domain and prevents duplicate spillover evaluation at both L2 and L3.

## Edge classification

Existing v0.29 edge labels remain backward compatible:

- `BASE_L1`
- `INTERNAL_L2`
- `CROSS_PARENT_L2`
- `L2_EXTERNAL`

v0.34c1 adds:

- `INTERNAL_L3`
- `CROSS_PARENT_L3`
- `MULTISCALE_EXTERNAL` when an L3 leaf interacts with a runtime node at another level.

## Channel policy

The configuration concept previously named `any_l2` is generalized to `any_subnational`.

The parser remains backward-compatible with `any_l2` while the canonical configuration now uses `any_subnational`.

For every non-L1 pair:

- alliance remains parent-retained and is never cloned;
- all other strategic channels require an explicit stable-catalog edge;
- missing edge or missing channel remains unresolved/null, never zero.

Stable catalog IDs remain generation-free. Runtime IDs may contain lineage suffixes, but catalog endpoints may not.

## Tests

`tests/test_fractal_graph_projection.py` now covers:

- projection onto two active L3 leaves under a refined L2 parent;
- omission of the L1 and L2 parent/context nodes;
- internal L3 edge classification;
- stable-catalog directional semantics at L3;
- L3-to-L1 external projection;
- parent-retained alliance semantics at L3;
- unresolved L3 edge preservation as null rather than zero;
- existing L2 edge-kind compatibility.

## Deferred within v0.34c

This milestone only generalizes graph projection. The remaining v0.34c increments are:

1. deepest-active regional phase/security regimes;
2. L3 event/spillover execution through the projected graph;
3. recursive parent-child coupling;
4. conservative L3 -> L2 reaggregation;
5. canonical L2 -> L3 -> L2 lifecycle validation.

L4/L5 remain deferred until that lifecycle is complete.

## Safety boundary

L3 graph edges remain strategic aggregate relationships. They do not encode tactical routes, individual facilities, targets, weapon choices, or operational execution.
