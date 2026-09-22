# Adaptive Fractal Simulation Architecture

**Status:** pre-engine architecture  
**Version:** 0.1  
**Date:** 2026-09-23

---

## 1. Objective

The simulator should represent escalation from ordinary state competition and domestic stress to localized disorder, insurgency, civil conflict and regional contagion without permanently simulating every city, police unit, criminal group, mosque, infrastructure site or political actor.

The canonical approach is **adaptive multiscale resolution**.

The closest computational analogy is adaptive mesh refinement:

```text
low stress  -> coarse aggregate node
high stress -> selectively expand the affected node
lower stress -> aggregate it again after hysteresis/persistence conditions
```

This preserves complexity where it matters and prevents state-space explosion.

---

## 2. Fractal hierarchy

Canonical resolution levels:

```text
L0  SYSTEM
    Europe / Maghreb / Middle East / alliance space

L1  COUNTRY
    Spain / France / Germany / Morocco / ...

L2  REGION
    autonomous community / Land / region / nation / governorate

L3  METRO_OR_LOGISTICS_AREA
    major metropolitan area / port complex / border area / industrial basin

L4  ACTOR_NETWORK
    police command / extremist network / criminal OCG / critical-infrastructure operator /
    religious-institution network / local political authority

L5  EVENT_CLUSTER
    protest wave / prison disorder / infrastructure outage / localized violence /
    criminal-market conflict / institutional fracture
```

The model should normally operate at L1.

Lower levels are activated only when needed.

---

## 3. Refinement triggers

A country or region may be decomposed when one or more latent variables exceed a threshold for a persistence period.

Candidate trigger families:

### Political / institutional

- government legitimacy collapse;
- competing legal authority;
- regional-government confrontation;
- security-force command fracture;
- emergency-law activation;
- sustained mass protest.

### Security

- repeated extremist violence;
- organized-crime territorial pressure;
- prison-control degradation;
- police overstretch;
- local arms availability;
- communal violence.

### Infrastructure

- electricity disruption;
- fuel shortage;
- telecom outage;
- water-system stress;
- transport-node closure;
- major port/airport degradation.

### Economic

- bank/liquidity stress;
- rapid inflation;
- unemployment shock;
- fiscal-payment disruption;
- food/fuel price shock.

### External

- refugee/displacement surge;
- border closure;
- sanctions shock;
- foreign intervention/support;
- alliance fracture;
- external war spillover.

No single trigger should automatically imply civil war.

---

## 4. Hysteresis

Refinement and collapse thresholds must differ.

Example conceptual policy:

```text
expand node when stress > T_high for P_expand
collapse node when stress < T_low for P_collapse

where T_low < T_high
```

This prevents nodes repeatedly opening and closing due to noise.

---

## 5. Fibonacci-inspired observation windows

The simulator may test Fibonacci windows as a multiscale observation grid:

```text
1, 2, 3, 5, 8, 13, 21, 34, 55, 89 days
```

These can coexist with conventional windows:

```text
1, 7, 14, 30, 90, 180, 365 days
```

Potential uses:

- stress persistence;
- event clustering;
- actor adaptation;
- institutional fatigue;
- propaganda/recruitment memory;
- volatility;
- refinement/de-refinement hysteresis.

Fibonacci windows remain experimental.

Backtesting must determine whether they improve explanatory or predictive performance.

---

## 6. Core country state — always active

The engine should keep the permanent L1 state compact.

Recommended always-on state groups:

### A. State coercive capacity

- Armed Forces effective capacity;
- police/gendarmerie effective capacity;
- intelligence/counterintelligence;
- cyber/ISR;
- prisons;
- border/customs/coast security.

### B. State cohesion

- government legitimacy;
- command cohesion;
- civil-military alignment;
- security-force cohesion;
- regional-authority cohesion;
- judicial/administrative continuity.

### C. Economic survival

- GDP;
- fiscal capacity;
- debt/borrowing access;
- FX reserves;
- gold reserves;
- inflation;
- unemployment;
- industrial regeneration.

### D. Essential-resource resilience

