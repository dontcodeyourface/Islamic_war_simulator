from __future__ import annotations

import logging
from typing import Any

from .config import get_value
from .normalization import normalize_baseline_anchor, normalize_empirical_latent
from .rng import RNGManager
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


def _numeric_mean(value: Any) -> float | None:
    logger.info("_numeric_mean type=%s", type(value).__name__)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        numeric = [
            float(item)
            for item in value.values()
            if isinstance(item, (int, float)) and not isinstance(item, bool)
        ]
        if numeric:
            return sum(numeric) / len(numeric)
    return None


def _first_value(snapshot: dict[str, Any], paths: list[str]) -> Any:
    logger.info("_first_value candidates=%s", paths)
    for path in paths:
        value = get_value(snapshot, path, default=None)
        if value is not None:
            return value
    return None


def _extract_physical_stocks(snapshot: dict[str, Any]) -> dict[str, int | float | None]:
    logger.info("_extract_physical_stocks country=%s", get_value(snapshot, "identity.country_name"))
    fuel_days = _numeric_mean(
        _first_value(snapshot, ["energy_security.strategic_petroleum_stock_days"])
    )
    return {
        "population_total": _first_value(snapshot, ["population.total"]),
        "working_age_population": _first_value(
            snapshot,
            [
                "population.age.age_15_64",
                "population.age.working_age",
                "manpower.working_age_population",
            ],
        ),
        "dependent_population": _first_value(
            snapshot,
            [
                "population.age.dependent_population",
                "demographic_dynamics.dependent_population",
            ],
        ),
        "displaced_people": 0,
        "reception_population": 0,
        "fuel_stock_days_equivalent": fuel_days,
        "strategic_food_stock_days": _numeric_mean(
            _first_value(snapshot, ["food_water_security.strategic_food_stock_days"])
        ),
        "available_police_personnel": _numeric_mean(
            _first_value(
                snapshot,
                [
                    "law_enforcement.total_officers",
                    "law_enforcement.total_workforce",
                ],
            )
        ),
        "available_military_personnel": _numeric_mean(
            _first_value(
                snapshot,
                [
                    "armed_forces.active_total",
                    "armed_forces.active_personnel",
                    "manpower.active_military",
                ],
            )
        ),
        "prison_population": _numeric_mean(
            _first_value(snapshot, ["prisons.total_prison_population", "prisons.total"])
        ),
        "foreign_reserves_usd": _numeric_mean(
            _first_value(
                snapshot,
                [
                    "economy.foreign_exchange_reserves_usd",
                    "economy.foreign_reserves_usd",
                ],
            )
        ),
        "gold_reserves_tonnes": _numeric_mean(
            _first_value(
                snapshot,
                [
                    "economy.official_gold_reserves_tonnes",
                    "economy.gold_reserves_tonnes",
                ],
            )
        ),
    }


def _init_rule_map(engine_state_registry: dict[str, Any]) -> dict[str, str]:
    logger.info("_init_rule_map")
    result: dict[str, str] = {}
    for group in engine_state_registry["latent_groups"].values():
        for item in group["variables"]:
            result[item["id"]] = item["init_rule_id"]
    return result


def _sample_prior(prior: dict[str, Any], rng: RNGManager) -> tuple[float, int]:
    logger.info("_sample_prior distribution=%s", prior["distribution"])
    stream = rng.stream("uncertainty_sampling")
    distribution = prior["distribution"]
    if distribution == "beta":
        draw_index = stream.draw_index
        return stream.betavariate(float(prior["alpha"]), float(prior["beta"])), draw_index
    if distribution == "normal_truncated":
        lower = float(prior["lower"])
        upper = float(prior["upper"])
        for _ in range(1000):
            draw_index = stream.draw_index
            value = stream.normalvariate(float(prior["mean"]), float(prior["sd"]))
            if lower <= value <= upper:
                return value, draw_index
        raise RuntimeError("Unable to sample truncated normal within 1000 draws")
    raise ValueError(f"Unsupported prior distribution: {distribution}")


def initialize_synthetic_state(
    *,
    snapshot: dict[str, Any],
    engine_state_registry: dict[str, Any],
    normalization_registry: dict[str, Any],
    rng: RNGManager,
    trace: TraceLedger,
) -> EngineState:
    """Create a fully populated EngineState using explicit smoke-test priors."""
    logger.info(
        "initialize_synthetic_state country=%s",
        get_value(snapshot, "identity.country_name"),
    )
    latent_registry = extract_latent_registry(engine_state_registry)
    prior_map = normalization_registry["synthetic_smoke_defaults"][
        "missing_latent_prior_classes"
    ]
    priors = normalization_registry["prior_policy"]["synthetic_smoke_v1"]["priors"]
    init_rules = _init_rule_map(engine_state_registry)

    latents: dict[str, float] = {}
    for latent_id in latent_registry:
        prior_id = prior_map[latent_id]
        value, draw_index = _sample_prior(priors[prior_id], rng)
        latents[latent_id] = float(value)
        trace.append_initialization(
            node_id=str(get_value(snapshot, "identity.iso3")),
            variable=latent_id,
            value=float(value),
            init_rule_id=init_rules[latent_id],
            prior_id=prior_id,
            rng_stream="uncertainty_sampling",
            draw_index=draw_index,
        )

    state = EngineState(
        node_id=str(get_value(snapshot, "identity.iso3")),
        day=0,
        physical_stocks=_extract_physical_stocks(snapshot),
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={
            "country_name": get_value(snapshot, "identity.country_name"),
            "snapshot_version": get_value(snapshot, "identity.snapshot_version"),
            "initialization_profile": "synthetic_smoke_v1",
            "empirical_fraction": 0.0,
            "prior_fraction": 1.0,
        },
    )
    state.validate(latent_registry)
    return state


