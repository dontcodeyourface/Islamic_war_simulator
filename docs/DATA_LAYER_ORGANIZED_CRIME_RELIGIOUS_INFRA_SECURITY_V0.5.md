# Data Layer v0.5 — Organized Crime, Religious Infrastructure and Security-Force Cohesion

**Status:** canonical pre-engine enrichment  
**Snapshot date:** 2026-09-23  
**Countries:** Spain, Morocco, France, United Kingdom, Germany

---

## 1. Purpose

This layer adds three classes of actors and institutions that were under-represented in earlier snapshots:

1. organized-crime markets and criminal networks;
2. Muslim religious infrastructure and Islamic institutional traditions;
3. law-enforcement capacity and security-force cohesion.

The engine remains unimplemented.

The purpose of this layer is to preserve evidence and causal structure before any scoring or faction-assignment logic is introduced.

---

## 2. Organized crime is not an ideological faction by default

The canonical model treats organized-crime groups primarily as economic/coercive networks.

Examples include:

- cocaine trafficking networks;
- cannabis/hashish trafficking networks;
- illicit-firearms networks;
- Mocro-Maffia-linked networks;
- Western Balkan organized-crime groups;
- Latin-American-origin street gangs;
- clan-based networks;
- other transnational organized-crime groups.

No criminal network is assigned automatically to an Islamist, Christian, left-wing, right-wing or state faction.

The default state is:

```text
ideological_alignment = predominantly_profit_seeking_nonideological
likely_conflict_alignment = opportunistic_unknown
```

A future conflict-alignment transition may depend on:

- profit;
- access to territory;
- coercion;
- family/network ties;
- protection arrangements;
- prison relationships;
- weapons access;
- disruption of normal markets;
- pressure from state/non-state actors;
- local political control.

Ethnicity, religion or gang branding is not sufficient evidence.

---

## 3. Why individual mafia leaders are not canonical country variables

Individual leaders can matter operationally, but storing names in the country baseline would make the model:

- fragile to arrests/deaths/succession;
- unnecessarily person-centric;
- difficult to maintain;
- prone to confusing one leader with an entire network.

The country layer therefore stores structural leadership properties:

```yaml
leadership_centralization:
succession_resilience:
network_fragmentation:
international_reach:
```

If a later scenario requires a specific leadership node, it should be instantiated dynamically as a lower-level actor.

This preserves realism without making the country baseline depend on continuously changing personalities.

---

## 4. Drug-market scope

Only three illicit-market categories are canonical in v0.5:

1. **COCAINE**
2. **CANNABIS_HASHISH**
3. **ILLICIT_FIREARMS**

Other drug categories remain outside the core model unless future evidence shows they materially change the conflict system.

This deliberately limits state-space growth.

---

## 5. Spain

### Religious infrastructure

Current public-data baseline:

- approximately **1,872** mosque/Islamic-association/community entries;
- derived from 23% of 8,140 non-Catholic worship/community entries in the public religious-pluralism dataset.

This is **not** equivalent to 1,872 purpose-built mosque buildings.

The Spanish Muslim institutional landscape is treated as plural and decentralized.

Sunni predominance and Maliki influence are stored only as low-confidence structural estimates; no national sect/fiqh census is available.

### Organized crime

Spain is modeled as a major European entry/transit/domestic node for cocaine and hashish.

The 2025 official drug statistics report:

- approximately 370 tonnes of cocaine, hashish, heroin and marijuana seized in total;
- approximately **257 tonnes of hashish**;
- approximately 875,000 cannabis plants seized.

Multiple recent official investigations document criminal organizations linked to the label **Mocro Maffia**.

This is stored as:

```yaml
mocro_maffia_linked_presence: documented
```

with an explicit note that this describes a criminal-network relationship, not Islamist ideology.

Recent police investigations also document active Latin-American-origin violent youth/street gangs, including groups using labels such as DDP and Trinitarios.

Again:

```text
gang identity != Christian political alignment
```

### Illicit firearms

Recent Spanish narcotics investigations document access by some networks to substantial firearms, including military-style rifles.

The model stores only:

- material network-specific firearms access;
- linkage between firearms and narcotics markets;
- criminal violence capacity.

It does not encode weapon-storage locations, trafficking routes or tactical use.

### Law enforcement

Current national baseline:

- **183,150 combined Policía Nacional + Guardia Civil personnel** in 2026;
- this excludes autonomous-community police and municipal police.

