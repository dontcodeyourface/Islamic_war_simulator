# Security-Chain Dynamics v0.15

**Status:** implementation milestone  
**Version:** 0.15.0  
**Date:** 2026-09-23  
**Calibration:** none

## Purpose

v0.15 adds continuous endogenous dynamics for the existing security-chain state. It does not yet classify or commit the discrete security-force regime.

The updated latents are:

- `security_chain_cohesion`;
- `command_cohesion`;
- `constitutional_loyalty`;
- `operational_fatigue`.

## Scores

A common stress score combines:

- public-order stress;
- external-conflict pressure;
- organized armed-actor capacity;
- salary-payment discontinuity;
- inverse government legitimacy;
- transport/logistics degradation.

A common resilience score combines:

- government legitimacy;
- salary-payment continuity;
- police effective capacity;
- intelligence effectiveness;
- administrative capacity;
- social cohesion.

All weights are versioned in `SECURITY_CHAIN_DYNAMICS_*`.

## Equations

For resilience-direction target `X`:

```text
recovery = resilience_score * (1 - X)
erosion  = stress_score * X
delta    = gain * (recovery - erosion)
```

For stress-direction target `F = operational_fatigue`:

```text
accumulation = stress_score * (1 - F)
recovery     = resilience_score * F
delta        = gain * (accumulation - recovery)
```

Each requested delta is capped by the configured `DYNAMIC_GAINS_*` daily cap before entering the canonical Owner Resolver.

## Synchronous semantics

All inputs are beginning-of-day state. Events, graph spillovers, reciprocal feedback or other proposals generated in the same day cannot retroactively change the security-chain proposal for that day.

The security layer never mutates EngineState directly.

## Model integrity

Ordinary party preference, religion and ethnicity are not fracture coefficients.

The model uses institutional function, operational load, conflict pressure and explicit violent-actor state.

## Scope boundary

v0.15 does not commit the discrete security-force regime. That should be a separate persistence/hysteresis layer using `SECURITY_REGIMES_*`.

All active weights remain engineering-only `synthetic_smoke_v1` values and are not empirical probabilities.
