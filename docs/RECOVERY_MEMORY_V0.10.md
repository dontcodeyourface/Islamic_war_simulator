# Recovery and Memory v0.10

**Status:** implementation milestone  
**Version:** 0.10.0  
**Date:** 2026-09-23  
**Active numeric profile:** `synthetic_smoke_v1`  
**Phase de-escalation:** disabled  
**Calibration:** none

## 1. Purpose

v0.10 introduces the first endogenous state relaxation mechanism.

Until v0.9, a stress variable changed only when an explicit event proposed another change. That meant a temporary shock could remain elevated indefinitely in the absence of new events.

v0.10 adds bounded recovery for a deliberately small set of variables whose semantics naturally relax toward their factual start-state baseline.

Recovery is not allowed to directly change national phase.

## 2. Canonical equation

Equation ID:

`RECOVERY_TO_BASELINE_V1`

For a variable with baseline `b`, current value `x`, and half-life `h` days:

```text
alpha = 1 - 2^(-1 / h)

delta = (b - x) * alpha
```

Therefore:

- if current > baseline, recovery delta is negative;
- if current < baseline, recovery delta is positive;
- if current == baseline, no proposal is emitted.

The equation approaches baseline exponentially without overshooting it by itself.

## 3. Baseline definition

Recovery does not use:

- 0.5;
- a global country-independent neutral value;
- a hard-coded political assumption.

Every initialized EngineState now stores:

```text
metadata.baseline_latents
metadata.baseline_latents_version = ENGINESTATE_T0_V1
```

`baseline_latents` is an immutable tuple representation of the exact initialized 60-latent state at `t0`.

This means recovery is relative to that country's own starting state in that run.

## 4. Baseline validation

When recovery is enabled:

- baseline metadata must exist;
- baseline version must match;
- baseline variable set must equal current EngineState latent set;
- duplicate baseline entries fail closed.

A missing or incompatible baseline invalidates the transaction.

## 5. Active variables

v0.10 enables recovery only for:

### Short-memory social/security stress

- `communal_fear`;
- `public_order_stress`.

### Infrastructure functionality

- `electricity_functionality`;
- `fuel_distribution_functionality`;
- `transport_logistics_functionality`;
- `telecom_internet_functionality`;
- `health_system_functionality`.

These variables can plausibly relax after a temporary shock when no new pressure sustains the deviation.

## 6. Memory classes

v0.10 reuses the already frozen parameter:

`MEM_HALF_LIVES_SYN_V1`

Current synthetic engineering values:

```text
immediate     2 days
short         8 days
medium       34 days
structural  144 days
long        610 days
```

Current recovery mapping:

```text
communal_fear                    -> short
public_order_stress              -> short
telecom_internet_functionality   -> short

electricity_functionality        -> medium
fuel_distribution_functionality -> medium
transport_logistics_functionality -> medium
health_system_functionality      -> medium
```

These half-lives are engineering test parameters, not empirically calibrated claims.

## 7. Variables deliberately excluded

Generic mean reversion is forbidden for path-dependent variables including:

- state cohesion;
- territorial control;
- regional fragmentation pressure;
- security-chain cohesion;
- command cohesion;
- constitutional loyalty;
- criminal-network power;
- violent Islamist pressure;
- violent ultranationalist pressure;
- revolutionary-extremist pressure;
- organized armed actor capacity;
- foreign support to non-state actors;
- displacement pressure;
- demographic momentum.

Those variables require dedicated dynamics and recovery conditions.

A civil conflict cannot disappear because a generic exponential decay function ran for enough days.

## 8. Proposal architecture

Recovery does not mutate EngineState directly.

It creates ordinary immutable `DeltaProposal` objects:

```text
ENDOGENOUS_RECOVERY_V1
  -> DeltaProposal
  -> Owner Resolver
  -> bounded committed delta
```

Each recovery proposal uses:

- canonical variable owner;
- beginning-of-day value;
- registered half-life parameter;
- deterministic proposal ID;
- deterministic source ID;
- `PROPOSED_NOT_APPLIED` status.

## 9. Same-day event composition

Recovery is computed from the beginning-of-day state, just like event-effect proposals.

Example:

```text
public_order_stress(t) = 0.50

mass protest proposal:
  +0.060

recovery proposal:
  -0.020

owner resolver:
  raw_sum_delta = +0.040

public_order_stress(t+1) = 0.54
```

The recovery proposal does not see the +0.060 event effect first.

The event proposal does not see recovery first.

Both observe the same synchronous state.