- electricity;
- fuel;
- food;
- water;
- telecommunications;
- transport/logistics.

### E. Social pressure

- polarization;
- protest mobilization;
- demographic stress;
- displacement;
- religious/identity infrastructure;
- extremist-network pressure.

### F. Non-state coercive networks

- violent Islamist networks;
- violent ultranationalist networks;
- revolutionary violent networks;
- organized crime;
- gangs;
- prison-linked networks.

### G. Information / technology

- media/information integrity;
- disinformation pressure;
- communications availability;
- cyber;
- AI;
- surveillance/ISR.

### H. External environment

- alliances;
- foreign support;
- foreign coercion;
- sanctions;
- neighboring instability;
- refugee flows;
- diaspora/remittance/foreign-funding pressure.

These are broad latent variables, not thousands of detailed objects.

---

## 7. High-value factors still missing from the canonical snapshot

To improve realism without oversizing, the highest-value missing layers are:

### 7.1 Critical infrastructure resilience

Keep only national aggregates until failure:

```yaml
electricity_resilience:
fuel_reserves:
telecom_resilience:
water_resilience:
transport_resilience:
port_capacity:
airport_capacity:
data_center_resilience:
critical_spare_parts_dependency:
```

If a national value becomes stressed, then instantiate a regional/metro infrastructure node.

### 7.2 Food and fuel security

Essential for prolonged disorder:

```yaml
food_import_dependency:
strategic_food_stock:
fuel_import_dependency:
strategic_fuel_stock:
domestic_refining_capacity:
agricultural_resilience:
```

### 7.3 Judicial and administrative continuity

Civil conflict depends heavily on whether ordinary institutions continue working.

```yaml
court_continuity:
prosecution_capacity:
civil_registry_continuity:
tax_collection_continuity:
public_salary_payment_continuity:
emergency_governance_capacity:
```

### 7.4 Regional-government topology

This is especially important for:

- Spain;
- Germany;
- UK;
- federal/devolved states added later.

Store only:

```yaml
subnational_autonomy:
regional_police_control:
regional_fiscal_control:
regional_identity_pressure:
regional_government_legitimacy:
center_region_conflict:
```

Do not instantiate every region until stress requires it.

### 7.5 Information ecosystem

High-value compact variables:

```yaml
mainstream_media_trust:
social_media_dependency:
misinformation_pressure:
foreign_information_operations:
encrypted_network_adoption:
internet_resilience:
government_communications_credibility:
```

### 7.6 Emergency-health capacity

Health-system collapse can amplify institutional failure but does not require hospital-level simulation.

```yaml
emergency_bed_capacity:
trauma_capacity:
ambulance_resilience:
medicine_import_dependency:
public_health_continuity:
```

### 7.7 Diaspora / remittance / external-finance networks

Useful for both state and non-state resilience:

```yaml
diaspora_size:
remittance_dependency:
foreign_private_funding:
cross_border_family_networks:
external_political_financing_pressure:
```

No ethnic/religious diaspora is assumed to support a conflict faction.

---

## 8. Factors that should remain conditional nodes

The following should **not** exist permanently at country resolution:

- individual gang leaders;
- individual extremist cells;
- individual police stations;
- individual military units;
- individual mosques;
- individual neighborhoods;
- individual ports/terminals;
- individual power plants;
- individual influencers;
- individual politicians.

They become explicit only when they materially affect a hotspot.

---

## 9. Actor-network activation

A non-state actor becomes an explicit network node only if it crosses a materiality threshold.

Candidate materiality factors:

```text
financial_capacity
+ membership/network size
+ coercive capacity
+ territorial influence
+ logistics capability
+ public influence
+ external support
+ intelligence penetration
```

This threshold should be evidence-based and sensitivity-tested.

---

## 10. Organized-crime interaction with conflict

Organized crime should not behave like a conventional army.

Its high-level state can evolve through:

```text
NORMAL_MARKET
→ STRESS_ADAPTATION
→ BLACK_MARKET_EXPANSION
→ TERRITORIAL_INFLUENCE
→ PROTECTION_RELATIONSHIP
→ COERCIVE_LOCAL_ACTOR
```

