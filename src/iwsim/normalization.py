from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import get_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvidenceDatum:
    path: str
    value: Any
    unit: str | None
    reference_date: str | None
    source_ids: tuple[str, ...]
    quality: str
    freshness_class: str | None
    estimated: bool
    derived: bool
    imputed: bool


@dataclass(frozen=True)
class NormalizedValue:
    value: float
    normalization_rule_id: str
    parameter_ids: tuple[str, ...]
    snapshot_field_refs: tuple[str, ...]
    source_ids: tuple[str, ...]
    data_quality: str
    freshness: str
    uncertainty_multiplier: float


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    logger.info("clamp value=%s low=%s high=%s", value, low, high)
    return min(high, max(low, value))


def numeric_mean(value: Any) -> float | None:
    logger.info("numeric_mean type=%s", type(value).__name__)
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


def read_datum(snapshot: dict[str, Any], path: str) -> EvidenceDatum | None:
    logger.info("read_datum path=%s", path)
    try:
        raw = get_path(snapshot, path)
    except KeyError:
        return None
    if not isinstance(raw, dict) or "value" not in raw or raw["value"] is None:
        return None
    source_ids = raw.get("source_ids") or []
    return EvidenceDatum(
        path=path,
        value=raw["value"],
        unit=raw.get("unit"),
        reference_date=raw.get("reference_date"),
        source_ids=tuple(str(item) for item in source_ids),
        quality=str(raw.get("quality", "unavailable")),
        freshness_class=raw.get("freshness_class"),
        estimated=bool(raw.get("estimated", False)),
        derived=bool(raw.get("derived", False)),
        imputed=bool(raw.get("imputed", False)),
    )


