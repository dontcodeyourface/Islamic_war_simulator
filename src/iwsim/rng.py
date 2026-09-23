from __future__ import annotations

import hashlib
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RNGStream:
    name: str
    seed: int
    _rng: random.Random = field(init=False, repr=False)
    draw_index: int = 0

    def __post_init__(self) -> None:
        logger.info("RNGStream.__post_init__ name=%s seed=%s", self.name, self.seed)
        self._rng = random.Random(self.seed)

    def random(self) -> float:
        logger.info("RNGStream.random name=%s draw_index=%s", self.name, self.draw_index)
        value = self._rng.random()
        self.draw_index += 1
        return value

    def betavariate(self, alpha: float, beta: float) -> float:
        logger.info(
            "RNGStream.betavariate name=%s draw_index=%s alpha=%s beta=%s",
            self.name,
            self.draw_index,
            alpha,
            beta,
        )
        value = self._rng.betavariate(alpha, beta)
        self.draw_index += 1
        return value

    def normalvariate(self, mu: float, sigma: float) -> float:
        logger.info(
            "RNGStream.normalvariate name=%s draw_index=%s mu=%s sigma=%s",
            self.name,
            self.draw_index,
            mu,
            sigma,
        )
        value = self._rng.normalvariate(mu, sigma)
        self.draw_index += 1
        return value


@dataclass
class RNGManager:
    master_seed: int
    algorithm: str = "python_random_mt19937"
    _streams: dict[str, RNGStream] = field(default_factory=dict, init=False, repr=False)

    def _derive_seed(self, stream_name: str) -> int:
        logger.info("RNGManager._derive_seed stream_name=%s", stream_name)
        payload = f"{self.master_seed}|{stream_name}|iwsim-rng-v1".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest[:8], "big", signed=False)

    def stream(self, stream_name: str) -> RNGStream:
        logger.info("RNGManager.stream stream_name=%s", stream_name)
        if stream_name not in self._streams:
            self._streams[stream_name] = RNGStream(
                name=stream_name,
                seed=self._derive_seed(stream_name),
            )
        return self._streams[stream_name]

    def describe(self) -> dict[str, object]:
        logger.info("RNGManager.describe streams=%s", sorted(self._streams))
        return {
            "master_seed": self.master_seed,
            "algorithm": self.algorithm,
            "streams": {
                name: {"seed": stream.seed, "draw_index": stream.draw_index}
                for name, stream in sorted(self._streams.items())
            },
        }
