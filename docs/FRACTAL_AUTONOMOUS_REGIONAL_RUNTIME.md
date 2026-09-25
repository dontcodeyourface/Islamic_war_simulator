# Fractal Autonomous Regional Runtime

**Status:** canonical implementation roadmap  
**Version:** 1.0  
**Date:** 2026-09-25  
**Applies after:** fractal lifecycle v0.24

## 1. Architectural decision

The adaptive fractal model is not complete when lower-resolution topology merely exists.

When an L1 country is refined to L2, the active L2 regional children must become autonomous simulation domains for the state variables and dynamics that are spatially owned at regional scale.

The canonical rule is:

> resolution follows stress, and dynamic authority follows active resolution.

The current v0.19-v0.24 implementation establishes the first complete topology lifecycle:

1. persistent refinement/collapse evaluation;
2. explicit L1 -> L2 materialization;
3. conservation-safe child initialization;
4. one-time uncertainty widening;
5. conservative L2 -> L1 reaggregation;
6. immutable refine-collapse-refine lineage generations.

Those milestones deliberately keep child dynamics disabled. That is a staging constraint, not the final fractal architecture.

A production-capable fractal simulator therefore requires autonomous L2 runtime dynamics before the model can be considered architecturally complete.

## 2. Canonical runtime authority model

The engine must distinguish:

- **topology existence** — a node exists in fractal lineage;
- **runtime activity** — a node is currently active for dynamic execution;
- **state authority** — the resolution level that owns updates for a variable;
- **aggregate view** — a parent value derived from active lower-level children.

When a country remains coarse:

```text
L1 COUNTRY
  ACTIVE
  authoritative for spatializable country dynamics
```

When it is refined:

```text
                    L1 COUNTRY
          national-only authoritative state
                 +
         derived aggregate projection
                 |
        +--------+--------+
        |                 |
        v                 v
     L2 REGION         L2 REGION
       ACTIVE            ACTIVE
       autonomous        autonomous
       EngineState       EngineState
```

The engine must not execute the same spatialized causal mechanism independently at both L1 and L2 during the same day.

That would double-count:

- event effects;
- recovery;
- graph spillover;
- extremist-network growth;
- reciprocal radicalization;
- security-chain degradation/recovery;
- infrastructure degradation;
- displacement or other regionalizable stocks.

## 3. Variable ownership

Every EngineState field participating in multiscale execution must have an explicit scale policy.

Minimum policy classes:

### 3.1 Regionalizable additive stocks

Examples:

- population;
- working-age population;
- dependent population;
- displaced population;
- reception population;
- police personnel;
- prison population.

At active L2 resolution, children own these values and parent aggregates are reconstructed conservatively.

### 3.2 Regionalizable intensive variables

Examples:

- public-order stress;
- polarization;
- communal fear;
- police effective capacity;
- infrastructure functionality;
- extremist-network pressure;
- criminal-network pressure;
- displacement pressure.

At active L2 resolution, child values evolve autonomously. The L1 value is an explicit weighted aggregation/projection and must not independently receive the same regional causal delta.

### 3.3 National-only state

Examples include variables that are not spatialized by an implemented allocation contract, such as:

- central foreign reserves;
- national gold reserves;
- selected national military or alliance-control state;
- other explicitly central variables.

These remain authoritative at L1 until a later allocation contract exists.

No variable may silently switch scale semantics.

## 4. Active multiscale runtime set

The engine must construct an explicit active execution set for every simulation day.

For each L1 parent:

- if refinement level is `L1_COUNTRY`, the L1 node is active for regionalizable dynamics;
- if refinement level is `L2_REGION`, active L2 children replace the parent for regionalizable dynamics;
- the parent remains present for national-only state, lineage, aggregation and cross-scale coordination;
- inactive historical children never participate in dynamics.

The active runtime set must be deterministic, traceable and included in transaction identity.

Required trace fields include:

- runtime node ID;
- catalog node ID;
- lineage generation;
- active resolution level;
- parent node ID;
- authority policy ID;
- variables/modules owned at that level.

## 5. Autonomous L2 day dynamics

An active L2 child is not a frozen copy.

Subject to its scale policy, it must participate in the same generic country-independent dynamic machinery used by L1:

- endogenous recovery;
- strategic event hazards;
- event-effect proposals;
- owner resolution;
- extremist-network dynamics;
- reciprocal-radicalization feedback;
- security-chain dynamics;
- security-regime evaluation and transition;
- phase evaluation and transition where the phase model is valid at L2;
- graph spillover;
- causal trace and deterministic RNG.

