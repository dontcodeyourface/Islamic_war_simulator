# Atomic Day Transaction v0.7

**Status:** executable infrastructure  
**Version:** 0.7.0  
**Profile:** synthetic_smoke_v1  
**Calibration:** none

## 1. Purpose

v0.7 composes the existing strategic event engine, event-effect proposals and owner-module resolver into the first complete state-changing simulation day.

The transaction is atomic and synchronous.

All candidate events observe the same beginning-of-day EngineState snapshot.

No event can see another same-day event's effects.

## 2. Daily transaction

Canonical order:

1. validate graph/state node coverage;
2. validate synchronized day;
3. clone RNG state;
4. create staged trace ledger;
5. evaluate configured event candidates against beginning-of-day states;
6. collect occurred events;
7. generate all DeltaProposal objects against beginning-of-day values;
8. resolve all proposals once through the owner resolver;
9. validate resolved states;
10. advance every state exactly one day;
11. write per-node checkpoints;
12. write transaction commit trace;
13. commit RNG state and staged trace.

If any step fails before step 13, caller RNG and trace remain unchanged.

Original EngineState objects are never mutated.

## 3. Config-driven candidate pass

Configuration:

`config/engine/day_transaction_v1.yaml`

v0.7 evaluates:

- INTERSTATE_INCIDENT_V1 across every structural graph edge;
- MASS_PROTEST_TRIGGER_V1 across every country node.

Unknown event/scope combinations fail closed.

## 4. Synchronous semantics

Suppose Spain receives two same-day effects on `public_order_stress`:

- interstate incident: +0.025;
- mass protest: +0.060.

Both proposals record the same beginning-of-day `value_before`.

The owner resolver aggregates:

```text
raw_sum_delta = 0.025 + 0.060 = 0.085
```

and applies one bounded resolution.

This removes event-order artifacts.

## 5. Atomicity

The transaction uses:

- `RNGManager.clone()`;
- private `TraceLedger`;
- immutable-by-convention state resolution.

Only a fully successful transaction calls:

- `rng.replace_from(working_rng)`;
- `trace.extend_from(staged_trace)`.

Thus an exception after stochastic draws does not advance the caller RNG.

## 6. Deterministic transaction identity

Transaction ID is derived from:

- manifest replay key;
- day;
- graph hash;
- sorted beginning-of-day state hashes;
- execution-order version.

Equivalent replay inputs therefore produce the same transaction ID.

## 7. Trace records

v0.7 adds:

- day_transaction_started;
- existing event candidate records;
- event RNG draws;
- event_created;
- delta_proposal;
- owner_resolution;
- daily_checkpoint;
- day_transaction_committed.

Each node checkpoint contains:

- state hash before;
- state hash after;
- event IDs affecting the node;
- resolution IDs affecting the node;
- clamp-producing resolution IDs.

## 8. Clock semantics

All input states must share one day.

For input day `t`:

- events are evaluated for `t + 1`;
- resolution uses values at `t`;
- returned states have day `t + 1`.

Every successful transaction advances every graph node exactly once.

## 9. State safety

The transaction rejects:

- missing graph nodes;
- extra state nodes;
- mismatched mapping keys and state.node_id;
- unsynchronized state days;
- invalid EngineState values;
- unknown candidate-pass configurations.

## 10. RNG isolation

Event streams remain namespaced by event family and actor set.

Country initialization streams remain namespaced by ISO3.

The day transaction clones all stream states before work begins and commits only on success.

## 11. Current event effects

Under synthetic_smoke_v1 only:

INTERSTATE_INCIDENT_V1, per actor:

- external_conflict_pressure +0.060;
- public_order_stress +0.025;
- communal_fear +0.015.

MASS_PROTEST_TRIGGER_V1:

- public_order_stress +0.060;
- government_legitimacy -0.030;
- social_cohesion -0.020.

These are engineering test values, not calibrated causal estimates.

## 12. CLI

Run one complete five-country day:

```bash
iwsim day-smoke \
  --repo-root . \
  --seed 42 \
  --git-commit "$(git rev-parse HEAD)" \
  --out run_output/day-smoke
```

Outputs include:

- manifest.json;
- graph.json;
- initial_states.json;
- day_result.json;
- final_states.json;
- replay_summary.json;
- trace.jsonl.

## 13. Validation

The v0.7 test suite requires:

- no-event day advances all five nodes once;
- caller states remain unchanged;
- generated interstate and mass-protest events resolve in one batch;
- same-variable proposals aggregate from the common beginning state;
- clamp behavior is visible in node checkpoints;
- exact replay;
- state-dictionary order independence;
- node mismatch fails before side effects;
- failure after event RNG consumption rolls back RNG, trace and states.

## 14. Scope boundary

Still disabled:

- phase transitions;
- graph spillover effects;
- recovery / mean reversion;
- resource depletion;
- reciprocal-radicalization state updates;
- strategic-agent decisions;
- event chaining;
- fractal refinement;
- calibrated event probabilities.

## 15. Next milestone

The next logical layer is **v0.8 memory and recovery**.

It should add only bounded owner-routed endogenous proposals for variables that naturally relax toward baseline, for example:

- communal_fear;
- public_order_stress;
- infrastructure functionality.

Path-dependent variables should not receive generic mean reversion.

The memory/recovery layer must use the already registered time-scale parameters and remain fully traceable.

---

**v0.7 is the first atomic state-changing day, not yet a calibrated conflict simulator.**
