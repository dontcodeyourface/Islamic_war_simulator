# Canonical L3 Partition Policy v0.34d

**Status:** implementation + data-contract milestone  
**Version:** 0.34d  
**Date:** 2026-09-25  
**Depends on:** v0.34c3 recursive lifecycle closure

## Purpose

v0.34d defines how a production L2 node is allowed to refine into L3 and how the engine behaves while country-specific L3 child data is still incomplete.

The key rule is:

> missing L3 data must block refinement, not abort the simulation and not invent children.

This is distinct from an invalid configured catalog. Missing data is a known coverage limitation. Invalid data is a contract violation and remains fail-closed.

## Runtime behavior

When an L2 node reaches a matured `EXPAND` proposal:

1. resolve the stable catalog identity of the runtime L2 parent;
2. inspect the explicit child catalog for that stable parent;
3. if an entry exists, continue through normal materialization validation;
4. if no entry exists, record `fractal_refinement_blocked_missing_catalog`;
5. leave the node at L2;
6. preserve its refinement persistence/streak;
7. continue the rest of the day transaction.

The action proposal remains traceable, but no topology or child EngineState is created.

The blocked trace records:

- action ID;
- runtime node ID;
- stable catalog parent ID;
- day;
- from/to levels;
- reason;
- `BLOCKED_NOT_APPLIED` status.

## Invalid catalog behavior

If a parent entry exists but is malformed, the materializer still fails closed.

Examples:

- fewer than two children;
- more than configured maximum children;
- duplicate IDs;
- child IDs not namespaced by the parent;
- non-positive/non-finite weights;
- weights not summing to one;
- missing source ID;
- reserved runtime generation suffix in stable catalog identity.

There is no fallback to equal weights and no implicit child generation.

## Canonical partition policy

The policy is stored in:

`config/engine/fractal_l3_partition_policy_v1.yaml`

The runtime level remains `L3_METRO_OR_LOGISTICS_AREA`, but the **stable territorial container** used to initialize that resolution is selected from official statistical/administrative geography.

This avoids inventing bespoke operational zones while preserving a stable spatial scaffold for strategic local dynamics.

### Spain

Base: autonomous community/city at L2.

Preferred L3 partition:

- province or equivalent NUTS3 statistical unit.

Topology sources:

- Eurostat NUTS;
- INE provincial geography.

Population weights:

- INE Estadística Continua de Población at province level.

Small/singleton parents such as autonomous cities remain at L2 unless a separate explicit multi-child partition is sourced.

### France

Base: region at L2.

Preferred L3 partition:

- department or equivalent NUTS3 unit.

Topology source:

- Eurostat NUTS.

Population weights:

- INSEE subregional population tables selected in the dedicated data PR.

### Germany

Base: Land at L2.

Preferred L3 partition:

- the next stable NUTS2/statistical subregion below the Land.

This is intentionally one hierarchy step below the L2 Land rather than jumping directly to Kreis level where that would create excessive child fan-out.

Population weights:

- Destatis subregional population tables selected in the dedicated data PR.

City states or other single-unit parents remain L2 unless a separate multi-child partition is sourced.

### United Kingdom

Base: constituent country at L2.

Preferred L3 partition:

- first stable ONS International Territorial Level below the constituent-country parent that yields a meaningful multi-child partition.

Examples of the hierarchy are provided by ONS ITL 2025. England may therefore use ITL1 regions, while Scotland, Wales and Northern Ireland use the first lower ITL tier appropriate to their parent.

Population weights:

- ONS population estimates aligned to the selected ITL release.

### Morocco

Base: region at L2.

Preferred L3 partition:

- province or prefecture.

Topology and population source:

- HCP RGPH 2024 legal population by region, province, prefecture and commune.

## Weight policy

Population share remains the default initialization basis.

Before any production parent is activated at L3:

- every child must have a positive population-derived weight;
- weights must normalize exactly within the parent;
- the source/date must be registered in provenance;
- equal-weight fallback is forbidden;
- inferred/unsourced fallback is forbidden.

Population share initializes spatializable stocks. It does not imply every variable follows population spatially.

## Provenance

v0.34d registers canonical source identifiers for:

- Eurostat NUTS 2024;
- INE provincial ECP 2026;
- ONS ITL 2025;
- HCP RGPH 2024 territorial results;
- reserved exact-table IDs for INSEE, Destatis and ONS population datasets to be bound in the dedicated child-data PRs.

Reserved IDs cannot be used for production child weights until their exact table/date is documented.

## Tests

`tests/test_fractal_l3_partition_policy.py` validates:

- policy coverage for all five snapshot countries;
- adjacent L2 -> L3 transition;
- explicit-catalog requirement;
- block-not-abort semantics for missing catalog;
- hard fail-closed semantics for invalid catalog;
- no weight fallback;
- country-specific partition basis;
- provenance registry resolution;
- strategic abstraction boundary.

`tests/test_fractal_regional_day.py::test_v034d_missing_l3_catalog_blocks_refinement_without_aborting_day` validates the runtime behavior:

- ESP refines to L2 normally;
- an L2 child reaches a matured L3 expansion threshold;
- production L2 catalog has no L3 entry;
- transaction commits successfully;
- no L3 topology is created;
- L2 authority remains active;
- persistence remains at L2;
- a single blocked-refinement trace is emitted.

## Next data increments

v0.34d establishes the contract. The next PRs should populate child sets and exact population-share weights country by country.

Recommended order:

1. Spain — provinces/NUTS3 with INE ECP weights;
2. Morocco — provinces/prefectures with RGPH 2024 weights;
3. France — departments/NUTS3;
4. Germany — NUTS2 subregions within Länder;
5. United Kingdom — ONS ITL hierarchy.

Each data PR must include:

- exact source/date;
- complete parent child-set;
- normalized weights;
- catalog validation tests;
- graph-channel coverage status;
- no country-specific dynamics equations.

## Safety boundary

L3 remains strategic and aggregate.

The partition policy does not define:

- tactical routes;
- facility targets;
- weapon choices;
- attack methods;
- operational execution.

Official territorial/statistical areas are used only as stable containers for aggregate simulation state.
