# Canonical Fractal Regional Catalog v1

**Status:** evidence-backed data milestone  
**Scope:** snapshot-v1 countries  
**Runtime levels:** complete L2_REGION + partial evidence-backed L3

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

## Current L3 coverage

Spain is the first production L3 dataset. Ten multi-province L2 parents now have
explicit province children using INE two-digit province codes and 1 July 2026
ECP population-share weights. The 43 raw province counts are stored alongside
the weights and reconcile exactly to each parent total.

The Spanish L2 parents Asturias, Illes Balears, Cantabria, Madrid, Murcia,
Navarra, La Rioja, Ceuta and Melilla remain intentionally without L3 children
under the current province partition because it would yield fewer than two
children. Their matured L3 requests are blocked without aborting the day.

See [FRACTAL_SPAIN_L3_CATALOG_V0.34E.md](FRACTAL_SPAIN_L3_CATALOG_V0.34E.md).

## Initialization weights

The catalog uses population share as the v1 default initialization weight.
Weights are normalized within each parent and must sum to one. They are not a
claim that every state variable follows population spatially. Additive or
intensive variables with a better evidence-backed allocation basis must use an
explicit variable-specific policy rather than silently inheriting population
share.

## Provenance

- ESP L2 — INE Estadística Continua de Población, autonomous-community/city
  geography. Existing L2 weights remain the original v0.33 baseline.
- ESP L3 — INE ECP table 59589, total sex/all ages by province, 1 July 2026;
  Eurostat NUTS 2024 supplies the stable statistical-geography reference.
- FRA — INSEE population estimates by region, 1 January 2026.
- DEU — Destatis population by Länder, 31 December 2025.
- GBR — ONS mid-2024 population estimates for England, Scotland, Wales and
  Northern Ireland.
- MAR — Haut-Commissariat au Plan, RGPH 2024 regional population.

The source IDs stored in the YAML are stable repository provenance identifiers;
external URLs are intentionally not runtime dependencies.

## Invariants

- every snapshot-v1 country has an explicit L1 parent entry;
- recursive parent entries may coexist in the same `parents` mapping;
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
