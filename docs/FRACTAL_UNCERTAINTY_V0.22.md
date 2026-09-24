# Fractal L2 Uncertainty Widening v0.22

**Status:** implementation milestone  
**Version:** 0.22.0  
**Date:** 2026-09-24  
**Child dynamics:** disabled  
**Calibration:** synthetic smoke only

## Purpose

v0.22 introduces one-time local heterogeneity when an L1 country is expanded into newly initialized L2 regional children.

The objective is to implement the architecture rule that uncertainty widens as resolution becomes finer without pretending that synthetic regional differences are observed local facts.

## Ordering

The daily transaction orders the fractal path as:

```text
refinement evaluation
-> L2 topology materialization
-> v0.21 conservation-safe child initialization
-> v0.22 local latent uncertainty widening
-> checkpoint
```

Variation is applied only to children created in the current transaction. Existing L2 states are not resampled on later days.

## Conservation

v0.22 never modifies physical stocks, regimes, the L1 parent state, CountryGraph topology, or child-dynamics activation.

For every varied latent, sibling offsets are centered by the same child initialization weights used by v0.21. The resulting weighted L2 mean must reproduce the parent latent within the configured numeric tolerance.

This prevents finer resolution from creating artificial national drift.

## Bounds and correlation

Each latent's requested synthetic variation width comes from the authoritative parameter registry. The realized amplitude is reduced, when necessary, so every child remains inside the canonical EngineState bounds. Values are never clipped as a substitute for conservation.

Variation is group-correlated rather than independently sampled for every latent. A single regional draw drives each configured group, with explicit `same` or `inverse` orientation.

Variables not listed in a group continue to inherit the parent exactly. The synthetic widths are engineering-only values, not empirical regional estimates.

## RNG and replay

Each parent/group/day uses a dedicated deterministic stream:

```text
fractal_uncertainty:{parent}:{group}:{day}
```

Draw indices, normalized sibling offsets, realized amplitudes, config hash and parameter ID are traced. Because the day transaction operates on a cloned RNG and staged trace, a later failure rolls both back atomically.

## Calibration fail-closed

`calibrated_v1` has no v0.22 parameter values. A calibrated call therefore fails closed; it never falls back to `synthetic_smoke_v1`.

## Safety boundary

No religion, ethnicity, civilian identity or ordinary political affiliation is used as a direct local-variation input.

v0.22 adds no tactical target selection, route planning, weapon selection or operational execution.

## Next step

v0.23 should implement L2 -> L1 collapse/reaggregation with explicit conservative semantics, using the same topology lineage and weighted-mean contracts rather than discarding child state.
