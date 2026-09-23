# Event Engine v0.4 — Dry-Run Generation and Trace

**Status:** implementation milestone  
**Date:** 2026-09-23  
**Event effects:** disabled  
**Phase transitions:** disabled  
**Active parameter profile:** `synthetic_smoke_v1`

## 1. Purpose

v0.4 implements the first executable strategic event generator.

It exists to prove:

- endogenous event generation;
- stochastic RANDOM_SHOCK generation;
- deterministic replay;
- independent RNG streams;
- event ancestry/causal identifiers;
- full hazard traceability.

It deliberately does **not** change EngineState yet.

## 2. Supported event families

The first executable families are:

- `INTERSTATE_INCIDENT_V1`
- `MASS_PROTEST_TRIGGER_V1`

Other event families remain declared in the design contract but are not executable yet.

## 3. Occurrence paths

Every supported event candidate computes a bounded hazard score.

Two occurrence paths are possible.

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

If the hazard is below the generated threshold:

```text
p_day =
p_floor
+ score_scale * hazard_score
```

under the synthetic profile.

A deterministic pseudo-random draw from the event-specific stream is then evaluated.

If:

```text
draw < p_day
```

the event occurs as:

```text
provenance_class = RANDOM_SHOCK
```

The synthetic probability conversion is an engineering test mechanism only.

It is not a real-world probability model.

## 4. Interstate incident features

The v0.4 strategic interstate-incident hazard uses only:

- mean external-conflict pressure of the two states;
- geographic proximity;
- direct-land-border status;
- alliance/security-link deterrence.

No tactical military variables are used.

No attack method, target, route or weapon is represented.

## 5. Synthetic interstate hazard

Current smoke-test hazard:

```text
score =
base
+ w1 * external_conflict_pressure_mean
+ w2 * geographic_proximity
+ w3 * land_border
- w4 * alliance_deterrence
```

Weights live in:

`EVENT_HAZARD_WEIGHTS_SYN_V1`

The generated threshold is deliberately reachable in tests.

This does not mean the threshold is empirically calibrated.

## 6. Mass-protest trigger features

The first domestic event family uses:

- polarization;
- inflation pressure;
- unemployment pressure;
- inverse government legitimacy;
- social cohesion as a damping term.

Again, the coefficients are engineering values only.

## 7. Event object

Every created event stores:

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

## 8. Deterministic event identity

The event ID is derived from:

- replay key;
- day;
- event family;
- sorted actors.

Therefore identical replay conditions produce the same event ID.

A different run can still have a different `run_id`.

## 9. RNG namespacing

Event RNG streams use:

```text
events:<event_type>:<sorted_actor_ids>
```

Example:

```text
events:INTERSTATE_INCIDENT_V1:ESP--MAR
```

This means adding another event family does not shift the Spain-Morocco incident stream.

## 10. Country-prior RNG namespacing

v0.4 also hardens initialization RNG.

Priors now use:

```text
uncertainty_sampling:<ISO3>
```

Examples:

```text
uncertainty_sampling:ESP
uncertainty_sampling:MAR
```

Therefore adding or reordering countries does not alter another country's prior draws.

## 11. Trace records

A RANDOM_SHOCK candidate emits an RNG trace containing:

```yaml
rng_stream:
draw_index:
random_draw:
occurrence_probability:
```

Every evaluated candidate emits:

```yaml
event_type:
actors:
hazard_score:
generated_threshold:
occurrence_probability:
random_draw:
occurred:
provenance_class:
feature_values:
parameter_ids:
dry_run:
```

Every created event emits its full event object.

## 12. State immutability

Event evaluation in v0.4 is read-only.

The tests explicitly compare EngineState hashes before and after evaluation.

An event can be created in trace while:

```text
state_before == state_after
```

This separation is intentional.

## 13. Why dry-run first

Mixing generation and effects immediately would make it difficult to tell whether a bad result comes from:

- hazard scoring;
- RNG behavior;
- event identity;
- effect equations;
- phase transitions.

v0.4 isolates event creation first.

## 14. Supported conflict start behavior

The default engine architecture can now represent:

```text
baseline
  ↓
low hazard
  ↓
RANDOM_SHOCK interstate incident
```

or:

```text
baseline
  ↓
accumulated external pressure
  ↓
GENERATED interstate incident
```

or:

```text
baseline
  ↓
no event
```

This satisfies the design requirement that conflict initiation is not hard-coded.

## 15. Safety abstraction

The executable event contract explicitly excludes:

- target selection;
- weapon selection;
- attack method;
- tactical route planning;
- operational execution.

Events are strategic state-transition candidates only.

## 16. Tests

v0.4 validates:

- GENERATED interstate path;
- GENERATED path consumes no event RNG;
- RANDOM_SHOCK path records RNG draw;
- no-event path is possible;
- GENERATED mass protest path;
- identical seed replays event candidates exactly;
- event evaluation does not mutate EngineState;
- country-prior streams are independent of country load order;
- unrelated event families do not shift one another's RNG streams.

## 17. What remains disabled

v0.4 does not yet implement:

- event effects;
- daily multi-node event scheduling;
- event ancestry beyond root events;
- graph spillover effects;
- alliance reaction events;
- diplomatic-crisis chaining;
- phase transitions;
- resource depletion;
- extremist feedback;
- fractal refinement.

## 18. Next milestone

The recommended v0.5 milestone is:

> implement an event scheduler + effect proposal layer where events produce **proposed deltas** rather than directly mutating state.

The proposed-delta layer should preserve:

- event source;
- target variable;
- raw delta;
- equation ID;
- parameter IDs;
- saturation/constraint path.

Only after proposals are traceable should owner modules commit those deltas to EngineState.

---

**Event Engine v0.4 proves event causality and replay without yet changing the simulated world.**
