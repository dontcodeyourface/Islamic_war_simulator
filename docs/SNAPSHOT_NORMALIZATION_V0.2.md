# Snapshot Normalization v0.2

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Engine dynamics:** still disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.2 begins replacing synthetic EngineState initialization with traceable Snapshot v1 evidence.

It does **not** attempt to normalize all 60 latents at once.

The rule is conservative:

> use empirical/computable evidence only where the mapping is semantically clear; otherwise preserve the explicit registered prior.

This avoids hiding arbitrary model assumptions inside initialization code.

## 2. Initialization precedence

For every EngineState latent:

```text
1. empirical normalization from Snapshot v1
        ↓ if unavailable
2. baseline-relative anchor
        ↓ if unavailable
3. registered synthetic prior
```

Every result records its source type.

Possible values:

```text
empirical
baseline_anchor
prior
```

## 3. Country independence

The mapping is stored in:

`config/engine/snapshot_feature_map_v1.yaml`

It contains Snapshot paths and normalization-rule types.

It contains no country-specific conditionals.

The same initializer is called for Spain, Morocco and future Snapshot-v1 countries.

## 4. Empirically initialized latents in v0.2

### demographic_momentum

Source:

`demographic_dynamics.annual_population_growth_rate`

Synthetic engineering normalization:

```text
tanh(growth_percent / demographic_growth_scale_percent)
```

The scale parameter is registered under `INIT_NORMALIZATION_SYN_V1`.

This normalization is not a demographic forecast.

### dependency_pressure

Preferred evidence:

```text
population.total
population.age.age_15_64
```

If a country only provides a compatible working-age share, v0.2 can use that share.

The age-dependency ratio is then passed through a bounded saturation transform.

### inflation_pressure

Source:

`economy.inflation_rate`

Linear synthetic engineering anchor.

### unemployment_pressure

Source:

`economy.unemployment_rate`

Linear synthetic engineering anchor.

### energy_resilience

Uses, when all are available:

- strategic petroleum-stock days;
- petroleum import-dependency category;
- domestic refining availability.

Synthetic engineering weights:

- strategic stocks: 0.50;
- import resilience: 0.30;
- domestic refining: 0.20.

These weights are registered parameters, not calibrated estimates.

### food_resilience

Uses the complement of a comparable cereal import-dependency ratio when available.

A missing comparable denominator results in prior fallback.

### water_resilience

Uses the complement of national water-stress percentage.

### prison_control

Uses prison occupancy where available.

Synthetic engineering anchors:

- 100% occupancy -> 1.0 control contribution;
- 200% occupancy -> 0.0.

This is only a first-order engineering normalization. It is not a claim that occupancy alone determines prison control.

## 5. Baseline-relative functionality anchors

The following variables represent functionality relative to the factual simulation start state:

- economic_output;
- electricity_functionality;
- fuel_distribution_functionality;
- transport_logistics_functionality;
- telecom_internet_functionality;
- health_system_functionality.

Unless Snapshot v1 explicitly describes current degraded functionality, v0.2 initializes these to:

```text
1.0 = factual baseline functionality at t0
```

This does **not** mean the country is objectively perfect.

It means future deltas are measured relative to the simulation start state.

These six values are tagged:

`source_type = baseline_anchor`

and do not count as empirical evidence.

## 6. Spain v0.2 initialization

Current expected empirical latents:

| Latent | Approx. v0.2 value | Snapshot evidence |
|---|---:|---|
| demographic_momentum | 0.4219 | +0.90% population growth |
| dependency_pressure | 0.4214 | total population + age 15–64 |
| inflation_pressure | 0.2700 | 2.7% inflation |
| unemployment_pressure | 0.4160 | 10.4% unemployment |
| energy_resilience | 0.7600 | stocks + import dependency + refining |
| food_resilience | 0.5390 | 46.1% gross cereal import/internal-use ratio |
| water_resilience | 0.5675 | 43.25% water stress |

Prison control remains prior-based because the current Spain Snapshot does not contain a comparable occupancy figure.

Initialization mix:

```text
empirical       7 / 60
baseline anchor 6 / 60
prior          47 / 60
```

## 7. Morocco v0.2 initialization

Expected empirical latents:

| Latent | Approx. v0.2 value | Snapshot evidence |
|---|---:|---|
| demographic_momentum | 0.4011 | +0.85% average annual population growth |
| dependency_pressure | 0.4737 | 59.7% age 15–59 share |
| inflation_pressure | 0.0700 | 0.7% inflation |
| unemployment_pressure | 0.3600 | 9.0% unemployment |
| energy_resilience | 0.3244 | ~53 stock-days + near-total import dependence + no domestic refining |
| water_resilience | 0.4925 | 50.75% water stress |
| prison_control | 0.4670 | 153.3% prison occupancy |

Food resilience remains prior-based because v1 intentionally lacks a synchronized national cereal-dependency ratio.

Initialization mix:

```text
empirical       7 / 60
baseline anchor 6 / 60
prior          47 / 60
```

The fact that Spain and Morocco currently have the same count is incidental. Future countries can resolve different subsets.

## 8. Initialization trace

Every empirical initialization now stores:

```yaml
source_type: empirical
normalization_rule_id:
parameter_ids:
snapshot_field_refs:
source_ids:
data_quality:
freshness:
uncertainty_multiplier:
empirical_fraction: 1.0
prior_fraction: 0.0
baseline_fraction: 0.0
```

A prior-based initialization stores:

- prior ID;
- RNG stream;
- RNG draw index.

A baseline anchor stores:

- anchor rule;
- anchor parameter ID;
- no fabricated source IDs.

## 9. State-level evidence mix

EngineState metadata now reports:

```yaml
empirical_latent_count:
baseline_latent_count:
prior_latent_count:

empirical_fraction:
baseline_fraction:
prior_fraction:
```

The three fractions sum to 1.0.

This enables later output to state clearly how much of an initialized country state is empirically grounded.

## 10. Source quality

Normalization preserves:

- `source_ids`;
- source quality;
- freshness.

Quality/freshness modify uncertainty metadata.

They do not silently change the normalized mean toward a neutral value.

## 11. What v0.2 deliberately does not do

v0.2 does not yet empirically initialize:

- government legitimacy;
- state/elite cohesion;
- security-force loyalty/cohesion;
- extremist-network pressure;
- criminal-network power;
- detailed military effectiveness;
- defence industrial capacity;
- alliance support;
- AI maturity;
- cyber resilience.

Those require stronger cross-country normalization rules or dedicated calibration.

They continue to use explicit registered synthetic priors.

## 12. No behavioral dynamics yet

The daily engine remains no-op.

v0.2 does not implement:

- RANDOM_SHOCK;
- GENERATED events;
- graph spillover;
- phase transitions;
- reciprocal radicalization;
- military losses;
- resource depletion;
- alliance decisions;
- fractal refinement.

This milestone improves only `t=0` state construction and traceability.

## 13. Next milestone

After v0.2 the recommended implementation order is:

1. complete high-confidence initialization rules for additional latents;
2. implement typed graph data and edge normalization;
3. implement the event object + hazard trace without event effects;
4. add the first bounded domestic dynamics;
5. only then enable phase transitions.

The highest-priority next initialization candidates are:

- police_effective_capacity;
- terrorism_threat_pressure;
- criminal_network_power;
- military domain effective-capacity variables;
- defence_industrial_capacity;
- replenishment_capacity;
- alliance_support.

Each should be implemented only when the data semantics are comparable enough to justify the mapping.

---

**Snapshot Normalization v0.2 increases empirical grounding without pretending the model is calibrated.**