No Spain-, France-, Morocco- or region-specific Python equation may be introduced.

Scale differences must be expressed through:

- topology;
- state;
- configuration;
- registered parameters;
- explicit aggregation/ownership policy;
- evidence and uncertainty.

## 6. Multiscale Owner Resolver

Owner resolution must support runtime node IDs below L1.

A material L2 delta must remain attributable to:

```text
runtime node
-> owner module
-> variable
-> equation ID
-> parameter IDs
-> source inputs
-> source event/spillover IDs
-> raw delta
-> bounded delta
-> value before
-> value after
```

Resolution must remain atomic with the day transaction.

A failure in any active node must roll back:

- all L1 updates;
- all L2 updates;
- topology changes;
- persistence state;
- RNG draws;
- trace records.

## 7. Regional phase and regime divergence

Sibling regions must be allowed to diverge when their local state diverges.

For example:

```text
ESP::R1 -> TENSION
ESP::R2 -> MASS_UNREST
```

or:

```text
ESP::R1 security_force_regime -> COHESIVE
ESP::R2 security_force_regime -> STRAINED
```

The engine must never force sibling equality merely to preserve easy reaggregation.

This requires explicit aggregation policies for categorical state before a dynamic L2 collapse can commit.

Until such a policy is implemented, divergent categorical state must fail closed on collapse.

## 8. Multiscale graph semantics

A refined region cannot be dynamically isolated.

The graph layer must distinguish:

- L1 strategic graph;
- internal L2 adjacency/connectivity;
- L2-to-external inherited or allocated connectivity;
- cross-border regional connectivity when explicitly evidenced;
- aggregation back to L1.

The engine must not clone 100% of every L1 edge onto every child.

For each graph channel, refinement needs an explicit projection rule, for example:

- geographic adjacency;
- land-border exposure;
- migration connectivity;
- trade dependency;
- energy dependency;
- information connectivity;
- extremist-network connectivity;
- criminal-network connectivity;
- alliance/institutional channels where scale-appropriate.

Unresolved projected channels remain null, not zero.

## 9. Regional event engine

Events must support lower-level source and target nodes.

Examples of valid strategic-level identities:

```text
source_node = ESP::R1
target_node = ESP::R2
```

or:

```text
source_node = ESP::R1
target_node = FRA
```

Event generation must retain:

- deterministic event identity;
- level-aware RNG streams;
- hazard provenance;
- source/target runtime lineage;
- parent-event relationships;
- scenario/run identity.

Lower resolution does not authorize tactical targeting, route planning, weapon selection or operational execution.

## 10. Parent-child coupling

Multiscale dynamics require explicit bidirectional coupling.

### Child -> parent

Regional evolution may modify national aggregates through:

- weighted aggregation;
- exact stock summation;
- explicitly defined regime/phase aggregation;
- national stress contributions;
- national resource demand where applicable.

### Parent -> child

National-only state may influence active children through explicit cross-scale inputs such as:

- alliance support;
- national fiscal capacity;
- central policy;
- national emergency regime;
- national resource constraints;
- strategic external-conflict pressure.

Cross-scale effects must have their own equation IDs or projection-policy IDs.

The same causal effect must never be applied once at L1 and again at L2 without an explicit decomposition rule.

## 11. Dynamic reaggregation

v0.23 reaggregation is conservation-safe for children that have not yet run autonomous dynamics.

Once L2 dynamics are enabled, collapse must handle evolved children.

Required semantics:

- exact conservation for additive stocks;
- explicit weighted aggregation for intensive variables;
- explicit handling of nulls;
- explicit categorical aggregation for regimes;
- parent-only variables remain authoritative at L1;
- all child lineage is closed immutably;
- active child states are removed only after successful parent reconstruction;
- collapse remains atomic.

A collapse must never discard unresolved regional divergence silently.

## 12. Repeated lifecycle

The canonical end-to-end fractal lifecycle becomes:

```text
L1 coarse dynamics
-> persistent refinement pressure
-> L2 materialization
-> conservation-safe initialization
-> uncertainty widening
-> autonomous L2 dynamics
-> L2 event/spillover interaction
-> parent-child aggregation/coupling
-> persistent collapse pressure
-> conservative dynamic reaggregation
-> immutable lineage closure
-> later stress recurrence
-> generation N+1 materialization
```