The exact national total across all Spanish policing systems therefore remains larger but unpopulated.

### Cohesion

No law-enforcement faction is given a left/right loyalty coefficient.

Political heterogeneity is acknowledged, but future split/defection variables require evidence of institutional fracture.

---

## 6. France

### Religious infrastructure

Official parliamentary material refers to approximately **2,600 mosques**.

France's Islamic institutional landscape is treated as heterogeneous and predominantly Sunni, with substantial Maghrebi and Turkish institutional traditions.

Exact population-level fiqh/sect percentages remain unknown.

### Organized crime

French official material describes narcotrafficking as a major nationwide security issue.

Current public indicators include:

- estimated narcotrafficking turnover around **EUR 6.8 billion**;
- approximately **200,000 people** involved across the market;
- **42 tonnes of cocaine** seized in the first half of 2025, already above the full-year 2024 figure cited by the Interior Ministry.

The model does not assign national control to one mafia.

Instead:

```text
national_market_structure =
    polycentric_fragmented_national_and_transnational
```

### Firearms

The Gendarmerie reports that firearms trafficking has been rising and is strongly associated with narcotics crime.

This becomes:

- firearms access;
- criminal violence capacity;
- drug/firearm linkage.

It is not converted into an armed-force inventory.

### Law enforcement

The current public personnel baselines have different statistical scopes:

- Police nationale: **152,197 agents** in March 2026;
- Gendarmerie: public institutional material describes nearly/more than **130,000 personnel**, including active and reserve components.

Because these scopes differ, v0.5 does not add them into one false precision total.

---

## 7. United Kingdom

### Religious infrastructure

The current independent mosque directory reports approximately:

- **1,895 actual masjids**;
- **2,187 total places available for salah** when broader prayer facilities are included.

The canonical count uses the narrower 1,895 definition.

The institutional landscape is predominantly Sunni and highly diverse.

Mosque-directory data show especially prominent:

- Deobandi traditions;
- Bareilvi traditions;
- other Sunni institutions;
- Shia and other minority traditions.

These are institutional/religious categories, not political-radicalisation scores.

### Organized crime

The 2026 NCA assessment identifies cocaine as a high threat.

Public indicators include:

- approximately **18.5 tonnes of cocaine seized in 2025**;
- approximately **127 tonnes of cannabis seized at the UK border** in the year ending March 2025.

The NCA assesses Western Balkan organized-crime groups as retaining the highest level of control over end-to-end cocaine supply into the UK.

This is modeled as partial wholesale-market concentration, not monopoly.

### Firearms

The NCA describes criminal firearms availability as constrained compared with some other countries, but still material to serious organized crime.

The model therefore distinguishes:

```text
criminal firearms availability
!=
military firearms availability
```

### Law enforcement

Approximate territorial-police officer baseline:

- England and Wales: 145,886 FTE;
- Police Scotland establishment: 16,564;
- PSNI: 6,444 FTE.

Near-current composite:

**~168,894 territorial police officers**

The definitions/dates are not perfectly identical, so the figure is marked estimated/medium-quality rather than exact.

---

## 8. Germany

### Religious infrastructure

Germany does not maintain a complete national mosque register.

The Bundestag Scientific Services estimated approximately **2,800 mosques** in 2019.

This value therefore receives substantial freshness decay.

Germany has unusually useful official-linked Muslim branch estimates:

- Sunni: ~74%;
- Alevi: ~8%;
- Shia: ~4%;
- Ahmadi: ~1%;
- other: ~1%;
- unaffiliated/undisclosed: ~12%.

These percentages describe religious affiliation, not political behavior.

### Organized crime

BKA 2023 data show:

- cocaine offences increased by 27.4%;
- approximately **43 tonnes of cocaine** were seized;
- cannabis represented roughly two thirds of recorded drug offences;
- approximately 20.9 tonnes of marijuana and 3.7 tonnes of hashish were seized.

The BKA identifies drug trafficking, especially cannabis and cocaine, as the dominant organized-crime activity.

### Firearms

In 2024:

- nine organized-crime groups had firearms trafficking/smuggling as their primary activity;
- 80 suspects were associated with those investigations.

BKA also notes firearms crime frequently accompanies drug crime.

### Law enforcement

Destatis provides unusually useful institutional topology.

At 30 June 2024:

