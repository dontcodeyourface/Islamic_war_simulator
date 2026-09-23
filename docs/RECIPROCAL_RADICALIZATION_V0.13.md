# Reciprocal Radicalization v0.13

**Status:** implementation milestone  
**Version:** 0.13.0  
**Date:** 2026-09-23  
**Calibration:** none

## Purpose

v0.13 implements the Phase-1 reciprocal-radicalization feedback between the already separate violent Islamist and violent ultranationalist network-state variables.

The implementation is deliberately aggregate. It models pressure in violent networks, not civilian religious or political populations.

## State variables

The symmetric pair is:

- `violent_islamist_pressure`;
- `violent_ultranationalist_pressure`.

Shared endogenous inputs are:

- `communal_fear`;
- `civilizational_narrative_strength`;
- `social_cohesion`;
- `government_legitimacy`;
- `police_effective_capacity`;
- `intelligence_effectiveness`.

No population share, religion share or party preference is an equation input.

## Equation

For each direction `source -> target`:

```text
damping_score =
    mean(
        social_cohesion,
        government_legitimacy,
        police_effective_capacity,
        intelligence_effectiveness
    )

cross_component =
    cross_reaction_gain
    * source_pressure
    * communal_fear

narrative_component =
    narrative_amplification_gain
    * civilizational_narrative_strength
    * target_pressure

damping_component =
    damping_gain
    * damping_score
    * target_pressure

raw_delta =
    cross_component
    + narrative_component
    - damping_component
```

The reverse direction uses the exact same equation with source and target exchanged.

All gains come from the versioned `RECIPROCAL_RADICALIZATION_*` parameter family.

## Synchronous semantics

Both directions observe the same beginning-of-day state.

A proposal generated for one network cannot affect the reverse-direction equation until a later day.

The feedback layer does not mutate `EngineState` directly. It emits canonical `DeltaProposal` objects and the existing Owner Resolver aggregates and clamps them with event, recovery and matured graph-spillover proposals.

## Damping interpretation

Institutional damping is the arithmetic mean of four existing resilience/capability latents.

This is a structural composition, not an additional hidden coefficient. The only numerical feedback gains are stored in the parameter registry.

High damping can produce a negative daily delta; low damping plus fear/network pressure can produce a positive delta.

## Traceability

For every node and direction the engine records:

- `reciprocal_radicalization_evaluation`;
- source and target pressure;
- communal fear;
- narrative strength;
- damping score;
- cross component;
- narrative component;
- damping component;
- raw delta;
- equation ID;
- parameter ID.

Every non-zero effect additionally records:

- `reciprocal_radicalization_delta_proposal`;
- canonical `delta_proposal`;
- downstream `owner_resolution`.

## Safety/model integrity

Civilian identity is not a violence-propensity coefficient.

The model does not infer violent-network pressure from Muslim population share, Christian population share, immigration status, nationality, ordinary conservative/nationalist voting, mosque counts or similar identity proxies.

Violent network state must come from its own initialized evidence/prior, explicit events, validated network mechanisms or future evidence-backed graph channels.

## Scope boundary

v0.13 does not yet implement:

- security-chain endogenous dynamics;
- evidence-backed directed extremist-network graph edges;
- alliance response;
- multi-day scenario orchestration;
- Monte Carlo orchestration;
- adaptive fractal refinement;
- empirical calibration.

All active gains remain `synthetic_smoke_v1` engineering values and are not real-world probability estimates.
