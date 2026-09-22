# Data Snapshot v0.1 — Spain and Morocco

**Status:** raw-data pilot  
**Snapshot date:** 2026-09-22  
**Engine status:** not implemented  
**Normalized power scores:** not implemented  
**Probability outputs:** prohibited at this stage

This snapshot validates the country-data model before any simulation engine is written.

The files are:

- `config/countries/_schema.yaml`
- `config/countries/spain.yaml`
- `config/countries/morocco.yaml`
- `data/provenance/snapshot_v0.1_sources.yaml`

---

## 1. Method

The snapshot follows four rules:

1. preserve raw values before normalization;
2. preserve the date and provenance of each value;
3. keep unknown values explicitly null;
4. never turn demographic identity directly into combatant alignment.

A later normalization layer may derive comparable indices, but it must always retain the source datum.

---

## 2. Raw comparison

| Variable | Spain | Morocco | Comparability note |
|---|---:|---:|---|
| Population | 49,801,559 | 36,828,330 | Spain: INE 2026-07-01; Morocco: HCP census 2024-09-01 |
| Foreign residents | 7,437,543 | 148,152 | Different migration systems and dates |
| Broad working-age demographic | 32,207,416 aged 15–64 (2024, derived) | 59.7% aged 15–59 (2024) | Age bands differ; not directly comparable |
| Muslim share / estimate | Pew 3.6% in 2020; UCIDE 2,542,498 estimate in 2024 | >99% Muslim, predominantly Sunni (2023 estimate) | Different methods and sources |
| Active regular military personnel | ~120,000 derived from 2026 Spanish MoD planning baseline | ~200,000 CIA estimate from 2022 | Date mismatch: do not interpret as a current head-to-head ratio |
| Land personnel | null | ~175,000 (2022 estimate) | Spain branch-level current figure not yet populated |
| Naval personnel | null | ~10,000 (2022 estimate) | Same issue |
| Air personnel | null | ~15,000 (2022 estimate) | Same issue |
| Military expenditure | ~$40.2bn (2025) | ~$6.3bn (2025) | SIPRI estimates; same reference year |
| GDP | ~$1.906tn (2025) | ~$182.37bn (2025) | World Bank current USD |
| Defence industrial baseline | Diversified land/aerospace/naval/electronics base | Domestic armored-vehicle production expanding | Different industrial maturity measures; no combined score yet |
| AI policy | Spain AI Strategy 2024 + ALIA/supercomputing programs | Maroc IA 2030 implementation roadmap | Policy/infrastructure evidence, not military-AI score |
| Intelligence baseline | CNI + CIFAS + CITCO + MCCE | DGST documented; bilateral counterterrorism cooperation | Open-source visibility differs substantially |

No row in this table is a political or military verdict.

---

## 3. Spain — notable raw facts captured

### Population

INE reports 49,801,559 residents at 1 July 2026, including 7,437,543 foreign residents.

The broad 15–64 population is stored only as a demographic variable. It is explicitly **not** military manpower.

### Religion

Two sources are retained simultaneously rather than reconciled artificially:

- Pew's comparable 2020 estimate: 69.5% Christian, 3.6% Muslim, 26.4% unaffiliated;
- UCIDE's 2024 demographic estimate: 2,542,498 Muslims, including 1,147,308 with Spanish nationality.

Spanish nationality is not treated as a proxy for second/third-generation status.

### Armed forces

The v0.1 snapshot stores approximately 120,000 active personnel as a **derived planning baseline** from the Ministry of Defence statement that the 2029 target is 127,500, 7,500 above the baseline.

Branch-level current personnel remain null until a sufficiently strong source is added.

### Industry

The snapshot records:

- SIPRI 2025 military expenditure: approximately USD 40.2bn;
- Spanish defence/security turnover in 2024: EUR 9.364bn;
- direct employment: 43,190;
- exports: EUR 4.672bn;
- established domestic activity in aerospace, naval shipbuilding, land systems and defence electronics;
- domestic expansion in loitering-munition/intelligent-system production.

Production rates, ammunition depth and wartime surge multipliers remain unknown.

### Intelligence / cyber

Documented institutions include:

- CNI;
- CIFAS;
- CITCO;
- Mando Conjunto del Ciberespacio.

Presence of an institution is not converted into an arbitrary quantitative capability score.

### AI

