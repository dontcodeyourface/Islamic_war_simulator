# EURO-MENA SYSTEMIC CONFLICT SIMULATOR

## Canonical Scenario Specification

**Status:** Canonical baseline v0.2  
**Baseline date:** 2026-09-22  
**Purpose:** Strategic simulation / stress testing  
**Scope:** Europe, North Africa, Sahel, Middle East and external great-power intervention  
**Model class:** Hybrid stochastic system-dynamics / network-contagion simulator  

> This repository explores a deliberately extreme tail-risk scenario. It is **not a forecast** and must never present scenario assumptions or simulation outputs as verified real-world facts.

---

## 1. Objective

This repository models how a localized Spain–Morocco crisis centered on Ceuta/Melilla could, under deliberately severe assumptions, propagate through:

1. Spain as an interstate security crisis;
2. Spanish domestic political and social stability;
3. France and neighboring European states;
4. transnational violent-extremist networks;
5. reciprocal nationalist/anti-Muslim violent mobilization;
6. revolutionary or anti-system violent movements;
7. North Africa and the Sahel;
8. the wider Middle East;
9. NATO/EU alliance dynamics;
10. energy, trade, migration and humanitarian systems;
11. external powers such as the United States, Russia and China;
12. a possible multipolar systemic conflict.

The simulator must distinguish rigorously between:

- **verified baseline facts**;
- **scenario assumptions**;
- **model parameters**;
- **stochastic shocks**;
- **simulation-generated outcomes**.

No generated outcome may later be presented as though it were a baseline fact.

Detailed pre-engine capability specification: [docs/FACTOR_MODEL.md](docs/FACTOR_MODEL.md).

---

## 2. Core analytical rule

> Population identity is not equivalent to combatant alignment.

Religion, ethnicity, nationality or political affiliation may affect social networks, narratives and mobilization pressure, but the simulator must never convert an entire civilian population into a military faction.

Therefore:

- Muslim population != Islamist insurgency.
- Christian population != Christian militia.
- Conservative population != ultranationalist violence.
- Left-wing population != revolutionary violence.
- Immigrant/refugee population != hostile actor.
- Moroccan ancestry != loyalty to Morocco.
- European citizenship != automatic loyalty to a particular government faction.

Violent actors are represented as **separate network variables** whose growth depends on recruitment, grievance, propaganda, organizational capability, state weakness, external support, reciprocal violence and other modeled mechanisms.

This distinction is mandatory for every implementation.

---

# PART I — VERIFIED BASELINE

## 3. Europe: religion and social composition

The current canonical demographic baseline is Pew Research Center's 2020 reconstruction for Europe:

- population: approximately **753 million**;
- Christians: approximately **67%**;
- religiously unaffiliated: approximately **25%**;
- Muslims: approximately **6%**, around **46 million people**.

This creates two modeling constraints:

1. Europe contains large Muslim communities, including citizens of first, second and later generations.
2. Those communities are not a single political or military bloc.

**Canonical source:** Pew Research Center, *Religion in Europe* (2025).

## 4. EU terrorism landscape

Europol's EU TE-SAT 2026 describes a fragmented terrorism environment rather than a binary religious conflict.

For 2025 Europol reported:

- 45 terrorist attacks in the EU;
- 24 classified as jihadist;
- 347 of 486 terrorism-related arrests linked to jihadist terrorism;
- right-wing, left-wing/anarchist, separatist and other anti-system forms also remained present.

The simulator therefore represents multiple extremist ecosystems simultaneously.

**Canonical source:** Europol, *EU Terrorism Situation and Trend Report 2026*.

## 5. Ceuta crisis baseline

As of September 2026, Ceuta is experiencing an exceptional migration and political crisis following a mass border incident in July.

The baseline includes:

- a very large July crossing from Morocco;
- a remaining migrant population in Ceuta;
- significant political polarization around the episode;
- continuing Spain–Morocco communication intended to avoid renewed mass border pressure.

This baseline must **not** automatically become an interstate war in the model. Interstate war is an explicit scenario shock.

## 6. Morocco's international position

Morocco must not be hard-coded into an anti-Western bloc.

Relevant baseline:

- Morocco is a U.S. **Major Non-NATO Ally**;
- Morocco participates in NATO's **Mediterranean Dialogue**;
- Morocco maintains extensive defense/counterterrorism relationships with the U.S. and Europe.

Therefore, a Spain–Morocco war creates alliance contradictions before any broader ideological alignment emerges.

## 7. NATO and EU

### NATO

Article 5 establishes collective defense following an armed attack within treaty scope. Article 6 defines geographic scope. Ceuta/Melilla require separate legal/political handling rather than assumptions of automatic NATO behavior.

### European Union

Article 42(7) TEU establishes the EU mutual-assistance clause.

The simulator must model NATO and EU responses as **distinct mechanisms**.

## 8. France and Africa

The simulator must not describe sovereign African states as current French colonies.

The factual model variable is:

`french_africa_influence`

not:

`french_sovereignty_over_africa`.

France historically maintained extensive military, political and economic influence across parts of Africa, but that footprint has sharply contracted. Its actual overseas territories are a different legal category and must not be mixed with sovereign former colonies.

## 9. Sahel security baseline

The Sahel is already a high-conflict environment.

Canonical baseline mechanisms include:

- expansion of JNIM and Islamic State Sahel Province;
- cross-border activity;
- pressure on Mali, Burkina Faso and Niger;
- attacks on state forces and civilians;
- displacement;
- weakened state control in some areas.

The Sahel is therefore modeled as a potential **amplifier**, not an automatic member of a European conflict bloc.

