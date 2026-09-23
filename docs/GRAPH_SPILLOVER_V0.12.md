# State-Changing Graph Spillover v0.12

**Status:** implementation milestone  
**Version:** 0.12.0  
**Date:** 2026-09-23  
**Calibration:** none

## Purpose

v0.12 turns one previously traced graph mechanism into an actual state-changing mechanism without introducing a second mutation path.

Only spillovers that were created with `apply_to_state: true`, reached their deterministic effective day and matured as `MATURED_READY_FOR_PROPOSAL` can request a state delta.

## Enabled state-changing rule

`REGIONAL_CONFLICT_PRESSURE_TRACE_V1`

Source latent:

`external_conflict_pressure`

Target latent:

`external_conflict_pressure`

Resolved channels:

- `geographic_proximity`;
- `land_border`.

The effect was already calculated and frozen when the spillover record was created:

```text
raw_effect =
    edge_weight
    * source_pressure_at_creation
    * channel_transmission_factor
```

On maturation the stored effect is converted into a `DeltaProposal` using the target node's current beginning-of-day value.

## Still trace-only

The following rules remain `apply_to_state: false`:

- information-driven polarization;
- criminal-network propagation;
- violent Islamist network propagation;
- violent ultranationalist network propagation;
- revolutionary extremist network propagation.

Their directed graph channels are currently unresolved (`null`), so they cannot be scheduled or applied.

Population identity and religious similarity remain forbidden as substitutes for violent-network connectivity.

## Atomic execution

The daily proposal set is now:

```text
event proposals
+ recovery proposals
+ matured spillover proposals
-> one deterministic Owner Resolver
```

Every spillover proposal uses the same target beginning-of-day value as every other proposal for that target variable.

This preserves synchronous semantics.

## Proposal lineage

A state-changing spillover emits:

1. `graph_spillover_candidate`;
2. queue persistence;
3. `graph_spillover_matured`;
4. `spillover_delta_proposal`;
5. canonical `delta_proposal`;
6. `owner_resolution`;
7. checkpoint `spillover_ids_applied`.

The DeltaProposal preserves the originating `spillover_id` in its source/event lineage field and preserves the spillover rule ID as its equation ID.

## Latency semantics

Latency freezes at creation time.

Changing source pressure after scheduling does not retroactively change an already queued spillover.

This is deliberate: the queued record represents delayed transmission of the pressure observed when the transmission was created.

## Bounds

The spillover layer does not independently mutate or clamp EngineState.

All simultaneous graph/event/recovery deltas are aggregated and bounded by the canonical Owner Resolver using EngineState registry bounds.

## Atomicity

Queue state, RNG state, trace records and EngineState commit together only after full transaction success.

An owner-resolution failure therefore cannot partially consume or apply a matured spillover.

## Next milestones

Major remaining Phase-1 dynamics include:

- endogenous security-chain dynamics;
- reciprocal radicalization;
- evidence-backed directed graph channels;
- alliance response;
- repeated multi-day runner/scenario packs;
- Monte Carlo orchestration;
- adaptive fractal refinement;
- empirical calibration.

All v0.12 graph gains and latencies remain synthetic engineering parameters, not empirical forecasts.