This preserves the v0.7 transaction semantics.

## 10. Daily execution order

With recovery and v0.9 phases enabled:

```text
1. validate state/graph/history
2. clone transactional RNG
3. evaluate event candidates
4. create event-effect proposals
5. create endogenous recovery proposals
6. aggregate all proposals through owner resolver once
7. advance clock
8. evaluate national phase
9. arbitrate mature phase proposals
10. commit phase and persistence
11. checkpoint
12. atomically commit RNG + trace
```

## 11. Transaction identity

When recovery is enabled, the canonical hash of `recovery_v1.yaml` is included in the transaction identity.

Thus two otherwise identical runs using different recovery mappings cannot share the same `transaction_id`.

## 12. No RNG

Recovery is deterministic.

It consumes no random stream.

Randomness can affect the state that recovery observes, but the recovery equation itself is deterministic.

## 13. Traceability

Every recovery proposal emits the ordinary:

`delta_proposal`

record and an additional:

`recovery_proposal`

record.

The recovery-specific record contains:

- proposal ID;
- deterministic recovery source ID;
- node/day;
- variable;
- baseline value;
- beginning-of-day value;
- memory class;
- half-life;
- daily alpha;
- raw delta;
- equation ID;
- parameter IDs;
- baseline version.

The end-of-day transaction record also stores:

- recovery proposal IDs;
- recovery config hash.

## 14. Atomic rollback

Recovery executes inside the staged transaction.

If recovery fails after the event engine has already consumed working RNG:

- caller RNG is not advanced;
- caller trace receives no staged records;
- input EngineStates remain unchanged.

This invariant is tested.

## 15. Calibrated profile

`MEM_HALF_LIVES_CAL_V1` remains null.

Therefore:

```text
profile = calibrated_v1
+ recovery enabled
-> fail closed
```

No synthetic half-life silently leaks into a calibrated run.

## 16. Phase interaction

Recovery can alter latents that later participate in phase evaluation.

However recovery does not:

- directly propose a phase;
- reverse a phase;
- bypass phase persistence;
- implement de-escalation.

The existing phase evaluator sees only the fully resolved end-of-day state.

A future de-escalation contract must define its own recovery thresholds and persistence.

## 17. Infrastructure recovery interpretation

A baseline functionality of `1.0` means:

> factual functionality at simulation start.

It does not mean globally perfect infrastructure.

If an event or future dynamic reduces a functionality variable below the t0 baseline, v0.10 permits gradual restoration toward that starting level.

It cannot recover above its own t0 baseline through this equation.

## 18. Validation

v0.10 tests require:

- t0 baseline contains exactly the initialized latent map;
- short-memory recovery uses the registered 8-day half-life;
- infrastructure recovery uses the registered 34-day half-life;
- recovery direction points toward baseline;
- excluded variables receive no generic recovery;
- event and recovery proposals share one beginning-of-day value;
- event + recovery aggregate in a single owner resolution;
- recovery config changes transaction identity;
- calibrated recovery fails closed;
- missing baseline fails closed;
- failure after event evaluation rolls back RNG, trace and state.

Existing v0.7-v0.9 tests remain active.

## 19. Machine-readable contract

Configuration:

`config/engine/recovery_v1.yaml`

Implementation:

`src/iwsim/recovery.py`

The config specifies:

- enabled variables;
- memory class;
- parameter mapping;
- forbidden generic-recovery variables;
- baseline version;
- transaction semantics;
- trace requirements.

## 20. Scope boundary

v0.10 still does not implement:

- graph spillover effects;
- reciprocal-radicalization state updates;
- extremist-network endogenous growth/decay;
- security-chain endogenous dynamics;
- alliance strategic decisions;
- economic/resource stock depletion;
- phase de-escalation;
- fractal refinement;
- calibrated probabilities.

## 21. Recommended next milestone

Recommended v0.11:

> **executable typed graph spillover proposals.**

Start with a small subset of channels whose semantics are already defined and traceable.

The spillover layer should:

1. operate on beginning-of-day source state;
2. use typed edge channels and registered transmission parameters;
3. generate owner-routed DeltaProposal objects;
4. apply channel-specific latency/memory explicitly;
5. preserve a `spillover_id` lineage record;
6. resolve together with events and recovery in the same owner pass;
7. remain bounded and synthetic-profile-only until calibrated.

Do not enable criminal/extremist-network contagion until the corresponding directional edge data are populated.

---

**v0.10 introduces bounded endogenous recovery without generic state healing, hidden constants or phase de-escalation.**
