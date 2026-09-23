# Owner-Module Resolver v0.6

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Package version:** 0.6.0  
**State mutation:** enabled only through resolver output  
**Phase transitions:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.6 is the first layer allowed to convert one or more `DeltaProposal` objects into committed EngineState changes.

Events still cannot mutate state directly.

Canonical path:

```text
SimEvent
  -> DeltaProposal[]
  -> Owner Resolver
  -> bounded committed delta
  -> new EngineState
```

## 2. Resolver responsibilities

The resolver:

1. groups proposals by target node and variable;
2. verifies target node and variable existence;
3. verifies canonical owner-module routing;
4. verifies every proposal was computed from the current pre-resolution value;
5. rejects duplicate proposal IDs;
6. aggregates raw deltas deterministically;
7. applies canonical EngineState bounds;
8. records raw, unbounded, bounded and clamp values;
9. returns new EngineState objects;
10. leaves original states unchanged.

## 3. Aggregation policy

Synthetic policy:

```text
aggregation = sum
order       = proposal_id ascending
summation   = math.fsum
```

Parameter ID:

`OWNER_RESOLVER_POLICY_SYN_V1`.

This is an engineering resolution policy, not a calibrated causal model.

## 4. Determinism

Floating-point addition can vary with order.

The resolver therefore sorts proposal IDs and uses `math.fsum`.

The same proposal set must produce the same result regardless of input order.

## 5. Stale-proposal protection

Each proposal stores `value_before`.

Before resolution:

```text
proposal.value_before == current_state.latents[variable]
```

within strict tolerance.

If state has already changed, the proposal is stale and resolution fails closed.

## 6. Ownership validation

Proposal ownership is checked against `config/engine/engine_state_v1.yaml`.

A proposal cannot redirect a latent to a different module.

## 7. Canonical bounds

Bounds come only from EngineState registry metadata.

Most latents use:

```text
0 <= x <= 1
```

Signed latents retain their registered bounds.

Bounds are not duplicated in resolver code.

## 8. Clamp trace

Example:

```text
value_before = 0.97
raw_sum_delta = +0.06
unbounded = 1.03
value_after = 1.00
bounded_delta = +0.03
clamp_amount = +0.03
```

The attempted overshoot remains visible.

## 9. Resolution record

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

Equation:

`OWNER_RESOLVE_SUM_CLAMP_V1`.

Current apply status:

`COMMITTED`.

## 10. Proposal lineage

Every resolution keeps all contributing proposal IDs.

The causal path is therefore:

```text
committed state delta
  <- owner resolution
  <- delta proposals
  <- event
  <- hazard / RNG / parameters
```

## 11. Immutability

The resolver clones states before applying committed values.

Required invariant:

```text
original_state_hash_before == original_state_hash_after
```

and for a non-zero delta:

```text
resolved_state_hash != original_state_hash
```

## 12. Clock semantics

v0.6 does not advance simulation time.

```text
resolved_state.day == input_state.day
```

Clock advancement remains a transaction/engine-loop responsibility.

## 13. Fail-closed checks

The resolver rejects:

- duplicate proposal IDs;
- stale proposals;
- unknown nodes;
- unknown variables;
- owner mismatches;
- already-applied proposal status;
- missing profile parameters.

## 14. Calibrated profile

`OWNER_RESOLVER_POLICY_CAL_V1` remains null.

A calibrated resolution attempt therefore fails closed.

## 15. Validation

v0.6 tests:

- deterministic aggregation of several proposals;
- original-state immutability;
- creation of new state objects;
- upper-bound clamp;
- lower-bound clamp;
- clamp amount visibility;
- stale proposal rejection;
- owner mismatch rejection;
- duplicate proposal rejection;
- input-order independence;
- calibrated profile fail-closed behavior.

## 16. Still disabled

v0.6 does not implement:

- phase transitions;
- recovery/mean reversion;
- graph spillover effects;
- resource depletion;
- event chaining;
- alliance-agent decisions;
- fractal refinement.

## 17. Next milestone

v0.7 should combine the existing layers into an atomic single-day transaction:

```text
states(t)
  -> evaluate event candidates against the same pre-day state
  -> create events
  -> create proposals
  -> resolve all proposals
  -> commit new states
  -> checkpoint
  -> advance to t+1
```

No event earlier in the day may change the hazard of a later event.

Phase classification must remain disabled until that daily transaction is replay-stable.

---

**Owner Resolver v0.6 is the first committed state-update layer, not yet a full daily simulation engine.**
