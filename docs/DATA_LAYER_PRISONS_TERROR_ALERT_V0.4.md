# Data Layer v0.4 — Prisons, Extremist Inmates and Terrorism Threat Posture

**Status:** canonical pre-engine enrichment  
**Snapshot date:** 2026-09-23  
**Countries:** Spain, Morocco, France, United Kingdom, Germany

---

## 1. Purpose

This layer adds two strategic-security inputs:

1. prison-system exposure to violent-extremist networks;
2. the state's current public terrorism-threat posture.

It does **not** treat prisoners, Muslim prisoners, or terrorism offenders as automatic combatants.

In a state-fragmentation scenario, loss of prison control may increase:

- uncontrolled releases;
- extremist-network density;
- recruitment;
- coercive/criminal networks;
- intelligence burden;
- local violence;
- pressure on police and corrections systems.

That is represented as a **security-pressure mechanism**, not as a deterministic troop pool.

---

## 2. Prison populations

| Country | Prison population baseline | Reference |
|---|---:|---|
| Spain | 62,398 | 2025-12-31 |
| France | 89,500 | 2026-07-01 |
| United Kingdom | ~96,426 | 2026-06-30 to 2026-07-03 composite |
| Germany | 57,812 | 2025-01-31 |
| Morocco | 99,366 | 2025-12-31 |

The UK figure is a near-synchronous sum of England & Wales, Scotland and Northern Ireland. Germany's total comes from Council of Europe data surfaced through World Prison Brief; Destatis separately reports a narrower sentenced-prisoner series.

---

## 3. Islamist-extremism / terrorism prisoner data

### Spain

Latest specific public figure located:

- 82 prisoners for jihadist-terrorism offences;
- 28 convicted;
- 54 held pre-trial;
- another 70 inmates identified by prison administration as susceptible to jihadist recruitment.

Using the later total prison population only as a rough scale denominator:

```text
82 / 62,398 ≈ 0.13%
```

This is a mixed-date proxy and is marked low quality.

### France

Official parliamentary material reported at end-2023:

- 258 persons convicted for Islamist terrorism (TIS) incarcerated;
- a separate official series reported 540 common-law prisoners suspected of radicalisation (RAD) in 2023.

A mixed-date scale comparison:

```text
258 / 89,500 ≈ 0.29%
```

This is **not** a current-2026 prevalence estimate.

TIS and RAD are different categories and must not be added mechanically.

### United Kingdom

Great Britain has the cleanest current ideology split.

At 31 March 2026:

- 273 people were in custody for terrorism or terrorism-connected offences;
- 58% were categorized as Islamist-extremist;
- approximately 158 persons therefore fall in that category;
- 41 terrorist prisoners of all ideologies were released in the year ending December 2025.

Using a near-synchronous Great Britain prison-population denominator:

```text
~158 / ~95,758 ≈ 0.17%
```

The 58% applies **only to terrorism/terrorism-connected prisoners**, not to the general prison population or Muslim prisoners.

### Germany

No current nationwide prison-stock statistic comparable to the UK or Spain was located.

Therefore:

```yaml
islamist_extremist_terrorism_prisoners: null
islamist_extremist_share_of_total_prison_population: null
```

The BfV national estimate of violence-oriented Islamist persons must not be substituted for prison-specific evidence.

### Morocco

Morocco reports:

- total prison population of 99,366 at end-2025;
- prison capacity of about 64,812;
- occupancy around 153%;
- Moussalaha rehabilitation programmes for prisoners involved in radicalization/terrorism cases.

The 19th Moussalaha edition included 24 detainees, with 436 cumulative participants since 2017 at that date.

That cumulative rehabilitation count is **not** the current stock of extremist prisoners.

The current nationwide stock therefore remains null.

---

## 4. Prison crowding

Crowding matters independently of extremism because it can affect:

- control quality;
- staff workload;
- violence;
- illicit communication;
- programme delivery;
- classification/separation capacity;
- resilience during a wider state emergency.

Current explicit values in this layer include:

- Germany: about 80.2% occupancy in the cited 2025 dataset;
- Morocco: about 153.3% at end-2025.

Spain, France and UK occupancy fields remain unpopulated in v0.4 pending harmonized data.

---

## 5. Terrorism threat posture

National alert systems are not directly interchangeable.

