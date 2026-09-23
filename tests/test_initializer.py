from __future__ import annotations

import logging
from pathlib import Path

import pytest

from iwsim.config import load_yaml
from iwsim.initializer import initialize_hybrid_state, initialize_synthetic_state
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


def _initialize_hybrid(country_file: str, seed: int):
    logger.info("_initialize_hybrid country_file=%s seed=%s", country_file, seed)
    snapshot = load_yaml(ROOT / country_file)
    state_registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    normalization = load_yaml(ROOT / "config/engine/normalization_parameters_v1.yaml")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    feature_map = load_yaml(ROOT / "config/engine/snapshot_feature_map_v1.yaml")
    trace = TraceLedger()
    state = initialize_hybrid_state(
        snapshot=snapshot,
        engine_state_registry=state_registry,
        normalization_registry=normalization,
        parameter_registry=parameters,
        feature_map=feature_map,
        rng=RNGManager(seed),
        trace=trace,
        profile="synthetic_smoke_v1",
    )
    return state, trace, state_registry


def _initialization_record(trace: TraceLedger, variable: str):
    logger.info("_initialization_record variable=%s", variable)
    matches = [
        record
        for record in trace.records
        if record["record_type"] == "initialization"
        and record["variable"] == variable
    ]
    assert len(matches) == 1
    return matches[0]


def test_spain_hybrid_initialization_uses_snapshot_evidence() -> None:
    logger.info("test_spain_hybrid_initialization_uses_snapshot_evidence")
    state, trace, registry = _initialize_hybrid("config/countries/spain.yaml", 100)

    assert state.latents["demographic_momentum"] == pytest.approx(0.421899, rel=1e-5)
    assert state.latents["dependency_pressure"] == pytest.approx(0.42145, rel=2e-3)
    assert state.latents["inflation_pressure"] == pytest.approx(0.27)
    assert state.latents["unemployment_pressure"] == pytest.approx(0.416)
    assert state.latents["energy_resilience"] == pytest.approx(0.76)
    assert state.latents["food_resilience"] == pytest.approx(0.539)
    assert state.latents["water_resilience"] == pytest.approx(0.5675)
    assert state.latents["economic_output"] == pytest.approx(1.0)
    assert state.latents["electricity_functionality"] == pytest.approx(1.0)

    assert state.metadata["empirical_latent_count"] == 7
    assert state.metadata["baseline_latent_count"] == 6
    assert state.metadata["prior_latent_count"] == 47
    assert (
        state.metadata["empirical_latent_count"]
        + state.metadata["baseline_latent_count"]
        + state.metadata["prior_latent_count"]
        == 60
    )

    record = _initialization_record(trace, "energy_resilience")
    assert record["source_type"] == "empirical"
    assert record["prior_id"] is None
    assert "energy_security.strategic_petroleum_stock_days" in record["snapshot_field_refs"]
    assert "ES-CORES-RESERVES-2025" in record["source_ids"]
    assert "INIT_NORMALIZATION_SYN_V1" in record["parameter_ids"]

    prior_record = _initialization_record(trace, "government_legitimacy")
    assert prior_record["source_type"] == "prior"
    assert prior_record["prior_id"] is not None

    baseline_record = _initialization_record(trace, "economic_output")
    assert baseline_record["source_type"] == "baseline_anchor"
    assert baseline_record["empirical_fraction"] == 0.0
    assert baseline_record["baseline_fraction"] == 1.0

    state.validate(extract_latent_registry(registry))


def test_morocco_hybrid_initialization_uses_snapshot_evidence() -> None:
    logger.info("test_morocco_hybrid_initialization_uses_snapshot_evidence")
    state, trace, registry = _initialize_hybrid("config/countries/morocco.yaml", 100)

    assert state.latents["demographic_momentum"] == pytest.approx(0.401134, rel=1e-5)
    assert state.latents["dependency_pressure"] == pytest.approx(0.4736, rel=2e-3)
    assert state.latents["inflation_pressure"] == pytest.approx(0.07)
    assert state.latents["unemployment_pressure"] == pytest.approx(0.36)
    assert state.latents["energy_resilience"] == pytest.approx(0.324444, rel=1e-5)
    assert state.latents["water_resilience"] == pytest.approx(0.4925)
    assert state.latents["prison_control"] == pytest.approx(0.467)
    assert state.metadata["empirical_latent_count"] == 7
    assert state.metadata["baseline_latent_count"] == 6
    assert state.metadata["prior_latent_count"] == 47

    food_record = _initialization_record(trace, "food_resilience")
    assert food_record["source_type"] == "prior"
    assert food_record["prior_id"] is not None

    prison_record = _initialization_record(trace, "prison_control")
    assert prison_record["source_type"] == "empirical"
    assert prison_record["source_ids"] == ["MA-PRISON-POP-2025"]

    state.validate(extract_latent_registry(registry))


def test_hybrid_initialization_replays_exactly() -> None:
    logger.info("test_hybrid_initialization_replays_exactly")
    state_a, trace_a, _ = _initialize_hybrid("config/countries/spain.yaml", 55)
    state_b, trace_b, _ = _initialize_hybrid("config/countries/spain.yaml", 55)
    assert state_a.to_dict() == state_b.to_dict()
    assert trace_a.records == trace_b.records


def test_hybrid_initialization_mix_sums_to_one() -> None:
    logger.info("test_hybrid_initialization_mix_sums_to_one")
    state, _, _ = _initialize_hybrid("config/countries/spain.yaml", 55)
    total = (
        state.metadata["empirical_fraction"]
        + state.metadata["baseline_fraction"]
        + state.metadata["prior_fraction"]
    )
    assert total == pytest.approx(1.0)
