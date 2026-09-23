# Graph Spillover Trace and Latency Queue v0.11

**Status:** implementation milestone  
**Version:** 0.11.0  
**Date:** 2026-09-23  
**State-changing graph effects:** disabled  
**Calibration:** none

## Purpose

v0.11 implements the trace-before-effect sequence required by the typed graph contract.

It adds:

1. a canonical cross-node spillover record;
2. deterministic per-channel latency selection;
3. an immutable pending queue carried across simulation days;
4. trace-only maturation;
5. explicit handling of unresolved and zero-value channels;
6. transaction identity coupling to queue history and spillover configuration.

No v0.11 spillover mutates EngineState.

## Candidate equation

For resolved channel k:

```text
raw_effect[i -> j, k] =
    edge_weight[i, j, k]
    * source_pressure[i]
    * transmission_factor[k]
```

Transmission factors come from `GRAPH_TRANSMISSION_*`.

The result is recorded as `bounded_effect` unchanged in v0.11 because state effects are disabled. Canonical EngineState bounds will be enforced by the Owner Resolver only when state-changing spillover proposals are introduced.

## Latency

Each channel retains its configured latency interval from `GRAPH_LATENCIES_*`.

A deterministic hash over:

- evaluation day;
- source node;
- target node;
- channel;
- rule ID;

selects an integer in the inclusive configured interval.

This consumes no RNG stream and therefore cannot perturb stochastic event replay.

## Queue contract

`SpilloverQueueState` contains:

- `last_processed_day`;
- immutable scheduled records whose `day_effective` is still in the future.

At day zero an absent queue is normalized to an empty queue.

After day zero, integrated spillover execution requires the queue returned by the previous day. Missing or stale queue history fails closed.

A record whose effective day is reached becomes `MATURED_TRACE_ONLY` and leaves the pending queue.

## Statuses

Candidate records use:

- `SCHEDULED`;
- `UNRESOLVED_CHANNEL`;
- `ZERO_EDGE`;
- `ZERO_SOURCE`;
- `ZERO_TRANSMISSION`.

Matured records use:

- `MATURED_TRACE_ONLY`.

Unresolved directed channels remain null and are never silently interpreted as zero.

## Initial rule set

The first resolved structural rule traces regional external-conflict pressure over:

- `geographic_proximity`;
- `land_border`.

Additional trace-only rules exercise the currently unresolved directed contracts for:

- information-driven polarization;
- organized crime;
- violent Islamist networks;
- violent ultranationalist networks;
- revolutionary extremist networks.

The three extremist families use the same channel contract. Population or religious identity is not an input.

## Atomic daily placement

v0.11 evaluates graph spillovers before stochastic event generation:

```text
beginning state
  -> graph spillover trace/queue pass
  -> event candidates
  -> event effects
  -> recovery proposals
  -> owner resolution
  -> clock advance
  -> phase evaluation/commit
  -> checkpoint
```

Because v0.11 is trace-only, matured spillovers are not listed as applied spillovers in checkpoints.

## Next milestone

v0.12 may convert a narrowly selected matured spillover family into DeltaProposal objects routed through the existing Owner Resolver.

That PR should not activate unresolved directed channels until comparable evidence populates those edges.
