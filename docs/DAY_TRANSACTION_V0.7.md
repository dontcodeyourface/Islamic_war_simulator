# Atomic Day Transaction v0.7

**Status:** implementation milestone  
**Version:** 0.7.0  
**Date:** 2026-09-23  
**Parameter profile:** `synthetic_smoke_v1` only for engineering tests  
**Phase transitions:** disabled  
**Graph spillover effects:** disabled

## 1. Purpose

v0.7 introduces the first complete one-day state transaction.

Previous milestones provided:

- Snapshot initialization;
- structural graph;
- event generation;
- event-effect proposals;
- owner-module resolution.

v0.7 composes those layers into one deterministic daily transaction while preserving atomicity and traceability.

The transaction is intentionally synchronous.

All event candidates for a day observe the same **beginning-of-day** state.

No event created during that day can alter another event candidate evaluated during the same day.

## 2. Canonical flow

```text
EngineState[t] for all active nodes
        ↓
validate graph/state/day consistency
        ↓
clone RNG
create staged trace ledger
        ↓
evaluate all configured event candidates
against EngineState[t]
        ↓
collect occurred events
        ↓
generate all DeltaProposal objects
against EngineState[t]
        ↓
resolve all proposals in one owner batch
        ↓
validate resulting states
        ↓
advance every node to t+1
        ↓
write daily checkpoints
        ↓
commit RNG + staged trace
        ↓
EngineState[t+1]
```

## 3. Atomicity

The transaction contract is defined in:

`config/engine/day_transaction_v1.yaml`

A day commits only after every phase succeeds.

Before commit:

- caller EngineState objects remain untouched;
- the caller RNG remains untouched;
- the caller TraceLedger remains untouched.

The transaction works with:

- cloned RNG state;
- a private staged TraceLedger;
- new state objects produced by the owner resolver.

If any exception occurs before commit, those temporary objects are discarded.

Therefore a failed day must leave:

```text
state_after_failure == state_before
rng_after_failure   == rng_before
trace_after_failure == trace_before
```

## 4. RNG transactionality

v0.7 adds:

```text
RNGStream.clone()
RNGManager.clone()
RNGManager.replace_from()
```

Event evaluation consumes random numbers only from the cloned working RNG.

The working RNG replaces the caller RNG only after a successful state transaction.

This prevents a failed simulation day from silently shifting every later random event.

## 5. Trace staging

All transaction records are first written into a temporary TraceLedger.

The staged ledger can contain:

- transaction start;
- event RNG draws;
- event candidates;
- created events;
- delta proposals;
- owner resolutions;
- daily checkpoints;
- transaction commit.

Only after successful state resolution and day advancement is the staged ledger appended to the caller ledger.

Failed days leave no partial causal history.

## 6. Event evaluation order

The current configured order is:

1. `INTERSTATE_INCIDENT_V1` over all structural graph edges;
2. `MASS_PROTEST_TRIGGER_V1` over all country nodes.

Within each scope:

- graph edges use ascending `edge_id`;
- nodes use ascending `node_id`.

The order is explicit and versioned.

Adding another event family requires adding it to the transaction contract and implementing a supported dispatcher.

Unknown event/scope pairs fail closed.

## 7. Synchronous same-day semantics

Suppose an interstate incident and a mass protest both occur on day 12.

Both hazards are calculated from:

```text
EngineState[day 11 end / day 12 beginning]
```

The interstate incident does not increase public-order stress before the mass-protest hazard is evaluated.

Instead:

```text
candidate A
candidate B
candidate C
...
        ↓
all events fixed
        ↓
all effect proposals fixed
        ↓
single resolution
```

This prevents event-order artifacts.

Cross-event feedback therefore begins on the following simulation day unless a future explicitly versioned mechanism introduces within-day substeps.

## 8. Proposal aggregation

Every occurred event may emit `DeltaProposal` objects.

All proposals are based on the same beginning-of-day value.

The owner resolver then groups by:

```text
target_node + variable
```

and performs the canonical deterministic sum-and-clamp resolution.

Therefore two events can both affect:

`ESP.public_order_stress`

without one proposal becoming stale simply because another event happened earlier in the evaluation loop.

## 9. State immutability

Input state objects remain unchanged.

The owner resolver returns new state objects at the same day.

The transaction layer then clones those resolved states to:

```text
day = previous_day + 1
```

