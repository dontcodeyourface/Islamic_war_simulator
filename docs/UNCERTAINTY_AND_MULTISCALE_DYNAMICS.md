# Uncertainty and Multiscale Dynamics

**Status:** canonical pre-engine methodology  
**Version:** 0.1  
**Date:** 2026-09-22

This document defines how unresolved data and temporal complexity may later enter the simulator.

---

## 1. Missing data is not zero

A null value means:

- the datum is unavailable;
- or not sufficiently reliable;
- or not yet researched;
- or not directly measurable.

A null value must never silently become zero.

If the field materially affects simulation outcomes, it may later be represented by an explicit uncertainty distribution.

---

## 2. Evidence-bounded uncertainty

A sampled variable requires at least one of:

- a documented lower/upper interval;
- a documented central estimate plus uncertainty;
- a historical empirical distribution;
- a scenario-defined stress interval;
- an expert-elicited distribution with provenance.

The simulator must reject unbounded randomization of critical nulls.

Example:

```yaml
mobilizable_180d:
  value: null
  uncertainty:
    mode: interval
    lower: 90000
    upper: 140000
    distribution: triangular
    parameters:
      mode: 115000
    correlation_group: manpower_training_pipeline
```

The numbers above are illustrative only.

---

## 3. Correlation matters

Military, political and economic unknowns are often correlated.

Examples:

- ammunition stock and industrial replacement capacity;
- military spending and fiscal capacity;
- reserve readiness and training throughput;
- AI compute and data-centre/electricity access;
- social polarization and extremist recruitment;
- alliance cohesion and external support.

Independent sampling of all uncertain variables would create physically implausible worlds.

Every important distribution may therefore carry a `correlation_group`.

---

## 4. Freshness

Source quality and source freshness are distinct.

A source may be authoritative yet old.

Conceptually:

```text
evidence_strength =
    source_quality
  × freshness
  × measurement_directness
  × cross_source_consistency
```

Freshness decay is domain-specific:

- population census: slow decay;
- GDP: moderate decay;
- force personnel: faster decay;
- munitions inventory: very fast decay during crisis;
- AI capability: very fast decay;
- alliance treaty: slow decay unless politically challenged.

No universal freshness half-life should be used.

---

## 5. Multiscale time

The future engine should distinguish several temporal scales:

- daily tactical/operational shock pressure at aggregate level;
- weekly political/security adaptation;
- monthly mobilization and economic effects;
- quarterly industrial regeneration;
- annual demographic/industrial structural change.

The simulator may combine these scales rather than updating every variable identically each day.

---

## 6. Fractal and self-similar behaviour

Conflict systems often show clustering, bursts, persistence and cross-scale feedback.

The model may test self-similar or long-memory processes such as:

- autoregressive persistence;
- Hawkes/self-exciting event processes;
- fractional Brownian/fractional Gaussian noise;
- heavy-tailed shock distributions;
- regime-switching processes;
- cascades on networks;
- multiscale volatility.

These mechanisms are candidates, not assumptions.

They must be validated against historical data.

---

## 7. Fibonacci-inspired scales

Fibonacci numbers may be used as an **experimental multiscale window grid**:

```text
1, 2, 3, 5, 8, 13, 21, 34, 55, 89 ...
```

Potential uses:

- event-memory windows;
- moving aggregation windows;
- escalation observation windows;
- adaptation-cycle sensitivity tests;
- multiscale trend decomposition.

Fibonacci spacing is not treated as a law of war or human behaviour.

It remains only if it outperforms or usefully complements ordinary scales such as:

```text
1, 7, 14, 30, 90, 180, 365 days
```

during validation/backtesting.

---

## 8. Natural growth is bounded

No important variable should use unconstrained exponential growth indefinitely.

Examples:

- extremist recruitment;
- AI diffusion;
- mobilization;
- industrial production;
- propaganda reach;
- drone production.

Preferred models include:

- logistic/S-curves;
- Gompertz curves;
- capacity-constrained growth;
- learning curves;
- piecewise exponential then saturation;
- innovation diffusion.

---

## 9. Self-exciting violence

Where evidence supports it, violent incidents may use a self-exciting process:

```text
incident
→ short-term elevated probability of retaliation/copycat event
→ decay
```

The excitation coefficient is actor- and context-specific.

The model must separately represent:

- Islamist extremist violence;
- ultranationalist violence;
- revolutionary violence;
- criminal violence;
- state coercion.

No civilian demographic group becomes a violent actor automatically.

---

## 10. Regime switching

Countries can move between latent regimes such as:

- normal;
- tense;
- emergency;
- mobilization;
- insurgency;
- dual authority;
- civil war;
- fragmentation.

Transition probabilities depend on state variables and shocks.

They are not constant Markov probabilities unless historical calibration supports that simplification.

---

## 11. Uncertainty output

Before forecasting calibration, output must be phrased as:

> X% of runs under scenario S, parameter set P and uncertainty model U reached state Z.

Never:

> There is an X% real-world probability of Z.

---

## 12. Sensitivity requirement

Every major conclusion must be tested against:

- different distribution families;
- wider/narrower uncertainty bounds;
- correlated vs independent sampling;
- Fibonacci vs conventional time windows;
- no-long-memory vs long-memory processes;
- different shock clustering assumptions.

If a result disappears under reasonable alternatives, it must be labeled fragile.

---

## 13. Canonical implementation rule

The uncertainty engine is not to be implemented until:

1. country data model is stable;
2. major null fields are classified;
3. uncertainty bounds are documented;
4. correlations are defined;
5. historical validation datasets are selected.

This repository remains pre-engine until those conditions are met.
