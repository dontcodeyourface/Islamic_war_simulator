# Data Snapshot v0.2 — France, United Kingdom and Germany

**Status:** raw-data expansion  
**Snapshot date:** 2026-09-22  
**Engine status:** not implemented  
**Normalization status:** not implemented  
**Forecast probabilities:** prohibited at this stage

This snapshot extends the Spain–Morocco pilot with three central European/NATO nodes:

- France;
- United Kingdom;
- Germany.

It also formalizes the uncertainty model before any simulation engine is written.

---

## 1. New methodological rule: unresolved data can become bounded uncertainty

A missing or stale field may later participate in simulation as uncertainty, but only if its distribution is explicitly documented.

A critical null cannot be randomized arbitrarily.

Valid future examples include:

- interval bounded by multiple reputable estimates;
- triangular distribution around a documented central estimate;
- empirical distribution from historical data;
- scenario-specific stress range;
- correlated distribution linked to related variables.

See:

- `docs/UNCERTAINTY_AND_MULTISCALE_DYNAMICS.md`
- `config/countries/_schema.yaml` v0.2

The schema now includes:

- `geographic_scope`;
- `freshness_class`;
- explicit uncertainty mode;
- lower/upper bounds;
- distribution family;
- parameters;
- correlation group;
- confidence.

---

## 2. Fibonacci and fractal behaviour

Fibonacci is retained as an experimental **multiscale time-window grid**, not as an assumed natural law.

Candidate windows:

```text
1, 2, 3, 5, 8, 13, 21, 34, 55, 89 ...
```

These will later be compared with ordinary policy/security windows:

```text
1, 7, 14, 30, 90, 180, 365 days
```

Potential uses include:

- event-memory windows;
- escalation persistence;
- adaptation cycles;
- trend decomposition;
- multiscale stress aggregation.

The engine may also test:

- Hawkes/self-exciting events;
- autoregressive persistence;
- fractional/long-memory noise;
- heavy-tailed shocks;
- regime switching;
- network cascades.

None becomes canonical until historical backtesting supports it.

---

## 3. Raw comparison

| Variable | France | United Kingdom | Germany | Notes |
|---|---:|---:|---:|---|
| Population | 69.082m (2026-01-01) | 69.487m (mid-2025 provisional) | 83.363m (2026-03-31) | Official national statistics |
| Active/regular force baseline | ~200k military personnel (2025) | 137,480 UK Regular Forces (2026-07-01) | 186,356 military personnel (2026-08-31) | Definitions differ and are preserved |
| Operational/volunteer/ordered reserve baseline | 43,794 operational reservists (2024-12-31) | 32,130 Volunteer Reserves; 28,880 trained FR20 reserve strength (2026-07-01) | ~60,200 ordered reservists (end-2025) | Not equivalent to immediately deployable strength |
| Military expenditure | ~$68.0bn (2025) | ~$89.0bn (2025) | ~$114.0bn (2025) | SIPRI |
| GDP | ~$3.37tn (2025) | ~$4.00tn (2025) | ~$5.05tn (2025) | World Bank current USD |
| National nuclear deterrent | Yes | Yes | No | Alliance deterrence modeled separately |
| Defence AI institution/policy | AMIAD | Defence AI Strategy + DAIC/RAID acceleration | Bundeswehr AI operationalisation | No overall AI power score yet |

This table is descriptive data, not an overall ranking or outcome prediction.

---

## 4. France

### 4.1 Population

INSEE estimates **69.082 million** residents on 1 January 2026, of whom about 66.793 million are in metropolitan France.

The country file preserves France-wide scope rather than silently substituting metropolitan-only data.

### 4.2 Religion

The current comparable religious baseline remains Pew's 2020 estimate.

Religion is stored only as social/demographic context.

No Muslim or Christian population is mapped automatically into any faction.

Generation-by-religion fields remain null until a reliable direct cross-tab is found.

### 4.3 Forces and reserve

Current/near-current official sources allow a better baseline than was available for Morocco:

- nearly 200,000 military personnel in 2025 at ministry level;
- approximately 112,000 Army personnel within the ministry;
- 40,542 active Air and Space Force personnel on 1 January 2026;
- 43,794 operational reservists at 31 December 2024.

The Navy active-only total is intentionally left null because the public headline combines active sailors and reservists.

### 4.4 Defence industry

France has a documented multi-domain national defence industrial base.

The raw snapshot records:

