# Factor Model v0.2 — Demography, Force Structure and Modern Warfare

**Canonical status:** normative model specification  
**Applies to:** all country and institutional nodes  
**Baseline date:** 2026-09-22  
**Purpose:** define the variables that must exist before the simulation engine is implemented.

This document does not assign automatic political or military loyalty to demographic groups. Demographic data describe populations; violent organizations, armed factions and state forces are separate model entities.

---

## 1. Population and manpower

Every country node must contain a population snapshot with provenance and reference year.

### 1.1 Required population fields

```yaml
population:
  total: null
  reference_year: null
  source: null

  age:
    under_15: null
    age_15_17: null
    age_18_24: null
    age_25_44: null
    age_45_64: null
    age_65_plus: null

  sex:
    male: null
    female: null

  citizenship:
    citizens: null
    non_citizens: null

  urbanization:
    urban_share: null

  direct_military_manpower:
    legally_eligible: null
    medically_fit_estimate: null
    trained_or_prior_service: null
    immediately_available: null
    mobilizable_30d: null
    mobilizable_180d: null
    sustainable_365d: null

  non_direct_manpower:
    children: null
    elderly: null
    medically_unavailable: null
    essential_civilian_workforce: null
```

The World Bank/UN 15–64 indicator may be used as a broad demographic input, but **must never be treated as a military manpower count**.

### 1.2 Direct versus indirect relevance

People outside direct military age are not "irrelevant" to the conflict. They should be excluded from direct combat manpower while still affecting:

- humanitarian demand;
- health-system load;
- food demand;
- industrial labor;
- public administration;
- family dependency ratios;
- political pressure;
- displacement;
- social resilience.

The simulator therefore distinguishes:

- `direct_military_manpower`;
- `essential_civilian_workforce`;
- `dependent_population`;
- `humanitarian_load`.

---

## 2. Religion, origin and generation

### 2.1 Required rule

Religion and generation may be stored only when supported by a cited public dataset.

Permitted fields:

```yaml
demography:
  religion:
    christian: null
    muslim: null
    jewish: null
    unaffiliated: null
    other: null
    unknown: null

  migration_generation:
    foreign_born: null
    native_born_with_foreign_born_parent: null
    later_generation: null
    unknown: null

  religion_by_generation:
    muslim_first_generation: null
    muslim_second_generation: null
    muslim_third_plus_generation: null
    christian_first_generation: null
    christian_second_generation: null
    christian_third_plus_generation: null
```

### 2.2 Missing-data policy

The joint variables under `religion_by_generation` are populated **only** when an official or high-quality survey actually publishes that cross-tabulation.

Forbidden inference methods include:

- surnames;
- neighborhoods;
- nationality alone;
- ancestry alone;
- language alone;
- country of birth alone;
- mosque/church density;
- electoral results.

When unavailable:

```yaml
value: null
quality: unavailable
imputed: false
```

No synthetic religious-generation estimate may silently enter the baseline.

---

## 3. Armed forces personnel

Each country must distinguish personnel pools.

```yaml
forces:
  active_total: null
  active_land: null
  active_naval: null
  active_air: null
  active_joint_support: null
  active_cyber_space: null

  reserve_total: null
  reserve_ready: null
  reserve_training_quality: null

  paramilitary_total: null
  gendarmerie_total: null
  national_guard_total: null

  readiness:
    deployable_share: null
    training_level: null
    personnel_fill_rate: null
    fatigue: null
    morale: null
    command_cohesion: null
```

Personnel counts must retain a `reference_year` because many open estimates lag reality.

### 3.1 Provisional source hierarchy

1. national defence ministry / official budget;
2. NATO official personnel data when available;
3. IISS *Military Balance* or equivalent professional source;
4. authoritative parliamentary/research publications;
5. CIA World Factbook estimates as fallback;
6. secondary sources only with explicit quality downgrade.

The CIA 2022 archive gives a useful initial cross-country fallback: approximately 120,000 active-duty troops for Spain, 200,000 for Morocco, 205,000 for France, 184,000 for Germany, 170,000 for Italy and 153,000 regular forces for the United Kingdom. These values are **provisional historical baselines**, not 2026 current-strength claims.

