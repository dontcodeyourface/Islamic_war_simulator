from __future__ import annotations

import logging
from pathlib import Path

from iwsim.config import canonical_hash, load_yaml
from iwsim.engine import NoOpEngine
from iwsim.initializer import initialize_synthetic_state
from iwsim.manifest import build_manifest
from iwsim.rng import RNGManager
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _run(seed: int, days: int):
    logger.info("_run seed=%s days=%s", seed, days)
    snapshot = load_yaml(ROOT / "config/countries/spain.yaml")
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")

    rng = RNGManager(seed)
    trace = TraceLedger()
    initial = initialize_synthetic_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        rng=rng,
        trace=trace,
    )

    parameter_set = parameters["parameter_sets"]["synthetic_smoke_v1"]
    manifest = build_manifest(
        created_at="2026-09-23T00:00:00+00:00",
        engine_version="0.1.0",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash(snapshot),
        country_file_hashes={"ESP": "TEST"},
        graph_hash=canonical_hash({"graph": "none"}),
        scenario_id="SCN-SMOKE-NOOP",
        scenario_hash=canonical_hash({"scenario": "noop"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(parameter_set),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=seed,
        rng_algorithm=rng.algorithm,
        time_step_days=1,
        start_date="2026-09-23",
        horizon_days=days,
        enabled_modules=("initializer", "trace", "noop_engine"),
        normalization_version="1.0",
        execution_order_version="EXEC_ORDER_V1",
    )

    result = NoOpEngine(state_registry).run(
        initial_state=initial,
        manifest=manifest,
        trace=trace,
        days=days,
    )
    return manifest, result, trace


def test_noop_engine_replays_exactly() -> None:
    logger.info("test_noop_engine_replays_exactly")
    manifest_a, result_a, trace_a = _run(2026, 30)
    manifest_b, result_b, trace_b = _run(2026, 30)

    assert manifest_a.replay_key == manifest_b.replay_key
    assert result_a.state_hashes == result_b.state_hashes
    assert result_a.final_hash() == result_b.final_hash()
    assert trace_a.records == trace_b.records


def test_noop_engine_preserves_latents() -> None:
    logger.info("test_noop_engine_preserves_latents")
    _, result, trace = _run(2026, 30)
    initialization_records = [
        record for record in trace.records if record["record_type"] == "initialization"
    ]
    assert len(initialization_records) == 60
    assert result.final_state.day == 30