def initialize_hybrid_state(
    *,
    snapshot: dict[str, Any],
    engine_state_registry: dict[str, Any],
    normalization_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    feature_map: dict[str, Any],
    rng: RNGManager,
    trace: TraceLedger,
    profile: str = "synthetic_smoke_v1",
) -> EngineState:
    """Initialize EngineState using empirical evidence, baseline anchors, then priors."""
    logger.info(
        "initialize_hybrid_state country=%s profile=%s",
        get_value(snapshot, "identity.country_name"),
        profile,
    )
    if profile != "synthetic_smoke_v1":
        raise ValueError("v0.2 initializer currently supports synthetic_smoke_v1 only")

    latent_registry = extract_latent_registry(engine_state_registry)
    prior_map = normalization_registry["synthetic_smoke_defaults"][
        "missing_latent_prior_classes"
    ]
    priors = normalization_registry["prior_policy"]["synthetic_smoke_v1"]["priors"]
    init_rules = _init_rule_map(engine_state_registry)

    latents: dict[str, float] = {}
    empirical_count = 0
    baseline_count = 0
    prior_count = 0

    for latent_id in latent_registry:
        empirical = normalize_empirical_latent(
            latent_id=latent_id,
            snapshot=snapshot,
            feature_map=feature_map,
            parameter_registry=parameter_registry,
            normalization_registry=normalization_registry,
            profile=profile,
        )
        if empirical is not None:
            latents[latent_id] = empirical.value
            empirical_count += 1
            trace.append_initialization(
                node_id=str(get_value(snapshot, "identity.iso3")),
                variable=latent_id,
                value=empirical.value,
                init_rule_id=init_rules[latent_id],
                prior_id=None,
                rng_stream=None,
                draw_index=None,
                source_type="empirical",
                normalization_rule_id=empirical.normalization_rule_id,
                parameter_ids=empirical.parameter_ids,
                snapshot_field_refs=empirical.snapshot_field_refs,
                source_ids=empirical.source_ids,
                data_quality=empirical.data_quality,
                freshness=empirical.freshness,
                uncertainty_multiplier=empirical.uncertainty_multiplier,
                empirical_fraction=1.0,
                prior_fraction=0.0,
                baseline_fraction=0.0,
            )
            continue

        baseline = normalize_baseline_anchor(
            latent_id=latent_id,
            feature_map=feature_map,
            parameter_registry=parameter_registry,
            profile=profile,
        )
        if baseline is not None:
            latents[latent_id] = baseline.value
            baseline_count += 1
            trace.append_initialization(
                node_id=str(get_value(snapshot, "identity.iso3")),
                variable=latent_id,
                value=baseline.value,
                init_rule_id=init_rules[latent_id],
                prior_id=None,
                rng_stream=None,
                draw_index=None,
                source_type="baseline_anchor",
                normalization_rule_id=baseline.normalization_rule_id,
                parameter_ids=baseline.parameter_ids,
                snapshot_field_refs=(),
                source_ids=(),
                data_quality=baseline.data_quality,
                freshness=baseline.freshness,
                uncertainty_multiplier=baseline.uncertainty_multiplier,
                empirical_fraction=0.0,
                prior_fraction=0.0,
                baseline_fraction=1.0,
            )
            continue

        prior_id = prior_map[latent_id]
        value, draw_index = _sample_prior(priors[prior_id], rng)
        latents[latent_id] = float(value)
        prior_count += 1
        trace.append_initialization(
            node_id=str(get_value(snapshot, "identity.iso3")),
            variable=latent_id,
            value=float(value),
            init_rule_id=init_rules[latent_id],
            prior_id=prior_id,
            rng_stream="uncertainty_sampling",
            draw_index=draw_index,
            source_type="prior",
            empirical_fraction=0.0,
            prior_fraction=1.0,
            baseline_fraction=0.0,
        )

    total = len(latent_registry)
    state = EngineState(
        node_id=str(get_value(snapshot, "identity.iso3")),
        day=0,
        physical_stocks=_extract_physical_stocks(snapshot),
        latents=latents,
        regimes={
            "national_phase": "STABLE",
            "security_force_regime": "COHESIVE",
            "prison_regime": "CONTROLLED",
            "organized_crime_regime": "NORMAL_MARKET",
        },
        metadata={
            "country_name": get_value(snapshot, "identity.country_name"),
            "snapshot_version": get_value(snapshot, "identity.snapshot_version"),
            "initialization_profile": profile,
            "empirical_fraction": empirical_count / total,
            "baseline_fraction": baseline_count / total,
            "prior_fraction": prior_count / total,
            "empirical_latent_count": empirical_count,
            "baseline_latent_count": baseline_count,
            "prior_latent_count": prior_count,
        },
    )
    state.validate(latent_registry)
    return state
