# Data Layer v0.3 — Religion, Violent-Islamist Proxies, GDP and Gold

**Status:** canonical pre-engine enrichment  
**Snapshot date:** 2026-09-23  
**Countries:** Spain, Morocco, France, United Kingdom, Germany

---

## 1. Why religion and violent extremism are separate variables

The simulator needs religious-demography data because identity, community networks, propaganda narratives and transnational events may affect political and social dynamics.

However:

> Muslim population share is not a violent-extremism rate.

The model therefore stores two independent layers:

1. `religion.*` — civilian demographic composition;
2. `violent_islamist_extremism.*` — observable security/extremism proxies.

A causal relationship, if any, is estimated later through calibrated social, institutional and network mechanisms.

---

## 2. Approximate Muslim population share

| Country | Best current approximation in snapshot | Reference | Comparable note |
|---|---:|---|---|
| Spain | ~5.0% | UCIDE/Observatorio Andalusí, 2024 | Pew comparable estimate was 3.6% in 2020 |
| Morocco | >99% | U.S. State Department, 2023 | Overwhelmingly Sunni Muslim |
| France | ~9.1% | Pew, 2020 | No newer equally comparable national religion census |
| United Kingdom | ~6.0% | UK-wide British Social Attitudes, 2019 | England & Wales Census 2021: 6.5%; whole-UK harmonisation pending |
| Germany | ~6.4–6.7% | BAMF, 2019 | Pew describes ~7% in 2020 |

These are approximate demographic estimates with different methodologies.

They must not be interpreted as ideological alignment.

---

## 3. Why there is no universal "% radical Muslims" field

The active countries do not publish the same statistic.

### Spain

Public data provide:

- counterterrorism operations;
- jihadist-terrorism arrests.

In 2025, official data record:

- 64 operations in Spain;
- 100 people arrested in Spain for jihadist terrorism.

This is an **annual flow**, not a prevalence estimate.

### France

France maintains FSPRT, a prevention/tracking file for terrorist radicalisation.

The French government reported more than **15,000 entries** in March 2025.

An FSPRT entry does not mean:

- conviction;
- active terrorist membership;
- operational capability;
- violent intent in every case.

Therefore it is not divided by France's Muslim population.

### United Kingdom

MI5 provides a different measure.

As of May 2026, MI5 stated that approximately:

- 75% of its counterterrorism workload was Islamist extremist;
- 25% was extreme-right.

This is a **share of security-service counterterrorism workload**, not a share of Muslims and not a headcount.

### Germany

Germany provides the closest thing to a population-style security estimate.

For 2025:

- Islamism / Islamist-terrorism person-potential: **28,645**;
- violence-oriented Islamist person-potential: **9,110**.

BAMF's latest detailed Muslim-population estimate is 5.3–5.6 million, for 2019.

A mechanical ratio gives:

```text
9,110 / 5.6m = 0.163%
9,110 / 5.3m = 0.172%
```

Therefore the German file stores a country-specific proxy of approximately:

**0.16–0.17%**

But this is explicitly tagged as **not cross-country comparable**, because:

- numerator and denominator refer to different years;
- the BfV concept is a security-service "person potential";
- BAMF's denominator has a specific migration-background methodology;
- "violence-oriented Islamist" is not equivalent to a survey-defined "radical Muslim".

The broader 28,645 Islamist person-potential would mechanically correspond to around 0.51–0.54% of the BAMF Muslim estimate, but that broader group includes nonviolent Islamist organizations and therefore is not stored as a violent-radical rate.

### Morocco

The 2024 U.S. State Department terrorism report says Moroccan authorities arrested at least **29 ISIS-inspired persons** that year.

In February 2025, Moroccan authorities documented a **12-person cell** receiving direct incitement from an ISIL leader in the Sahel.

These are enforcement/network indicators, not population prevalence.

---

## 4. Canonical extremism fields

```yaml
violent_islamist_extremism:
  comparable_radical_share_of_muslim_population:
  country_specific_proxy_percent_of_muslim_estimate:
  observed_person_potential:
  violence_oriented_person_potential:
  radicalization_registry_count:
  annual_jihadist_arrests:
  disrupted_plots:
  terrorism_caseload_share:
  extremist_network_assessment:
  external_network_linkage:
  methodological_note:
```