## 10. Religious violence in Africa

The model includes `sectarian_violence` because religiously framed violence can become a major propaganda input into European polarization.

The baseline remains multi-causal:

- jihadist violence;
- attacks on Christian communities;
- attacks on Muslim civilians;
- ethnic, economic, territorial and criminal drivers.

Canonical mechanism:

`local violence -> transnational narrative amplification -> reciprocal mobilization`

not:

`religion -> automatic combatant alignment`.

---

# PART II — HYPOTHETICAL SCENARIO

## 11. Central scenario

> A severe Ceuta/Melilla crisis escalates into armed confrontation between Spain and Morocco. The interstate conflict interacts with political polarization, terrorism and extremist networks. Reciprocal violent mobilization spreads through parts of Europe while instability in the Sahel and Middle East intensifies. European and regional states face simultaneous internal-security, alliance, economic, migration and military pressures. Under the most severe branch, several states experience institutional fracture and the crisis evolves into a multipolar international conflict.

This is the scenario to simulate.

It is explicitly **not** a claim that this sequence will occur.

---

# PART III — CASCADE MODEL

## 12. Escalation state machine

The simulator must be able to traverse, reverse or avoid these stages:

```text
STABLE
  ↓
TENSION
  ↓
EMERGENCY
  ↓
MASS_UNREST
  ↓
ORGANIZED_POLITICAL_VIOLENCE
  ↓
INSURGENCY
  ↓
DUAL_AUTHORITY
  ↓
CIVIL_WAR
  ↓
STATE_FRAGMENTATION
```

Transitions must be reversible.

### S0 — Managed tension

- migration crisis;
- diplomatic hostility;
- disinformation;
- demonstrations;
- border reinforcement;
- military signaling;
- functioning institutions.

### S1 — Spain–Morocco confrontation

Potential scenario triggers:

- lethal border incident;
- maritime/air incident;
- attribution dispute;
- diplomatic rupture;
- sustained coercive pressure;
- limited armed confrontation.

Effects:

- Spanish mobilization;
- Moroccan mobilization;
- EU/NATO consultations;
- market reaction;
- displacement shock.

### S2 — Spanish internal polarization

Feedback:

```text
external conflict
→ identity polarization
→ extremist propaganda
→ violent incidents
→ retaliation
→ stronger polarization
```

Violent-network families:

- jihadist/islamist violent networks;
- ultranationalist/anti-Muslim violent networks;
- revolutionary anti-system networks;
- separatist/territorial violent actors if independently activated;
- criminal actors exploiting state distraction.

Civilian populations are never assigned automatically to these networks.

### S3 — Synchronized European unrest

Primary states:

- Spain;
- France;
- Belgium;
- Netherlands;
- Germany;
- Italy;
- United Kingdom;
- Sweden;
- Austria;
- Portugal.

Mechanisms:

- copycat violence;
- online propaganda;
- displacement;
- diaspora/family networks;
- extremist transnational networks;
- reciprocal hate crimes;
- emergency-state measures;
- economic disruption.

### S4 — France as European pivot

France is a key propagation node because of:

- Iberia–continental Europe geography;
- major metropolitan networks;
- nuclear-armed status;
- major EU/NATO military role;
- Mediterranean exposure;
- historic Africa relationships.

Possible outcomes:

1. institutions absorb shock;
2. chronic unrest;
3. widespread terrorist/extremist violence;
4. localized insurgency;
5. security-force overstretch;
6. political duality;
7. state fragmentation.

Only outcomes 5–7 create conditions for systemic European conflict.

### S5 — Sahel deterioration

Mechanisms:

- reduced European attention;
- weakening security partnerships;
- opportunistic jihadist expansion;
- coups/government crises;
- refugee generation;
- criminal-route expansion;
- propaganda linkage with Europe.

Feedback:

```text
European crisis
→ less external stabilization capacity
→ Sahel deterioration
→ greater displacement/extremist activity
→ higher European pressure
```

### S6 — Globalized sectarian narratives

Violent actors may attempt to recast separate conflicts as a single global struggle.

Possible narratives:

- "global war against Muslims";
- "global war against Christians/Europeans/the West".

The simulator models **narrative strength**, not narrative truth.

Key variable:

`civilizational_narrative_strength`

### S7 — Middle East escalation

The simulator must not assume a single "Islamic bloc".

At minimum distinguish:

- Iran and aligned actors;
- Gulf monarchies;
- Turkey;
- Israel;
- Arab states with differing interests;
- Pakistan;
- jihadist non-state organizations.

Possible behaviors:

- neutrality;
- mediation;
- opportunistic intervention;
- material support;
- economic coercion;
- proxy escalation;
- direct interstate involvement.

### S8 — Great-power intervention

Actors:

- United States;
- Russia;
- China;
- potentially India.

No major power is permanently assigned to a religious bloc.

### S9 — Systemic war

Exists only if several conditions coincide:

- multiple European states suffer institutional fracture;
- interstate wars broaden;
- alliance systems activate;
- external powers intervene;
- energy/trade networks suffer severe disruption;
- conflict narratives become transnational;
- conventional deterrence fails.

The simulator terminates or switches model class before detailed nuclear employment.

Nuclear escalation exists only as:

`NUCLEAR_ESCALATION_RISK`

No nuclear target planning is part of this project.

---

# PART IV — ACTOR MODEL

## 13. Actor families

### State governments

Attributes:

- legitimacy;
- institutional cohesion;
- coercive capacity;
- fiscal capacity;
- intelligence capacity;
- economic resilience;
- alliance access;
- foreign-policy orientation.

