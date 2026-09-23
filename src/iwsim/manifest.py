from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .config import canonical_hash

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    created_at: str
    engine_version: str
    git_commit: str
    snapshot_schema_version: str
    snapshot_bundle_hash: str
    country_file_hashes: dict[str, str]
    graph_hash: str
    scenario_id: str
    scenario_hash: str
    parameter_set_id: str
    parameter_set_hash: str
    calibration_version: str
    rng_master_seed: int
    rng_algorithm: str
    time_step_days: int
    start_date: str
    horizon_days: int
    enabled_modules: tuple[str, ...]
    normalization_version: str
    execution_order_version: str
    replay_key: str

    def to_dict(self) -> dict[str, Any]:
        logger.info("RunManifest.to_dict run_id=%s", self.run_id)
        return asdict(self)


def build_replay_key(payload: dict[str, Any]) -> str:
    logger.info("build_replay_key")
    stable = dict(payload)
    stable.pop("created_at", None)
    stable.pop("run_id", None)
    stable.pop("replay_key", None)
    return canonical_hash(stable)


def build_manifest(**kwargs: Any) -> RunManifest:
    logger.info("build_manifest scenario_id=%s", kwargs.get("scenario_id"))
    payload = dict(kwargs)
    created_at = payload.pop(
        "created_at",
        datetime.now(timezone.utc).isoformat(),
    )
    payload["created_at"] = created_at
    replay_key = build_replay_key(payload)
    run_id = payload.pop("run_id", f"run-{uuid4()}")
    return RunManifest(
        run_id=run_id,
        replay_key=replay_key,
        **payload,
    )
