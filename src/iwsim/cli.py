from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import __version__
from .config import canonical_hash, file_sha256, load_yaml
from .day import run_day_transaction
from .engine import NoOpEngine
from .graph import build_country_graph
from .initializer import initialize_hybrid_state
from .io import write_json
from .logging import configure_logging
from .manifest import build_manifest
from .rng import RNGManager
from .trace import TraceLedger

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    logger.info("build_parser")
    parser = argparse.ArgumentParser(prog="iwsim")
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke = subparsers.add_parser("smoke", help="Run infrastructure-only deterministic smoke loop")
    smoke.add_argument("--repo-root", default=".")
    smoke.add_argument("--country", required=True)
    smoke.add_argument(
        "--graph-config",
        default="config/graph/country_graph_v1.yaml",
    )
    smoke.add_argument("--seed", type=int, default=42)
    smoke.add_argument("--days", type=int, default=30)
    smoke.add_argument("--out", default="run_output")
    smoke.add_argument("--git-commit", default="UNKNOWN")
    smoke.add_argument("--log-level", default="INFO")

    day_smoke = subparsers.add_parser(
        "day-smoke",
        help="Run one complete atomic multi-country day transaction",
    )
    day_smoke.add_argument("--repo-root", default=".")
    day_smoke.add_argument(
        "--graph-config",
        default="config/graph/country_graph_v1.yaml",
    )
    day_smoke.add_argument(
        "--day-config",
        default="config/engine/day_transaction_v1.yaml",
    )
    day_smoke.add_argument(
        "--phase-config",
        default="config/engine/phase_evaluator_v1.yaml",
    )
    day_smoke.add_argument(
        "--recovery-config",
        default="config/engine/recovery_v1.yaml",
    )
    day_smoke.add_argument(
        "--spillover-config",
        default="config/engine/graph_spillover_v1.yaml",
    )
    day_smoke.add_argument(
        "--extremist-network-config",
        default="config/engine/extremist_network_dynamics_v1.yaml",
    )
    day_smoke.add_argument(
        "--reciprocal-radicalization-config",
        default="config/engine/reciprocal_radicalization_v1.yaml",
    )
    day_smoke.add_argument(
        "--security-chain-config",
        default="config/engine/security_chain_dynamics_v1.yaml",
    )
    day_smoke.add_argument(
        "--security-regime-config",
        default="config/engine/security_regime_evaluator_v1.yaml",
    )
    day_smoke.add_argument(
        "--security-regime-transition-config",
        default="config/engine/security_regime_transition_v1.yaml",
    )
    day_smoke.add_argument(
        "--security-regime-recovery-config",
        default="config/engine/security_regime_recovery_v1.yaml",
    )
    day_smoke.add_argument(
        "--security-regime-recovery-transition-config",
        default="config/engine/security_regime_recovery_transition_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-refinement-config",
        default="config/engine/fractal_refinement_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-materialization-config",
        default="config/engine/fractal_materialization_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-region-catalog",
        default="config/engine/fractal_region_catalog_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-child-state-config",
        default="config/engine/fractal_child_state_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-uncertainty-config",
        default="config/engine/fractal_uncertainty_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-reaggregation-config",
        default="config/engine/fractal_reaggregation_v1.yaml",
    )
    day_smoke.add_argument(
        "--fractal-runtime-config",
        default="config/engine/fractal_runtime_v1.yaml",
    )
    day_smoke.add_argument(
        "--phase-transition-config",
        default="config/engine/phase_transition_v1.yaml",
    )
    day_smoke.add_argument("--seed", type=int, default=42)
    day_smoke.add_argument("--out", default="run_output/day-smoke")
    day_smoke.add_argument("--git-commit", default="UNKNOWN")
    day_smoke.add_argument("--log-level", default="INFO")
    return parser


