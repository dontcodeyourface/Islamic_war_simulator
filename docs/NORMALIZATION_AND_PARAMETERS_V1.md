
# Normalization and Parameters v1

**Status:** canonical design / pre-code  
**Version:** 1.0  
**Date:** 2026-09-23  
**Depends on:** Snapshot v1, Engine Dynamics v1, EngineState v1  
**Implementation:** not started

## 1. Purpose

This contract defines how Snapshot v1 evidence becomes the 60 EngineState v1 latents and how the future engine handles normalization, missing data, priors, uncertainty, correlation, temporal memory, graph edges, phase thresholds, stochastic event hazards, bounded feedback, fractal refinement and calibration.

It deliberately separates engineering test parameters from any future empirically calibrated model.

## 2. Parameter profiles

### synthetic_smoke_v1

Purpose:

- CI;
- deterministic replay;
- bounded-feedback tests;
- module integration;
- trace validation;
- state-transition plumbing.

Its numerical values are artificial engineering parameters. They are not real-world probabilities or forecasts.

### calibrated_v1

Purpose:

- historical backtesting;
- comparative analysis;
- any future empirically grounded interpretation.

It is intentionally UNPOPULATED.

A calibrated run must fail closed if a required parameter is missing. There is no fallback from calibrated_v1 to synthetic_smoke_v1.

## 3. Authoritative files

Authoritative numeric parameters:

    config/engine/parameter_registry_v1.yaml

Normalization and rule registry:

    config/engine/normalization_parameters_v1.yaml

Every run manifest stores:

    parameter_set_id
    parameter_set_hash

Every material equation delta stores the equation ID and parameter IDs used.

# PART I — NORMALIZATION

## 4. Objectives

Snapshot v1 contains heterogeneous evidence:

- percentages;
- persons;
- money;
- tonnes;
- stock-days;
- categorical assessments;
- booleans;
- ordinal levels;
- sparse values.

A normalized value is not the original evidence. Both are preserved in trace.

## 5. Canonical transforms

### NORM_CLAMP_01_V1

    x' = min(1, max(0, x))

Only for values already dimensionless and semantically aligned.

### NORM_CLAMP_SIGNED_V1

For demographic momentum:

    -1 <= x <= +1

### NORM_RATIO_SAT_V1

    f(x) = x / (x + k)

Useful for load/capacity relationships such as reception pressure or displacement pressure.

The scale k is parameterized.

### NORM_LOGISTIC_V1

    f(x) = 1 / (1 + exp(-s * (x-m)))

Useful where a known middle region changes system behavior. Slope and midpoint are parameters.

### NORM_SIGNED_TANH_V1

Used for growth or decline measures centered on zero.

### NORM_LINEAR_ANCHOR_V1

    f(x) = (x-low) / (high-low)

then clamp.

Anchors are versioned parameters, never hidden constants.

### NORM_EVIDENCE_BLEND_V1

Multiple empirical contributors representing one latent are normalized and combined.

Evidence quality changes uncertainty, not political interpretation.

### NORM_GEOMEAN_V1

Used where one weak component should constrain effective capacity.

Example:

    effective military capacity
      = geometric mean of
        nominal capacity,
        readiness,
        logistics,
        training

This prevents nominal inventory from dominating when sustainment is weak.

### NORM_ORDINAL_V1

Categorical values may only be mapped through a versioned mapping table.

No ad hoc low=0.25 / medium=0.5 / high=0.75 code literals.

# PART II — EVIDENCE QUALITY AND UNCERTAINTY

## 6. Quality changes confidence, not the mean by default

Synthetic uncertainty multipliers:

    high       1.00
    medium     1.35
    low        1.80

Freshness multipliers:

    current    1.00
    recent     1.10
    aging      1.30
    stale      1.65
    structural 1.00

These are engineering values until calibrated.

A weak source should normally widen uncertainty. It should not silently drag a value toward 0.5.

## 7. Derived values

Derived quantities inherit uncertainty from contributors and a derivation penalty.

Long proxy chains must carry wider uncertainty than direct measurements.

## 8. Initialization confidence metadata

Every initialized latent should retain:

    empirical_fraction
    prior_fraction
    uncertainty_width
    freshness
    data_quality

Thus two equal runtime values can still have very different evidentiary confidence.

# PART III — MISSING DATA AND PRIORS

## 9. Silent neutral defaults are forbidden