Generation identity from v0.24 remains mandatory.

## 13. Implementation sequence

The next implementation sequence is canonical unless superseded by a later architecture decision.

### v0.25 — active multiscale runtime set — IMPLEMENTED

Implemented by [FRACTAL_RUNTIME_V0.25.md](FRACTAL_RUNTIME_V0.25.md):

- deterministic active execution set;
- explicit state-authority policy with exact EngineState registry coverage;
- beginning-of-day versus committed-next-day runtime plans;
- prevention of silent legacy L1 execution once a day begins refined;
- runtime-plan trace and replay identity.

v0.25 originally failed closed when beginning-of-day L2 authority existed without autonomous execution. v0.26-v0.27 activate safe child dynamics and scale-aware resolution; v0.27.1 then removes the circular day-transaction gate by suppressing stale L1 refinement evaluation while active L2 owns regionalizable state.

### v0.26 — autonomous L2 day transaction — IMPLEMENTED

Enable generic lower-level execution for safe modules first:

- bounded recovery;
- event evaluation/effect proposals;
- owner resolution;
- extremist-network dynamics;
- reciprocal radicalization;
- security-chain dynamics.

Keep unsupported modules fail-closed.

Implementation detail: [FRACTAL_CHILD_DYNAMICS_V0.26.md](FRACTAL_CHILD_DYNAMICS_V0.26.md).

### v0.27 — multiscale Owner Resolver and transaction atomicity — IMPLEMENTED

Extend proposal and resolution identity to L2 and validate full transaction rollback across mixed L1/L2 state.

Implementation detail: [FRACTAL_MULTISCALE_RESOLVER_V0.27.md](FRACTAL_MULTISCALE_RESOLVER_V0.27.md).

### v0.28 — L2 security/phase divergence — IMPLEMENTED

Enable regional regime/phase persistence and transitions where their semantics are valid at L2.

Define the contract for categorical aggregation.

Implementation detail: [FRACTAL_REGIONAL_REGIMES_V0.28.md](FRACTAL_REGIONAL_REGIMES_V0.28.md).

### v0.29 — multiscale graph projection — IMPLEMENTED

Implement:

- internal L2 topology;
- projected external links;
- explicit channel-specific allocation rules;
- null preservation;
- deterministic graph identity.

Implementation detail: [FRACTAL_GRAPH_PROJECTION_V0.29.md](FRACTAL_GRAPH_PROJECTION_V0.29.md).

### v0.30 — regional event and spillover execution — IMPLEMENTED

Allow event generation and graph propagation between active runtime nodes at different scales.

### v0.31 — parent-child coupling — IMPLEMENTED

Implement explicit child-to-parent aggregation and parent-to-child national context propagation without double counting.

### v0.32 — dynamic L2 -> L1 reaggregation — IMPLEMENTED

Upgrade v0.23 collapse for independently evolved child states and divergent categorical state.

### v0.32 implementation note

The collapse path now accepts autonomous L2 child states carrying
`fractal_child_dynamics_active=true` and reconstructs L1 from the live child
state rather than from the initialization snapshot. Existing conservation
semantics remain authoritative: additive stocks are summed exactly, intensive
and latent values use their declared weighted aggregation policy, parent-only
state remains at L1, and categorical disagreement still fails closed.

The implementation deliberately does not weaken the categorical-consensus
guard. A refined country whose active regions still disagree on a categorical
regime is not collapse-ready; the regional divergence must first resolve under
the regional-regime contract.

### v0.33 — canonical end-to-end lifecycle validation

Provide multi-day tests covering:

```text
L1
-> refine
-> L2 divergence
-> regional interaction
-> recovery
-> collapse
-> later re-refine as generation 2
```

Requirements:

- exact deterministic replay;
- conservation;
- immutable historical lineage;
- no inactive-node dynamics;
- no double application of a causal effect;
- identical manifest + seeds -> identical run.

### v0.34a — recursive topology and lineage — IMPLEMENTED

The first recursive increment generalizes adjacent topology materialization from L1 -> L2 to L2 -> L3 while preserving the existing L1/L2 wrapper.

Implemented by [FRACTAL_RECURSIVE_TOPOLOGY_V0.34A.md](FRACTAL_RECURSIVE_TOPOLOGY_V0.34A.md):