def _parameter_set(
    parameter_registry: dict[str, Any],
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info("_parameter_set profile=%s parameter_id=%s", profile, parameter_id)
    parameter = parameter_registry["parameter_sets"][profile]["parameters"].get(parameter_id)
    if parameter is None:
        raise ValueError(f"Missing parameter {parameter_id} for profile {profile}")
    return parameter


def _combined_quality(datums: list[EvidenceDatum]) -> str:
    logger.info("_combined_quality count=%s", len(datums))
    order = {"high": 0, "medium": 1, "low": 2, "unavailable": 3}
    return max((datum.quality for datum in datums), key=lambda item: order.get(item, 3))


def _combined_freshness(datums: list[EvidenceDatum]) -> str:
    logger.info("_combined_freshness count=%s", len(datums))
    values = {datum.freshness_class or "unspecified" for datum in datums}
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


def _uncertainty_multiplier(
    datums: list[EvidenceDatum],
    normalization_registry: dict[str, Any],
) -> float:
    logger.info("_uncertainty_multiplier count=%s", len(datums))
    confidence = normalization_registry["confidence_model"]
    quality_map = confidence["quality_to_uncertainty_multiplier"]
    freshness_map = confidence["freshness_to_uncertainty_multiplier"]
    multipliers: list[float] = []
    for datum in datums:
        quality_multiplier = quality_map.get(datum.quality)
        if quality_multiplier is None:
            quality_multiplier = 2.0
        freshness_multiplier = freshness_map.get(datum.freshness_class or "structural", 1.25)
        multipliers.append(float(quality_multiplier) * float(freshness_multiplier))
    return max(multipliers) if multipliers else 1.0


def _normalized_result(
    *,
    value: float,
    rule_id: str,
    parameter_id: str,
    datums: list[EvidenceDatum],
    normalization_registry: dict[str, Any],
) -> NormalizedValue:
    logger.info("_normalized_result rule_id=%s parameter_id=%s", rule_id, parameter_id)
    source_ids = sorted({source_id for datum in datums for source_id in datum.source_ids})
    return NormalizedValue(
        value=float(value),
        normalization_rule_id=rule_id,
        parameter_ids=(parameter_id,),
        snapshot_field_refs=tuple(datum.path for datum in datums),
        source_ids=tuple(source_ids),
        data_quality=_combined_quality(datums),
        freshness=_combined_freshness(datums),
        uncertainty_multiplier=_uncertainty_multiplier(datums, normalization_registry),
    )


def _first_datum(snapshot: dict[str, Any], paths: list[str]) -> EvidenceDatum | None:
    logger.info("_first_datum paths=%s", paths)
    for path in paths:
        datum = read_datum(snapshot, path)
        if datum is not None:
            return datum
    return None


def _normalize_signed_growth(
    *,
    snapshot: dict[str, Any],
    rule: dict[str, Any],
    params: dict[str, Any],
    parameter_id: str,
    normalization_registry: dict[str, Any],
) -> NormalizedValue | None:
    logger.info("_normalize_signed_growth rule_id=%s", rule["rule_id"])
    datum = _first_datum(snapshot, rule["paths"])
    if datum is None:
        return None
    numeric = numeric_mean(datum.value)
    if numeric is None:
        return None
    scale = float(params["demographic_growth_scale_percent"])
    value = math.tanh(numeric / scale)
    return _normalized_result(
        value=clamp(value, -1.0, 1.0),
        rule_id=rule["rule_id"],
        parameter_id=parameter_id,
        datums=[datum],
        normalization_registry=normalization_registry,
    )


def _normalize_dependency(
    *,
    snapshot: dict[str, Any],
    rule: dict[str, Any],
    params: dict[str, Any],
    parameter_id: str,
    normalization_registry: dict[str, Any],
) -> NormalizedValue | None:
    logger.info("_normalize_dependency rule_id=%s", rule["rule_id"])
    for strategy in rule["strategies"]:
        if "total_path" in strategy:
            total = read_datum(snapshot, strategy["total_path"])
            working = read_datum(snapshot, strategy["working_path"])
            if total is not None and working is not None:
                total_value = numeric_mean(total.value)
                working_value = numeric_mean(working.value)
                if (
                    total_value is not None
                    and working_value is not None
                    and total_value > working_value > 0
                ):
                    ratio = (total_value - working_value) / working_value
                    k = float(params["dependency_ratio_k"])
                    value = ratio / (ratio + k)
                    return _normalized_result(
                        value=clamp(value),
                        rule_id=rule["rule_id"],
                        parameter_id=parameter_id,
                        datums=[total, working],
                        normalization_registry=normalization_registry,
                    )
        if "working_share_path" in strategy:
            working_share = read_datum(snapshot, strategy["working_share_path"])
            if working_share is not None:
                share = numeric_mean(working_share.value)
                if share is not None and 0 < share < 100:
                    ratio = (100.0 - share) / share
                    k = float(params["dependency_ratio_k"])
                    value = ratio / (ratio + k)
                    return _normalized_result(
                        value=clamp(value),
                        rule_id=rule["rule_id"],
                        parameter_id=parameter_id,
                        datums=[working_share],
                        normalization_registry=normalization_registry,
                    )
    return None


def _normalize_percent_linear(
    *,
    snapshot: dict[str, Any],
    rule: dict[str, Any],
    params: dict[str, Any],
    parameter_id: str,
    normalization_registry: dict[str, Any],
) -> NormalizedValue | None:
    logger.info("_normalize_percent_linear rule_id=%s", rule["rule_id"])
    datum = _first_datum(snapshot, rule["paths"])
    if datum is None:
        return None
    numeric = numeric_mean(datum.value)
    if numeric is None:
        return None
    high = float(params[rule["parameter_key"]])
    return _normalized_result(
        value=clamp(numeric / high),
        rule_id=rule["rule_id"],
        parameter_id=parameter_id,
        datums=[datum],
        normalization_registry=normalization_registry,
    )


def _normalize_percent_complement(
    *,
    snapshot: dict[str, Any],
    rule: dict[str, Any],
    parameter_id: str,
    normalization_registry: dict[str, Any],
) -> NormalizedValue | None:
    logger.info("_normalize_percent_complement rule_id=%s", rule["rule_id"])
    datum = _first_datum(snapshot, rule["paths"])
    if datum is None:
        return None
    numeric = numeric_mean(datum.value)
    if numeric is None:
        return None
    return _normalized_result(
        value=clamp(1.0 - numeric / 100.0),
        rule_id=rule["rule_id"],
        parameter_id=parameter_id,
        datums=[datum],
        normalization_registry=normalization_registry,
    )


def _normalize_prison_control(
    *,
    snapshot: dict[str, Any],
    rule: dict[str, Any],
    params: dict[str, Any],
    parameter_id: str,
    normalization_registry: dict[str, Any],
) -> NormalizedValue | None:
    logger.info("_normalize_prison_control rule_id=%s", rule["rule_id"])
    datum = _first_datum(snapshot, rule["paths"])
    if datum is None:
        return None
    occupancy = numeric_mean(datum.value)
    if occupancy is None:
        return None
    full = float(params["prison_occupancy_full_control_percent"])
    zero = float(params["prison_occupancy_zero_control_percent"])
    if zero <= full:
        raise ValueError("Invalid prison occupancy control anchors")
    value = 1.0 - (occupancy - full) / (zero - full)
    return _normalized_result(
        value=clamp(value),
        rule_id=rule["rule_id"],
        parameter_id=parameter_id,
        datums=[datum],
        normalization_registry=normalization_registry,
    )


def _normalize_energy(
    *,
    snapshot: dict[str, Any],
    rule: dict[str, Any],
    params: dict[str, Any],
    parameter_id: str,
    normalization_registry: dict[str, Any],
) -> NormalizedValue | None:
    logger.info("_normalize_energy rule_id=%s", rule["rule_id"])
    paths = rule["paths"]
    stock = read_datum(snapshot, paths["strategic_stock"])
    dependency = read_datum(snapshot, paths["import_dependency"])
    refining = read_datum(snapshot, paths["domestic_refining"])
    if stock is None or dependency is None or refining is None:
        return None

    stock_days = numeric_mean(stock.value)
    if stock_days is None:
        return None
    stock_component = clamp(stock_days / float(params["energy_stock_target_days"]))

    dependency_key = str(dependency.value)
    mapping = params["petroleum_import_dependency_scores"]
    if dependency_key not in mapping:
        return None
    import_component = float(mapping[dependency_key])

    if not isinstance(refining.value, bool):
        return None
    refining_component = 1.0 if refining.value else 0.0

    weights = params["energy_weights"]
    value = (
        float(weights["strategic_stock"]) * stock_component
        + float(weights["import_resilience"]) * import_component
        + float(weights["domestic_refining"]) * refining_component
    )
    return _normalized_result(
        value=clamp(value),
        rule_id=rule["rule_id"],
        parameter_id=parameter_id,
        datums=[stock, dependency, refining],
        normalization_registry=normalization_registry,
    )


def normalize_empirical_latent(
    *,
    latent_id: str,
    snapshot: dict[str, Any],
    feature_map: dict[str, Any],
    parameter_registry: dict[str, Any],
    normalization_registry: dict[str, Any],
    profile: str,
) -> NormalizedValue | None:
    logger.info("normalize_empirical_latent latent_id=%s profile=%s", latent_id, profile)
    rule = feature_map.get("empirical_rules", {}).get(latent_id)
    if rule is None:
        return None

    parameter_id = feature_map["parameter_ids"][profile]["normalization"]
    parameter = _parameter_set(parameter_registry, profile, parameter_id)
    params = parameter["value"]
    kind = rule["kind"]

    if kind == "signed_growth_tanh":
        return _normalize_signed_growth(
            snapshot=snapshot,
            rule=rule,
            params=params,
            parameter_id=parameter_id,
            normalization_registry=normalization_registry,
        )
    if kind == "age_dependency_ratio":
        return _normalize_dependency(
            snapshot=snapshot,
            rule=rule,
            params=params,
            parameter_id=parameter_id,
            normalization_registry=normalization_registry,
        )
    if kind == "percent_linear":
        return _normalize_percent_linear(
            snapshot=snapshot,
            rule=rule,
            params=params,
            parameter_id=parameter_id,
            normalization_registry=normalization_registry,
        )
    if kind == "percent_complement":
        return _normalize_percent_complement(
            snapshot=snapshot,
            rule=rule,
            parameter_id=parameter_id,
            normalization_registry=normalization_registry,
        )
    if kind == "prison_occupancy_control":
        return _normalize_prison_control(
            snapshot=snapshot,
            rule=rule,
            params=params,
            parameter_id=parameter_id,
            normalization_registry=normalization_registry,
        )
    if kind == "energy_composite":
        return _normalize_energy(
            snapshot=snapshot,
            rule=rule,
            params=params,
            parameter_id=parameter_id,
            normalization_registry=normalization_registry,
        )
    raise ValueError(f"Unsupported empirical normalization kind: {kind}")


def normalize_baseline_anchor(
    *,
    latent_id: str,
    feature_map: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
) -> NormalizedValue | None:
    logger.info("normalize_baseline_anchor latent_id=%s profile=%s", latent_id, profile)
    rule = feature_map.get("baseline_anchor_rules", {}).get(latent_id)
    if rule is None:
        return None
    parameter_id = feature_map["parameter_ids"][profile]["baseline_anchor"]
    parameter = _parameter_set(parameter_registry, profile, parameter_id)
    value = float(parameter["value"][rule["value_key"]])
    return NormalizedValue(
        value=clamp(value),
        normalization_rule_id=rule["rule_id"],
        parameter_ids=(parameter_id,),
        snapshot_field_refs=(),
        source_ids=(),
        data_quality="structural",
        freshness="baseline",
        uncertainty_multiplier=1.0,
    )
