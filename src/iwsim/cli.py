from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import __version__
from .config import canonical_hash, file_sha256, load_yaml
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


def main() -> int:
    logger.info("main")
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    if args.command == "smoke":
        return run_smoke(args)
    parser.error(f"Unsupported command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
