# Typed Structural Graph v0.3

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Behavioral contagion:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.3 introduces the first executable country graph used by the future contagion engine.

The graph is structural only.

It does not yet propagate conflict, migration, information, extremism, markets or alliance behavior.

Its purpose is to make topology:

- explicit;
- typed;
- reproducible;
- traceable;
- hashable;
- independent from country-specific code.

## 2. Active nodes

The current structural graph contains the five active Snapshot-v1 countries:

```text
ESP Spain
MAR Morocco
FRA France
DEU Germany
GBR United Kingdom
```

Node configuration lives in:

`config/graph/base_country_graph_v1.yaml`

## 3. Canonical distance source

The graph does not recalculate or duplicate geography.

It consumes:

`config/geography/country_distance_matrix_v1.yaml`

The distance metric remains:

`capital_to_capital_great_circle_km`

with land-border status stored separately.

## 4. Materialized channels in v0.3

Only three channels are currently materialized.

### geographic_proximity

Rule:

`EDGE_GEO_V1`

Synthetic engineering transform:

```text
proximity = exp(-distance_km / lambda_km)
```

Parameter:

`EDGE_GEO_SCALE_SYN_V1`

The current 1000-km scale is an engineering value, not a calibrated geopolitical transmission coefficient.

### land_border

Rule:

`EDGE_LAND_BORDER_V1`

Values:

```text
direct border = 1
no direct border = 0
```

This is structural data, not a probability.

### alliance_link

Rule:

`EDGE_ALLIANCE_V1`

The synthetic profile currently recognizes:

- shared NATO membership;
- shared European Union membership;
- explicitly documented bilateral security relationships.

Parameter:

`ALLIANCE_EDGE_SYN_V1`

Synthetic engineering scores:

```text
shared NATO membership                           1.00
shared European Union membership                 0.75
documented bilateral counterterrorism cooperation 0.55
```

Aggregation is currently `max`.

These are topology-strength test values only.

They are not estimates of automatic wartime support.

## 5. Spain-Morocco relationship

Spain and Morocco do not share NATO/EU membership.

The graph nevertheless preserves the documented bilateral counterterrorism/intelligence cooperation already present in Snapshot v1.

Therefore:

```text
ESP-MAR alliance_link = 0.55
```

under the synthetic engineering parameter set.

Its provenance includes:

`MA-DGST-SPAIN-COOP-2025`

This does not classify Morocco as a NATO ally of Spain.

## 6. Formal alliance examples

Spain and France share NATO and EU membership.

The synthetic aggregation therefore produces:

```text
ESP-FRA alliance_link = 1.0
```

France and the United Kingdom share NATO membership:

```text
FRA-GBR alliance_link = 1.0
```

Morocco and France have no materialized formal-common-membership or explicit bilateral relationship in the current graph seed:

```text
MAR-FRA alliance_link = 0.0
```

A zero here means:

> no relationship represented by the currently enabled `alliance_link` evidence rules.

It does not mean the countries have no diplomatic/security relationship in reality.

## 7. Missing channels

The following canonical channels are intentionally not yet materialized:

- trade_dependency;
- energy_dependency;
- migration_link;
- diaspora_link;
- information_link;
- criminal_network_link;
- extremist_network_link.

They remain absent until comparable evidence and normalization rules are implemented.

Missing optional channels are not silently interpreted as empirical zero transmission.

## 8. Edge provenance

Every channel stores:

```yaml
value:
rule_id:
parameter_ids:
evidence_refs:
source_ids:
```

For a NATO link, evidence refs identify the membership paths in both Snapshot-v1 country files.

For an explicit bilateral relationship, the edge keeps its original source IDs.

## 9. Graph hash

The structural graph hash includes the canonical serialized values of:

- graph seed configuration;
- distance matrix;
- active parameter profile;
- Spain Snapshot;
- Morocco Snapshot;
- France Snapshot;
- Germany Snapshot;
- United Kingdom Snapshot;
- normalized edge values.

Therefore any material change to a graph input changes:

`graph_hash`

and consequently changes the run replay identity.

## 10. Smoke-run integration

The CLI now writes:

`graph.json`

and the immutable run manifest stores the real structural:

`graph_hash`

instead of the previous placeholder graph hash.

## 11. Current topology

Ten undirected baseline pairs are materialized because five countries produce:

```text
5 * 4 / 2 = 10
```

pairs.

Representative synthetic proximity values:

| Pair | Distance km | Land border | Geographic proximity |
|---|---:|---:|---:|
| ESP-MAR | 763 | 1 | ~0.466 |
| ESP-FRA | 1053 | 1 | ~0.349 |
| FRA-GBR | 344 | 0 | ~0.709 |
| FRA-DEU | 877 | 1 | ~0.416 |
| MAR-DEU | 2611 | 0 | ~0.073 |

These values have no standalone political interpretation.

## 12. Undirected baseline

v0.3 uses undirected structural edges.

Future channels may be directional.

Examples:

- migration flow;
- energy dependence;
- trade exposure;
- information influence;
- financial support.

The graph schema explicitly allows those future directional channels without changing country dynamics.

## 13. No contagion yet

v0.3 does not execute:

```text
source pressure
× edge
× transmission
→ target delta
```

The graph is constructed and hashed only.

This is deliberate.

Before contagion is enabled, the engine must first prove:

- edge reproducibility;
- channel provenance;
- parameter traceability;
- manifest integration.

## 14. Validation requirements

v0.3 tests require:

- exactly five configured active nodes;
- exactly ten baseline edges;
- correct land-border flags;
- expected geographic proximity transform;
- shared NATO membership produces the expected synthetic alliance link;
- Spain-Morocco bilateral cooperation retains source provenance;
- missing represented relationship produces zero alliance-link evidence;
- graph construction is deterministic;
- changing graph evidence changes graph hash;
- graph hash provenance includes all five Snapshot inputs.

## 15. Next milestone

The next graph milestone should add high-confidence directional or weighted channels in this order:

1. trade dependency;
2. energy dependency;
3. migration connectivity;
4. information connectivity;
5. documented criminal-network connectivity;
6. documented violent-extremist-network connectivity.

Only then should `GRAPH_SPILLOVER_V1` begin changing EngineState variables.

---

**Typed Structural Graph v0.3 establishes topology and provenance, not contagion.**