def run_smoke(args: argparse.Namespace) -> int:
    logger.info(
        "run_smoke country=%s seed=%s days=%s",
        args.country,
        args.seed,
        args.days,
    )
    root = Path(args.repo_root)
    country_path = root / args.country
    engine_state_path = root / "config/engine/engine_state_v1.yaml"
    normalization_path = root / "config/engine/normalization_parameters_v1.yaml"
    parameters_path = root / "config/engine/parameter_registry_v1.yaml"
    feature_map_path = root / "config/engine/snapshot_feature_map_v1.yaml"
    graph_config_path = root / args.graph_config

    snapshot = load_yaml(country_path)
    engine_state_registry = load_yaml(engine_state_path)
    normalization_registry = load_yaml(normalization_path)
    parameter_registry = load_yaml(parameters_path)
    feature_map = load_yaml(feature_map_path)
    graph_config = load_yaml(graph_config_path)
    distance_matrix = load_yaml(root / graph_config["distance_matrix_path"])

    graph_snapshots: dict[str, dict[str, object]] = {}
    country_file_hashes: dict[str, str] = {}
    for iso3, node_config in graph_config["nodes"].items():
        graph_country_path = root / node_config["snapshot_path"]
        graph_snapshot = load_yaml(graph_country_path)
        graph_snapshots[iso3] = graph_snapshot
        country_file_hashes[iso3] = file_sha256(graph_country_path)

    country_graph = build_country_graph(
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        snapshots=graph_snapshots,
        parameter_registry=parameter_registry,
        profile="synthetic_smoke_v1",
    )

    selected_iso3 = str(snapshot["identity"]["iso3"])
    if selected_iso3 not in graph_snapshots:
        raise ValueError(
            f"Selected country {selected_iso3} is not present in graph config "
            f"{args.graph_config}"
        )
    if canonical_hash(snapshot) != canonical_hash(graph_snapshots[selected_iso3]):
        raise ValueError(
            "Selected country file does not match the snapshot referenced by the graph"
        )

    rng = RNGManager(master_seed=args.seed)
    trace = TraceLedger()
    initial_state = initialize_hybrid_state(
        snapshot=snapshot,
        engine_state_registry=engine_state_registry,
        normalization_registry=normalization_registry,
        parameter_registry=parameter_registry,
        feature_map=feature_map,
        rng=rng,
        trace=trace,
        profile="synthetic_smoke_v1",
    )

    parameter_set = parameter_registry["parameter_sets"]["synthetic_smoke_v1"]
    scenario_payload = {"scenario_id": "SCN-SMOKE-NOOP", "version": "1"}

    manifest = build_manifest(
        engine_version=__version__,
        git_commit=args.git_commit,
        snapshot_schema_version=str(snapshot["identity"]["snapshot_version"]),
        snapshot_bundle_hash=canonical_hash(graph_snapshots),
        country_file_hashes=country_file_hashes,
        graph_hash=country_graph.graph_hash(),
        scenario_id="SCN-SMOKE-NOOP",
        scenario_hash=canonical_hash(scenario_payload),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(parameter_set),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=args.seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date=str(snapshot["identity"]["snapshot_date"]),
        horizon_days=args.days,
        enabled_modules=("initializer", "typed_graph", "trace", "noop_engine"),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )

    engine = NoOpEngine(engine_state_registry)
    result = engine.run(
        initial_state=initial_state,
        manifest=manifest,
        trace=trace,
        days=args.days,
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "manifest.json", manifest.to_dict())
    write_json(out / "graph.json", country_graph.to_dict())
    write_json(out / "initial_state.json", initial_state.to_dict())
    write_json(out / "final_state.json", result.final_state.to_dict())
    write_json(
        out / "replay_summary.json",
        {
            "run_id": manifest.run_id,
            "replay_key": manifest.replay_key,
            "initial_hash": result.state_hashes[0],
            "final_hash": result.state_hashes[-1],
            "days": args.days,
            "graph_hash": country_graph.graph_hash(),
            "graph_nodes": len(country_graph.nodes),
            "graph_edges": len(country_graph.edges),
            "rng": rng.describe(),
            "profile_warning": "ENGINEERING TEST PROFILE / PARTIAL EMPIRICAL INITIALIZATION / NOT CALIBRATED / NOT A REAL-WORLD PROBABILITY",
            "initialization_mix": {
                "empirical_fraction": initial_state.metadata["empirical_fraction"],
                "baseline_fraction": initial_state.metadata["baseline_fraction"],
                "prior_fraction": initial_state.metadata["prior_fraction"],
            },
        },
    )
    trace.to_jsonl(out / "trace.jsonl")
    return 0



