# Fractal Multiscale Owner Resolver v0.27

**Status:** implementation milestone  
**Version:** 0.27.0  
**Date:** 2026-09-25  
**Depends on:** v0.26 autonomous L2 dynamics

## Purpose

v0.27 hardens Owner Resolver identity and provenance for mixed L1/L2 execution.

The numeric aggregation and clamping semantics remain unchanged. The change is that a resolution executed under a multiscale runtime plan now records which runtime authority produced it and includes that authority context in resolution identity.

## Runtime provenance

When a runtime plan is present, every resolution records:

- runtime level;
- runtime parent node ID;
- runtime authority scope;
- runtime-plan hash;
- runtime policy ID.

For example, an active L2 resolution is explicitly attributable to:

```text
runtime_node       = ESP::R1
runtime_level      = L2_REGION
parent             = ESP
authority_scope    = REGIONALIZABLE
runtime_plan_hash  = ...
runtime_policy_id  = FRACTAL_RUNTIME_AUTHORITY_V1
```

An unrefined L1 resolution uses the corresponding L1 runtime authority record.

## Resolution identity

Runtime context participates in the deterministic `resolution_id` whenever a multiscale runtime plan exists.

Therefore, two otherwise identical resolutions executed under different scale-authority plans cannot silently share the same identity.

Legacy behavior is preserved when no runtime plan is supplied: the historical resolution-ID payload remains unchanged.

## Context construction

The v0.25 runtime plan is the sole source of resolver-scale provenance.

`build_runtime_resolver_context()` converts explicit runtime authority nodes into the resolver context for the exact state set being resolved.

Unknown runtime nodes fail closed.

The resolver itself also rejects:

- context entries for unknown state nodes;
- missing context for a target when explicit multiscale context was supplied;
- incomplete level/scope metadata.

## L1 and L2 binding

The day transaction now passes scale context to the ordinary L1 Owner Resolver whenever a fractal runtime plan exists.

The autonomous child executor passes L2 context to the same Owner Resolver.

This means both paths use identical aggregation/clamping code while retaining distinct runtime provenance.

## Atomic trace semantics

The autonomous L2 executor now stages its own proposal/resolution trace.

Only a successful child-dynamics commit extends the caller trace.

If proposal-authority validation or Owner Resolver execution fails:

- the input child store remains unchanged;
- partial child proposal/resolution trace is not published.

The outer day transaction remains the final atomic commit boundary for mixed L1/L2 state, RNG and trace.

## Validation

v0.27 adds tests for:

- explicit L2 provenance in ResolutionRecord and trace;
- scale context participating in resolution identity;
- fail-closed missing resolver context;
- L2 resolutions carrying parent/scope/plan/policy provenance;
- failed child resolution leaving both input state and caller trace unchanged;
- legacy deterministic behavior without a runtime plan.

## Non-goals

v0.27 does not add:

- L2 phase/security regime divergence;
- graph projection;
- regional events/spillovers;
- parent-child aggregate coupling;
- dynamic categorical reaggregation.

Those remain in v0.28+.

## Next milestone

v0.28 enables persistent L2 security-regime and phase divergence, with explicit categorical aggregation semantics required for eventual dynamic collapse.

---

No tactical targeting, route planning, weapon selection or operational execution is introduced.


## v0.27.1 lifecycle gating fix

The first v0.26/v0.27 integration retained a staging guard that blocked the
fractal refinement evaluator whenever beginning-of-day L2 authority existed.
Because the existing child lifecycle advances through the materialization
transaction path, this created a circular end-to-end gate on the second refined
day.

v0.27.1 resolves that contradiction without evaluating invalid L1 collapse
pressure:

- the refinement evaluator still runs for coarse L1 parents;
- already refined L1 parents are explicitly excluded while L2 owns regional
  state;
- excluded parent refinement persistence advances to the committed day with
  expand/collapse streaks reset to zero;
- a trace record states that evaluation was suppressed pending explicit
  parent-child coupling;
- materialization/topology retention and child-state advancement continue
  normally.

This permits consecutive autonomous L2 days while preventing stale L1 aggregate
state from generating collapse pressure before the coupling milestone.
