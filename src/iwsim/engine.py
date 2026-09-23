from __future__ import annotations

import logging
from dataclasses import dataclass

from .manifest import RunManifest
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    final_state: EngineState
    state_hashes: list[str]

    def final_hash(self) -> str:
        logger.info("RunResult.final_hash day=%s", self.final_state.day)
        return self.final_state.state_hash()


class NoOpEngine:
    """Infrastructure-only engine that advances time without behavioral deltas."""

    def __init__(self, engine_state_registry: dict[str, object]) -> None:
        logger.info("NoOpEngine.__init__")
        self._latent_registry = extract_latent_registry(engine_state_registry)

    def step(
        self,
        *,
        state: EngineState,
        manifest: RunManifest,
        trace: TraceLedger,
    ) -> EngineState:
        logger.info("NoOpEngine.step node_id=%s day=%s", state.node_id, state.day)
        state.validate(self._latent_registry)
        before_hash = state.state_hash()
        next_state = state.clone_for_next_day()
        next_state.validate(self._latent_registry)
        after_hash = next_state.state_hash()
        trace.append_daily_checkpoint(
            run_id=manifest.run_id,
            day=next_state.day,
            node_id=state.node_id,
            state_hash_before=before_hash,
            state_hash_after=after_hash,
        )
        return next_state

    def run(
        self,
        *,
        initial_state: EngineState,
        manifest: RunManifest,
        trace: TraceLedger,
        days: int,
    ) -> RunResult:
        logger.info(
            "NoOpEngine.run node_id=%s days=%s run_id=%s",
            initial_state.node_id,
            days,
            manifest.run_id,
        )
        if days < 0:
            raise ValueError("days must be >= 0")
        if days != manifest.horizon_days:
            raise ValueError(
                f"days={days} does not match manifest.horizon_days={manifest.horizon_days}"
            )
        if manifest.time_step_days != 1:
            raise ValueError("NoOpEngine v0.1 requires a 1-day time step")
        state = initial_state
        hashes = [state.state_hash()]
        for _ in range(days):
            state = self.step(state=state, manifest=manifest, trace=trace)
            hashes.append(state.state_hash())
        return RunResult(final_state=state, state_hashes=hashes)