---

## 4. Military domains

Military capability must be decomposed into domains rather than one global "army power" number.

### 4.1 Land

Variables:

- active land personnel;
- mechanized capacity;
- armored capacity;
- indirect-fire capacity;
- long-range fires;
- engineering;
- mobility;
- protected mobility;
- battlefield logistics;
- ground-based air defence;
- territorial defence;
- reserve integration.

### 4.2 Air

Variables:

- combat-air mass;
- sortie-generation capacity;
- pilot/training depth;
- airborne early warning;
- aerial refuelling;
- strategic/tactical transport;
- rotary-wing capacity;
- airbase resilience;
- precision-strike capacity;
- integrated air-defence penetration index;
- maintenance/spares.

### 4.3 Naval

Variables:

- surface-combatant capacity;
- submarine capacity;
- amphibious capacity;
- mine warfare;
- maritime patrol;
- naval aviation;
- sealift/logistics;
- anti-submarine warfare;
- port resilience;
- maintenance/spares.

### 4.4 Space / ISR / C4ISR

Variables:

- satellite access;
- commercial satellite access;
- reconnaissance quality;
- persistent surveillance;
- secure communications;
- positioning/navigation resilience;
- command-and-control resilience;
- sensor-to-decision latency;
- allied ISR access.

---

## 5. Weapon-category abstraction

Version 1 will **not** track individual weapon models.

Inventory is represented through categories and effective-capability scores.

### 5.1 Categories

```text
INFANTRY_SYSTEMS
PROTECTED_MOBILITY
ARMORED_SYSTEMS
INDIRECT_FIRE
LONG_RANGE_FIRES
GROUND_AIR_DEFENCE
COMBAT_AIR
AIR_SUPPORT
ROTARY_WING
SURFACE_NAVAL
SUBMARINE
AMPHIBIOUS
MARITIME_PATROL
UNCREWED_AERIAL_SYSTEMS
UNCREWED_GROUND_SYSTEMS
UNCREWED_MARITIME_SYSTEMS
COUNTER_UAS
ELECTRONIC_WARFARE
CYBER_CAPABILITY
ISR_C4ISR
ENGINEERING
LOGISTICS
PRECISION_MUNITIONS
MASS_MUNITIONS
```

### 5.2 Effective inventory

A raw inventory count is not enough.

For category `c`:

```text
effective_capability[c] =
    nominal_inventory[c]
  × readiness[c]
  × maintenance[c]
  × trained_crews[c]
  × ammunition_depth[c]
  × sensor_network[c]
  × communications_resilience[c]
  × logistics_support[c]
```

All multiplicative factors are normalized and calibrated.

The formula is conceptual; implementation may use a bounded/nonlinear transform to avoid unrealistic collapse from a single noisy variable.

---

## 6. Capability weighting

Weights are **scenario dependent**.

No universal ranking is canonical.

### 6.1 Capability vector

```text
K =
[
  manpower,
  land,
  air,
  naval,
  air_defence,
  drones,
  counter_uas,
  ew,
  cyber,
  isr_c4isr,
  intelligence,
  logistics,
  industrial_rearmament,
  reserve_mobilization,
  ai_enabled_capability
]
```

### 6.2 Weighted score

```text
military_capacity_index = Σ(weight[i] × normalized_capability[i])
```

Weights must sum to 1.0.

### 6.3 Canonical profiles

The repo will eventually provide configurable weight profiles, for example:

- `IBERIAN_STRAIT_INTERSTATE`
- `CONTINENTAL_HIGH_INTENSITY`
- `URBAN_INTERNAL_SECURITY`
- `MEDITERRANEAN_MARITIME`
- `SAHEL_INSURGENCY`
- `PROLONGED_ATTRITION`

This prevents naval power from receiving the same relevance in a landlocked Sahel scenario as in the Strait of Gibraltar.

---

## 7. Lessons from modern high-intensity warfare

The Russia–Ukraine war demonstrates that conventional platforms alone are insufficient.

The model must include at least the following factors.