- one canonical L0..L5 level order;
- adjacent-only refinement;
- stable catalog identity separated from runtime lineage identity;
- collision-safe descendants beneath generation-N parents;
- generation-N+1 child re-refinement;
- explicit deferral of L4/L5 activation.

### v0.34b — deepest-active recursive runtime authority — IMPLEMENTED

Implemented by [FRACTAL_RECURSIVE_RUNTIME_V0.34B.md](FRACTAL_RECURSIVE_RUNTIME_V0.34B.md).

When an L2 node has active L3 children, the L2 node remains materialized as parent/context state but delegated regionalizable execution moves to the deepest active L3 leaves. Recursive child-state initialization now derives L3 state from the live L2 parent and preserves additive conservation. Autonomous child execution processes only authority leaves and retains parent-context states unchanged.

### v0.34c1 — L3 projected graph — IMPLEMENTED

Implemented by [FRACTAL_L3_GRAPH_PROJECTION_V0.34C1.md](FRACTAL_L3_GRAPH_PROJECTION_V0.34C1.md).

The projected strategic graph now follows deepest-active authority through L3. Refined L2 parent/context nodes are excluded from graph execution, L3 runtime ancestry must resolve to a valid L1 country, existing L2 edge semantics remain compatible, and all non-L1 strategic channels continue to require explicit stable-catalog evidence or remain unresolved/null.

### v0.34c2 — deepest-active regimes and recursive coupling — IMPLEMENTED

Implemented by [FRACTAL_L3_REGIMES_COUPLING_V0.34C2.md](FRACTAL_L3_REGIMES_COUPLING_V0.34C2.md).

Regional phase/security persistence now follows authority handoff from refined L2 parents to active L3 leaves. Transitional ancestor persistence is permitted only while structurally justified, then pruned. Parent-child coupling now aggregates bottom-up from L3 -> L2 -> L1, and day-transaction event/spillover state coverage excludes non-executing parent-context nodes.

### v0.34c3+ — recursive reaggregation and lifecycle closure

Next, conservative L3 -> L2 collapse/reaggregation, authority restoration and actual generation-2 L3 re-refinement must be implemented. A canonical L2 -> L3 -> L2 -> L3(g2) lifecycle test is required before materialization/runtime activation continues to L4 actor networks and L5 event clusters.

## 14. Validation requirements

The autonomous L2 implementation is not complete unless tests demonstrate all of the following:

- an unrefined parent evolves at L1;
- a refined parent no longer executes duplicate regionalizable dynamics at L1;
- active children evolve independently;
- sibling divergence is possible from different local state/input;
- inactive historical children do not evolve;
- child RNG streams are deterministic and isolated;
- child events and spillovers are traceable;
- parent aggregate views reconcile with active children;
- additive stocks are conserved across refine/collapse;
- national-only variables are not spuriously spatialized;
- transaction failure restores L1, L2, topology, trace and RNG state;
- collapse cannot silently erase categorical disagreement;
- re-refinement creates the next immutable lineage generation;
- adding a new regional catalog requires no country-specific dynamic equations.

## 15. Relationship to Phase 1

Autonomous regional dynamics are a prerequisite for completing the documented fractal portion of Phase 1.

They should be implemented before:

- recursive L3/L4/L5 refinement;
- serious Monte Carlo interpretation;
- broad scenario expansion that depends on regional divergence;
- claims that the adaptive fractal architecture is complete.

Other Phase-1 gaps remain independent and still require implementation, including:

- alliance-response dynamics;
- multi-day scenario runner;
- Monte Carlo orchestration;
- broader empirical initialization;
- calibrated parameters;
- unresolved graph channels;
- resource depletion and other documented system dynamics.

## 16. Documentation interpretation rule

Historical implementation documents v0.21-v0.24 may state that child dynamics are disabled.

Those statements describe the scope of those milestones only.

They must not be interpreted as a permanent architecture decision.

The canonical direction after v0.24 is autonomous lower-level execution governed by this document and the broader adaptive-fractal architecture.

## 17. Safety and abstraction boundary

Fractal refinement changes computational resolution, not operational military detail.

This roadmap does not introduce:

- tactical target selection;
- weapon selection;
- attack-method optimization;
- route planning;
- operational execution;
- automatic combatant classification from civilian identity.

All military and security behavior remains strategic and aggregate.

---

**Canonical decision:** topology refinement without autonomous lower-level dynamics is an intermediate implementation state, not completion of the adaptive fractal model.
