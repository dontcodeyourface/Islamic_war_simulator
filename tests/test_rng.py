from __future__ import annotations

import logging

from iwsim.rng import RNGManager

logger = logging.getLogger(__name__)


def test_rng_same_seed_same_stream_same_values() -> None:
    logger.info("test_rng_same_seed_same_stream_same_values")
    a = RNGManager(42)
    b = RNGManager(42)
    values_a = [a.stream("events").random() for _ in range(5)]
    values_b = [b.stream("events").random() for _ in range(5)]
    assert values_a == values_b


def test_rng_streams_are_independent_of_call_order() -> None:
    logger.info("test_rng_streams_are_independent_of_call_order")
    a = RNGManager(42)
    event_a = a.stream("events").random()
    _ = a.stream("demographic_sampling").random()

    b = RNGManager(42)
    _ = b.stream("demographic_sampling").random()
    event_b = b.stream("events").random()

    assert event_a == event_b