### Security institutions

Variables:

- chain-of-command cohesion;
- police capacity;
- military cohesion;
- intelligence effectiveness;
- fatigue;
- public legitimacy;
- territorial coverage.

A state enters genuine civil-war territory primarily when:

`security_chain_of_command_cohesion`

falls below a critical threshold and competing authorities gain durable coercive capacity.

### Civilian communities

Variables:

- trust;
- perceived security;
- institutional confidence;
- integration;
- economic stress;
- violence exposure;
- propaganda exposure.

No civilian community receives automatic faction assignment.

### Violent Islamist networks

Represent only actors pursuing political violence under Islamist ideological framing.

Variables:

- recruitment;
- network density;
- financing;
- propaganda reach;
- external sponsorship;
- operational capability;
- popular rejection/support;
- counterterrorism pressure.

### Violent ultranationalist networks

Parallel variable family.

Recruitment may increase after:

- attacks;
- perceived state weakness;
- migration shocks;
- propaganda;
- reciprocal communal violence.

### Revolutionary / anti-system networks

Configurable:

- violent far-left;
- anarchist;
- anti-state revolutionary;
- hybrid ideological actors.

Cooperation with Islamist actors is **not assumed**.

### Criminal networks

Can exploit:

- border chaos;
- trafficking;
- smuggling;
- black markets;
- infrastructure disruption.

They may cooperate transactionally without ideological alignment.

### External patrons

Abstract support types:

- diplomatic;
- financial;
- intelligence;
- humanitarian;
- economic;
- security assistance.

No tactical targeting or weapon-employment planner is required.

---

# PART V — GEOGRAPHY

## 14. Minimum node set

### Iberia

- Spain_Mainland
- Ceuta
- Melilla
- Canary_Islands
- Portugal

### Western/Central Europe

- France
- Belgium
- Netherlands
- Germany
- Italy
- United_Kingdom
- Sweden
- Austria
- Switzerland

### North Africa

- Morocco
- Algeria
- Tunisia
- Libya

### Sahel / West Africa

- Mali
- Burkina_Faso
- Niger
- Nigeria
- Benin
- Senegal
- Mauritania
- Chad

### Middle East

- Turkey
- Israel
- Iran
- Iraq
- Syria
- Lebanon
- Jordan
- Saudi_Arabia
- UAE
- Qatar
- Yemen

### South Asia

- Pakistan
- India

### Great powers

- United_States
- Russia
- China

### Institutional/system nodes

- NATO
- European_Union
- global_energy_market
- Mediterranean_shipping
- information_ecosystem

---

# PART VI — SPAIN SUBSYSTEM

## 15. Spain-specific decomposition

Production model minimum:

- central government;
- armed forces;
- Guardia Civil;
- Policía Nacional;
- autonomous administrations;
- Ceuta;
- Melilla;
- mainland civilian population;
- Muslim civilian population as demographic/social group, **not a faction**;
- Moroccan-origin population as social/diaspora variable, **not a faction**;
- violent Islamist network;
- violent ultranationalist network;
- revolutionary violent network;
- organized crime;
- economy;
- energy system;
- ports/logistics;
- information environment;
- EU support;
- NATO support.

Optional regional expansion:

- Andalusia;
- Madrid;
- Catalonia;
- Valencia;
- Murcia;
- Basque Country;
- remaining autonomous communities.

Regional politics must never be translated automatically into insurgent behavior.

---

# PART VII — CORE VARIABLES

## 16. State variables

Normalized variables use `[0,1]` unless otherwise defined.

### Institutional

- `state_cohesion`
- `government_legitimacy`
- `security_chain_of_command_cohesion`
- `police_capacity`
- `military_institutional_cohesion`
- `intelligence_effectiveness`
- `judicial_functionality`
- `administrative_capacity`

### Social

- `social_trust`
- `polarization`
- `communal_fear`
- `intergroup_hostility`
- `civil_unrest`
- `hate_crime_pressure`
- `civilizational_narrative_strength`

### Extremist networks

- `violent_islamist_mobilization`
- `violent_ultranationalist_mobilization`
- `revolutionary_extremist_mobilization`
- `separatist_violent_mobilization`
- `criminal_network_power`

### External conflict

- `external_conflict_pressure`
- `interstate_war_intensity`
- `foreign_intervention`
- `proxy_support`
- `alliance_support`
- `alliance_cohesion`

### Humanitarian

- `displacement_pressure`
- `refugee_absorption_capacity`
- `food_security`
- `health_system_stress`
- `humanitarian_capacity`

### Economic

- `economic_resilience`
- `fiscal_capacity`
- `energy_security`
- `trade_disruption`
- `unemployment_stress`
- `inflation_stress`
- `infrastructure_stress`

### Information

- `disinformation_intensity`
- `propaganda_reach`
- `online_radicalization_pressure`
- `media_trust`

### Africa / France

- `french_africa_influence`
- `regional_security_cooperation`
- `sahel_state_control`
- `sahel_jihadist_pressure`

---

# PART VII-A — NATIONAL CAPABILITY AND MODERN WARFARE

## 16A. Population and mobilization

Every country must store a dated population snapshot and a manpower pipeline separating total population, legally eligible population, medically fit population, trained/prior-service personnel, immediately available personnel, 30-day mobilizable personnel, 180-day mobilizable personnel and a sustainable 365-day force.

The World Bank/UN 15–64 population is only a broad demographic input and must never be interpreted directly as usable military manpower. Children, elderly people and other non-direct military populations remain relevant to humanitarian demand, industrial labor, public administration, dependency ratios, displacement and social resilience.