Possible relationships with state/non-state factions:

```text
NEUTRAL
TRANSACTIONAL
COERCED
PROTECTED_BY
FINANCES
SUPPLIES
LOCALLY_ALIGNED
HOSTILE
```

Transitions remain stochastic and reversible.

---

## 11. Security-force fracture

Security forces should not have a static political allegiance variable.

A better latent model is:

```text
institutional_split_pressure =
    competing_authorities
  + command_breakdown
  + regional_conflict
  + extremist_infiltration
  + operational_fatigue
  + salary/logistics_failure
  + coercion
  + casualty_pressure
  - professional_identity
  - constitutional_legitimacy
  - command_cohesion
  - functioning_pay_and_logistics
```

Potential regimes:

```text
COHESIVE
STRAINED
SELECTIVE_NONCOMPLIANCE
COMMAND_FRACTURE
LOCALIZED_DEFECTION
MULTIPLE_COMMANDS
```

A force's members may have diverse political views while the institution remains completely cohesive.

---

## 12. Religious infrastructure

Religious infrastructure should influence only plausible social mechanisms:

- community communication;
- welfare/support networks;
- institutional leadership;
- ideological competition;
- state-religion relations;
- foreign institutional links;
- resilience/community mediation.

It must not use:

```text
number_of_mosques -> terrorism
```

as a causal equation.

For Southeast Asia, South Asia, Iran, Gulf states and the Levant, additional religious dimensions may become more important:

- Sunni / Shia;
- Ibadi;
- Alevi;
- Ahmadi;
- local Sufi institutions;
- jurisprudential school;
- state-controlled vs decentralized religious authority;
- transnational clerical institutions.

---

## 13. Computational budget

Recommended future engine budget:

### Always active

Approximately 30–60 latent state variables per country.

### Refined country

Approximately 5–20 regional nodes.

### Hot region

Approximately 3–15 metro/logistics nodes.

### Material non-state actors

Only 1–20 explicit actor networks per hotspot.

### Event clusters

Created and expired dynamically.

The exact number should be benchmarked.

This architecture allows dozens of countries without millions of permanently active variables.

---

## 14. Aggregation/de-aggregation conservation

When a country node is refined, parent-level quantities should be distributed using documented weights.

Examples:

```text
population
GDP
police
infrastructure
religious institutions
organized-crime pressure
political stress
```

When lower nodes are collapsed, they aggregate back into the parent.

The operation should preserve conserved quantities where appropriate.

---

## 15. Uncertainty across scales

Uncertainty should increase as resolution becomes finer unless strong local data exists.

Conceptually:

```text
country data    -> narrower uncertainty
regional proxy  -> wider uncertainty
city inference  -> wider again
actor behavior  -> stochastic transition
```

A detailed-looking model must not pretend to possess detailed data it does not have.

---

## 16. Recommended pre-engine roadmap

Before engine implementation:

### Phase A — finish core country data

Add remaining strategic countries using schema v0.5+.

### Phase B — add four compact missing layers

1. critical infrastructure;
2. food/fuel security;
3. regional-government topology;
4. information ecosystem.

### Phase C — normalize only high-value variables

Do not normalize every raw field.

Create approximately 30–60 engine-facing latent variables.

### Phase D — define refinement rules

Create explicit:

- refinement triggers;
- de-refinement triggers;
- persistence windows;
- uncertainty expansion rules.

### Phase E — select historical calibration cases

Use multiple unrelated crises so the model does not overfit one war or one region.

### Phase F — engine

Only then implement:

- state transitions;
- stochastic shocks;
- network contagion;
- Monte Carlo;
- sensitivity analysis.

---

## 17. Design principle

The simulator should become more detailed **because the simulated world becomes unstable**, not because the codebase contains more data.

That is the core fractal rule:

> resolution follows stress.

This provides a realistic path from stable-state aggregates to localized crisis dynamics without making the baseline model unmanageably large.

---

**End of Adaptive Fractal Simulation Architecture.**