- SIPRI military expenditure of approximately USD 68.0bn in 2025;
- DGA orders of almost EUR 38bn in 2025;
- approximately EUR 20bn in export orders;
- industrial activity spanning land, aerospace, naval, electronics, missiles, space, drones and ammunition.

The file does **not** yet assign a wartime surge multiplier.

### 4.5 AI

France now has a directly identifiable defence-AI institution:

**Agence ministérielle pour l'intelligence artificielle de défense (AMIAD).**

Official material reports:

- 400 identified AI use cases;
- 300 recruits planned by end-2026;
- dedicated research/engineering sites;
- central coordination of ministry defence-AI projects.

These are strong indicators of institutional integration but not a single operational effectiveness score.

### 4.6 Strategic deterrence

France has an independent national nuclear deterrent.

This is represented only through strategic-deterrence state variables.

The project does not model target selection or tactical nuclear employment.

---

## 5. United Kingdom

### 5.1 Population

ONS places the provisional mid-2025 UK population at **69,487,000**.

### 5.2 Religion

The UK demonstrates why geographic scope must be explicit.

England and Wales Census 2021 provides detailed religion data, but Scotland and Northern Ireland use their own census systems.

Therefore v0.2 does **not** fabricate a single whole-UK census share by combining incompatible tables without a defined methodology.

Whole-UK religion fields remain null until that methodology is added.

### 5.3 Forces

UK Ministry of Defence official statistics at 1 July 2026 report:

- 137,480 UK Regular Forces;
- 73,660 Army Regulars;
- 32,430 Royal Navy/Royal Marines Regulars;
- 31,390 RAF Regulars;
- 32,130 Volunteer Reserves;
- 28,880 trained Future Reserves 2020 strength.

The broader total UK Armed Forces service personnel figure is larger because it includes Gurkhas and other personnel categories. The raw data retains these scope distinctions.

### 5.4 Intelligence and cyber

The UK file records the public institutional architecture:

- MI5;
- SIS/MI6;
- GCHQ;
- Defence Intelligence;
- JTAC;
- Cyber & Specialist Operations Command.

Defence Intelligence publicly reports around 5,000 staff, roughly two-thirds military and one-third civilian.

Again, institutional size is not treated as effectiveness.

### 5.5 AI

The UK already has:

- Defence AI Strategy;
- Defence AI Centre;
- Defence AI and Autonomy Unit;
- responsible-AI governance;
- a June 2026 push to accelerate deployment of AI into the Armed Forces.

The 2026 Rapid AI Delivery Taskforce provides a useful future variable for **adaptation latency**: how quickly a state can move a new AI capability from technical availability to operational use.

### 5.6 Industry

The snapshot records:

- SIPRI 2025 military expenditure of approximately USD 89.0bn;
- 274,000 direct and indirect jobs supported by MOD industry expenditure in 2024/25, including about 164,000 direct jobs;
- more than GBP 20bn in defence export deals announced for 2025.

Production throughput and wartime surge remain separate unknowns.

### 5.7 Strategic deterrence

The UK maintains Continuous At-Sea Deterrence and a sovereign nuclear deterrent.

This is modeled at strategic level only.

---

## 6. Germany

### 6.1 Population

Destatis reports **83.363 million** residents at 31 March 2026:

- 41.127m male;
- 42.236m female;
- 70.967m German population;
- 12.396m foreign population.

The foreign-population share was 14.9%.

This is citizenship, not religion and not faction alignment.

### 6.2 Muslim demographic estimate

BAMF's *Muslim Life in Germany 2020* estimated **5.3–5.6 million Muslims** with migration background from predominantly Muslim countries, or about **6.4–6.7%** of the 2019 population under that study's methodology.

This estimate has an important methodological value for the project: BAMF explicitly notes that origin from a predominantly Muslim country does **not** reliably establish a person's religion.

The simulator adopts the same principle.

### 6.3 Forces

Bundeswehr official personnel data at 31 August 2026 reports:

- 186,356 uniformed military personnel;
- 64,697 Army;
- 28,577 Air Force;
- 15,961 Navy;
- 13,771 Cyber and Information Domain;
- 48,035 Support Area personnel.

This is currently one of the cleanest branch-level personnel datasets in the pilot.

### 6.4 Reserve

At the end of 2025 approximately:

- 60,200 reservists were assigned to positions;
- 21,300 performed reserve service during 2025.

These are **not** the same thing as total prior-service population or instantly mobilizable manpower.

The raw model keeps those concepts separate.