Forbidden:

    if missing:
        value = 0.5

Allowed:

    missing evidence
      -> versioned prior
      -> documented distribution
      -> uncertainty_sampling RNG
      -> sampled value
      -> trace

## 10. calibrated_v1

No generic prior is automatically valid.

A prior must come from historical calibration, comparable evidence, formal elicitation or another documented basis.

Otherwise initialization fails.

## 11. synthetic_smoke_v1

The engineering profile contains broad priors for:

- resilient institutions;
- moderate capacity;
- low stress;
- moderate stress;
- signed near-zero demographic momentum.

They exist only to make the software testable before calibration.

# PART IV — CORRELATED UNCERTAINTY

## 12. Why correlation is required

Independent sampling can create absurd combinations.

Examples:

    state cohesion excellent
    administrative capacity collapsed
    salary continuity perfect
    judicial continuity collapsed

with no causal reason.

Therefore the uncertainty layer supports correlation groups.

## 13. Initial groups

GOV_INSTITUTIONAL_V1:

- government legitimacy;
- state cohesion;
- elite cohesion;
- administrative capacity;
- judicial continuity;
- fiscal capacity;
- salary continuity.

SECURITY_CAPACITY_V1:

- police capacity;
- intelligence;
- security-chain cohesion;
- command cohesion;
- constitutional loyalty.

RESOURCE_RESILIENCE_V1:

- energy;
- electricity;
- fuel distribution;
- food;
- water;
- logistics.

MILITARY_CAPACITY_V1:

- land;
- air;
- naval;
- ISR/EW;
- drone/C-UAS;
- logistics;
- industry;
- replenishment.

SOCIAL_STRESS_V1:

- polarization;
- communal fear;
- public-order stress;
- terrorism threat.

STATE_RESILIENCE_STRESS_INVERSE_V1:

Expected inverse relationship between resilience and stress variables.

EXTREMIST_FEEDBACK_V1:

Crisis-conditional relationship among violent-network pressures, communal fear and narrative strength. This is not a relationship between ordinary demographic identity and violence.

## 14. Future implementation

Preferred methods:

- Gaussian copula; or
- explicit multivariate distribution.

The method itself must be versioned.

# PART V — TIME AND MEMORY

## 15. Memory classes

Synthetic half-lives are stored under parameter MEM_HALF_LIVES_SYN_V1:

    immediate     2 days
    short         8 days
    medium       34 days
    structural  144 days
    long        610 days

They are engineering defaults inspired by multiscale/Fibonacci spacing, not empirical claims.

## 16. Exponential memory

A future EMA can use:

    M[t+1] = alpha*x[t] + (1-alpha)*M[t]

with alpha derived from the selected half-life.

This provides smooth decay and accumulation.

## 17. Multiple memories

A variable may use more than one memory.

Government legitimacy, for example, can react to recent events while remaining dominated by weeks or months of accumulated performance.

# PART VI — INITIALIZATION RULES

## 18. One stable rule ID per latent

All 60 latents have an init_rule_id.

Examples:

    DEM_MOMENTUM_INIT_V1
    POLICE_CAPACITY_INIT_V1
    ENERGY_RESILIENCE_INIT_V1
    MIL_LAND_INIT_V1
    AI_DEFENCE_INIT_V1

The full list is machine readable.

## 19. Demographic momentum

Potential contributors:

- population growth;
- natural increase;
- fertility;
- age structure;
- migration;
- switching where directly measured.

Religious-demographic evidence affects demographic cohorts. It does not directly initialize violent-network pressure.

## 20. Migration pressure

Conceptually:

    migration pressure =
      function of
        flow,
        population,
        labor absorption,
        housing,
        integration capacity

Absolute migrant population alone is insufficient.

## 21. Reception pressure

Conceptually:

    reception pressure =
      function of
        current demand,
        reception capacity,
        housing/service pressure

This allows two countries receiving the same inflow to experience very different pressure.

## 22. Institutional state

Examples:

    state cohesion =
      function of
        institutional cohesion,
        regional topology,
        security-force cohesion

    fiscal capacity =
      function of
        economic capacity,
        tax collection,
        reserves,
        borrowing access,
        fiscal space

Political-party identity is not an automatic contributor.

## 23. Security state

Police effective capacity should incorporate:

- personnel;
- frontline availability;
- territorial coverage;
- public-order capability;
- logistics.

Intelligence effectiveness combines relevant intelligence disciplines and fusion capacity.

