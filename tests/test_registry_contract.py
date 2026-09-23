from __future__ import annotations

import logging
from pathlib import Path

from iwsim.config import load_yaml
from iwsim.state import extract_latent_registry

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def test_engine_state_registry_has_exact_contract() -> None:
    logger.info("test_engine_state_registry_has_exact_contract")
    registry = load_yaml(ROOT / "config/engine/engine_state_v1.yaml")
    latent_registry = extract_latent_registry(registry)
    assert len(latent_registry) == 60
    assert len(registry["physical_stocks"]) == 12
    assert len(set(latent_registry)) == 60


def test_parameter_references_are_declared() -> None:
    logger.info("test_parameter_references_are_declared")
    parameters = load_yaml(ROOT / "config/engine/parameter_registry_v1.yaml")
    assert "synthetic_smoke_v1" in parameters["parameter_sets"]
    assert "calibrated_v1" in parameters["parameter_sets"]
    synthetic = parameters["parameter_sets"]["synthetic_smoke_v1"]["parameters"]
    assert "DYNAMIC_GAINS_SYN_V1" in synthetic
    assert "EVENT_HAZARD_PROBABILITY_SYN_V1" in synthetic
    assert parameters["parameter_sets"]["calibrated_v1"]["missing_policy"] == "fatal"