Only those advanced state objects are returned as the committed result.

## 10. State-set integrity

v0.7 requires the runtime state node set to match the active structural graph node set exactly.

For the current base graph:

```text
DEU
ESP
FRA
GBR
MAR
```

A missing or additional node fails before event evaluation.

This prevents accidental partial-country transactions.

Future fractal execution may require a different graph/state contract, but that must be separately versioned.

## 11. Day synchronization

All input states must have the same `day`.

Example invalid input:

```text
ESP day 11
FRA day 11
MAR day 10
```

This fails closed.

The transaction cannot silently bring nodes into synchronization.

## 12. Transaction identity

Each successful or attempted transaction has a deterministic ID derived from:

- replay key;
- beginning day;
- structural graph hash;
- beginning state hashes;
- transaction rule ID.

Conceptually:

```text
DAY_TRANSACTION_V1
+ replay identity
+ day
+ graph
+ state hashes
→ transaction_id
```

Equivalent replay state therefore produces the same transaction ID.

## 13. Result contract

`DayTransactionResult` contains:

- transaction ID;
- day before;
- day after;
- committed state objects;
- every candidate result;
- every occurred event;
- every delta proposal;
- every owner-resolution record;
- state hashes before;
- state hashes after.

This provides a compact programmatic view while the TraceLedger remains the detailed causal history.

## 14. Daily checkpoints

Each node checkpoint now records:

- state hash before;
- state hash after;
- event IDs applied to the node;
- resolution IDs;
- clamp-producing resolution IDs;
- future placeholders for spillovers, agents and refinement.

This makes the daily ledger directly navigable.

## 15. SimEvent dry-run semantics

The event generator remains read-only.

`SimEvent.dry_run = true` means:

> the event generator itself does not mutate EngineState.

It does **not** mean the event is ignored.

In v0.7 the valid path is:

```text
SimEvent
→ DeltaProposal
→ owner resolver
→ committed next state
```

Direct event mutation remains forbidden.

A later schema version may rename this field for clarity, but v0.7 preserves backward compatibility with v0.4–v0.6.

## 16. Current event families

v0.7 currently integrates:

### INTERSTATE_INCIDENT_V1

If it occurs, the current synthetic effect proposal set can influence each actor's:

- external conflict pressure;
- public-order stress;
- communal fear.

### MASS_PROTEST_TRIGGER_V1

If it occurs, the current synthetic effect proposal set can influence:

- public-order stress;
- government legitimacy;
- social cohesion.

All values remain engineering-only `synthetic_smoke_v1` parameters.

They are not calibrated causal estimates.

## 17. What v0.7 does not implement

Still disabled:

- phase transitions;
- graph spillover effects;
- alliance reaction chaining;
- resource depletion;
- military attrition;
- institutional recovery;
- reciprocal radicalization dynamics;
- event ancestry/chaining within the same day;
- fractal refinement;
- strategic-agent decisions.

The purpose of v0.7 is transactional integrity, not realism expansion.

## 18. CLI smoke path

A five-country transaction can be executed with:

```bash
iwsim day-smoke \
  --repo-root . \
  --seed 42 \
  --git-commit "$(git rev-parse HEAD)" \
  --out /tmp/iwsim-day
```

Outputs:

- `manifest.json`;
- `graph.json`;
- `initial_states.json`;
- `day_result.json`;
- `replay_summary.json`;
- `trace.jsonl`.

## 19. Test contract

v0.7 tests require:

- no-event day advances every node exactly once;
- input states remain unchanged;
- generated events produce committed effects;
- multiple proposals against one variable are aggregated;
- canonical bounds clamp overshoot;
- exact replay;
- state-dictionary input order does not alter results;
- node mismatch fails before side effects;
- a forced post-RNG failure rolls back RNG, trace and state.

## 20. Next milestone

After v0.7 the safest next addition is **v0.8 phase evaluation in read-only mode**.

Recommended sequence:

1. evaluate national phase from committed end-of-day state;
2. emit a proposed phase-transition record;
3. require persistence windows;
4. do not mutate phase initially;
5. validate hysteresis/replay;
6. only then allow phase-transition commit.

This follows the same staged architecture used successfully for event effects.

---

**Atomic Day Transaction v0.7 establishes the first deterministic state-changing simulation day while keeping conflict dynamics narrowly scoped and fully auditable.**