Constitutional loyalty uses institutional evidence or a documented prior. Voting preferences are not a direct input.

## 24. Violent Islamist pressure

Allowed evidence includes:

- documented violent-network activity;
- terrorism posture;
- prison-network pressure;
- external violent-network support;
- recent relevant violent activity with decay.

Forbidden direct inputs:

    Muslim population share
    mosque count

Equivalent protections apply to violent ultranationalist and revolutionary pressure.

## 25. Organized armed actor capacity

This latent represents aggregate non-state ability to sustain organized political violence.

Possible contributors:

- material violent networks;
- organization;
- finance;
- high-level weapons access;
- territorial influence;
- external support.

Ordinary ideological populations are not contributors.

## 26. Energy resilience

Conceptually:

    energy resilience =
      function of
        strategic stocks,
        import dependency,
        domestic refining/production,
        electricity diversification,
        storage,
        external supply access

Geological petroleum reserves and operational fuel stocks remain distinct evidence.

## 27. Food and water

Food resilience can combine:

- domestic supply;
- import access;
- stocks;
- agricultural resilience.

Water resilience can combine:

- renewable resources;
- water stress;
- desalination;
- distribution resilience.

## 28. Military capacity

Land, air and naval effective capacity use limiting-factor aggregation where appropriate.

Example:

    land effective =
      geometric mean of
        nominal capability,
        readiness,
        training,
        logistics

No engagement-level combat model is introduced.

# PART VII — GRAPH NORMALIZATION

## 29. Typed channels

Canonical edge channels:

    geographic_proximity
    land_border
    trade_dependency
    energy_dependency
    migration_link
    diaspora_link
    alliance_link
    information_link
    criminal_network_link
    extremist_network_link

## 30. Geographic proximity

Synthetic engineering transform:

    edge = exp(-distance_km / lambda)

The synthetic lambda is stored in EDGE_GEO_SCALE_SYN_V1.

Land-border adjacency remains a separate channel.

## 31. Why distance is not enough

Capital-to-capital distance does not capture territorial adjacency such as borders and exclaves.

Therefore proximity and land-border status are separate inputs.

## 32. Diaspora link

A diaspora/family edge may affect:

- information;
- remittances;
- migration connectivity.

It never implies faction allegiance.

## 33. Extremist-network link

Requires evidence of violent-network connectivity.

Religious similarity is not sufficient.

## 34. Spillover

Canonical equation ID:

    GRAPH_SPILLOVER_V1

Conceptually:

    spillover(i -> j)
      = sum over channels of
        edge(channel)
        * source pressure(channel)
        * transmission(channel)

then apply:

- latency;
- saturation;
- target resilience;
- trace.

Synthetic transmission values are stored under GRAPH_TRANSMISSION_SYN_V1.

Synthetic latencies are stored under GRAPH_LATENCIES_SYN_V1.

# PART VIII — DYNAMIC UPDATE PARAMETERS

## 35. Generic bounded update

Canonical starter equation:

    GENERIC_BOUNDED_DELTA_V1

Concept:

    x[t+1] =
      clamp(
        x[t]
        + gain * positive pressure
        - loss * negative pressure
        + recovery * (baseline anchor - x[t])
      )

This exists for initial implementation and testing. Mature modules can later receive their own versioned equations.

## 36. Time-scale gains

Authoritative synthetic gains:

    DYNAMIC_GAINS_SYN_V1

Fast variables are allowed larger daily movement.

Structural and demographic variables move much less.

A maximum single-day delta protects against runaway behavior.

## 37. Recovery

Many variables should mean-revert when stress disappears.

Examples:

- communal fear;
- public-order stress;
- infrastructure functionality.

Other variables can have strong path dependence:

- institutional fracture;
- displacement;
- criminal territorial influence.

Variable-specific recovery can be introduced by new equation/parameter versions.

# PART IX — PHASE CLASSIFICATION

## 38. Philosophy

Phase thresholds classify simulated states. They are not scientific definitions of real conflicts.

Synthetic thresholds exist to test persistence, hysteresis and multi-variable requirements.

The calibrated profile remains empty.

## 39. STABLE to TENSION

Synthetic parameter:

    PHASE_STABLE_TENSION_SYN_V1

Sustained external pressure, polarization or public-order stress can enter TENSION.

## 40. TENSION to EMERGENCY