Religion and migration generation may be stored only when directly supported by a published dataset. If a country does not publish reliable second-/third-generation Muslim or Christian cross-tabulations, those fields remain unknown rather than being inferred from surnames, neighborhoods, nationality, ancestry or language.

## 16B. Force structure

Country nodes must distinguish active forces, land forces, naval forces, air forces, joint/support personnel, cyber/space personnel where identifiable, reserves, ready reserves, gendarmerie/national guard/paramilitary forces, deployable share, training, personnel fill rate, command cohesion, fatigue and morale.

Personnel data must retain a reference year. As a fallback historical baseline, the CIA World Factbook 2022 archive estimated about 120,000 active-duty personnel for Spain, 200,000 for Morocco, 205,000 for France, 184,000 for Germany, 170,000 for Italy and 153,000 regular forces for the United Kingdom. These values are provisional historical inputs, not claims about exact 2026 strength.

## 16C. Military domains and weapon categories

Military capability is decomposed into land, air, naval, air/missile defence, drones/uncrewed systems, counter-UAS, electronic warfare, cyber, ISR/C4ISR, intelligence, engineering, logistics, mobilization, defence industry and AI-enabled capability.

Version 1 tracks weapon categories rather than individual systems: infantry systems, protected mobility, armored systems, indirect fire, long-range fires, ground air defence, combat air, air support/transport/refuelling, rotary wing, surface naval, submarines, amphibious capability, maritime patrol, uncrewed aerial/ground/maritime systems, counter-UAS, electronic warfare, cyber, ISR/C4ISR, engineering, logistics, precision munitions and mass munitions.

Raw inventory is never equal to effective power. Readiness, maintenance, trained crews, ammunition depth, sensors, communications and logistics modify the usable capability.

## 16D. Scenario-dependent weights

There is no universal military-power score. Capability weights must be configurable by theatre. Canonical profiles will include Iberian Strait interstate conflict, continental high-intensity conflict, urban internal-security crisis, Mediterranean maritime conflict, Sahel insurgency and prolonged attrition. All weights must be versioned and sum to 1.0.

## 16E. Modern warfare factors

The model must include structural lessons visible in the Russia–Ukraine war: mass low-cost drones, rapid drone replacement, counter-UAS, electronic warfare, navigation and communications denial/resilience, distributed sensing, commercial satellite access, contested logistics, air-defence interceptor depth, repair capacity, industrial replacement, dispersed command-and-control, civil-military innovation and rapid adaptation cycles.

Low-cost drones are represented as an ecosystem: production, imports, critical components, operator training, losses, EW conditions, replacement rate and adaptation all affect value.

## 16F. Rearmament and war economy

Initial arsenal and regenerative capacity are separate. Required variables include military expenditure, domestic defence industry, ammunition capacity, drone production, vehicle/aerospace/naval/electronics capacity, repair capacity, 90-day and 365-day industrial surge, import dependency, critical-component dependency, semiconductor access, energy dependency, fiscal war capacity and financing constraints.

NATO's Industrial Capacity Expansion Pledge explicitly identifies defence-industrial capacity, critical munitions, air/missile defence, joint procurement, technological adoption and resilient supply chains as strategic requirements. SIPRI military-expenditure, arms-transfer and arms-industry datasets are canonical data sources for this layer.

## 16G. Intelligence

Aggregate intelligence capability includes HUMINT, SIGINT, GEOINT/IMINT, OSINT, cyber intelligence, counterintelligence, domestic threat detection, analytic fusion, strategic warning, allied intelligence sharing and regional/language expertise. The simulator models intelligence quality and sharing, not covert operational instructions.

## 16H. Artificial intelligence

AI is dynamic rather than a fixed national bonus. Required dimensions include frontier-model access, domestic model capability, compute, data centres, semiconductor/fabrication access, electricity, AI talent, research strength, open-model access, cloud access, defence integration, autonomous-systems maturity, AI-enabled ISR/logistics/EW, cyber AI, information operations, model security and allied AI access.

NATO's revised AI strategy treats AI as a rapidly evolving general-purpose defence technology and emphasizes data readiness, interoperability, responsible adoption, testing and protection against adversarial AI use.

Stanford AI Index 2026 reports that U.S.-based institutions produced 59 notable AI models in 2025 and Chinese institutions 35; it also reports global AI compute capacity growing about 3.3x per year since 2022. AI power must therefore be represented as a dated multi-dimensional capability, not a binary 'controls AI' flag. Growth will use bounded adoption/diffusion models rather than an unlimited exponential.

## 16I. Political leadership, elites and high-level interests

Political and elite interests are modeled through explicit incentives and observable proxies rather than unsupported conspiracy assumptions. Variables include government/regime survival, territorial integrity, alliance credibility, economic continuity, ideological commitments, public support, elite cohesion/fragmentation, civil-military alignment, bureaucratic cohesion, security-service loyalty, defence-industry influence, major-business exposure, energy/financial exposure, foreign-asset exposure, sanctions vulnerability and corruption/state-capture proxies.

World Bank WGI, OECD trust data and V-Dem are canonical sources for institutional and governance baselines where applicable.

## 16J. Geography, logistics and alliance interoperability

Country capability must also include strategic depth, population density, borders, coastline, ports, airbase dispersion, road/rail redundancy, chokepoint exposure, energy routes and proximity to allies/adversaries. Allied strength is not simply additive: common standards, compatible munitions, command integration, political authorization latency, cross-border logistics, intelligence sharing and maintenance compatibility all affect usable coalition strength.

