from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import __version__
from .config import canonical_hash, file_sha256, load_yaml
from .engine import NoOpEngine
from .graph import build_structural_graph
from .initializer import initialize_hybrid_state
from .io import write_json
from .logging import configure_logging
from .manifest import build_manifest
from .rng import RNGManager
from .trace import TraceLedger
from .transaction import execute_day_transaction

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    logger.info("build_parser")
    parser = argparse.ArgumentParser(prog="iwsim")
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke = subparsers.add_parser("smoke", help="Run infrastructure-only deterministic smoke loop")
    smoke.add_argument("--repo-root", default=".")
    smoke.add_argument("--country", required=True)
    smoke.add_argument("--seed", type=int, default=42)
    smoke.add_argument("--days", type=int, default=30)
    smoke.add_argument("--out", default="run_output")
    smoke.add_argument("--git-commit", default="UNKNOWN")
    smoke.add_argument("--log-level", default="INFO")

    day_smoke = subparsers.add_parser(
        "day-smoke",
        help="Run one atomic five-country transaction day",
    )
    day_smoke.add_argument("--repo-root", default=".")
    day_smoke.add_argument("--seed", type=int, default=42)
    day_smoke.add_argument("--out", default="day_run_output")
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
    graph_config_path = root / "config/graph/base_country_graph_v1.yaml"

    snapshot = load_yaml(country_path)
    engine_state_registry = load_yaml(engine_state_path)
    normalization_registry = load_yaml(normalization_path)
    parameter_registry = load_yaml(parameters_path)
    feature_map = load_yaml(feature_map_path)
    graph_config = load_yaml(graph_config_path)
    distance_matrix = load_yaml(root / graph_config["distance_matrix_path"])
    graph = build_structural_graph(
        repo_root=root,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameter_registry,
        profile="synthetic_smoke_v1",
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
        snapshot_bundle_hash=canonical_hash(snapshot),
        country_file_hashes={initial_state.node_id: file_sha256(country_path)},
        graph_hash=graph.graph_hash(),
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
        enabled_modules=("initializer", "structural_graph", "trace", "noop_engine"),
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
    write_json(out / "graph.json", graph.to_dict())
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
    logger.info("run_day_smoke seed=%s out=%s", args.seed, args.out)
    root = Path(args.repo_root)
    engine_state_registry = load_yaml(root / "config/engine/engine_state_v1.yaml")
    normalization_registry = load_yaml(
        root / "config/engine/normalization_parameters_v1.yaml"
    )
    parameter_registry = load_yaml(root / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(root / "config/engine/snapshot_feature_map_v1.yaml")
    graph_config = load_yaml(root / "config/graph/base_country_graph_v1.yaml")
    transaction_config = load_yaml(root / "config/engine/day_transaction_v2.yaml")
    phase_config = load_yaml(root / "config/engine/phase_evaluator_v1.yaml")
    phase_resolver_config = load_yaml(
        root / "config/engine/phase_transition_resolver_v1.yaml"
    )
    distance_matrix = load_yaml(root / graph_config["distance_matrix_path"])

    graph = build_structural_graph(
        repo_root=root,
        graph_config=graph_config,
        distance_matrix=distance_matrix,
        parameter_registry=parameter_registry,
        profile="synthetic_smoke_v1",
    )

    snapshots = {
        node_id: load_yaml(root / spec["snapshot_path"])
        for node_id, spec in sorted(graph_config["nodes"].items())
    }
    rng = RNGManager(master_seed=args.seed)
    trace = TraceLedger()
    states = {
        node_id: initialize_hybrid_state(
            snapshot=snapshots[node_id],
            engine_state_registry=engine_state_registry,
            normalization_registry=normalization_registry,
            parameter_registry=parameter_registry,
            feature_map=feature_map,
            rng=rng,
            trace=trace,
            profile="synthetic_smoke_v1",
        )
        for node_id in sorted(snapshots)
    }

    parameter_set = parameter_registry["parameter_sets"]["synthetic_smoke_v1"]
    scenario_payload = {"scenario_id": "SCN-DAY-SMOKE", "version": "1"}
    manifest = build_manifest(
        engine_version=__version__,
        git_commit=args.git_commit,
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshots),
        country_file_hashes={
            node_id: file_sha256(
                root / graph_config["nodes"][node_id]["snapshot_path"]
            )
            for node_id in sorted(snapshots)
        },
        graph_hash=graph.graph_hash(),
        scenario_id="SCN-DAY-SMOKE",
        scenario_hash=canonical_hash(scenario_payload),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(parameter_set),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=args.seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date=str(next(iter(snapshots.values()))["identity"]["snapshot_date"]),
        horizon_days=1,
        enabled_modules=(
            "initializer",
            "structural_graph",
            "event_engine",
            "event_effect_proposals",
            "owner_resolver",
            "day_transaction",
            "phase_evaluator",
            "phase_resolver",
            "trace",
        ),
        normalization_version="1.0-hybrid-v0.2",
        execution_order_version="EXEC_ORDER_V1",
    )

    result = execute_day_transaction(
        states=states,
        graph=graph,
        transaction_config=transaction_config,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile="synthetic_smoke_v1",
        rng=rng,
        manifest=manifest,
        trace=trace,
        phase_config=phase_config,
        phase_resolver_config=phase_resolver_config,
        phase_persistence={node_id: None for node_id in sorted(states)},
        phase_context_flags={},
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "manifest.json", manifest.to_dict())
    write_json(out / "graph.json", graph.to_dict())
    write_json(
        out / "initial_states.json",
        {
            node_id: state.to_dict()
            for node_id, state in sorted(states.items())
        },
    )
    write_json(out / "day_result.json", result.to_dict())
    write_json(
        out / "replay_summary.json",
        {
            "run_id": manifest.run_id,
            "replay_key": manifest.replay_key,
            "transaction_id": result.transaction_id,
            "day_from": result.day_from,
            "day_to": result.day_to,
            "events": [event.event_id for event in result.events],
            "candidate_count": len(result.candidate_results),
            "proposal_count": len(result.proposals),
            "resolution_count": len(result.resolutions),
            "phase_commit_count": len(result.phase_commits),
            "phase_commits": [
                commit.to_dict() for commit in result.phase_commits
            ],
            "phase_persistence": {
                node_id: persistence.to_dict()
                for node_id, persistence in sorted(result.phase_persistence.items())
            },
            "state_hashes_before": dict(result.state_hashes_before),
            "state_hashes_after": dict(result.state_hashes_after),
            "rng": rng.describe(),
            "profile_warning": (
                "ENGINEERING TEST PROFILE / NOT CALIBRATED / "
                "NOT A REAL-WORLD PROBABILITY"
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
