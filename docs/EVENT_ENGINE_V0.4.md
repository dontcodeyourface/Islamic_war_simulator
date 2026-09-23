# Event Engine v0.4 — Dry-Run Generation and Trace

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Package version:** 0.4.0  
**Event effects:** disabled  
**Phase transitions:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.4 introduces the first executable strategic event generator on top of the canonical typed-country graph.

It proves four properties before any event is allowed to mutate EngineState:

- endogenous `GENERATED` events;
- stochastic `RANDOM_SHOCK` events;
- deterministic replay;
- complete event/hazard/RNG traceability.

The event engine is deliberately read-only with respect to EngineState.

## 2. Executable event families

The initial executable families are:

- `INTERSTATE_INCIDENT_V1`;
- `MASS_PROTEST_TRIGGER_V1`.

Other event families remain design-only until added explicitly.

## 3. Occurrence paths

Every candidate receives a bounded hazard score.

### GENERATED

If:

```text
hazard_score >= generated_threshold
```

the event occurs deterministically as:

```text
provenance_class = GENERATED
```

No event RNG draw is consumed.

### RANDOM_SHOCK

If hazard remains below the generated threshold, the synthetic profile computes:

```text
p_day = p_floor + score_scale * hazard_score
```

and compares it with an event-specific deterministic random draw.

If:

```text
draw < p_day
```

the event occurs as:

```text
provenance_class = RANDOM_SHOCK
```

The synthetic probability conversion is an engineering test mechanism only. It is not a real-world probability model.

## 4. Interstate incident hazard

The strategic interstate candidate uses only:

- mean external-conflict pressure of the two states;
- geographic proximity from the canonical typed graph;
- direct land-border status;
- shared formal-alliance connectivity as a deterrence term.

Conceptually:

```text
score =
base
+ w1 * external_conflict_pressure_mean
+ w2 * geographic_proximity
+ w3 * land_border
- w4 * alliance_deterrence
```

All coefficients live in `EVENT_HAZARD_WEIGHTS_SYN_V1`.

No target, weapon, route, tactical movement or engagement model exists.

## 5. Mass protest hazard

The domestic candidate uses:

- polarization;
- inflation pressure;
- unemployment pressure;
- inverse government legitimacy;
- social cohesion as a damping term.

Again, all coefficients are synthetic engineering values.

## 6. Event object

A created event stores:

```yaml
event_id:
event_type:
provenance_class:
day_created:
day_effective:
duration_days:
actors:
source_nodes:
target_nodes:
hazard_score:
occurrence_probability:
random_draw:
generated_threshold:
feature_values:
parameter_ids:
parent_event_ids:
causal_trace_id:
scenario_id:
run_id:
rng_stream:
dry_run:
```

## 7. Deterministic identity

The event ID is derived from:

- replay key;
- day;
- event family;
- sorted actor IDs.

Identical replay conditions therefore produce the same event identity.

`run_id` remains unique per execution.

## 8. RNG namespacing

Event streams use:

```text
events:<event_type>:<sorted_actor_ids>
```

Example:

```text
events:INTERSTATE_INCIDENT_V1:ESP--MAR
```

Adding a different event family cannot shift that stream.

Initialization priors are also namespaced:

```text
uncertainty_sampling:<ISO3>
```

so adding/reordering countries does not change another country's prior realization.

## 9. Trace records

A stochastic candidate records:

- RNG stream;
- draw index;
- random draw;
- occurrence probability.

Every candidate records:

- event type;
- actors;
- hazard;
- generated threshold;
- probability;
- feature values;
- parameter IDs;
- occurrence result;
- provenance.

Created events emit the full event object.

## 10. State immutability

Event evaluation in v0.4 does not change EngineState.

Tests compare state hashes before and after event evaluation.

This isolates event-generation correctness from future effect equations.

## 11. Default conflict-start behavior

The architecture can now represent:

```text
baseline
  -> RANDOM_SHOCK interstate incident
```

or:

```text
baseline
  -> accumulated pressure
  -> GENERATED interstate incident
```

or:

```text
baseline
  -> no incident
```

Conflict initiation therefore remains emergent rather than hard-coded.

## 12. Parameter discipline

The authoritative parameter registry adds:

- `EVENT_HAZARD_WEIGHTS_SYN_V1`;
- `EVENT_HAZARD_WEIGHTS_CAL_V1 = null`.

The existing probability-conversion parameter remains:

- `EVENT_HAZARD_PROBABILITY_SYN_V1`.

`calibrated_v1` continues to fail closed.

## 13. Safety abstraction

Executable events explicitly exclude:

- target selection;
- weapon selection;
- attack method;
- tactical route planning;
- operational execution.

They are strategic event abstractions only.

## 14. Validation

v0.4 tests:

- deterministic GENERATED interstate path;
- no RNG consumption on GENERATED path;
- RANDOM_SHOCK path with recorded RNG;
- no-event path;
- GENERATED mass-protest path;
- exact event replay;
- event-state immutability;
- unrelated event-family RNG isolation;
- country prior-stream order independence;
- calibrated-profile fail-closed behavior.

## 15. Disabled in v0.4

Not yet implemented:

- event effects;
- event scheduler over all nodes/pairs;
- parent-child event chains;
- graph spillover deltas;
- phase transitions;
- alliance reaction events;
- resource depletion;
- extremist feedback;
- fractal refinement.

## 16. Next milestone

v0.5 should introduce **event effect proposals**, not direct state mutation.

An event should be able to emit proposed changes containing:

```text
source event
target node
target latent
raw delta
equation ID
parameter IDs
duration/decay
```

Those proposals must remain uncommitted until the owner-module resolver validates them.

This preserves the core architecture:

```text
event generation
  -> proposed deltas
  -> owner resolution
  -> bounded commit
```

before phase logic observes the new state.

---

**Event Engine v0.4 creates and explains events; it does not yet change the simulated world.**
