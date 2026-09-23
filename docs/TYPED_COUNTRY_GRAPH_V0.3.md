# Typed Country Graph v0.3

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Package version:** 0.3.0  
**Behavioral spillover:** disabled

## 1. Purpose

v0.3 introduces the first executable country graph.

The graph is not yet a contagion engine. It provides the static, typed and reproducible topology that future spillover equations will consume.

Current nodes:

- Spain (ESP)
- Morocco (MAR)
- France (FRA)
- Germany (DEU)
- United Kingdom (GBR)

The graph contains all 10 unordered country pairs.

## 2. Data separation

Country snapshots, the graph configuration and the canonical distance matrix remain separate artifacts.

Country snapshots provide country identity and formal memberships.

The distance matrix provides capital-to-capital distance and direct-land-border status.

The graph config declares which snapshots participate, the explicit distance-matrix alias for each node, channel directionality, and whether a channel is resolved or unresolved.

No country-specific graph equation exists in Python.

## 3. Explicit distance-matrix aliases

Snapshot display names and distance-matrix identifiers are not assumed to be identical.

Example:

~~~text
snapshot country_name:
United Kingdom

distance matrix:
United_Kingdom
~~~

The graph config therefore declares an explicit distance_matrix_name for GBR.

This prevents implicit string transformations and makes topology traceable.

## 4. Symmetric channels

v0.3 treats three channels as symmetric.

### geographic_proximity

~~~text
edge = exp(-distance_km / lambda_km)
~~~

Synthetic parameter: EDGE_GEO_SCALE_SYN_V1.

Current engineering value:

~~~text
lambda = 1000 km
~~~

This is not an empirical conflict-propagation coefficient.

### land_border

Binary structural channel:

~~~text
direct border -> 1
no direct border -> 0
~~~

Spain-Morocco is treated as having a direct land border because of Ceuta and Melilla, consistently with the canonical distance dataset.

### alliance_link

v0.3 uses only shared formal institutional membership.

Synthetic score map:

~~~text
shared NATO membership -> 1.00
shared EU membership   -> 0.75
no shared formal membership -> 0.00
~~~

If multiple formal memberships are shared, the maximum topological score is used.

This scalar is only a coarse graph-connectivity feature. It does not replace NATO consultation/Article 4/Article 5 dynamics, EU Article 42.7 dynamics, bilateral political decisions, or actual support levels. Those remain separate system-node dynamics.

## 5. Directed channels

The following channels are explicitly directional:

- trade_dependency;
- energy_dependency;
- migration_link;
- diaspora_link;
- information_link;
- criminal_network_link;
- extremist_network_link.

For a country pair A/B, each can contain A -> B and B -> A independently.

This matters because A depending strongly on B does not imply B depends strongly on A.

The architecture therefore does not symmetrize these channels.

## 6. Unknown is not zero

All seven directed channels are currently unresolved in v0.3.

They are stored as null in both directions.

~~~text
null = not yet resolved / insufficient comparable evidence
0.0  = evidence supports absence / negligible link
~~~

The two meanings must never be conflated.

## 7. Identity safeguards

The graph contract explicitly forbids:

~~~text
religious similarity -> extremist_network_link
diaspora presence     -> faction alignment
population identity   -> violent-network connection
~~~

An extremist-network edge requires evidence of violent-network connectivity.

A diaspora edge, when later populated, represents social/family/migration connectivity only.

## 8. Graph object model

The runtime representation contains:

~~~text
CountryGraph
├─ GraphNode[]
└─ GraphEdge[]
   ├─ SymmetricChannelValue[]
   └─ DirectedChannelValue[]
~~~

Pair topology is stored once per country pair.

Directionality lives inside the pair for channels where direction matters.

This avoids duplicating geographic/border data while preserving asymmetric dependencies.

## 9. Immutability

Graph nodes, edges and channel records are frozen dataclasses.

Metadata uses immutable tuples internally.

The graph is hashed from a canonical serialized representation.

Therefore:

~~~text
same graph inputs
+ same parameter profile
= same graph_hash
~~~

## 10. Manifest integration

The smoke runtime now writes the real graph hash into manifest.graph_hash.

The previous placeholder graph hash has been removed.

The run manifest also hashes the entire five-country snapshot bundle, because graph construction depends on country metadata beyond the selected country.

It stores file hashes for ESP, MAR, FRA, DEU and GBR.

## 11. Runtime artifact

Every smoke run writes graph.json alongside manifest.json, initial_state.json, final_state.json, replay_summary.json and trace.jsonl.

The replay summary reports graph hash, node count and edge count.

## 12. Current graph semantics

Resolved today:

| Channel | Directionality | Source |
|---|---|---|
| geographic_proximity | symmetric | canonical distance matrix |
| land_border | symmetric | canonical distance matrix |
| alliance_link | symmetric | shared formal memberships |

Unresolved today:

| Channel | Directionality |
|---|---|
| trade_dependency | directed |
| energy_dependency | directed |
| migration_link | directed |
| diaspora_link | directed |
| information_link | directed |
| criminal_network_link | directed |
| extremist_network_link | directed |

## 13. Five-country portability test

The same CLI must successfully initialize and execute the no-op smoke loop for Spain, Morocco, France, Germany and the United Kingdom.

No country-specific engine branch is permitted.

This directly tests the project requirement that adding a Snapshot-v1 country and graph data must not require changing engine equations.

## 14. Safety and abstraction

The graph represents strategic connectivity.

It does not contain target locations, attack routes, tactical movement, weapons employment or logistics-route optimization.

Future military/security spillover remains strategic and aggregate.

## 15. What v0.3 does not yet do

No graph channel affects EngineState yet.

Not implemented:

- spillover deltas;
- channel latency queues;
- target resilience;
- event propagation;
- information contagion;
- alliance actions;
- migration flows;
- trade/energy dependencies;
- criminal/extremist network propagation.

v0.3 only freezes and validates topology.

## 16. Next milestone

Recommended v0.4 sequence:

1. define a graph-spillover record;
2. add deterministic latency queues;
3. implement a zero-effect / trace-only spillover pass;
4. verify every candidate transmission records source, target, channel, edge value, latency and parameter IDs;
5. only then enable the first state-changing spillover equation.

This preserves the project principle: trace the mechanism before allowing the mechanism to change the simulation.

---

**Typed Country Graph v0.3 defines connectivity; it does not yet propagate conflict.**