Synthetic parameter:

    PHASE_TENSION_EMERGENCY_SYN_V1

Requires combined public-order stress and weakened legitimacy.

## 41. MASS_UNREST

Synthetic classification requires:

- substantial public-order stress;
- high polarization;
- reduced social cohesion;
- persistence.

## 42. ORGANIZED_POLITICAL_VIOLENCE

Requires material organized armed actor capacity plus severe public-order stress.

A protest wave does not automatically become organized political violence.

## 43. INSURGENCY

Requires:

- stronger organized armed capacity;
- weakened security-chain cohesion;
- some territorial-control degradation;
- persistence.

## 44. DUAL_AUTHORITY

Requires:

- degraded territorial control;
- degraded center-region cohesion;
- degraded state cohesion;
- an explicit competing-authority node/event.

Continuous state alone cannot invent a rival authority.

## 45. CIVIL_WAR

Synthetic test parameter:

    PHASE_CIVIL_WAR_SYN_V1

Requires simultaneously:

- durable organized armed capacity;
- major security-chain deterioration;
- territorial-control deterioration;
- administrative deterioration;
- persistence.

No demographic threshold can directly trigger it.

## 46. STATE_FRAGMENTATION

Synthetic parameter:

    PHASE_FRAGMENTATION_SYN_V1

Requires still deeper simultaneous loss of territorial control, administration, state cohesion, command and payroll continuity.

## 47. De-escalation

Recovery uses hysteresis and longer persistence.

A country cannot flip phases daily because one input crossed a boundary briefly.

# PART X — SECURITY-FORCE REGIMES

## 48. Regime parameters

Synthetic classifier:

    SECURITY_REGIMES_SYN_V1

It combines:

- security-chain cohesion;
- command cohesion;
- constitutional loyalty;
- operational fatigue;
- center-region cohesion;
- explicit competing-authority nodes.

Political preference is not an input.

# PART XI — STOCHASTIC EVENTS

## 49. Hazard architecture

The event process has two stages.

Stage 1:

    hazard score =
      base
      + state terms
      + memory terms
      + graph terms
      + context

Then clamp 0..1.

Stage 2:

Convert the hazard score to an event probability using the active profile.

The calibrated conversion is not defined yet.

## 50. Synthetic conversion

Parameter:

    EVENT_HAZARD_PROBABILITY_SYN_V1

It exists only to generate occasional events in tests.

Every output using it must display:

    ENGINEERING TEST PROFILE
    NOT CALIBRATED
    NOT A REAL-WORLD PROBABILITY

## 51. Initial event families

Strategic event families:

- interstate incident;
- diplomatic crisis;
- mass-protest trigger;
- extremist-violence shock;
- infrastructure failure;
- prison disorder;
- government crisis;
- alliance consultation;
- displacement surge;
- market-confidence shock.

These remain abstract.

The model contains no target selection, attack method, weapon selection or tactical execution.

## 52. Conflict initiation

Default endogenous conflict initiation uses RANDOM_SHOCK or GENERATED events.

The first interstate incident can therefore occur early, late or never.

A scenario pack can still force a confrontation explicitly as SCENARIO_ASSUMPTION.

# PART XII — RECIPROCAL RADICALIZATION

## 53. Feedback equation

Equation ID:

    RECIPROCAL_RADICALIZATION_V1

Violent incidents can affect:

- communal fear;
- hostile narratives;
- opposing violent-network recruitment pressure.

Damping includes:

- social cohesion;
- legitimacy;
- policing/intelligence;
- community rejection;
- credible communication.

## 54. Forbidden shortcuts

The following direct edges are forbidden:

    Muslim share -> violent Islamist pressure
    Christian share -> violent ultranationalist pressure
    conservative vote -> violent ultranationalist pressure
    left vote -> revolutionary violent pressure

Violent-network variables require violent-network evidence or generated network dynamics.

# PART XIII — FRACTAL REFINEMENT

## 55. Refinement equation

Equation ID:

    REFINEMENT_TRIGGER_V1

Combines:

- violence;
- institutional stress;
- infrastructure stress;
- network activity;
- displacement.

Synthetic parameter set:

    FRACTAL_REFINEMENT_SYN_V1

## 56. Hysteresis

Expansion requires sustained high pressure.

Collapse requires sustained lower pressure for longer.

This avoids repeated opening and closing of nodes.

# PART XIV — EXECUTION ORDER

## 57. Operator-order contract

