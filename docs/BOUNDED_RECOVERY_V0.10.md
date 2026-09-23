# Bounded Recovery v0.10

**Status:** implementation milestone  
**Version:** 0.10.0  
**Date:** 2026-09-23  
**Active profile:** `synthetic_smoke_v1`  
**Calibration:** none

## Purpose

v0.10 adds deterministic endogenous recovery without adding a second state-mutation path.

The daily flow becomes:

```text
beginning-of-day state
  -> event candidates
  -> event-effect proposals
  -> bounded recovery proposals
  -> one owner-resolution pass
  -> clock advance
  -> phase evaluation/arbitration/commit
  -> checkpoint
```

Event and recovery proposals observe the same beginning-of-day values. Recovery therefore cannot react to a shock generated later in the same synchronous day.

## Memory contract

Every initialized EngineState stores an immutable copy of its initial latent vector at:

`metadata.initial_latents`

v0.10 uses that vector as recovery memory. This preserves country-specific starting conditions and avoids hard-coding a universal equilibrium.

Missing recovery memory fails closed when recovery is enabled.

## Enabled recovery variables

Only variables with natural relaxation semantics are enabled:

- `communal_fear`;
- `public_order_stress`;
- `electricity_functionality`;
- `telecom_internet_functionality`.

Path-dependent variables are deliberately excluded.

## Equation

For variable `x` with immutable initial baseline `b`:

```text
raw_delta = (b - x_t) * recovery_gain
delta = clamp(raw_delta, -max_daily_delta, +max_daily_delta)
```

All gains and caps come from the authoritative `DYNAMIC_GAINS_*` parameter set.

## Traceability

Each non-zero recovery change emits:

- `recovery_proposal`;
- the canonical `delta_proposal`;
- the downstream `owner_resolution`.

The proposal retains equation ID, parameter ID, node, day, baseline and exact value-before.

## Safety and model integrity

Recovery is generic state relaxation. It does not use demographic identity, political identity or religious share as a violence propensity.

## Still missing

- de-escalation phase transitions;
- typed graph spillover effects;
- extremist-network endogenous dynamics;
- reciprocal radicalization;
- security-chain dynamics;
- alliance response;
- repeated multi-day runner;
- Monte Carlo;
- fractal refinement;
- empirical calibration.
