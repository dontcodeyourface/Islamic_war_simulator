# Atomic Phase Transition v0.9

**Status:** implementation milestone  
**Version:** 0.9.0  
**Date:** 2026-09-23  
**Active profile:** `synthetic_smoke_v1`  
**De-escalation:** disabled  
**Calibration:** none

## 1. Purpose

v0.9 closes the gap between the read-only phase evaluator and the atomic daily transaction.

The runtime can now execute:

```text
beginning-of-day states
  -> event candidates
  -> occurred events
  -> effect proposals
  -> owner resolution
  -> clock advance
  -> end-of-day phase evaluation
  -> deterministic phase arbitration
  -> atomic phase commit
  -> persistence commit
  -> checkpoints
```

This remains a strategic state classifier. It does not create tactical behavior.

## 2. Why arbitration is required

v0.8 intentionally allowed multiple mature outgoing proposals.

The important current example is:

```text
INSURGENCY
  -> DUAL_AUTHORITY
  -> CIVIL_WAR
```

Both rules can mature on the same day.

v0.9 permits at most one phase commit per node per day.

The arbitration policy is explicit and versioned:

`PHASE_ARBITRATION_HIGHEST_ORDER_V1`

Policy:

1. rank every target by canonical `phase_order`;
2. select the highest target phase;
3. if equal, select `proposal_id` ascending;
4. retain every rejected proposal ID in trace.

Thus input-list order can never decide the transition.

## 3. Current phase order

The arbitration rank comes from:

`config/engine/phase_evaluator_v1.yaml`

Canonical order:

```text
STABLE
TENSION
EMERGENCY
MASS_UNREST
ORGANIZED_POLITICAL_VIOLENCE
INSURGENCY
DUAL_AUTHORITY
CIVIL_WAR
STATE_FRAGMENTATION
```

v0.9 permits escalation only.

A proposal whose target rank is not higher than its current phase fails closed.

## 4. Commit contract

Configuration:

`config/engine/phase_transition_v1.yaml`

Implementation:

`src/iwsim/phase_transition.py`

Commit rule:

`PHASE_COMMIT_V1`

A commit:

- creates a new EngineState;
- changes only `regimes.national_phase`;
- preserves all latents and physical stocks;
- validates the resulting state;
- verifies the original state hash did not change;
- emits a deterministic commit ID;
- records the state hashes before and after.

Direct mutation of the input state remains forbidden.

## 5. Persistence semantics

Phase history is now part of transactional simulation state.

After day zero, phase integration requires a `PhasePersistenceState` for every country node.

Missing history fails closed.

If no transition commits:

```text
evaluator persistence
  -> committed persistence
```

If a transition commits:

```text
new phase
last_evaluated_day = current day
streaks = {}
```

Old-phase streaks cannot leak into the new phase.

## 6. Transaction identity

Before v0.9, transaction identity depended on:

- replay key;
- day;
- graph hash;
- beginning state hashes;
- execution-order version.

v0.9 additionally includes:

- phase-persistence history;
- phase context flags;
- phase-evaluator config hash;
- phase-transition config hash.

This is necessary because two otherwise identical EngineStates with different persistence streaks can produce different phase outcomes.

## 7. Context flags

Structural facts remain explicit.

Examples:

- `competing_authority_present`;
- `multiple_authority_nodes_present`.

The transaction accepts context flags per node.

Unknown context-node IDs fail closed.

A scalar state cannot invent a competing authority.

## 8. Atomicity

Phase evaluation/arbitration executes inside the existing staged transaction.

The caller RNG and trace are committed only after:

1. event generation;
2. effect proposal generation;
3. owner resolution;
4. clock advance;
5. phase evaluation;
6. arbitration;
7. phase state/persistence commit;
8. checkpoints.

Any exception before final commit leaves caller:

- RNG unchanged;
- trace unchanged;
- input EngineStates unchanged;
- input persistence unchanged.

## 9. Trace records

v0.9 adds:

### `phase_arbitration`

Contains:

- arbitration ID;
- node/day/from phase;
- all proposal IDs;
- selected proposal ID;
- rejected proposal IDs;
- arbitration rule;
- target phase ranks.

### `phase_transition_committed`

Contains:

- commit ID;
- arbitration ID;
- selected proposal ID;
- from/to phase;
- transition rule;
- threshold parameter ID;
- state hashes before/after.

### `phase_persistence_committed`

Contains:

- node/day;
- committed current phase;
- committed streak map;
- whether persistence came from ordinary evaluation or transition reset;
- transition commit ID when applicable.

Daily checkpoints now also contain:

`phase_transition_ids`.

## 10. Transaction result

`DayTransactionResult` now exposes:

- committed states;
- event candidates;
- events;
- effect proposals;
- owner resolutions;
- phase persistence by node;
- phase evaluations;
- phase arbitrations;
- phase commits.

Legacy callers can keep phase integration disabled explicitly.

The canonical v0.9 `day-smoke` command enables it.

## 11. First-day semantics

At simulation day zero there is no prior evaluator history.

Therefore:

```text
phase_persistence = None
```

is permitted only for the first integrated transaction.

After that first day, every node must provide the returned persistence object.

This prevents accidental streak resets between days.

## 12. Simultaneous INSURGENCY proposals

When both conditions mature:

```text
INSURGENCY -> DUAL_AUTHORITY
INSURGENCY -> CIVIL_WAR
```

the current synthetic policy chooses:

`CIVIL_WAR`

because it has the higher canonical phase rank.

The rejected DUAL_AUTHORITY proposal remains visible in the arbitration record.

This is an engineering arbitration rule, not an empirical claim about real conflicts.

## 13. De-escalation remains disabled

v0.9 does not implement reverse transitions.

The Normalization/Parameters contract already requires hysteresis and stronger recovery persistence.

Before de-escalation is enabled, the project still needs:

- explicit recovery equations;
- recovery thresholds;
- recovery-memory semantics;
- de-escalation persistence;
- historical calibration/validation.

No reverse transition is inferred automatically from the escalation thresholds.

## 14. CLI

`iwsim day-smoke` now loads:

- day transaction config;
- phase evaluator config;
- phase-transition config.

The one-day smoke run generally creates persistence history without a transition because synthetic phase rules require multi-day persistence.

Outputs expose:

- phase commit IDs;
- resulting phase persistence.

## 15. Tests

v0.9 validation covers:

- atomic STABLE -> TENSION commit after the required prior streak;
- original-state immutability;
- persistence reset after committed transition;
- checkpoint linkage to phase commit;
- simultaneous INSURGENCY arbitration;
- highest-target selection independent of proposal list order;
- transaction-ID sensitivity to persistence history;
- mandatory persistence after day zero;
- rollback of RNG/trace/state on arbitration failure.

Existing v0.7/v0.8 replay tests remain active.

## 16. Safety/model integrity

Phase transition logic cannot use demographic identity as a direct shortcut.

It remains forbidden to map:

- Muslim population -> Islamist violence;
- Christian population -> ultranationalist violence;
- conservative population -> violent defection;
- left-wing population -> revolutionary violence.

Phases arise from the documented latent/network/institutional dynamics.

## 17. Calibration status

The phase thresholds remain `synthetic_smoke_v1`.

The arbitration policy is deterministic engine plumbing.

Neither constitutes a real-world probability or prediction.

## 18. What is still missing

After v0.9, the major Phase-1 gaps are:

1. endogenous memory/recovery proposals;
2. executable typed graph spillover;
3. broader extremist-network dynamics;
4. reciprocal-radicalization state updates;
5. security-chain endogenous dynamics;
6. alliance response dynamics;
7. repeated multi-day runner / scenario packs;
8. Monte Carlo orchestration;
9. adaptive fractal refinement;
10. empirical calibration.

## 19. Recommended next milestone

Recommended v0.10:

> **memory and bounded recovery inside the atomic day transaction.**

Start only with variables whose semantics naturally relax toward their baseline:

- `communal_fear`;
- `public_order_stress`;
- selected infrastructure functionality.

Do not apply generic mean reversion to path-dependent variables such as:

- state fragmentation;
- organized armed actor capacity;
- displacement stocks;
- criminal territorial control.

Recovery proposals must pass through the same owner resolver and causal trace as event effects.

---

**v0.9 turns phase proposals into atomic, replayable state transitions without introducing de-escalation or tactical behavior.**