### 7.1 Cheap drones and mass uncrewed systems

Variables:

- `cheap_uas_production_rate`
- `cheap_uas_import_access`
- `fpv_equivalent_mass_index`
- `recon_uas_density`
- `loitering_munition_capacity`
- `autonomy_level`
- `drone_operator_training_pipeline`
- `drone_loss_replacement_rate`
- `commercial_component_dependency`

Strategic lesson: low-cost drones can generate disproportionate battlefield effects, but their value depends on scale, replacement, communications, EW conditions and component supply.

### 7.2 Counter-UAS

Variables:

- kinetic counter-UAS;
- electronic counter-UAS;
- detection coverage;
- interceptor cost efficiency;
- magazine depth;
- adaptation rate.

### 7.3 Electronic warfare

Variables:

- jamming capacity;
- spectrum awareness;
- navigation denial resilience;
- frequency agility;
- communications resilience;
- EW production/replacement;
- EW adaptation cycle.

### 7.4 Distributed sensing and reconnaissance

Variables:

- sensor density;
- commercial imagery access;
- targeting/decision-chain latency at aggregate level;
- reconnaissance persistence;
- data fusion quality.

The simulator does not model target selection.

### 7.5 Logistics under observation

Variables:

- logistics dispersion;
- transport redundancy;
- stockpile dispersion;
- repair nodes;
- fuel resilience;
- port/rail/road redundancy;
- contested-logistics penalty.

### 7.6 Air defence and missile defence

Variables:

- layered defence;
- interceptor stock depth;
- replacement rate;
- radar/sensor resilience;
- point-defence density;
- cost-exchange sustainability.

### 7.7 Fortification, engineering and adaptation

Variables:

- engineering capacity;
- field fortification rate;
- mine-clearance/obstacle-management index at strategic level;
- rapid adaptation;
- lessons-learned cycle;
- civil-military innovation link.

---

## 8. Rearmament and war economy

A state's initial arsenal and its ability to regenerate combat power are separate.

### 8.1 Core variables

```yaml
war_industry:
  defence_spending:
    current_usd: null
    share_gdp: null

  industrial_base:
    domestic_arms_industry_score: null
    ammunition_capacity: null
    drone_capacity: null
    vehicle_capacity: null
    aerospace_capacity: null
    naval_shipbuilding_capacity: null
    electronics_capacity: null

  regeneration:
    repair_capacity: null
    replacement_rate: null
    surge_multiplier_90d: null
    surge_multiplier_365d: null
    workforce_expandability: null

  supply_chain:
    import_dependency: null
    critical_component_dependency: null
    semiconductor_access: null
    explosives_propellant_access: null
    energy_dependency: null
    shipping_dependency: null

  finance:
    fiscal_war_capacity: null
    borrowing_capacity: null
    inflation_tolerance: null
```

NATO's Industrial Capacity Expansion Pledge explicitly treats industrial capacity, production, critical munitions, air/missile defence, joint procurement and resilient supply chains as core defence variables.

SIPRI military-expenditure, arms-transfer and arms-industry datasets are canonical sources for this layer.

---

## 9. Mobilization and replacement

Variables:

- reserve size;
- reserve readiness;
- conscription system;
- training throughput;
- officer/NCO depth;
- equipment available for newly formed units;
- casualty replacement;
- industrial workforce competition;
- public willingness to serve;
- draft evasion / noncompliance;
- mobilisation legitimacy.

The model must separate:

```text
human beings theoretically of age
!=
trained replacement personnel
!=
equipped deployable personnel
```

---

## 10. Intelligence capability

Each state receives an aggregate intelligence architecture rather than a list of covert operations.

### 10.1 Intelligence dimensions

- HUMINT capacity;
- SIGINT capacity;
- GEOINT/IMINT access;
- OSINT capability;
- cyber-intelligence;
- counterintelligence;
- domestic threat detection;
- analytic fusion;
- strategic warning;
- allied intelligence sharing;
- linguistic/regional expertise;
- institutional coordination.

### 10.2 Intelligence effectiveness

