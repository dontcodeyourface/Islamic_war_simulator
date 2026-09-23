# Event Effect Proposals v0.5

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Direct EngineState mutation:** disabled  
**Owner-module resolution:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.5 introduces the first event-to-state coupling layer without allowing events to mutate state directly.

An event may now produce one or more **DeltaProposal** objects.

A proposal means:

> this event requests that the owner module consider changing this variable by this amount.

It does not mean the change has been committed.

## 2. Architecture

```text
SimEvent
  ↓
DeltaProposal[]
  ↓
owner-module resolver (future)
  ↓
constraints / saturation
  ↓
committed EngineState delta
```

The explicit proposal layer keeps event semantics separate from state ownership and constraint logic.

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

`PROPOSED_NOT_APPLIED`

## 4. Deterministic proposal identity

A proposal ID is derived from:

- event ID;
- target node;
- target variable;
- equation ID.

Identical replay conditions therefore recreate the same proposal IDs.

## 5. Owner-module routing

Ownership comes only from the canonical EngineState registry.

Representative routing:

```text
external_conflict_pressure -> external_system
public_order_stress       -> security
communal_fear             -> demographics
government_legitimacy     -> institutions
social_cohesion           -> demographics
```

Event code cannot bypass that registry.

## 6. Interstate incident proposals

Under the synthetic engineering profile, an `INTERSTATE_INCIDENT_V1` proposes for each actor:

```text
external_conflict_pressure +0.060
public_order_stress        +0.025
communal_fear              +0.015
```

Parameter set:

`EVENT_EFFECT_PROPOSALS_SYN_V1`

These are engineering test coefficients, not calibrated causal estimates.

## 7. Mass-protest proposals

A `MASS_PROTEST_TRIGGER_V1` proposes:

```text
public_order_stress      +0.060
government_legitimacy    -0.030
social_cohesion           -0.020
```

Again, these values exist only to exercise the effect pipeline.

## 8. No clamps yet

If:

```text
external_conflict_pressure = 0.97
raw proposal              = +0.06
```

v0.5 records:

```text
proposed_unbounded_value = 1.03
```

It does not clamp to 1.0.

Constraint handling belongs to the owner-module resolver.

This preserves visibility into attempted overshoot.

## 9. Multiple proposals remain separate

If several events affect the same variable on the same day, v0.5 keeps each proposal independently traceable.

The future owner resolver may decide whether to:

- sum;
- damp;
- saturate;
- reject;
- de-duplicate;
- apply diminishing returns.

That policy is intentionally not embedded in the event layer.

## 10. Traceability

Every proposal emits a `delta_proposal` trace record containing the full proposal object.

The future causal chain becomes:

```text
event
  ↓
delta proposal
  ↓
owner resolver
  ↓
constraint/clamp
  ↓
actual state delta
```

## 11. State immutability

Proposal generation is read-only.

Tests verify:

```text
state_hash_before == state_hash_after
```

for all affected states.

## 12. Supported event families

v0.5 proposal mappings exist only for:

- `INTERSTATE_INCIDENT_V1`
- `MASS_PROTEST_TRIGGER_V1`

A supported event without a registered effect mapping produces no proposals rather than inventing one.

## 13. Parameter discipline

Synthetic effects live under:

`EVENT_EFFECT_PROPOSALS_SYN_V1`

The calibrated counterpart:

`EVENT_EFFECT_PROPOSALS_CAL_V1`

remains null and fail-closed.

No effect magnitude is hidden in behavioral source code.

## 14. Machine-readable contract

The proposal contract is stored in:

`config/engine/event_effects_v1.yaml`

It explicitly requires:

- deterministic proposal IDs;
- registered variable ownership;
- no state mutation;
- no clamp at proposal time;
- separate proposals until owner resolution.

## 15. Tests

v0.5 verifies:

- interstate incident creates six proposals for two actors;
- correct variables are targeted;
- owner modules are resolved from EngineState registry;
- proposal parameter IDs are retained;
- proposal IDs are replay-stable;
- mass-protest effect signs are correct;
- state hashes remain unchanged;
- `delta_proposal` traces are emitted.

## 16. Still disabled

v0.5 does not implement:

- proposal aggregation;
- owner-module resolution;
- clamps/saturation;
- actual state mutation;
- recovery;
- phase transitions;
- graph spillover;
- event chaining.

## 17. Next milestone

v0.6 should implement the **owner-module resolver**.

Its responsibilities should be:

1. group proposals by node, variable and owner module;
2. verify all proposals reference the same pre-resolution state;
3. aggregate according to a versioned policy;
4. apply variable bounds;
5. emit raw/aggregated/bounded deltas;
6. create a new immutable next-state object;
7. preserve the original state;
8. prove exact replay;
9. leave phase transitions disabled.

Only after that resolver is stable should phase classifiers consume the updated state.

---

**Event Effect Proposals v0.5 defines requested change, not committed change.**