def run_day_smoke(args: argparse.Namespace) -> int:
    logger.info(
        "run_day_smoke seed=%s graph_config=%s day_config=%s",
        args.seed,
        args.graph_config,
        args.day_config,
    )
    root = Path(args.repo_root)
    engine_state_registry = load_yaml(root / "config/engine/engine_state_v1.yaml")
    normalization_registry = load_yaml(
        root / "config/engine/normalization_parameters_v1.yaml"
    )
    parameter_registry = load_yaml(root / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(root / "config/engine/snapshot_feature_map_v1.yaml")
    graph_config = load_yaml(root / args.graph_config)
    day_config = load_yaml(root / args.day_config)
    phase_config = load_yaml(root / args.phase_config)
    recovery_config = load_yaml(root / args.recovery_config)
    spillover_config = load_yaml(root / args.spillover_config)
    extremist_network_config = load_yaml(root / args.extremist_network_config)
    reciprocal_radicalization_config = load_yaml(
        root / args.reciprocal_radicalization_config
    )
    security_chain_config = load_yaml(root / args.security_chain_config)
    security_regime_config = load_yaml(root / args.security_regime_config)
    security_regime_transition_config = load_yaml(
        root / args.security_regime_transition_config
    )
    security_regime_recovery_config = load_yaml(
        root / args.security_regime_recovery_config
    )
    security_regime_recovery_transition_config = load_yaml(
        root / args.security_regime_recovery_transition_config
    )
    fractal_refinement_config = load_yaml(
        root / args.fractal_refinement_config
    )
    fractal_materialization_config = load_yaml(
        root / args.fractal_materialization_config
    )
    fractal_region_catalog = load_yaml(root / args.fractal_region_catalog)
    fractal_child_state_config = load_yaml(
        root / args.fractal_child_state_config
    )
    fractal_uncertainty_config = load_yaml(
        root / args.fractal_uncertainty_config
    )
    fractal_reaggregation_config = load_yaml(
        root / args.fractal_reaggregation_config
    )
    fractal_runtime_config = load_yaml(
        root / args.fractal_runtime_config
    )
    phase_transition_config = load_yaml(root / args.phase_transition_config)
    distance_matrix = load_yaml(root / graph_config["distance_matrix_path"])

    snapshots: dict[str, dict[str, object]] = {}
    country_file_hashes: dict[str, str] = {}
    for iso3, node_config in sorted(graph_config["nodes"].items()):
        country_path = root / node_config["snapshot_path"]
        snapshot = load_yaml(country_path)
        snapshots[iso3] = snapshot
        country_file_hashes[iso3] = file_sha256(country_path)

    country_graph = build_country_graph(
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        snapshots=snapshots,
        parameter_registry=parameter_registry,
        profile="synthetic_smoke_v1",
    )

    rng = RNGManager(master_seed=args.seed)
    trace = TraceLedger()
    states = {
        iso3: initialize_hybrid_state(
            snapshot=snapshots[iso3],
            engine_state_registry=engine_state_registry,
            normalization_registry=normalization_registry,
            parameter_registry=parameter_registry,
            feature_map=feature_map,
            rng=rng,
            trace=trace,
            profile="synthetic_smoke_v1",
        )
        for iso3 in sorted(snapshots)
    }

    parameter_set = parameter_registry["parameter_sets"]["synthetic_smoke_v1"]
    scenario_payload = {
        "scenario_id": "SCN-DAY-SMOKE",
        "version": "1",
        "mode": "atomic-single-day",
    }
    manifest = build_manifest(
        engine_version=__version__,
        git_commit=args.git_commit,
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes=country_file_hashes,
        graph_hash=country_graph.graph_hash(),
        scenario_id="SCN-DAY-SMOKE",
        scenario_hash=canonical_hash(scenario_payload),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(parameter_set),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=args.seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=1,
        enabled_modules=(
            "initializer",
            "typed_graph",
            "event_engine",
            "event_effects",
            "owner_resolver",
            "day_transaction",
            "bounded_recovery",
            "graph_spillover_trace",
            "graph_spillover_effects",
            "extremist_network_dynamics",
            "reciprocal_radicalization",
            "security_chain_dynamics",
            "security_regime_evaluator",
            "security_regime_commit",
            "security_regime_recovery_evaluator",
            "security_regime_recovery_commit",
            "phase_evaluator",
            "phase_arbitration",
            "phase_commit",
            "fractal_refinement_evaluator",
            "fractal_l2_materialization",
            "fractal_topology_lifecycle",
            "fractal_child_state_initialization",
            "fractal_uncertainty_widening",
            "fractal_collapse_reaggregation",
            "fractal_active_runtime_plan",
            "trace",
        ),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )

    initial_states = {
        node_id: state.to_dict()
        for node_id, state in sorted(states.items())
    }
    initial_hashes = {
        node_id: state.state_hash()
        for node_id, state in sorted(states.items())
    }

    result = run_day_transaction(
        states=states,
        graph=country_graph,
        day_config=day_config,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
        enable_phase_transitions=True,
        enable_recovery=True,
        recovery_config=recovery_config,
        enable_graph_spillover=True,
        spillover_config=spillover_config,
        spillover_queue=None,
        enable_extremist_network_dynamics=True,
        extremist_network_config=extremist_network_config,
        enable_reciprocal_radicalization=True,
        reciprocal_radicalization_config=(
            reciprocal_radicalization_config
        ),
        enable_security_chain_dynamics=True,
        security_chain_config=security_chain_config,
        enable_security_regime_evaluator=True,
        security_regime_config=security_regime_config,
        security_regime_persistence=None,
        security_regime_context_flags={},
        enable_security_regime_commits=True,
        security_regime_transition_config=(
            security_regime_transition_config
        ),
        enable_security_regime_recovery_evaluator=True,
        security_regime_recovery_config=(
            security_regime_recovery_config
        ),
        security_regime_recovery_persistence=None,
        enable_security_regime_recovery_commits=True,
        security_regime_recovery_transition_config=(
            security_regime_recovery_transition_config
        ),
        phase_config=phase_config,
        phase_transition_config=phase_transition_config,
        phase_persistence=None,
        phase_context_flags={},
        enable_fractal_refinement_evaluator=True,
        fractal_refinement_config=fractal_refinement_config,
        fractal_refinement_persistence=None,
        enable_fractal_materialization=True,
        fractal_materialization_config=fractal_materialization_config,
        fractal_region_catalog=fractal_region_catalog,
        fractal_topology=None,
        enable_fractal_child_state_initialization=True,
        fractal_child_state_config=fractal_child_state_config,
        fractal_child_state_store=None,
        enable_fractal_uncertainty=True,
        fractal_uncertainty_config=fractal_uncertainty_config,
        enable_fractal_reaggregation=True,
        fractal_reaggregation_config=fractal_reaggregation_config,
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "manifest.json", manifest.to_dict())
    write_json(out / "graph.json", country_graph.to_dict())
    write_json(out / "initial_states.json", initial_states)
    write_json(out / "day_result.json", result.to_dict())
    write_json(
        out / "final_states.json",
        {
            node_id: state.to_dict()
            for node_id, state in sorted(result.states.items())
        },
    )
    write_json(
        out / "replay_summary.json",
        {
            "run_id": manifest.run_id,
            "replay_key": manifest.replay_key,
            "transaction_id": result.transaction_id,
            "day_from": result.day_from,
            "day_to": result.day_to,
            "initial_state_hashes": initial_hashes,
            "final_state_hashes": {
                node_id: state.state_hash()
                for node_id, state in sorted(result.states.items())
            },
            "event_ids": [event.event_id for event in result.events],
            "proposal_count": len(result.proposals),
            "resolution_count": len(result.resolutions),
            "phase_commit_ids": [
                record.commit_id for record in result.phase_commits
            ],
            "spillover_candidate_count": len(result.spillover_candidates),
            "matured_spillover_count": len(result.matured_spillovers),
            "spillover_proposal_count": len(result.spillover_proposals),
            "network_proposal_count": len(result.network_proposals),
            "reciprocal_radicalization_proposal_count": len(
                result.reciprocal_radicalization_proposals
            ),
            "security_chain_proposal_count": len(
                result.security_chain_proposals
            ),
            "security_regime_proposal_count": len(
                result.security_regime_proposals
            ),
            "security_regime_commit_count": len(
                result.security_regime_commits
            ),
            "security_regime_commit_ids": [
                item.commit_id for item in result.security_regime_commits
            ],
            "security_regime_persistence": {
                node_id: item.to_dict()
                for node_id, item in sorted(
                    result.security_regime_persistence.items()
                )
            },
            "security_regime_recovery_proposal_count": len(
                result.security_regime_recovery_proposals
            ),
            "security_regime_recovery_commit_count": len(
                result.security_regime_recovery_commits
            ),
            "security_regime_recovery_commit_ids": [
                item.commit_id
                for item in result.security_regime_recovery_commits
            ],
            "security_regime_recovery_persistence": {
                node_id: item.to_dict()
                for node_id, item in sorted(
                    result.security_regime_recovery_persistence.items()
                )
            },
            "fractal_refinement_action_count": len(
                result.fractal_refinement_actions
            ),
            "fractal_refinement_action_ids": [
                item.action_id for item in result.fractal_refinement_actions
            ],
            "fractal_refinement_persistence": {
                node_id: item.to_dict()
                for node_id, item in sorted(
                    result.fractal_refinement_persistence.items()
                )
            },
            "fractal_materialization_commit_ids": [
                item.commit_id
                for item in result.fractal_materialization_commits
            ],
            "fractal_topology": (
                result.fractal_topology.to_dict()
                if result.fractal_topology is not None
                else None
            ),
            "fractal_child_initialization_ids": [
                item.initialization_id
                for item in result.fractal_child_initialization_records
            ],
            "fractal_conservation_audit_ids": [
                item.audit_id
                for item in result.fractal_conservation_audits
            ],
            "fractal_uncertainty_ids": [
                item.variation_id
                for item in result.fractal_uncertainty_records
            ],
            "fractal_uncertainty_audit_ids": [
                item.audit_id
                for item in result.fractal_uncertainty_audits
            ],
            "fractal_collapse_commit_ids": [
                item.commit_id
                for item in result.fractal_collapse_commits
            ],
            "fractal_reaggregation_audit_ids": [
                item.audit_id
                for item in result.fractal_reaggregation_audits
            ],
            "fractal_child_state_store": (
                result.fractal_child_state_store.to_dict()
                if result.fractal_child_state_store is not None
                else None
            ),
            "spillover_queue": (
                result.spillover_queue.to_dict()
                if result.spillover_queue is not None
                else None
            ),
            "phase_persistence": {
                node_id: persistence.to_dict()
                for node_id, persistence in sorted(result.phase_persistence.items())
            },
            "rng": rng.describe(),
            "profile_warning": (
                "ENGINEERING TEST PROFILE / SYNTHETIC EVENT PARAMETERS / "
                "NOT CALIBRATED / NOT A REAL-WORLD PROBABILITY"
            ),
        },
    )
    trace.to_jsonl(out / "trace.jsonl")
    return 0

def main() -> int:
    logger.info("main")
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    if args.command == "smoke":
        return run_smoke(args)
    if args.command == "day-smoke":
        return run_day_smoke(args)
    parser.error(f"Unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
