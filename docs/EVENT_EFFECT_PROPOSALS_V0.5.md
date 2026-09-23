# Event Effect Proposals v0.5

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Package version:** 0.5.0  
**Direct EngineState mutation:** disabled  
**Owner-module resolution:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.5 introduces the first event-to-state coupling layer without allowing events to mutate state directly.

A `SimEvent` may now emit one or more immutable `DeltaProposal` objects.

A proposal means:

> this event requests that the registered owner module consider changing this variable by this amount.

It does not mean the change has been committed.

## 2. Architecture

```text
SimEvent
  -> DeltaProposal[]
  -> owner-module resolver (future)
  -> constraints / saturation
  -> committed EngineState delta
```

This separates event semantics from variable ownership and constraint logic.

## 3. Proposal object

Each proposal stores:

```yaml
proposal_id:
event_id:
event_type:
target_node:
variable:
owner_module:
value_before:
raw_delta:
proposed_unbounded_value:
equation_id:
parameter_ids:
apply_status:
dry_run:
```

Current status is always:

`PROPOSED_NOT_APPLIED`.

## 4. Deterministic identity

Proposal IDs derive from:

- event ID;
- target node;
- target variable;
- equation ID.

Identical replay conditions therefore recreate identical proposal IDs.

## 5. Owner routing

Ownership comes only from the canonical EngineState registry.

Representative routing:

```text
external_conflict_pressure -> external_system
public_order_stress        -> security
communal_fear              -> demographics
government_legitimacy      -> institutions
social_cohesion            -> demographics
```

Event code cannot bypass that registry.

## 6. Interstate incident proposals

Under the synthetic engineering profile, each actor receives proposals for:

```text
external_conflict_pressure +0.060
public_order_stress        +0.025
communal_fear              +0.015
```

Parameter set:

`EVENT_EFFECT_PROPOSALS_SYN_V1`.

These values are engineering coefficients only.

## 7. Mass-protest proposals

A `MASS_PROTEST_TRIGGER_V1` proposes:

```text
public_order_stress      +0.060
government_legitimacy    -0.030
social_cohesion          -0.020
```

Again, these are uncalibrated engineering values.

## 8. No clamp at proposal time

If a variable is already near its upper bound, v0.5 preserves the attempted overshoot.

Example:

```text
before = 0.97
raw delta = +0.06
proposed unbounded value = 1.03
```

No clamp is applied yet.

That belongs to the future owner resolver so the trace preserves the requested change.

## 9. Multiple proposals stay separate

Several events affecting one variable on the same day remain separate proposals.

The future resolver may:

- aggregate;
- damp;
- saturate;
- reject;
- de-duplicate;
- apply diminishing returns.

That policy is not embedded in the event layer.

## 10. Traceability

Each proposal emits a `delta_proposal` trace containing the complete proposal.

The future causal chain becomes:

```text
event
  -> delta proposal
  -> owner resolver
  -> bounded delta
  -> actual state update
```

## 11. State immutability

Proposal generation is read-only.

Tests confirm the affected EngineState hashes remain unchanged.

## 12. Supported event mappings

v0.5 provides proposal mappings only for:

- `INTERSTATE_INCIDENT_V1`;
- `MASS_PROTEST_TRIGGER_V1`.

A valid event with no registered mapping returns no proposals instead of inventing effects.

## 13. Parameter discipline

Synthetic effects:

`EVENT_EFFECT_PROPOSALS_SYN_V1`.

Calibrated counterpart:

`EVENT_EFFECT_PROPOSALS_CAL_V1 = null`.

The calibrated profile therefore remains fail-closed.

## 14. Machine-readable contract

`config/engine/event_effects_v1.yaml`

requires:

- deterministic proposal IDs;
- registered variable ownership;
- no direct mutation;
- no proposal-time clamp;
- separate proposals until owner resolution.

## 15. Validation

v0.5 verifies:

- an interstate incident creates six proposals for two actors;
- expected variables and owner modules are preserved;
- effect parameter IDs remain in trace;
- mass-protest proposal signs are correct;
- proposal IDs replay exactly;
- EngineState remains unchanged;
- calibrated effect parameters fail closed.

## 16. Still disabled

v0.5 does not implement:

- proposal aggregation;
- owner-module resolution;
- clamping/saturation;
- actual state mutation;
- recovery;
- phase transitions;
- graph spillover effects;
- event chaining.

## 17. Next milestone

v0.6 should implement the **owner-module resolver**.

It should:

1. group proposals by node, variable and owner;
2. verify every proposal references the same pre-resolution value;
3. aggregate under a versioned policy;
4. apply EngineState bounds;
5. preserve raw/aggregated/bounded deltas;
6. create a new state object rather than mutating the original;
7. record a complete resolution trace;
8. preserve exact replay;
9. keep phase transitions disabled.

---

**v0.5 defines requested change, not committed change.**