Spain's 2024 national AI strategy documents ALIA, MareNostrum 5 / Spanish supercomputing infrastructure, public investment and talent programs.

Spain also hosted the 2026 REAIM summit.

None of this is treated as proof of a specific operational military-AI capability.

---

## 4. Morocco — notable raw facts captured

### Population

Morocco's 2024 census records a legal population of 36,828,330:

- 36,680,178 Moroccan;
- 148,152 foreign;
- 62.8% urban.

HCP reports:

- 26.5% under age 15;
- 59.7% age 15–59;
- 13.8% age 60+.

Again, the 15–59 group is not treated as mobilizable manpower.

### Religion

The U.S. State Department's 2023 religious-freedom estimate describes the population as more than 99% Sunni Muslim, with religious minorities collectively below 1%.

No exact Christian/Jewish/other share is fabricated.

### Armed forces

The strongest freely available official baseline currently stored is the CIA World Factbook 2022 archive estimate:

- ~200,000 regular active personnel;
- ~175,000 Army;
- ~10,000 Navy;
- ~15,000 Air Force;
- ~20,000 Royal Gendarmerie;
- ~5,000 Mobile Intervention Corps.

Because these data are from 2022, the snapshot marks them as historical estimates and **not exact 2026 force strength**.

### Modernization / industry

The snapshot distinguishes existing capability from acquisition approval and future production.

Documented examples:

- TATA Advanced Systems Morocco began WhAP 8x8 armored-vehicle production at Berrechid in September 2025;
- the official announcement states 35% locally sourced components at launch, with a planned progression toward 50%;
- Boeing documents first AH-64E deliveries to the Royal Moroccan Air Force in 2025;
- U.S. DSCA notifications document possible Stinger and air-munition sales, but those notifications are not treated as proof that the full notified quantities have been delivered.

### Intelligence

DGST is documented as an active national-security/counterterrorism institution with bilateral cooperation involving Spanish services.

Other intelligence capabilities remain unscored where public evidence is insufficient.

### AI

The September 2026 Maroc IA 2030 roadmap documents an implementation phase involving:

- sovereign digital infrastructure;
- data centres;
- sovereign cloud;
- national language models and shared platforms;
- a target of 200,000 trained/certified talents by 2030;
- a target of MAD 100bn additional GDP value and 50,000 direct/indirect jobs by 2030.

These are policy and capacity-building indicators, not a military-AI capability score.

---

## 5. Critical gaps before normalization

The pilot exposes the data we still need most urgently.

### Military manpower

For both states:

- legally mobilizable population;
- trained/prior-service population;
- reserve pool;
- reserve readiness;
- 30/180/365-day training throughput;
- deployable share.

### Stocks and readiness

- category-level inventory;
- operational availability;
- maintenance;
- munitions depth;
- spare parts;
- repair capacity;
- replacement lead time.

### Modern warfare

- drone stock and production;
- FPV/low-cost UAS industrial capacity;
- counter-UAS;
- EW;
- secure communications;
- sensor density;
- commercial satellite integration;
- adaptation cycle.

### Industrial regeneration

- ammunition production per year;
- vehicle/aircraft/ship repair throughput;
- critical component dependency;
- wartime surge;
- energy and finance constraints.

### Intelligence / cyber / AI

Open-source institutional existence is well documented, but comparable quantitative performance metrics are not.

These will require carefully defined proxies.

### Governance

WGI/V-Dem/OECD variables are not yet loaded.

---

## 6. Data-quality rule discovered during pilot

A major design requirement is now explicit:

> The age of a datum must affect its usefulness independently from source quality.

For example, a high-quality census from 2024 may remain an excellent population baseline in 2026, while an official 2022 military-personnel estimate may already need a substantial freshness penalty.

The future normalization layer therefore requires at minimum:

```text
evidence_strength =
    source_quality
  × freshness
  × measurement_directness
  × cross_source_consistency
```

This is evidence quality, not military power.

---

## 7. Next snapshot expansion

After this pilot is accepted, the same schema should be populated for:

1. France
2. Portugal
3. Germany
4. Italy
5. United Kingdom
6. Turkey
7. Israel
8. Iran
9. Saudi Arabia
10. Pakistan
11. United States
12. Russia
13. China

The engine remains blocked until the data model and baseline are sufficiently complete.

---

**Data Snapshot v0.1 ends here.**
