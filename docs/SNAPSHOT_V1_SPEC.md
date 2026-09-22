# Snapshot v1 — Canonical Country Data Contract

**Status:** FROZEN  
**Schema:** 1.0  
**Freeze date:** 2026-09-23  
**Engine:** not implemented

Snapshot v1 closes the set of country-level data families used by the future simulator.

After this freeze, ordinary country additions and data refreshes MUST fit the v1 template. Adding a new required top-level country-data family requires a major schema revision.

Canonical files:

- `config/countries/_schema.yaml`
- `config/countries/_snapshot_v1_template.yaml`
- `config/geography/country_distance_matrix_v1.yaml`
- `docs/ADAPTIVE_FRACTAL_MODEL_ARCHITECTURE.md`

---

## 1. Scope frozen in v1

The canonical country snapshot covers:

1. identity and population;
2. demographic dynamics;
3. religion and religious infrastructure;
4. violent-extremist pressure;
5. organized crime;
6. prisons and terrorism threat posture;
7. law enforcement and security-force cohesion;
8. manpower and armed forces;
9. military-domain capability categories;
10. defence industry and replenishment;
11. intelligence, cyber and AI;
12. economy and financial reserves;
13. energy security;
14. food and water security;
15. sustainment inputs;
16. critical infrastructure;
17. regional-government topology;
18. administrative continuity;
19. information environment;
20. emergency-health resilience;
21. diaspora/remittance/external-social-finance channels;
22. geography and inter-country distances;
23. alliances and governance;
24. provenance and uncertainty.

The future runtime engine should not ingest every raw field directly. Raw snapshots are evidence stores from which a smaller set of engine-facing latent variables will be normalized.

Target normal runtime size remains approximately **30–60 latent variables per country**.

---

## 2. Demographic rule

The canonical terminology is:

- Christian population;
- Muslim population;
- violent Islamist networks.

"Muslim" is a religious-demographic category.

"Islamist" is a political/ideological category and cannot be used as a synonym for Muslim.

Therefore Snapshot v1 may contain:

```yaml
christian_fertility_rate_direct:
muslim_fertility_rate_direct:
christian_population_growth_rate_direct:
muslim_population_growth_rate_direct:
```

but the values remain null unless a source directly measures religion.

The following substitutions are forbidden:

```text
foreign mother -> Muslim
Moroccan origin -> Muslim
Muslim -> Islamist
Christian -> political faction
```

In an overwhelmingly religiously homogeneous country, a national demographic rate may be retained as a clearly tagged **proxy**, never as direct religious measurement.

---

## 3. Distance model

Inter-country distance is kept outside individual country files in:

`config/geography/country_distance_matrix_v1.yaml`

The canonical baseline metric is:

`capital_to_capital_great_circle_km`

using the Haversine formula.

Direct land-border status is stored separately.

This avoids confusing:

- capital distance;
- minimum border distance;
- sea distance;
- logistics-route distance.

Future regional refinement may compute more relevant local distances without changing the country schema.

---

## 4. Petroleum reserves versus fuel security

Snapshot v1 distinguishes:

### Geological reserve

`proven_crude_oil_reserves_barrels`

This estimates recoverable underground reserves.

### Operational fuel security

```yaml
petroleum_consumption:
strategic_petroleum_stock_days:
petroleum_security_obligation_days:
refinery_capacity:
domestic_refining_available:
petroleum_import_dependency:
```

For short/medium conflict resilience, operational stocks, refinery capacity and import access usually matter more than underground reserve totals.

No single aggregate `oil_reserve` field is allowed.

---

## 5. Military consumption

Snapshot v1 deliberately does **not** store fixed wartime per-troop burn rates for:

- fuel;
- food;
- water;
- ammunition.

Those quantities depend on:

- branch and force composition;
- operational tempo;
- climate;
- geography;
- equipment;
- mobility;
- logistics;
- duration;
- damage and maintenance;
- scenario state.

Country snapshots instead store:

- observed civilian/national demand;
- fuel/food/water stocks;
- energy and food production;
- industrial and munitions-production capacity;
- logistics/resilience variables.

The future engine derives sustainment demand dynamically.

Canonical policy:

```yaml
military_sustainment_policy: scenario_derived
munitions_burn_policy: scenario_derived
```

This is a freeze rule.

---

## 6. Critical infrastructure

Only compact national-state variables are stored permanently:

- electricity;
- fuel storage;
- telecommunications;
- Internet;
- water;
- ports;
- airports;
- road/rail;
- data centers;
- spare-parts dependence;
- repair capacity.

Individual plants, substations, ports, terminals or data centers are not persistent country-level objects.

They can be instantiated only through adaptive fractal refinement if a hotspot makes them material.

---

## 7. Regional-government topology

The country snapshot stores institutional topology, not every subnational government.

Permanent variables include:

- degree/form of subnational autonomy;
- police-control topology;
- fiscal-control topology;
- emergency powers;
- latent regional identity pressure;
- center-region conflict;
- regional-government legitimacy.

If stress exceeds refinement thresholds, specific regions become explicit L2 nodes.

---

## 8. Administrative continuity

The future civil-conflict model needs to distinguish violence from state collapse.

Therefore v1 contains:

- courts;
- prosecution;
- civil registry;
- tax collection;
- public payroll;
- emergency governance.

Most baseline values may initially remain null.

The fields are frozen now so the engine can later model continuity without adding another country-data family.

---

## 9. Information environment

The frozen compact information layer contains:

- mainstream-media trust;
- social-media dependency;
- misinformation pressure;
- foreign information operations;
- encrypted-network adoption;
- government communication credibility.

Individual media outlets, accounts or influencers are not country-level nodes.

---

## 10. Health

Only crisis-continuity variables are included:

- hospital beds;
- emergency beds;
- trauma capacity;
- ambulance resilience;
- medicine-import dependence;
- public-health continuity.

The simulator is not a hospital-level model.

---

## 11. External social/financial networks

The country layer may store:

- diaspora size;
- remittance dependence;
- foreign private funding;
- cross-border family networks;
- external political-finance pressure.

No diaspora or religious group is assumed to support a faction.

Alignment remains scenario-dependent.

---

## 12. Organized crime freeze

Only three illicit markets are first-class country variables:

- cocaine;
- cannabis/hashish;
- illicit firearms.

Individual mafia bosses, trafficking routes, caches and tactical logistics are excluded from the permanent country layer.

Criminal networks remain primarily profit-seeking actors whose later conflict relationships are stochastic.

---

## 13. Fractal rule

Country snapshots are L1 evidence nodes.

Permanent baseline:

```text
SYSTEM -> COUNTRY
```

Only stressed areas refine:

```text
COUNTRY
 -> REGION
 -> METRO / LOGISTICS AREA
 -> ACTOR NETWORK
 -> EVENT CLUSTER
```

Resolution follows stress.

Fibonacci windows remain an experimental multiscale observation grid, not an assumed law of nature.

---

## 14. Nulls are valid

A null is preferable to a fabricated figure.

Snapshot v1 explicitly supports incomplete empirical coverage.

A null may later participate in Monte Carlo only when:

- a documented interval exists;
- a prior/distribution is justified;
- correlations are preserved;
- the uncertainty source is explicit.

Unbounded random sampling from null remains prohibited.

---

## 15. Registration contract

Every new country must:

- use schema version 1.x;
- contain every required top-level v1 section;
- use datum records with provenance;
- distinguish current data from estimates and derivations;
- record reference dates;
- preserve geographic scope;
- keep known gaps as null;
- follow the religion/extremism separation;
- follow organized-crime nonalignment rules;
- follow security-force cohesion rules;
- use the common distance matrix;
- keep tactical wartime burn rates outside the snapshot.

A new required top-level section requires **Snapshot v2 / schema 2.x**.

Data refreshes and filling null fields do not.

---

## 16. Snapshot maturity

At freeze:

- Spain and Morocco are the v1 reference countries with the new resilience/demographic layer populated;
- France, United Kingdom and Germany are structurally migrated to v1 and retain existing v0.x evidence, while newly frozen sections may contain null/empty values pending refresh;
- future countries must enter directly on the v1 template.

This distinction avoids blocking the schema freeze on complete data coverage for every country.

---

**Snapshot v1 country scope is frozen.**