```text
intelligence_effectiveness =
  collection_quality
× analysis_quality
× dissemination_quality
× decision_maker_trust
× counterintelligence_resilience
```

Again, implementation should bound this nonlinear relationship.

---

## 11. Artificial intelligence and military technological acceleration

AI must be a **dynamic capability**, not a fixed national bonus.

NATO's revised AI strategy explicitly treats AI as a rapidly evolving general-purpose technology for defence, including interoperability, data readiness, responsible adoption and protection against adversarial AI use.

Stanford's 2026 AI Index reports that in 2025 U.S.-based institutions produced 59 notable AI models and Chinese institutions 35, while China led several research-volume measures. It also reports extremely rapid global compute growth and major concentration of advanced AI infrastructure and semiconductor manufacturing.

### 11.1 National AI capacity

```yaml
ai:
  frontier_model_access: null
  domestic_model_capability: null
  compute_capacity: null
  data_center_capacity: null
  semiconductor_access: null
  advanced_fab_access: null
  electricity_for_compute: null
  ai_talent: null
  ai_research_strength: null
  open_model_access: null
  cloud_access: null
  cyber_ai_capability: null
  defence_ai_integration: null
  autonomous_systems_maturity: null
  ai_enabled_isr: null
  ai_enabled_logistics: null
  ai_enabled_ew: null
  ai_enabled_information_operations: null
  model_security: null
  allied_ai_access: null
```

### 11.2 Technological growth

Do not use an unbounded exponential.

Use a combination of:

- logistic/S-curve adoption;
- compute growth;
- learning curves;
- diffusion;
- sanctions/export controls;
- energy constraints;
- chip availability;
- talent;
- wartime acceleration;
- battlefield feedback.

Conceptually:

```text
AI_capability(t+1) =
    AI_capability(t)
  + R&D_gain
  + compute_gain
  + diffusion_gain
  + battlefield_learning
  - supply_constraints
  - cyber_loss
  - export_control_penalty
  - energy_constraint
```

### 11.3 AI power is not binary

The model must not encode "countries that control AI" as yes/no.

Use tiers generated from evidence:

- frontier developer;
- high-capability adopter;
- allied-access adopter;
- open-model adopter;
- constrained adopter;
- low-access actor.

Tier assignment must be dated because this field can change rapidly.

---

## 12. Cyber and information warfare

Variables:

- offensive cyber capacity;
- defensive cyber maturity;
- critical-infrastructure cyber resilience;
- military-network resilience;
- cloud dependency;
- identity/credential resilience;
- disinformation production;
- bot/amplification capacity;
- synthetic-media capability;
- public media literacy;
- platform cooperation;
- attribution confidence.

AI can modify several of these variables over time.

---

## 13. Political leadership and elite interests

"High-level interests" must be modeled through observable actor incentives rather than unsupported conspiracy assumptions.

### 13.1 State leadership utility

Potential objectives:

- regime/government survival;
- territorial integrity;
- alliance credibility;
- economic continuity;
- ideological commitments;
- electoral/public support where applicable;
- elite-coalition cohesion;
- avoiding military defeat;
- international prestige;
- control of strategic infrastructure;
- energy security.

### 13.2 Elite and institutional variables

- `elite_cohesion`
- `elite_fragmentation`
- `civil_military_alignment`
- `bureaucratic_cohesion`
- `security_service_loyalty`
- `defence_industry_influence`
- `major_business_war_exposure`
- `energy_sector_war_exposure`
- `financial_sector_war_exposure`
- `foreign_asset_exposure`
- `sanctions_vulnerability`
- `corruption_or_state_capture_proxy`

World Bank Worldwide Governance Indicators can provide baseline proxies for political stability, government effectiveness, rule of law and control of corruption. OECD trust data and V-Dem may supplement democratic/institutional variables where applicable.

### 13.3 No hidden-mastermind variable

The model must not contain an unobservable variable such as:

`secret_elite_plan`

Instead, elite behavior emerges from explicit incentives, institutional position, economic exposure and documented relationships.

---

## 14. Public willingness and national resilience

Military capacity is degraded if society cannot sustain the conflict.

Variables:

- public support for government;
- public support for war;
- tolerance for casualties;
- trust in armed forces;
- trust in government;
- perceived legitimacy of mobilisation;
- social solidarity;
- protest intensity;
- economic hardship;
- war fatigue;
- volunteer rate;
- desertion/noncompliance pressure.

These must be dynamic.

---

## 15. Economic and energy sustainment

Add:

- GDP;
- GDP per capita;
- government revenue;
- debt burden;
- foreign reserves;
- industrial electricity;
- oil dependency;
- gas dependency;
- refinery capacity;
- food import dependency;
- strategic commodity access;
- maritime trade dependency;
- sanctions exposure;
- payment-system resilience.

A country may possess strong forces but lose effective capacity if energy, finance or logistics collapse.

---

## 16. Geography and strategic depth

Variables:

- land area;
- population density;
- border length;
- coastline;
- mountainous terrain share;
- urban concentration;
- island dependencies;
- strategic depth;
- number of major ports;
- airbase dispersion;
- transport redundancy;
- proximity to allies;
- proximity to adversaries;
- chokepoint exposure.

For Spain specifically:

- Strait of Gibraltar exposure;
- Ceuta/Melilla isolation;
- Atlantic access;
- Mediterranean access;
- Portuguese rear-area stability;
- French land-corridor dependency.

---

## 17. Alliance interoperability

Raw allied strength is not simply additive.

Variables:

- common standards;
- shared munitions;
- communications interoperability;
- command integration;
- political authorization latency;
- cross-border logistics;
- intelligence-sharing level;
- combined training;
- maintenance compatibility.

This layer is essential for NATO/EU and for ad-hoc coalitions.

---

## 18. Attrition and regeneration

Every major capability category must track:

```yaml
capability:
  starting_stock: null
  available_stock: null
  readiness: null
  daily_loss_pressure: null
  repair_rate: null
  domestic_replacement_rate: null
  allied_replacement_rate: null
  import_replacement_rate: null
  training_replacement_rate: null
```

The strategic simulator does not calculate individual strikes. Loss pressure is generated by aggregate conflict intensity and relative capability.

---

## 19. Data quality and provenance

Every empirical field must carry:

```yaml
value: null
unit: null
reference_date: null
source_url: null
source_name: null
quality: high | medium | low | unavailable
estimated: false
imputed: false
notes: null
```

Conflicting sources must be stored rather than silently overwritten.

---

## 20. Canonical data sources

### Population / age

- UN World Population Prospects;
- World Bank World Development Indicators;
- Eurostat;
- national statistics offices.

### Religion

- Pew Research Center;
- censuses where religion is collected;
- high-quality national surveys.

### Military personnel / forces

- national defence ministries;
- NATO;
- IISS;
- parliamentary defence reports;
- CIA World Factbook as fallback.

### Military spending / arms / industry

- SIPRI Military Expenditure Database;
- SIPRI Arms Transfers Database;
- SIPRI Arms Industry Database;
- national budgets and procurement plans.

### Conflict / terrorism

- ACLED;
- Europol;
- UN reporting;
- national security reporting.

### Institutions / elites / trust

- World Bank WGI;
- V-Dem;
- OECD Trust Survey;
- national polling with provenance.

### AI

- Stanford AI Index;
- NATO AI strategy and implementation documents;
- national AI/defence strategies;
- semiconductor and data-centre statistics with dated provenance.

---

## 21. Pre-engine acceptance criteria

The simulation engine must **not** be implemented until the data model can represent:

- total population and age structure;
- religion with explicit unknowns;
- generation/origin with explicit unknowns;
- direct military manpower;
- active/reserve/security personnel;
- land/air/naval capability;
- weapon categories;
- drones and counter-UAS;
- EW;
- ISR/C4ISR;
- cyber;
- intelligence;
- industrial rearmament;
- replacement/repair;
- logistics;
- energy/economy;
- AI capability and growth;
- institutional/elite cohesion;
- alliance interoperability;
- public resilience;
- geography;
- data provenance.

The first data snapshot should then populate the Phase-1 countries before any simulation result is considered meaningful.
