# Parallel Violent-Network Dynamics v0.13

**Status:** implementation milestone  
**Version:** 0.13.0  
**Date:** 2026-09-23  
**Calibration:** none

## Purpose

v0.13 introduces endogenous daily dynamics for the three violent-network pressure families already separated in EngineState v1:

- `violent_islamist_pressure`;
- `violent_ultranationalist_pressure`;
- `revolutionary_extremist_pressure`.

All three use the same equation, the same input structure and the same parameter set.

No population identity, religion or ordinary political vote share is a direct recruitment or violence coefficient.

## Generic equation

For network pressure `N`:

```text
driver_score =
    weighted(
        polarization,
        communal_fear,
        civilizational_narrative_strength,
        foreign_support_nonstate,
        1 - prison_control
    )

damping_score =
    weighted(
        police_effective_capacity,
        intelligence_effectiveness,
        government_legitimacy,
        social_cohesion
    )

growth = driver_score * (1 - N)
damping = damping_score * N

delta =
    medium_daily_gain
    * (growth - damping)

delta = clamp(
    delta,
    -max_single_day_latent_delta,
    +max_single_day_latent_delta
)
```

The saturation terms prevent unrestricted growth and make damping proportional to existing network pressure.

## Symmetry

The equation intentionally contains no family-specific gain.

If the three network pressures start at the same value and observe the same state, their deltas are identical.

Family divergence can arise from:

- different initial network pressure;
- future evidence-backed directed network spillover;
- future reciprocal-radicalization mechanisms;
- future family-specific evidence and calibrated equation versions.

It does not arise from civilian demographic identity.

## Inputs

Drivers:

- polarization;
- communal fear;
- civilizational narrative strength;
- foreign support to non-state actors;
- inverse prison control.

Damping:

- police effective capacity;
- intelligence effectiveness;
- government legitimacy;
- social cohesion.

All are existing EngineState v1 latents.

## Atomic integration

v0.13 remains proposal-only.

```text
event proposals
+ recovery proposals
+ matured graph-spillover proposals
+ violent-network dynamics proposals
-> one Owner Resolver
```

All proposals observe the same beginning-of-day state.

An event that raises communal fear today therefore affects endogenous network dynamics from the next simulation day, not retroactively inside the same synchronous tick.

## Traceability

Each proposed network update records:

- family ID;
- target variable;
- driver inputs and transformed values;
- damping inputs and transformed values;
- driver/damping scores;
- growth/damping components;
- equation ID;
- parameter IDs;
- value before;
- requested delta.

The canonical `delta_proposal` and downstream `owner_resolution` records preserve the commit lineage.

## Parameter discipline

Numeric weights live in:

`EXTREMIST_NETWORK_DYNAMICS_SYN_V1`

The update gain and daily cap come from:

`DYNAMIC_GAINS_SYN_V1`

The calibrated counterparts remain null and fail closed.

## Explicit exclusions

v0.13 does not implement reciprocal radicalization yet.

It also does not infer violent-network pressure directly from:

- Muslim/Christian/other population share;
- foreign-born share;
- generation;
- nationality;
- neighborhoods;
- mosque/church density;
- ordinary party vote shares.

## Next milestone

v0.14 should add reciprocal radicalization as a separate feedback proposal layer, preserving the three network families and adding explicit damping rather than merging them into demographic blocs.

All v0.13 coefficients remain engineering-only synthetic values and are not empirical causal estimates or real-world probabilities.
