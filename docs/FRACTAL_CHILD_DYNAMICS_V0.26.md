# Fractal Autonomous L2 Dynamics v0.26

**Status:** implementation milestone  
**Version:** 0.26.0  
**Date:** 2026-09-25  
**Depends on:** v0.25 active multiscale runtime authority

## Purpose

v0.26 turns beginning-of-day active L2 children into real autonomous runtime states for the first safe subset of endogenous dynamics.

The canonical authority rule remains:

> resolution follows stress, and dynamic authority follows active resolution.

When an L1 parent is refined, regionalizable dynamics no longer execute on that L1 parent. They execute on its active L2 children.

## Enabled autonomous L2 modules

v0.26 executes the following generic modules directly against active child EngineState objects:

- bounded endogenous recovery;
- extremist-network dynamics;
- reciprocal-radicalization dynamics;
- security-chain dynamics;
- Owner Resolver aggregation/clamping.

The implementation reuses the existing country-independent equations. No country- or region-specific Python dynamics are introduced.

## Clock semantics

Child dynamics resolve from the beginning-of-day child state while the child remains on the beginning-of-day clock.

The existing child-state lifecycle then advances each child exactly once to the committed day.

This ordering prevents double clock advancement:

```text
child state day t
-> autonomous L2 proposals
-> L2 owner resolution
-> resolved child still labelled day t
-> existing child lifecycle advances once
-> committed child day t+1
```

## L1 suppression

A refined L1 parent has relinquished regionalizable authority.

Therefore v0.26 excludes refined parents from:

- recovery proposals;
- extremist-network proposals;
- reciprocal-radicalization proposals;
- security-chain proposals;
- country/edge event candidate passes that would apply regionalizable L1 effects.

Unrefined L1 nodes continue to execute normally.

This is the first executable enforcement of the no-double-counting rule.

## Proposal authority

Every L2 proposal is validated against the v0.25 authority plan.

A child proposal must:

- target an active L2 runtime node;
- target a latent classified as regionalizable;
- never mutate a national-only latent.

Any violation fails closed before resolution.

## Runtime metadata

After successful child resolution, each active child records:

- child dynamics active = true;
- runtime authority policy ID;
- runtime-plan hash;
- dynamics applied from day;
- dynamics applied to day.

The complete child-dynamics commit is written to causal trace with:

- executed node IDs;
- enabled modules;
- proposal IDs;
- resolution IDs;
- child-store hash before;
- child-store hash after.

## Deferred multiscale modules

v0.26 intentionally does not claim support for mechanisms whose multiscale semantics are not yet defined.

With active beginning-of-day L2, the day transaction fails closed if asked to execute:

- graph spillover — deferred to v0.29/v0.30;
- security-regime evaluation/recovery — deferred to v0.28;
- national/regional phase transitions — deferred to v0.28;
- collapse/refinement evaluation requiring parent-child coupling — deferred until the coupling path is implemented.

Regional event/spillover execution remains a later milestone. v0.26 suppresses legacy L1 event candidates for refined parents rather than pretending the L1 aggregate still owns regional event dynamics.

## Atomicity

L2 dynamics execute inside the staged day transaction.

Their proposals, owner resolutions and child-state mutations are written only to the staged trace/store. A later transaction failure therefore prevents the resolved child store from becoming committed output.

RNG behavior remains unchanged for the v0.26 safe modules because these endogenous equations do not introduce a new child-specific random stream.

## Relationship to child initialization

v0.21 child initialization still supplies the initial regional state.

v0.22 uncertainty widening still supplies one-time synthetic local heterogeneity.

v0.26 begins deterministic state evolution from that initialized/perturbed child state on subsequent days.

The child store remains the authoritative state container for active L2 runtime nodes.

## Validation requirements

v0.26 tests must demonstrate:

- active L2 runtime is accepted by the v0.25 planner;
- autonomous child recovery changes child state without advancing the clock twice;
- all safe modules target active children only;
- national-only child mutation fails closed;
- proposal resolution is deterministic;
- child metadata records active dynamics;
- inactive historical lineage remains outside the child store;
- refined parents do not receive duplicate safe regionalizable dynamics.

## Not implemented

Still deferred:

- L2 security/phase regime divergence;
- multiscale graph projection;
- regional event generation;
- regional graph spillover;
- parent-child aggregate feedback;
- dynamic categorical reaggregation;
- L3/L4/L5 recursion.

## Next milestone

v0.27 hardens the multiscale Owner Resolver and atomic transaction identity around mixed L1/L2 execution, including explicit scale-aware proposal/resolution provenance and rollback tests.

---

No tactical targeting, route planning, weapon selection or operational execution is introduced.