Version:

    EXEC_ORDER_V1

Daily order:

1. advance clock;
2. apply scheduled factual/scenario events;
3. update slow exogenous baselines;
4. compute domestic pressures;
5. compute graph spillovers;
6. evaluate strategic-agent actions;
7. evaluate random/generated events;
8. apply event effects;
9. resolve owner-module updates;
10. apply constraints/conservation;
11. evaluate regimes/phases;
12. evaluate fractal refinement;
13. persist trace ledgers;
14. checkpoint.

Nonlinear systems are order-sensitive. A change requires a new execution-order version.

# PART XV — PARAMETER TRACEABILITY

## 58. No hidden behavioral constants

Every material:

- weight;
- threshold;
- delay;
- half-life;
- gain;
- saturation constant;
- probability conversion;

must belong to a parameter ID.

The code may contain purely numerical implementation constants such as floating-point epsilon only when they do not materially determine modeled behavior.

## 59. Parameter hashes

Every run stores:

    parameter_set_id
    parameter_set_hash

Changing one threshold therefore changes the experimental configuration.

## 60. Transition trace

A phase transition trace should contain:

    transition rule ID
    threshold parameter ID
    persistence achieved
    input state values
    supporting event IDs
    supporting trace IDs

# PART XVI — CALIBRATION ROADMAP

## 61. Stage A: normalization calibration

Determine meaningful mappings from raw units into latent states.

## 62. Stage B: dynamic-rate calibration

Estimate:

- decay;
- recovery;
- lag;
- feedback strengths.

## 63. Stage C: event-history calibration

Estimate hazard relationships.

## 64. Stage D: phase validation

Test whether phase classifiers correspond reasonably to historical transitions.

## 65. Stage E: graph-contagion validation

Test transmission through:

- borders;
- economies;
- migration;
- information;
- alliances;
- violent-network links.

## 66. Multiple historical cases

Calibration must include both escalating and non-escalating crises.

It should span different regions and conflict types.

Calibrating only to the scenario the model is intended to simulate would simply teach the model the desired story.

## 67. Holdout cases

Some cases remain unseen during fitting and are evaluated afterward.

## 68. False-positive collapse

A critical metric is how often the model creates severe instability where historical systems remained stable.

A model that predicts collapse constantly is not useful.

## 69. Sensitivity and identifiability

If many parameter combinations produce nearly identical outcomes, the parameter is not well identified.

That uncertainty must be reported.

## 70. Calibration uncertainty

A calibrated profile should retain parameter distributions or intervals, not only point estimates.

Monte Carlo can then distinguish:

- empirical uncertainty;
- parameter uncertainty;
- event randomness;
- agent-choice randomness.

# PART XVII — REPORTING

## 71. Synthetic runs

Every synthetic run must state clearly that it is uncalibrated engineering output.

Run frequency is not real-world probability.

## 72. Calibrated runs

Even after calibration, results remain conditional on:

- model structure;
- snapshot;
- parameter posterior;
- scenario assumptions.

They should be reported as model frequencies, not certain predictions.

# PART XVIII — IMPLEMENTATION GATE

## 73. Contracts now closed

The architecture is now:

    Snapshot v1
      -> EngineState v1
      -> Normalization and Parameters v1
      -> Engine Dynamics v1

Structurally closed:

- variable identities;
- source sections;
- initialization rule IDs;
- normalization families;
- missing-data policy;
- synthetic priors;
- correlation groups;
- memory classes;
- graph channels;
- spillover architecture;
- phase parameter sets;
- security regime parameters;
- stochastic hazard architecture;
- random/generated conflict initiation;
- bounded dynamic gain classes;
- reciprocal-radicalization safeguards;
- fractal refinement;
- execution order;
- parameter traceability;
- calibration gate.

## 74. Remaining scientific work

Empirical calibration remains unfinished by design.

The software can now be implemented against synthetic_smoke_v1 without improvising behavioral constants inside source code.

## 75. Recommended next step

Implement the minimal engine infrastructure first:

1. config/registry loader;
2. Snapshot validator;
3. EngineState initializer;
4. deterministic RNG manager;
5. immutable run manifest;
6. state store;
7. trace ledgers;
8. replay verifier;
9. no-op daily engine loop;
10. synthetic smoke initialization.

Only after those foundations pass replay and trace tests should coupled behavioral equations be enabled.

---

**End of Normalization and Parameters v1.**
