from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.initializer import initialize_synthetic_state
from iwsim.rng import RNGManager
from iwsim.state import extract_latent_registry
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _initialize(country_file: str, seed: int):
    logger.info("_initialize country_file=%s seed=%s", country_file, seed)
    snapshot = load_yaml(ROOT / country_file)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    trace = TraceLedger()
    state = initialize_synthetic_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        rng=RNGManager(seed),
        trace=trace,
    )
    return state, trace, state_registry


@pytest.mark.parametrize(
    ("country_file", "expected_iso3", "expected_population"),
    [
        ("config/countries/spain.yaml", "ESP", 49801559),
        ("config/countries/morocco.yaml", "MAR", 36828330),
    ],
)
def test_country_initializer_is_generic(
    country_file: str,
    expected_iso3: str,
    expected_population: int,
) -> None:
    logger.info(
        "test_country_initializer_is_generic country_file=%s expected_iso3=%s",
        country_file,
        expected_iso3,
    )
    state, trace, registry = _initialize(country_file, 1234)
    assert state.node_id == expected_iso3
    assert state.physical_stocks["population_total"] == expected_population
    assert len(state.latents) == 60
    assert len(trace.records) == 60
    state.validate(extract_latent_registry(registry))


def test_initialization_replays_exactly() -> None:
    logger.info("test_initialization_replays_exactly")
    state_a, _, _ = _initialize("config/countries/spain.yaml", 77)
    state_b, _, _ = _initialize("config/countries/spain.yaml", 77)
    assert state_a.to_dict() == state_b.to_dict()
    assert state_a.state_hash() == state_b.state_hash()


def test_different_seed_changes_prior_sampled_state() -> None:
    logger.info("test_different_seed_changes_prior_sampled_state")
    state_a, _, _ = _initialize("config/countries/spain.yaml", 77)
    state_b, _, _ = _initialize("config/countries/spain.yaml", 78)
    assert state_a.latents != state_b.latents


def test_initialization_trace_rng_indices_are_unique_and_monotonic() -> None:
    logger.info("test_initialization_trace_rng_indices_are_unique_and_monotonic")
    _, trace, _ = _initialize("config/countries/spain.yaml", 91)
    draw_indices = [
        record["draw_index"]
        for record in trace.records
        if record["record_type"] == "initialization"
    ]
    assert draw_indices == sorted(draw_indices)
    assert len(draw_indices) == len(set(draw_indices))
