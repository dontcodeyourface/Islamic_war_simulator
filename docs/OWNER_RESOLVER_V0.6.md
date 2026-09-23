# Owner-Module Resolver v0.6

**Status:** implementation milestone  
**Date:** 2026-09-23  
**State mutation:** enabled only through resolver output  
**Phase transitions:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.6 is the first layer allowed to convert one or more `DeltaProposal` objects into committed EngineState changes.

Events still cannot mutate state directly.

The canonical path is now:

```text
SimEvent
  ↓
DeltaProposal[]
  ↓
Owner Resolver
  ↓
bounded committed delta
  ↓
new EngineState
```

## 2. Resolver responsibilities

The resolver must:

1. group proposals by target node and variable;
2. verify the target node exists;
3. verify the variable exists;
4. verify the proposal owner matches the canonical EngineState owner;
5. verify every proposal was computed from the current pre-resolution value;
6. reject duplicate proposal IDs;
7. aggregate raw deltas deterministically;
8. apply canonical variable bounds;
9. emit a resolution trace;
10. create new state objects;
11. leave original states unchanged.

## 3. Aggregation policy

Synthetic v0.6 policy:

```text
aggregation = sum
order       = proposal_id ascending
summation   = math.fsum
```

Policy ID:

`OWNER_RESOLVER_POLICY_SYN_V1`

This is an engineering resolution rule, not a calibrated political model.

## 4. Why deterministic ordering matters

Floating-point addition can vary slightly with ordering.

The resolver therefore sorts proposal IDs before aggregation and uses `math.fsum`.

The same proposal set must yield the same committed state regardless of input order.

## 5. Stale-proposal rejection

Every proposal contains `value_before`.

Before resolution:

```text
proposal.value_before
must equal
current_state.latents[variable]
```

within a strict numerical tolerance.

If another process has already changed the variable, the proposal is stale and resolution fails closed.

This prevents hidden double-application.

## 6. Ownership validation

Example:

```text
public_order_stress -> security
```

A proposal claiming:

```text
owner_module = institutions
```

is rejected.

The resolver never trusts the proposal's owner field without checking the canonical EngineState registry.

## 7. Bounds

Bounds come only from:

`config/engine/engine_state_v1.yaml`

Most latents use:

```text
0.0 <= x <= 1.0
```

Signed variables can use other registered bounds.

No bounds are duplicated inside resolver code.

## 8. Clamp visibility

Example:

```text
value_before = 0.97
raw_sum_delta = +0.06
unbounded = 1.03
```

The resolver records:

```text
value_after = 1.00
bounded_delta = +0.03
clamp_amount = +0.03
```

The attempted overshoot remains visible.

## 9. Lower-bound clamp

Example:

```text
value_before = 0.01
raw_sum_delta = -0.03
unbounded = -0.02
```

Resolution:

```text
value_after = 0.00
bounded_delta = -0.01
clamp_amount = -0.02
```

## 10. Resolution record

Every committed variable update stores:

```yaml
resolution_id:
target_node:
variable:
owner_module:
proposal_ids:
value_before:
raw_sum_delta:
proposed_unbounded_value:
lower_bound:
upper_bound:
bounded_delta:
value_after:
clamp_amount:
equation_id:
parameter_ids:
apply_status:
```

Current equation:

`OWNER_RESOLVE_SUM_CLAMP_V1`

Current apply status:

`COMMITTED`

## 11. Proposal lineage

A resolution record preserves every contributing proposal ID.

Therefore the causal path is fully traversable:

```text
state delta
  ↑
owner resolution
  ↑
delta proposals
  ↑
event
  ↑
hazard inputs / RNG / parameters
```

## 12. State immutability

The resolver creates new `EngineState` objects.

The original objects are not modified.

Required invariant:

```text
original_state_hash_before
==
original_state_hash_after
```

while:

```text
resolved_state_hash
!=
original_state_hash
```

when a non-zero committed delta exists.

## 13. Clock semantics

v0.6 does not advance the simulation day.

The resolver operates inside a daily update step.

Therefore:

```text
resolved_state.day == input_state.day
```

Clock advancement remains an engine-loop responsibility.

## 14. Duplicate proposal protection

Two proposals with the same `proposal_id` are rejected before aggregation.

This prevents accidental double counting from duplicated trace/event delivery.

## 15. Calibrated profile

`OWNER_RESOLVER_POLICY_CAL_V1`

is currently null.

A calibrated resolver request therefore fails closed.

The resolution algorithm itself may eventually remain identical across profiles, but the project does not silently assume that before the calibrated contract is approved.

## 16. Tests

v0.6 verifies:

- multiple proposals to one variable are aggregated;
- original state remains unchanged;
- new state object is created;
- upper bound is enforced;
- lower bound is enforced;
- clamp amount is visible;
- stale proposals fail;
- owner mismatch fails;
- duplicate proposal IDs fail;
- input order does not change output;
- calibrated profile fails closed while unpopulated.

## 17. Still disabled

v0.6 does not implement:

- phase transitions;
- recovery/mean reversion;
- graph spillover;
- resource-stock depletion;
- event chaining;
- alliance-agent decisions;
- fractal refinement.

## 18. Next milestone

v0.7 should integrate the existing pieces into a deterministic **single-day multi-node transaction**:

```text
states(t)
  ↓
evaluate event candidates
  ↓
create events
  ↓
create delta proposals
  ↓
owner resolver
  ↓
states(t) updated
  ↓
daily checkpoint
  ↓
advance to t+1
```

The transaction must be atomic at the simulation level:

- all event candidates evaluate against the same pre-day state;
- all proposals reference that same state;
- no earlier event in the day can change the hazard of a later event;
- state is committed only after all proposals are collected;
- checkpoint hashes must make replay divergence locatable.

Phase classification should remain disabled until this daily transaction is proven stable.

---

**Owner-Module Resolver v0.6 is the first committed state-update layer, but not yet a full daily engine.**