### 6.5 Cyber / information domain

Germany's Cyber- und Informationsraum is represented as a distinct force domain.

Its existence matters because the eventual force model should not force cyber, EW, IT, space-enabled support and information activities into a generic Army/Air/Navy bucket.

### 6.6 Industry

Germany's defence-industrial strategy explicitly prioritizes:

- rapid scaling of defence production;
- domestic/European industrial capacity;
- resilient supply chains;
- critical technologies;
- alliance defence.

SIPRI estimates German military expenditure at approximately **USD 114bn in 2025**, about 2.3% of GDP.

No production-rate index is inferred solely from expenditure.

### 6.7 AI

The Bundeswehr explicitly describes AI as a disruptive technology requiring military operationalisation and security.

The country file therefore marks defence-AI institutional development as active, but compute, model capability and battlefield integration remain unscored pending dedicated data.

### 6.8 Strategic deterrence

Germany has no national nuclear arsenal.

The schema now separates:

- national deterrent;
- allied extended deterrence;
- nuclear-sharing role.

The nuclear-sharing field remains lower-confidence until its primary-source provenance is normalized.

---

## 7. Why these three countries matter differently to the eventual model

The raw dataset already suggests that they should not be represented as interchangeable "European military power" nodes.

France introduces:

- continental/Iberian bridge geography;
- sovereign nuclear deterrence;
- large multi-domain defence industry;
- direct Mediterranean exposure;
- an explicit defence-AI agency.

The United Kingdom introduces:

- island geography;
- sovereign nuclear deterrence;
- Five Eyes intelligence relationships;
- global maritime and cyber/specialist structures;
- a large professional force with unusually clean current personnel data.

Germany introduces:

- central continental geography;
- the largest population of the three;
- substantial active force and expanding reserve structure;
- a dedicated cyber/information service branch;
- a rapidly expanding defence budget and industrial scale-up policy.

These are **different capability structures**, not a ranking.

---

## 8. New uncertainty requirements exposed by v0.2

The three-country pass confirms that future randomness needs several classes.

### Measurement uncertainty

Example:

- approximate French total active personnel;
- older religious-composition estimates.

### Scope uncertainty

Example:

- France Army personnel inside vs outside ministry;
- UK Regulars vs Gurkhas vs other personnel;
- ordered German reserve vs people who actually served.

### Freshness uncertainty

Example:

- 2019/2020 religious estimates;
- current 2026 force personnel.

### Latent capability uncertainty

Example:

- actual deployability;
- EW performance;
- munitions depth;
- cyber effectiveness;
- AI operational effectiveness.

### Political/behavioral uncertainty

Example:

- mobilization compliance;
- alliance political authorization;
- public resilience;
- elite cohesion.

These classes should later use different distributions instead of one generic random-noise term.

---

## 9. Correlation groups to add later

Candidate groups exposed by the data:

```text
MANPOWER_PIPELINE
RESERVE_READINESS
MUNITIONS_AND_INDUSTRY
AIR_POWER_AND_MAINTENANCE
NAVAL_POWER_AND_SHIPYARDS
DRONES_EW_COUNTER_UAS
ISR_INTELLIGENCE_CYBER
AI_COMPUTE_TALENT_INTEGRATION
FISCAL_CAPACITY_AND_DEFENCE_SPENDING
ALLIANCE_SUPPORT_AND_INTEROPERABILITY
SOCIAL_COHESION_AND_MOBILIZATION
```

Sampling within these groups must preserve plausible dependencies.

---

## 10. Next data priorities

Before normalizing the European layer, the highest-value missing variables are:

1. reserve/mobilization throughput;
2. deployable shares;
3. munitions stock depth;
4. annual ammunition production;
5. drone production and replacement;
6. counter-UAS capacity;
7. EW depth;
8. repair and maintenance throughput;
9. strategic transport/logistics;
10. AI compute and operational integration;
11. energy dependence;
12. fiscal war capacity;
13. WGI/V-Dem institutional data.

---

## 11. Next geographic expansion

After v0.2 the next high-value nodes are:

- Italy;
- Portugal;
- Turkey;
- Israel;
- Iran;
- Saudi Arabia;
- Pakistan;
- United States;
- Russia;
- China.

Portugal remains important as the Iberian stabilizer node; Italy as the central Mediterranean node.

The engine remains blocked until the baseline and data uncertainty model are sufficiently mature.

---

**End of Data Snapshot v0.2.**