Detailed field definitions and provenance requirements are in [docs/FACTOR_MODEL.md](docs/FACTOR_MODEL.md).

---
# PART VIII — DEMOGRAPHICS

## 17. Demographic inputs

Allowed:

- population;
- age structure;
- citizenship;
- migration history;
- religion;
- urban concentration;
- unemployment;
- income;
- integration indicators.

Forbidden shortcut:

```text
Muslim population × mobilization coefficient = Islamist fighters
```

Required conceptual form:

```text
network recruitment =
    existing extremist network
  + propaganda exposure
  + violent-event exposure
  + grievance
  + organizational access
  + foreign-network contact
  - state legitimacy
  - integration
  - counter-radicalization
  - policing/intelligence effectiveness
  - community rejection
```

The same structural rule applies to ultranationalist and revolutionary extremist recruitment.

## 18. Generational effects

First-, second- and later-generation populations may be modeled through:

- language integration;
- citizenship;
- socioeconomic integration;
- discrimination exposure;
- transnational family ties;
- institutional trust;
- identity salience;
- propaganda exposure.

These alter social behavior only through calibrated mechanisms, never predetermined loyalty.

---

# PART IX — RECIPROCAL RADICALIZATION

## 19. Core feedback loop

```text
violent Islamist incident
        ↓
communal fear
        ↓
ultranationalist mobilization
        ↓
anti-Muslim violence
        ↓
Muslim communal fear / grievance
        ↓
Islamist propaganda effectiveness
        ↓
violent Islamist recruitment
        ↺
```

The reverse direction exists as well.

State legitimacy, community cooperation and effective policing can dampen this loop.

Indiscriminate repression can amplify it.

This feedback is expected to matter more to European conflict propagation than raw demographic percentages.

---

# PART X — AFRICA → EUROPE FEEDBACK

## 20. Security/displacement chain

```text
Sahel state weakening
    ↓
armed-group expansion
    ↓
civilian displacement
    ↓
regional economic disruption
    ↓
North-African transit pressure
    ↓
Mediterranean migration pressure
    ↓
European political polarization
```

Narrative loop A:

```text
sectarian massacre / jihadist attack
    ↓
global media amplification
    ↓
"war on Christians" narrative
    ↓
European ultranationalist recruitment pressure
```

Narrative loop B:

```text
anti-Muslim violence in Europe
    ↓
global media amplification
    ↓
"war on Muslims" narrative
    ↓
jihadist recruitment pressure
```

Neither narrative is treated as an objective description of the overall conflict.

---

# PART XI — ALLIANCE MODEL

## 21. NATO

State variables:

- `consultation_level`
- `article4_activation`
- `article5_political_consensus`
- `military_support_level`
- `member_internal_stability`
- `us_commitment`
- `alliance_cohesion`

Alliance capability degrades when multiple members face simultaneous internal crises.

## 22. European Union

Variables:

- `article42_7_activation`
- `civil_protection_support`
- `financial_support`
- `border_support`
- `security_coordination`
- `political_cohesion`
- `refugee_burden_sharing`

EU and NATO responses are correlated but not interchangeable.

---

# PART XII — COALITION FORMATION

## 23. No hard-coded binary blocs

The model starts multipolar.

A later binary-looking conflict may emerge, but is never assumed.

Possible narratives:

- Western constitutional / national-defense;
- conservative or "Judeo-Christian" identity;
- Islamist revolutionary;
- revolutionary anti-Western.

State alignment depends on:

- regime survival;
- alliances;
- security interests;
- economics;
- domestic politics;
- rivalries;
- external threats.

Particularly important:

- Morocco;
- Turkey;
- Saudi Arabia;
- Pakistan;
- Iran;
- China;
- Russia.

## 24. Islamist–revolutionary tactical coalition

The extreme scenario permits a temporary Islamist–revolutionary alignment, but it must be emergent.

Variables:

- `common_enemy_alignment`
- `resource_complementarity`
- `foreign_sponsor_overlap`
- `ideological_incompatibility`
- `mutual_trust`
- `expected_postwar_conflict`

Conceptual condition:

```text
common_enemy_alignment
+ resource_complementarity
+ sponsor_overlap
>
ideological_incompatibility
+ distrust
+ expected_postwar_conflict
```

The coalition may fragment if the common enemy weakens.

---

# PART XIII — SPAIN STRATEGIC POSITION

## 25. Why Spain is a critical node

Spain is simultaneously exposed to:

1. Ceuta and Melilla;
2. Morocco;
3. Strait of Gibraltar;
4. Mediterranean migration;
5. Atlantic access;
6. French stability;
7. domestic polarization;
8. alliance cohesion;
9. North-African instability;
10. economic and energy disruption.

Spain is therefore a **multidimensional pressure node**, not automatically the weakest European state.

## 26. Stabilizers

- institutional continuity;
- unified security chain of command;
- EU membership;
- NATO membership;
- Atlantic/Mediterranean access;
- Portuguese stability;
- functioning economy;
- intelligence cooperation;
- community cooperation;
- effective crisis communication.

## 27. Failure accelerators

- direct Spain–Morocco war;
- prolonged Ceuta/Melilla crisis;
- reciprocal communal violence;
- security-force overstretch;
- French instability;
- simultaneous European crises;
- energy/economic shock;
- extreme disinformation;
- alliance paralysis;
- legitimacy collapse;
- security-chain fragmentation.

The strongest civil-war accelerator is **institutional/security fragmentation**, not religious demography.

---

# PART XIV — FRANCE

## 28. France as propagation hub

