# Spain L3 Province Catalog v0.34e

**Status:** evidence-backed production data milestone  
**Version:** 0.34e  
**Reference date:** 2026-07-01  
**Depends on:** v0.34d L3 partition/coverage gate

## Purpose

v0.34e supplies the first production L3 child catalog for the recursive fractal runtime.

Spanish L2 autonomous communities with at least two provinces may now refine into explicit province-level L3 children. No province is generated implicitly and no equal-weight fallback is used.

## Source

Population basis:

- source ID: `ES-INE-ECP-PROVINCES-2026`;
- INE operation: Estadística Continua de Población;
- API table: `59589`;
- selection: total sex, all ages, provinces;
- reference date: 1 July 2026;
- status: official provisional.

Topology basis:

- source ID: `EU-EUROSTAT-NUTS-2024`;
- stable province/NUTS3-compatible territorial identity.

The raw provincial population count is retained in the YAML beside every initialization weight.

## Activated multi-province L2 parents

| L2 parent | L3 children |
| --- | ---: |
| Andalucía | 8 |
| Aragón | 3 |
| Canarias | 2 |
| Castilla y León | 9 |
| Castilla-La Mancha | 5 |
| Cataluña | 4 |
| Comunitat Valenciana | 3 |
| Extremadura | 2 |
| Galicia | 4 |
| País Vasco | 3 |

Total production L3 children added: **43 provinces**.

Stable IDs use the INE two-digit province code beneath the canonical L2 identity, for example:

- `ESP::CT::08` — Barcelona;
- `ESP::CT::17` — Girona;
- `ESP::CT::25` — Lleida;
- `ESP::CT::43` — Tarragona.

Runtime lineage suffixes remain separate from this stable catalog identity.

## Deliberately non-activated L2 parents

The following L2 nodes do not receive a province-level child catalog because the selected province partition does not provide the minimum two children:

- Principado de Asturias;
- Illes Balears;
- Cantabria;
- Comunidad de Madrid;
- Región de Murcia;
- Comunidad Foral de Navarra;
- La Rioja;
- Ceuta;
- Melilla.

A matured L3 refinement request for these parents therefore follows the v0.34d contract:

`BLOCKED_NOT_APPLIED`

The day transaction continues at L2. A future evidence-backed alternative partition may be introduced in a dedicated migration, but it must not be invented implicitly.

## Initialization weights

For each multi-province parent:

`initialization_weight = province_population / sum(parent_province_populations)`

Every stored parent population total equals the exact sum of its stored child counts.

Weights are rounded to 12 decimal places with the final sibling adjusted so the stored sibling set sums exactly to 1.000000000000.

The weights initialize spatializable state only. They do not assert that every latent, regime, resource, or infrastructure variable is distributed by population.

## Materialization behavior

The generic recursive materializer consumes the same production catalog used by L1 -> L2.

For example, an eligible `ESP::CT` expansion produces four L3 runtime nodes from the stable catalog identities:

- `ESP::CT::08`;
- `ESP::CT::17`;
- `ESP::CT::25`;
- `ESP::CT::43`.

On later re-refinement, stable catalog identity is unchanged while runtime lineage receives the next generation suffix.

## Tests

`tests/test_fractal_spain_l3_catalog.py` validates:

- exact set of 10 multi-province parents;
- deliberate absence of the nine single/unpartitioned parents;
- exact 43 two-digit province codes;
- raw INE population counts;
- exact parent-total reconciliation;
- positive normalized weights;
- recomputation of each stored weight from raw count / parent total;
- no runtime generation suffix in stable IDs;
- real production materialization of Cataluña to four L3 provinces.

The v0.34d missing-catalog transaction test now uses `ESP::MD`, proving that deliberately unpartitioned L2 parents remain operationally safe after Spanish L3 data is added.

## Graph coverage

This PR adds node topology and initialization weights only.

It does **not** infer province-to-province interaction edges from administrative membership. Until explicit L3 graph channels are added, missing L3 graph relationships remain unresolved/null according to the existing graph-projection contract.

## Safety boundary

Province-level L3 nodes are strategic aggregate state containers.

They do not encode:

- tactical routes;
- individual facilities;
- targets;
- weapons;
- attack methods;
- operational execution.