- total police-function workforce: approximately **342,500 FTE**;
- official/Beamte component: approximately **294,000 FTE**;
- federal police-function workforce: 60,600;
- Länder/city-state police-function workforce: approximately 281,900.

The broader workforce includes administration, training and specialist institutions, so the 294,000 official component is retained as the closer—but still imperfect—officer proxy.

---

## 9. Morocco

### Religious infrastructure

Morocco differs structurally from the European cases.

The Ministry of Habous inventory reports:

- 24,106 Friday mosques;
- 27,748 five-daily-prayer mosques;

for a combined inventory of approximately **51,854 mosques**.

The figure is official but older and therefore receives freshness decay.

The official religious architecture is stored as:

```yaml
dominant_islamic_branch: Sunni
predominant_fiqh_school: Maliki
theological_tradition: Ashari_with_state_supported_Sufi_tradition
religious_governance_centralization: high_state_centralization
state_supervision: high
```

This distinction will become more important when Southeast Asian, Gulf, Iranian and South Asian states are added, where Islamic branch/tradition differs substantially.

### Organized crime

Morocco is represented as:

- major source/transit node for cannabis resin;
- growing transit interface for cocaine between Atlantic Africa, Europe and wider transnational networks;
- connected to multiple European criminal ecosystems.

The label Mocro Maffia is **not** modeled as a Moroccan Islamist organization.

Instead it appears only as a transnational diaspora-criminal-network linkage.

### Law enforcement

A reliable current total DGSN personnel stock was not located.

Therefore it remains null.

Available 2025 recruitment-flow information shows:

- 4,693 recruits entering training;
- 6,733 competition positions;
- 6,450 newly trained officers assigned.

These are flows, not total force size.

The Royal Gendarmerie retains the older approximately 20,000-person fallback already documented in the military/security snapshot.

---

## 10. Security-force political tendencies

Political attitudes inside armed and security institutions may matter during genuine state fracture.

However, the canonical model rejects:

```text
vote preference -> defection probability
```

or:

```text
dislike of government -> insurgent alignment
```

These are not equivalent relationships.

Instead the schema stores:

```yaml
constitutional_loyalty:
command_cohesion:
professional_identity:
political_heterogeneity:
partisan_preference_evidence:
union_or_association_fragmentation:
regional_identity_pressure:
extremist_infiltration_cases:
disciplinary_stress:
public_order_fatigue:
government_force_relations:
pay_working_conditions_pressure:
defection_hazard:
insubordination_hazard:
institutional_split_risk:
```

Most remain null before a crisis.

That is intentional.

---

## 11. What should drive security-force fracture

A future institutional-fracture model should be conditional on factors such as:

- competing constitutional authorities;
- breakdown of legal chain of command;
- territorial fragmentation;
- refusal of orders by organized units;
- regional-government control over police;
- military/police command conflict;
- extremist infiltration;
- sustained casualty/operational stress;
- unpaid salaries or logistical collapse;
- public-order fatigue;
- split intelligence institutions;
- mutiny/insubordination events;
- coercion against officers' families;
- strong local/regional identity conflicts.

Only after these conditions appear should `defection_hazard` or `institutional_split_risk` rise substantially.

---

## 12. What is deliberately NOT in the core country layer

To avoid over-sizing the future engine, v0.5 does not permanently instantiate:

- individual mafia bosses;
- individual mosques;
- every gang chapter;
- individual police units;
- every police union;
- every municipality;
- individual ports/warehouses/routes;
- individual politicians;
- individual clerics.

These can become lower-level nodes only when a scenario requires them.

---

## 13. Core causal use of organized crime

Organized crime should affect the future simulator through a limited number of channels:

```text
criminal_finance
criminal_logistics
black_market_supply
firearms_access
territorial_influence
corruption_pressure
money_laundering
prison_networks
violence_capacity
state_revenue_loss
police_intelligence_burden
```

This is sufficient to represent criminal power without turning the simulator into a detailed organized-crime game.

---

## 14. Engine gate

Before this layer becomes executable:

1. categorical variables must receive evidence-based normalization;
2. market-control variables require common definitions;
3. criminal-network alignment must remain stochastic/opportunistic;
4. security-force factionalism must be crisis-conditional;
5. mosque counts must remain infrastructure variables, not radicalisation coefficients;
6. lower-level actor nodes must be instantiated adaptively, not globally;
7. no tactical trafficking, weapons-procurement or attack-routing logic is introduced.

---

**End of Data Layer v0.5.**