Relevant model factors:

- domestic polarization;
- extremist-network activity;
- displacement pressure;
- security capacity;
- nuclear-state continuity;
- EU/NATO leadership;
- Mediterranean exposure;
- Africa partnerships/influence;
- metropolitan and overseas continuity.

A severe French institutional crisis sharply increases systemic European risk.

---

# PART XV — EXTERNAL POWERS

## 29. United States

Primary modeled incentives:

- NATO cohesion;
- European stability;
- Mediterranean access;
- counterterrorism;
- strategic-partner protection;
- prevention of nuclear escalation.

## 30. Russia

Primary modeled incentives:

- weaken adversarial alliances where useful;
- gain diplomatic leverage;
- protect own security perimeter;
- avoid uncontrolled jihadist expansion;
- preserve strategic relationships.

Russia is not modeled as communist.

## 31. China

Primary modeled incentives:

- preserve trade;
- preserve energy flows;
- avoid financial disruption;
- protect overseas assets;
- expand diplomatic leverage;
- prefer state stability over transnational ideological war.

China's party system does not imply automatic alignment with European revolutionary communists or Islamist organizations.

---

# PART XVI — TERMINATION STATES

## 32. Possible run classifications

- `DEESCALATION`
- `CONTAINED_INTERSTATE_CONFLICT`
- `SPANISH_INTERNAL_STABILIZATION`
- `PROLONGED_SPANISH_INSURGENCY`
- `SPANISH_CIVIL_WAR`
- `EUROPEAN_SECURITY_CRISIS`
- `MULTI_STATE_EUROPEAN_INSURGENCY`
- `EUROPEAN_STATE_FRAGMENTATION`
- `MENA_REGIONAL_WAR`
- `EURO_MENA_SYSTEMIC_WAR`
- `GREAT_POWER_DIRECT_CONFLICT`
- `NUCLEAR_ESCALATION_RISK`

These are model classifications, not predictions.

---

# PART XVII — SIMULATION ARCHITECTURE

## 33. Recommended hybrid architecture

### Layer A — System dynamics

For:

- economy;
- energy;
- migration;
- legitimacy;
- institutional capacity;
- alliance cohesion;
- humanitarian stress.

### Layer B — Graph contagion

For:

- propaganda;
- extremist diffusion;
- refugee flows;
- political contagion;
- economic disruption;
- cross-border violence.

### Layer C — Stochastic events

For:

- terrorist incidents;
- government crises;
- diplomatic rupture;
- accidental interstate incidents;
- alliance intervention;
- ceasefires.

### Layer D — Strategic agents

Agents:

- states;
- alliances;
- violent networks;
- external powers.

Agents select high-level actions from utilities/constraints.

No tactical combat planner is required.

---

# PART XVIII — TIME MODEL

## 34. Simulation clock

Recommended:

- base step: **1 day** during acute crisis;
- aggregation: weekly/monthly for long runs;
- normal horizon: **365–1,825 days**;
- Monte Carlo: **1,000+ runs** for exploratory analysis;
- parameter uncertainty for all high-impact variables.

---

# PART XIX — EVENT SYSTEM

## 35. Event schema

```json
{
  "id": "ESP_MAR_BORDER_ESCALATION",
  "day": 12,
  "duration_days": 4,
  "actors": ["Spain", "Morocco"],
  "effects": {
    "Spain.external_conflict_pressure": 0.08,
    "Spain.polarization": 0.03,
    "Morocco.external_conflict_pressure": 0.08
  },
  "tags": [
    "HYPOTHETICAL",
    "INTERSTATE"
  ]
}
```

Every event requires provenance:

- `FACTUAL`
- `SCENARIO_ASSUMPTION`
- `RANDOM_SHOCK`
- `GENERATED`

---

# PART XX — CALIBRATION

## 36. Parameters requiring real data

Priority:

1. population/demographics;
2. migration flows;
3. terrorism incidents;
4. hate crime;
5. economic indicators;
6. defense expenditure;
7. energy dependency;
8. trade dependency;
9. institutional-trust surveys;
10. government stability;
11. refugee absorption;
12. alliance treaties;
13. conflict-event datasets;
14. Sahel territorial/security indicators.

Potential sources:

- Eurostat;
- INE;
- Pew Research Center;
- Europol;
- ACLED;
- SIPRI;
- NATO;
- EU/EEAS;
- World Bank;
- IMF;
- UNHCR;
- IOM;
- national statistics offices.

---

# PART XXI — UNCERTAINTY

## 37. No fake precision

Before proper calibration, never report:

```text
Probability of European civil war = 63.74%
```

Instead:

```text
63.74% of runs under Scenario X and parameter distribution Y reached state Z.
```

That is a property of the model assumptions, not a real-world probability.

---

# PART XXII — VALIDATION

## 38. Required strategy

### Unit tests

Every transition function.

### Invariants

Examples:

- normalized variables stay in `[0,1]`;
- populations never become negative;
- displacement cannot exceed physically possible bounds;
- alliance support requires a defined membership/partnership route.

### Sensitivity analysis

Identify variables dominating:

- Spanish collapse;
- French collapse;
- European propagation;
- Sahel escalation;
- systemic war.

### Historical backtesting

Historical crises may be used only as structural analogues.

### Monte Carlo convergence

Verify stability against increasing run count.

---

# PART XXIII — REQUIRED OUTPUTS

## 39. Per-country timeline

For every node:

- phase;
- institutional cohesion;
- security cohesion;
- polarization;
- extremist pressures;
- economic resilience;
- displacement;
- external conflict;
- alliance support.

