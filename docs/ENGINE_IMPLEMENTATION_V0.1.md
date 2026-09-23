# Engine Infrastructure v0.1

**Status:** implementation skeleton  
**Behavioral dynamics:** disabled  
**Parameter profile:** synthetic_smoke_v1 only

## Purpose

This milestone proves the infrastructure required before implementing behavioral equations.

It is intentionally incapable of producing a conflict, phase transition, graph spillover or strategic decision.

## Implemented

- deterministic YAML loading;
- canonical hashing;
- EngineState validation against the 60-latent registry;
- physical-stock extraction from country snapshots;
- independent deterministic RNG streams;
- synthetic-prior initialization;
- immutable run manifest and replay key;
- initialization ledger;
- daily checkpoint ledger;
- infrastructure-only no-op engine;
- CLI output artifacts;
- replay tests.

## Current initialization limitation

The current initializer extracts physical stocks from Snapshot v1, including population and other available fields.

The **60 normalized latents are not yet empirically normalized from Snapshot v1**.

They are sampled from the explicit synthetic_smoke_v1 priors solely to test:

- reproducibility;
- state validation;
- RNG isolation;
- manifest hashing;
- trace generation;
- country-independent plumbing.

Therefore the state metadata explicitly reports:

    empirical_fraction: 0.0
    prior_fraction: 1.0
    initialization_profile: synthetic_smoke_v1

This is temporary.

The next implementation milestone should replace synthetic-prior initialization, latent by latent, with versioned normalization rules while preserving prior fallback only where Snapshot evidence is missing.

## Smoke command

Example:

    pip install -e ".[dev]"

    iwsim smoke       --repo-root .       --country config/countries/spain.yaml       --seed 42       --days 30       --git-commit "$(git rev-parse HEAD)"       --out run_output/spain

The same command can use Morocco or any future Snapshot-v1 country without country-specific engine code.

## Output artifacts

The smoke CLI writes:

- manifest.json
- initial_state.json
- final_state.json
- replay_summary.json
- trace.jsonl

## Replay contract

With identical:

- country snapshot;
- engine registries;
- parameter set;
- scenario payload;
- code commit;
- master seed;
- horizon;

the initialized state and no-op state-hash sequence must be identical.

## RNG streams

Streams are derived independently from the master seed using SHA-256.

A call to demographic_sampling must not alter the next value from events.

This property is tested.

## CI status

The repository contains the engine-smoke GitHub Actions workflow for Python 3.11 and 3.12.

If GitHub Actions does not execute for a stacked PR, the absence of a workflow run must be reported as **CI not observed**, never as a passing result.

## Explicitly absent

v0.1 does not implement:

- RANDOM_SHOCK evaluation;
- GENERATED events;
- graph contagion;
- state dynamics;
- phase classification;
- reciprocal radicalization;
- alliance behavior;
- military attrition;
- resource depletion;
- fractal refinement;
- calibrated initialization.

## Next implementation milestone

Implement the Snapshot v1 -> EngineState normalization pipeline:

1. datum extraction with source IDs;
2. normalization-rule dispatch;
3. empirical/prior blending;
4. confidence metadata;
5. correlated uncertainty;
6. initialization contribution trace;
7. deterministic validation for Spain and Morocco.

Only after empirical initialization works should daily behavioral equations be enabled.

---

**Engine Infrastructure v0.1 is plumbing, not a conflict model.**
