# Fractal Child State Initialization v0.21

**Status:** implementation milestone  
**Version:** 0.21.0  
**Date:** 2026-09-23  
**Child dynamics:** disabled  
**Random regional variation:** disabled

## Purpose

v0.21 initializes EngineState objects for L2 nodes created by v0.20.

The objective is not to make the regional children dynamic yet. The objective is to establish a conservation-safe, deterministic and fully traceable initial state.

## Physical-stock classification

v0.21 does not apply `weight * value` to every field.

### Additive integer conserved

These regionalizable person-count stocks are distributed across all children and must sum exactly back to the parent:

- total population;
- working-age population;
- dependent population;
- displaced people;
- reception population;
- available police personnel;
- prison population.

Allocation uses deterministic largest remainder:

1. compute `parent_total * child_weight`;
2. floor each child allocation;
3. distribute remaining units by descending fractional remainder;
4. break ties by child node ID.

This guarantees exact integer conservation.

### Intensive inherited

These are not additive quantities:

- fuel-stock days equivalent;
- strategic-food-stock days.

Every child inherits the parent value unchanged.

### Parent-only / not spatialized in v0.21

These remain `null` in child state until an explicit regional allocation rule exists:

- available military personnel;
- foreign reserves USD;
- gold reserves tonnes.

This avoids inventing spatial deployment of national military forces or central monetary assets.

## Latents

All normalized latents inherit the parent value exactly.

No child receives random or deterministic regional perturbation in v0.21.

That is intentionally reserved for v0.22 uncertainty widening.

## Regimes

All child regimes inherit the parent regime exactly at initialization.

## Metadata and lineage

Child metadata copies parent metadata and adds:

- fractal level;
- parent node ID;
- regional label;
- creation day;
- refinement action ID;
- refinement reason;
- initialization weight;
- catalog source ID;
- initialization-weight policy;
- inherited-uncertainty policy;
- aggregation rule;
- parent state hash at initialization;
- latent/regime/metadata policy IDs;
- child dynamics active=false.

## Conservation audit

Every newly initialized parent emits a conservation audit comparing each additive parent value with the exact sum across children.

Any mismatch aborts the transaction.

## Child-state store

L2 EngineState objects live in a separate `FractalChildStateStore`.

They are not inserted into:

- L1 `states`;
- L1 `CountryGraph`;
- event passes;
- spillover;
- Owner Resolver.

Existing child states advance their clock each day with values frozen while child dynamics remain disabled.

## Null handling

If an additive parent stock is legitimately unavailable/null, all children receive null and the conservation audit records null for both parent and child aggregate.

## Next PR

v0.22 adds finer-scale uncertainty widening/local variation while preserving the v0.21 conservation contract.

It must not change the additive stock totals.

No tactical or operational military functionality is introduced.


## Post-v0.24 architectural clarification

The `Child dynamics: disabled` status above is the deliberate scope of v0.21 only. It is not a permanent architecture decision.

After the topology lifecycle through v0.24 is complete, active L2 children are required to become autonomous runtime domains for regionalizable state. The parent remains authoritative for national-only state and as the aggregate/cross-scale coordinator.

The canonical follow-up contract is [FRACTAL_AUTONOMOUS_REGIONAL_RUNTIME.md](FRACTAL_AUTONOMOUS_REGIONAL_RUNTIME.md).

In particular, the current exclusion of child states from event passes, spillover and Owner Resolver is an intermediate staging constraint that the v0.25+ sequence must remove safely while preserving atomicity and preventing duplicate L1/L2 execution.