## 40. European systemic-risk dashboard

- states in emergency;
- states with insurgency;
- states with security fragmentation;
- NATO cohesion;
- EU cohesion;
- refugee pressure;
- energy disruption;
- extremist-network connectivity;
- civilizational narrative strength.

## 41. Spain dashboard

- mainland stability;
- Ceuta stability;
- Melilla stability;
- Morocco pressure;
- France pressure;
- Portugal stabilizer;
- police/security capacity;
- chain-of-command cohesion;
- competing extremist pressures;
- economic resilience;
- EU/NATO support.

## 42. Cascade graph

Every major outcome should expose its causal path.

Example:

```text
Ceuta shock
→ Spain-Morocco confrontation
→ Spanish polarization
→ reciprocal extremist mobilization
→ French spillover
→ French security overstretch
→ EU support reduction
→ Spanish institutional pressure
```

Explainability is mandatory.

---

# PART XXIV — PREDEFINED SCENARIOS

## 43. Scenario packs

### SCN-00 — Baseline stability
No major artificial shock.

### SCN-01 — Ceuta crisis contained
Severe migration/political crisis, no war.

### SCN-02 — Limited Spain–Morocco conflict
External conflict without Spanish institutional fracture.

### SCN-03 — Spanish internal violent polarization
Adds reciprocal extremist escalation.

### SCN-04 — France contagion
Adds substantial French instability.

### SCN-05 — Pan-European synchronized extremist crisis
Multiple European nodes activate simultaneously.

### SCN-06 — Sahel feedback
Adds major Sahel deterioration and displacement.

### SCN-07 — Middle-East escalation
Adds simultaneous MENA conflict.

### SCN-08 — Extreme Euro-MENA cascade
Combines SCN-02 through SCN-07.

### SCN-09 — State-fracture stress test
Artificially weakens security-chain cohesion to test collapse thresholds.

SCN-09 is an adversarial sensitivity test, not forecasting.

---

# PART XXV — CANONICAL QUESTIONS

## 44. Questions the simulator should answer

1. Under what shocks does a Spain–Morocco conflict remain contained?
2. Which variables most strongly protect Spain from fragmentation?
3. How important is French stability to Spain?
4. Does Portuguese stability materially improve Spanish resilience?
5. How much simultaneous extremist violence can European states absorb before security capacity degrades?
6. Which feedback loops drive reciprocal radicalization?
7. Does Sahel deterioration materially increase European instability?
8. Under what assumptions does conflict become genuinely paneuropean?
9. Which states tend to remain outside direct conflict?
10. Which alliances remain coherent?
11. Which countries become bridge nodes for contagion?
12. Under what assumptions does an Islamist–revolutionary tactical coalition form?
13. How stable is such a coalition?
14. What prevents the hypothesized binary religious war from forming?
15. Under what extreme assumptions can a binary-looking bloc structure emerge?
16. Which high-level interventions minimize systemic escalation?
17. What is Spain's relative resilience under each scenario?

---

# PART XXVI — PROJECT BOUNDARY

## 45. Scope

Intended for:

- strategic analysis;
- political-risk modeling;
- humanitarian planning;
- institutional resilience;
- economic impact;
- alliance dynamics;
- conflict-prevention research.

Out of scope:

- target selection;
- weapon-effect optimization;
- attack-route planning;
- sabotage instructions;
- tactical force deployment;
- instructions for harming civilian or military targets.

Strategic military capability is represented only through aggregate indices.

---

# PART XXVII — TARGET REPOSITORY STRUCTURE

## 46. Layout

```text
Islamic_war_simulator/
├── README.md
├── pyproject.toml
├── LICENSE
├── docs/
│   ├── BASELINE.md
│   ├── SCENARIO_ASSUMPTIONS.md
│   ├── MODEL_SPEC.md
│   ├── DATA_DICTIONARY.md
│   ├── CALIBRATION.md
│   ├── VALIDATION.md
│   ├── SOURCES.md
│   └── CHANGELOG_CANON.md
├── config/
│   ├── countries/
│   ├── regions/
│   └── scenarios/
│       ├── scn_00_baseline.yaml
│       ├── scn_01_ceuta_contained.yaml
│       ├── scn_02_spain_morocco.yaml
│       ├── scn_03_spain_internal.yaml
│       ├── scn_04_france_contagion.yaml
│       ├── scn_05_pan_europe.yaml
│       ├── scn_06_sahel_feedback.yaml
│       ├── scn_07_mena_escalation.yaml
│       ├── scn_08_extreme_cascade.yaml
│       └── scn_09_state_fracture.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   └── provenance/
├── src/
│   └── conflict_sim/
│       ├── __init__.py
│       ├── engine.py
│       ├── state.py
│       ├── actors.py
│       ├── geography.py
│       ├── networks.py
│       ├── contagion.py
│       ├── economy.py
│       ├── migration.py
│       ├── alliances.py
│       ├── extremism.py
│       ├── events.py
│       ├── scenarios.py
│       ├── metrics.py
│       ├── monte_carlo.py
│       └── logging_config.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── regression/
└── notebooks/
    └── exploratory/
```

---

# PART XXVIII — CANON RULES

## 47. Development rules

1. `README.md` defines the top-level intent.
2. Real-world facts go in `docs/BASELINE.md`.
3. Hypothetical assumptions go in `docs/SCENARIO_ASSUMPTIONS.md`.
4. No assumption may silently migrate into baseline.
5. Every calibrated datum carries source, date and geography.
6. Every scenario change requires a canon changelog entry.
7. Every result preserves:
   - scenario version;
   - git commit;
   - random seed;
   - parameter set;
   - data snapshot.
