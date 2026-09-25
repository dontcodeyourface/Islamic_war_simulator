# Canonical L2 Regional Catalog v1

**Status:** evidence-backed data milestone  
**Scope:** snapshot-v1 countries  
**Runtime level:** L2_REGION

## Decision

L2 follows the highest-value stable first-order territorial division that matches
the adaptive-fractal architecture. It is not forced to the same legal label in
every country.

| Parent | Canonical L2 | Children |
| --- | --- | ---: |
| ESP | autonomous communities + autonomous cities | 19 |
| FRA | regions, including overseas regions | 18 |
| DEU | Länder | 16 |
| GBR | constituent countries | 4 |
| MAR | regions | 12 |

For the UK, England is intentionally retained as one L2 nation. English regions
are candidates for L3 when England itself requires refinement; promoting them to
L2 would mix hierarchy depths inside one parent.

## Initialization weights

The catalog uses population share as the v1 default initialization weight.
Weights are normalized within each parent and must sum to one. They are not a
claim that every state variable follows population spatially. Additive or
intensive variables with a better evidence-backed allocation basis must use an
explicit variable-specific policy rather than silently inheriting population
share.

## Provenance

- ESP — INE Estadística Continua de Población, autonomous-community/city
  geography. Current ECP results are the canonical source; the present weights
  are marked provisional and must be refreshed from the machine-readable INE
  regional table before calibration claims.
- FRA — INSEE population estimates by region, 1 January 2026.
- DEU — Destatis population by Länder, 31 December 2025.
- GBR — ONS mid-2024 population estimates for England, Scotland, Wales and
  Northern Ireland.
- MAR — Haut-Commissariat au Plan, RGPH 2024 regional population.

The source IDs stored in the YAML are stable repository provenance identifiers;
external URLs are intentionally not runtime dependencies.

## Invariants

- every snapshot-v1 country has an explicit parent entry;
- every child ID is parent-namespaced;
- sibling IDs are unique;
- child count stays within materialization bounds;
- weights are positive and normalized to one;
- no region is generated implicitly;
- later re-refinement reuses catalog child identity but receives a new runtime
  lineage generation;
- changing a country's canonical child set is a data/schema migration, not a
  routine parameter tweak.

## Boundary

This catalog defines geography and initialization metadata only. It does not
populate regional political, demographic, religious, security, infrastructure
or conflict attributes. Those require separate sourced regional datasets.

The regional graph catalog is also separate: administrative membership does not
imply an interaction edge or a channel weight.