The field:

`comparable_radical_share_of_muslim_population`

remains **null for all five countries** in v0.3.

That is intentional.

The data currently do not justify one harmonized number.

---

## 5. GDP baseline

World Bank 2025 current-US-dollar GDP values already in the country snapshots:

| Country | GDP 2025 |
|---|---:|
| Germany | ~$5.05 trillion |
| United Kingdom | ~$4.003 trillion |
| France | ~$3.37 trillion |
| Spain | ~$1.906 trillion |
| Morocco | ~$182.37 billion |

GDP is a raw economic-capacity input, not a direct military-power score.

Later layers must incorporate:

- fiscal capacity;
- taxation;
- debt;
- borrowing;
- energy;
- imports;
- industrial conversion;
- inflation tolerance;
- alliance financing.

---

## 6. Public official gold reserves

Gold is added because reserve assets may contribute to financial resilience, sanctions resistance and emergency liquidity.

It is **not** treated as cash immediately available for war expenditure.

| Country | Gold reserve baseline |
|---|---:|
| Germany | ~3,350.25 tonnes |
| France | 2,437 tonnes |
| United Kingdom | ~310.29 tonnes |
| Spain | ~281.58 tonnes |
| Morocco | ~22.12 tonnes |

### Germany

Bundesbank reported **3,350.285 tonnes** of physical fine gold at 31 December 2025. The WGC/IMF quarterly series is approximately 3,350.25 tonnes in Q1 2026.

### France

Banque de France explicitly states that its stock remains **2,437 tonnes**.

### United Kingdom

WGC/IMF series gives approximately **310.29 tonnes** in Q2 2026. HM Treasury and Bank of England publish monthly international-reserve releases.

### Spain

Banco de España reported **9.054 million fine troy ounces** at end-2025, equivalent to about **281.58 tonnes**, unchanged during 2025. WGC reports the same approximate tonnage in Q1 2026.

### Morocco

WGC/IMF series reports approximately **22.12 tonnes**.

Morocco's official international-reserve template reports:

- gold market value: **MAD 29.443bn** in August 2026;
- total official reserve assets: **MAD 499.813bn**.

---

## 7. Future financial-resilience model

Gold will later interact with:

```text
foreign-exchange reserves
+ sovereign borrowing capacity
+ domestic currency credibility
+ sanctions exposure
+ external debt
+ current account
+ energy imports
+ sovereign wealth assets
+ gold
```

A large gold reserve alone does not imply greater war-financing capacity.

---

## 8. Future radicalisation model

The eventual radicalisation state should be latent and inferred from evidence.

A conceptual structure:

```text
violent_islamist_mobilisation(t) =
    existing_network_density
  + active_case_pressure
  + propaganda_exposure
  + foreign_network_linkage
  + conflict_grievance
  + reciprocal_communal_violence
  + online_self_radicalisation
  - intelligence_effectiveness
  - policing
  - community_rejection
  - institutional_legitimacy
  - prevention/deradicalisation
```

The Muslim population share can influence social-network scale only through calibrated mechanisms.

It is never itself a radicalisation coefficient.

---

## 9. Cross-country comparability grades

Suggested future grading:

### Grade A

Same definition, same date, same measurement system.

### Grade B

Comparable concept with modest methodological/date differences.

### Grade C

Useful national proxy but not directly comparable.

### Grade D

Qualitative evidence only.

Current violent-Islamist indicators:

- Germany violence-oriented person-potential: **C**
- France FSPRT registry: **C**
- Spain annual jihadist arrests: **C**
- UK Islamist share of CT workload: **C**
- Morocco annual ISIS-inspired arrests/network cases: **C**

No Grade A/B prevalence statistic currently exists across all five countries.

---

## 10. Engine rule

The future engine must never execute:

```text
terrorism_risk = muslim_population_share × radical_percentage
```

unless a future validated empirical model explicitly supports such a relationship.

Instead it will consume the separate demographic and extremist-network evidence layers through calibrated transition equations.

---

**End of Data Layer v0.3.**