8. No demographic group is automatically a combatant faction.
9. Coalitions are dynamic unless a stress-test explicitly fixes them.
10. Model outputs are not forecasts unless a separately validated forecasting methodology is developed.
11. Python production functions should use structured logging; development code should emit `logger.info` at function boundaries where useful for professional debugging.
12. Identical seed + config + commit must produce identical results.

---

# PART XXIX — CANONICAL SOURCE SNAPSHOT

## 48. Baseline v0.2

1. Pew Research Center — *Religion in Europe* (2025)  
   https://www.pewresearch.org/2025/06/09/religion-in-europe/

2. Europol — *EU Terrorism Situation and Trend Report 2026*  
   https://www.europol.europa.eu/publication-events/main-reports/european-union-terrorism-situation-and-trend-report-2026-eu-te-sat

3. Reuters — Ceuta border crisis (2026-09-18)  
   https://www.reuters.com/world/africa/ceuta-border-crisis-fuels-eus-far-right-despite-fall-migrant-arrivals-2026-09-18/

4. El País — Spain/Morocco coordination around Ceuta (2026-09-22)  
   https://elpais.com/espana/2026-09-22/albares-asegura-que-marruecos-le-ha-garantizado-que-impedira-un-salto-a-ceuta-el-23.html

5. U.S. Department of State — *U.S. Security Cooperation with Morocco*  
   https://2021-2025.state.gov/u-s-security-cooperation-with-morocco/

6. NATO — North Atlantic Treaty / Articles 5 and 6  
   https://www.nato.int/cps/en/natohq/official_texts_17120.htm

7. EEAS — Article 42(7) TEU mutual assistance clause  
   https://www.eeas.europa.eu/eeas/article-427-teu-eus-mutual-assistance-clause_en

8. Reuters — France ends permanent troop presence in Senegal (2025-07-17)  
   https://www.reuters.com/world/africa/france-ends-permanent-troop-presence-senegal-2025-07-17/

9. ACLED — Sahel insurgency expansion / 2026 analysis  
   https://acleddata.com/expert-comment/heni-nsaibia-sahel-insurgency-expansion-as-jihadist-rivalry-intensifies-across-borders

10. ACLED — Jihadist expansion in Africa  
    https://acleddata.com/report/jihadist-groups-pose-growing-and-expanding-threat-africa

11. USCIRF — 2026 Annual Report / Nigeria  
    https://www.uscirf.gov/sites/default/files/2026-03/USCIRF_2026_AR%20%282%29.pdf

12. USCIRF — Nonstate Violators of Religious Freedom in Nigeria: Fulani Militants (2026)  
    https://www.uscirf.gov/news-room/releases-statements/nonstate-violators-religious-freedom-nigeria-fulani-militants

13. World Bank — Population ages 15–64 / World Development Indicators  
    https://databank.worldbank.org/metadataglossary/world-development-indicators/series/SP.POP.1564.TO.ZS

14. CIA World Factbook 2022 Archive — Military and security service personnel strengths  
    https://www.cia.gov/the-world-factbook/about/archives/2022/field/military-and-security-service-personnel-strengths/

15. SIPRI — Military Expenditure Database  
    https://www.sipri.org/databases/milex

16. SIPRI — Arms Transfers Database  
    https://www.sipri.org/databases/armstransfers

17. SIPRI — Arms Industry Database  
    https://www.sipri.org/databases/armsindustry

18. NATO — Industrial Capacity Expansion Pledge  
    https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2024/07/10/nato-industrial-capacity-expansion-pledge

19. NATO — Revised Artificial Intelligence Strategy  
    https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2024/07/10/summary-of-natos-revised-artificial-intelligence-ai-strategy

20. Stanford HAI — AI Index Report 2026  
    https://hai.stanford.edu/ai-index/2026-ai-index-report

21. World Bank — Worldwide Governance Indicators 2025 revision  
    https://www.worldbank.org/en/publication/worldwide-governance-indicators

22. V-Dem — Dataset v16 (2026)  
    https://v-dem.net/data/the-v-dem-dataset/

23. OECD — Trust Survey data  
    https://www.oecd.org/en/data/datasets/oecd-trust-survey-data.html

---

# PART XXX — FIRST IMPLEMENTATION MILESTONE

## 49. Phase 1

Start with the minimal causal backbone:

```text
Spain_Mainland
Ceuta
Morocco
Portugal
France
Germany
Italy
Maghreb_rest
Sahel
Middle_East
NATO
EU
United_States
Russia
China
```

Implement:

1. deterministic baseline;
2. stochastic shocks;
3. graph spillover;
4. extremist-network separation;
5. reciprocal radicalization;
6. security-chain cohesion;
7. alliance response;
8. state-machine escalation;
9. Monte Carlo;
10. causal trace for every collapse.

Only after Phase 1 passes validation should the model expand country by country.

## 50. Definition of done

The first serious simulator is complete when:

- SCN-00 remains broadly stable over long runs;
- extreme scenarios can escalate without hard-coded collapse;
- removing extremist-network propagation reduces contagion;
- increasing institutional cohesion measurably reduces civil-war transitions;
- France and Portugal affect Spain through expected graph links;
- Sahel deterioration can increase European stress without guaranteeing European collapse;
- alliance support can stabilize states but is constrained by simultaneous crises;
- coalitions can form and fragment dynamically;
- every output can be traced to parameters/events;
- identical seed + config + commit produces identical results.

---

**End of canonical specification v0.2.**