| Country | Current public posture stored | Native scale |
|---|---|---|
| Spain | Level 4 — high, reinforced | 1–5 |
| France | vigilance renforcée | 3-stage Vigipirate |
| United Kingdom | SEVERE — attack highly likely | 5 categories |
| Germany | high qualitative threat | no equivalent public ordinal scale used here |
| Morocco | no comparable domestic public scale located | external U.S. advisory separately stored as Level 2/4 |

### Spain

Spain remains at NAA Level 4, officially corresponding to **high risk**, with reinforcement measures.

### France

The summer-autumn 2026 Vigipirate posture is **vigilance renforcée**, the middle of three stages under the revised system.

### United Kingdom

The national threat level is **SEVERE**, meaning an attack is highly likely.

### Germany

Federal authorities describe the security threat as **high** and separately characterize the Islamist-terrorism threat as persistently high.

This is qualitative rather than a public five-point scale.

### Morocco

No directly comparable domestic public terrorism-alert scale was located.

The U.S. Department of State currently assigns Morocco **Travel Advisory Level 2 — Exercise Increased Caution due to terrorism**.

That external travel advisory must not be treated as Morocco's own alert level.

---

## 6. Why raw alert numbers cannot yet be normalized mechanically

These operations would be invalid:

```text
Spain = 4/5 = 0.80
France = 2/3 = 0.67
UK = 4/5 = 0.80
```

The scales encode different semantics, decision rules and government responses.

A future semantic calibration should map each native level onto common latent concepts such as:

- background threat;
- attack likelihood;
- imminence;
- protective mobilization;
- intelligence confidence;
- geographic scope.

Only then should `normalized_cross_country_level` be populated.

---

## 7. Composite prison-extremism security pressure

The schema now defines:

`prison_extremism_security_pressure`

but it remains unscored until calibration.

A candidate structure is:

```text
P_prison_extremism(t) =
    w1 * extremist_prisoner_density
  + w2 * radicalization_vulnerability
  + w3 * terrorism_prisoner_release_flow
  + w4 * prison_overcrowding
  + w5 * national_extremist_network_pressure
  + w6 * calibrated_terrorism_threat_posture
  - w7 * prison_security_control
  - w8 * intelligence_effectiveness
  - w9 * deradicalization_and_rehabilitation
```

All terms must be normalized and evidence-bounded before use.

The weights are **not defined yet**.

---

## 8. State-collapse interaction

If state control deteriorates, a later model may change the prison-security state through transitions such as:

```text
CONTROLLED
→ STAFF_STRESS
→ PARTIAL_CONTROL_LOSS
→ DISORDER
→ UNCONTROLLED_RELEASES
```

This can modify:

- extremist-network pressure;
- criminal-network pressure;
- local security demand;
- intelligence burden;
- recruitment opportunities.

It does not automatically convert released prisoners into any faction.

Any later armed-group recruitment must remain a separate stochastic transition influenced by:

- prior organizational affiliation;
- ideology;
- network contact;
- willingness;
- coercion;
- local armed-group presence;
- state control;
- competing criminal/political incentives.

---

## 9. Uncertainty

Prison-extremism data are especially sensitive to definition and freshness.

Future Monte Carlo treatment may use uncertainty around:

- current stock after releases/new convictions;
- unobserved radicalization;
- rehabilitation effectiveness;
- prison-control resilience;
- extremist-network contact;
- release timing.

No uncertainty distribution may be created without explicit bounds or a documented prior.

---

## 10. Current country-data quality

### Stronger evidence

- UK terrorism-prisoner ideology split;
- Spain total prison population;
- France total prison population;
- Germany total/sentenced prison series;
- Morocco total/capacity/occupancy;
- national terrorism alert/posture for Spain, France and UK.

### Weaker or incomplete evidence

- current France TIS/RAD stock;
- current Spain jihadist prisoner stock;
- German Islamist-extremist prison stock;
- Moroccan current terrorism-prisoner stock;
- harmonized prison-radicalization programme effectiveness;
- cross-country threat-level normalization.

These remain explicit model uncertainties.

---

## 11. Engine gate

Before this layer enters the future engine:

1. alert scales must receive semantic calibration;
2. prison-security control variables must be defined;
3. mixed-date ratios must receive freshness penalties;
4. extremist-prisoner counts must not be interpreted as Muslim-prisoner counts;
5. recruitment after uncontrolled release must be modeled as a stochastic transition, never deterministic;
6. sensitivity tests must compare models with and without the prison-extremism channel.

---

**End of Data Layer v0.4.**
