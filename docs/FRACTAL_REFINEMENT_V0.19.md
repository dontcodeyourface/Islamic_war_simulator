# Fractal Refinement Evaluator v0.19

**Status:** implementation milestone  
**Version:** 0.19.0  
**Date:** 2026-09-23  
**Node materialization:** disabled

## Purpose

v0.19 implements the first executable piece of the adaptive fractal architecture.

The core rule remains:

> resolution follows stress.

The evaluator decides whether an L1 country has accumulated enough persistent stress to request L2 regional refinement, or whether an already-refined L2 representation has remained calm long enough to request collapse back to L1.

It does not create or delete nodes.

## Pressure equation

The canonical engine equation is:

```text
refinement_pressure =
    w_violence              * violence
  + w_institutional_stress  * institutional_stress
  + w_infrastructure_stress * infrastructure_stress
  + w_network_activity      * network_activity
  + w_displacement          * displacement
```

The five global weights and expand/collapse thresholds come from the existing versioned `FRACTAL_REFINEMENT_*` parameter family.

Each component is a documented mean over existing normalized EngineState latents.

No component weight or threshold is hidden in Python.

## v0.19 component mapping

### Violence

Mean of:

- public-order stress;
- terrorism threat pressure;
- organized armed-actor capacity.

### Institutional stress

Mean of:

- inverse government legitimacy;
- inverse state cohesion;
- inverse security-chain cohesion;
- regional fragmentation pressure.

### Infrastructure stress

Mean degradation of:

- electricity;
- fuel distribution;
- transport/logistics;
- telecom/internet;
- water resilience.

### Network activity

Mean of:

- organized-crime network power;
- violent Islamist network pressure;
- violent ultranationalist network pressure;
- revolutionary extremist pressure.

These are explicit network states, not civilian identity populations.

### Displacement

- displacement pressure.

## Hysteresis

The existing synthetic parameters define:

```text
expand when pressure >= 0.62 for 8 consecutive days
collapse when pressure <= 0.38 for 34 consecutive days
```

and enforce:

```text
T_collapse < T_expand
```

This prevents resolution flapping.

## Supported levels

v0.19 implements the first reversible boundary only:

```text
L1 COUNTRY <-> L2 REGION
```

Later PRs can extend the same contract to L2 -> L3, L3 -> L4 and L4 -> L5 without changing the pressure equation.

## Lineage-ready proposal

A matured action proposal records:

- parent node;
- action day;
- EXPAND or COLLAPSE;
- source/target levels;
- refinement pressure;
- dominant refinement reason;
- all component scores;
- source variables;
- initialization-weight policy ID;
- inherited-uncertainty policy ID;
- aggregation-rule ID.

The policy IDs are carried now so the materializer cannot invent lineage semantics later.

## Execution order

v0.19 is evaluated after committed national-phase transitions and before the daily checkpoint, matching the canonical engine order:

```text
state dynamics
-> graph/events
-> security regime
-> phase transitions
-> fractal refinement/de-refinement
-> trace/checkpoint
```

## Next fractal PRs

The documented implementation sequence is:

1. **v0.19** — read-only refinement/de-refinement evaluator;
2. **v0.20** — L1 -> L2 materialization and lineage records;
3. **v0.21** — conservation-aware parent-to-child initialization;
4. **v0.22** — uncertainty widening at finer scales;
5. **v0.23** — L2 -> L1 collapse/reaggregation conservation;
6. later — extension to L3/L4/L5 using the same interfaces.

Each step remains a separate PR.

## Scope boundary

Refinement is a computational-resolution decision, not a political or military outcome.

No tactical targeting, route planning, weapon selection or operational instruction is introduced.
