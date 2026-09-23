from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import canonical_hash, file_sha256, load_yaml
from .engine import NoOpEngine
from .initializer import initialize_synthetic_state
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

    snapshot = load_yaml(country_path)
    engine_state_registry = load_yaml(engine_state_path)
    normalization_registry = load_yaml(normalization_path)
    parameter_registry = load_yaml(parameters_path)

    rng = RNGManager(master_seed=args.seed)
    trace = TraceLedger()
    initial_state = initialize_synthetic_state(
        snapshot=snapshot,
        engine_state_registry=engine_state_registry,
        normalization_registry=normalization_registry,
        rng=rng,
        trace=trace,
    )

    parameter_set = parameter_registry["parameter_sets"]["synthetic_smoke_v1"]
    scenario_payload = {"scenario_id": "SCN-SMOKE-NOOP", "version": "1"}

    manifest = build_manifest(
        engine_version="0.1.0",
        git_commit=args.git_commit,
        snapshot_schema_version=str(snapshot["identity"]["snapshot_version"]),
        snapshot_bundle_hash=canonical_hash(snapshot),
        country_file_hashes={initial_state.node_id: file_sha256(country_path)},
        graph_hash=canonical_hash({"graph": "none", "version": "smoke-v1"}),
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
        enabled_modules=("initializer", "trace", "noop_engine"),
        normalization_version="1.0",
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
            "profile_warning": "ENGINEERING TEST PROFILE / NOT CALIBRATED / NOT A REAL-WORLD PROBABILITY",
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
