from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .config import canonical_hash

logger = logging.getLogger(__name__)


@dataclass
class EngineState:
    node_id: str
    day: int
    physical_stocks: dict[str, int | float | None]
    latents: dict[str, float]
    regimes: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self, latent_registry: dict[str, tuple[float, float]]) -> None:
        logger.info("EngineState.validate node_id=%s day=%s", self.node_id, self.day)
        missing = sorted(set(latent_registry) - set(self.latents))
        extra = sorted(set(self.latents) - set(latent_registry))
        if missing or extra:
            raise ValueError(f"Latent mismatch missing={missing} extra={extra}")
        for latent_id, value in self.latents.items():
            low, high = latent_registry[latent_id]
            if not low <= value <= high:
                raise ValueError(
                    f"{latent_id}={value} outside [{low}, {high}]"
                )

    def to_dict(self) -> dict[str, Any]:
        logger.info("EngineState.to_dict node_id=%s day=%s", self.node_id, self.day)
        return {
            "node_id": self.node_id,
            "day": self.day,
            "physical_stocks": dict(sorted(self.physical_stocks.items())),
            "latents": dict(sorted(self.latents.items())),
            "regimes": dict(sorted(self.regimes.items())),
            "metadata": self.metadata,
        }

    def state_hash(self) -> str:
        logger.info("EngineState.state_hash node_id=%s day=%s", self.node_id, self.day)
        return canonical_hash(self.to_dict())

    def clone_for_next_day(self) -> "EngineState":
        logger.info("EngineState.clone_for_next_day node_id=%s day=%s", self.node_id, self.day)
        return EngineState(
            node_id=self.node_id,
            day=self.day + 1,
            physical_stocks=dict(self.physical_stocks),
            latents=dict(self.latents),
            regimes=dict(self.regimes),
            metadata=dict(self.metadata),
        )


def extract_latent_registry(engine_state_registry: dict[str, Any]) -> dict[str, tuple[float, float]]:
    logger.info("extract_latent_registry")
    registry: dict[str, tuple[float, float]] = {}
    for group in engine_state_registry["latent_groups"].values():
        for item in group["variables"]:
            low, high = item["range"]
            registry[item["id"]] = (float(low), float(high))
    return registry


def extract_latent_ids(engine_state_registry: dict[str, Any]) -> list[str]:
    logger.info("extract_latent_ids")
    return list(extract_latent_registry(engine_state_registry))
