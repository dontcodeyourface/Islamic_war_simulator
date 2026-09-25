from __future__ import annotations

import logging
from pathlib import Path

from iwsim.config import load_yaml

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _policy() -> dict:
    logger.info("_policy")
    return load_yaml(
        ROOT / "config/engine/fractal_l3_partition_policy_v1.yaml"
    )


def _l2_catalog() -> dict:
    logger.info("_l2_catalog")
    return load_yaml(
        ROOT / "config/engine/fractal_region_catalog_v1.yaml"
    )


def test_l3_partition_policy_covers_every_snapshot_country() -> None:
    logger.info(
        "test_l3_partition_policy_covers_every_snapshot_country"
    )
    policy = _policy()
    catalog = _l2_catalog()

    assert set(policy["countries"]) == set(catalog["parents"])
    assert set(policy["countries"]) == {
        "ESP",
        "FRA",
        "DEU",
        "GBR",
        "MAR",
    }


def test_l3_partition_policy_is_adjacent_explicit_and_fail_closed() -> None:
    logger.info(
        "test_l3_partition_policy_is_adjacent_explicit_and_fail_closed"
    )
    policy = _policy()
    transition = policy["transition"]

    assert transition["from_level"] == "L2_REGION"
    assert transition["to_level"] == "L3_METRO_OR_LOGISTICS_AREA"
    assert transition["one_level_per_action"] is True
    assert transition["explicit_child_catalog_required"] is True
    assert transition["missing_catalog_behavior"] == "block_not_abort"
    assert transition["invalid_catalog_behavior"] == "fail_closed"
    assert transition["minimum_children"] == 2
    assert transition["maximum_children"] == 20


def test_l3_partition_policy_forbids_weight_fallbacks() -> None:
    logger.info(
        "test_l3_partition_policy_forbids_weight_fallbacks"
    )
    weight = _policy()["weight_policy"]

    assert weight["basis"] == "population_share"
    assert weight["weights_required_before_activation"] is True
    assert weight["equal_weight_fallback_allowed"] is False
    assert weight["inferred_weight_fallback_allowed"] is False


def test_l3_country_partition_bases_are_explicit_and_sourced() -> None:
    logger.info(
        "test_l3_country_partition_bases_are_explicit_and_sourced"
    )
    countries = _policy()["countries"]

    assert countries["ESP"]["partition_basis"] == (
        "province_or_equivalent_nuts3"
    )
    assert countries["FRA"]["partition_basis"] == (
        "department_or_equivalent_nuts3"
    )
    assert countries["DEU"]["partition_basis"] == (
        "nuts2_subregion_within_land"
    )
    assert countries["GBR"]["partition_basis"] == (
        "first_stable_itl_partition_below_constituent_country"
    )
    assert countries["MAR"]["partition_basis"] == (
        "province_or_prefecture"
    )

    for iso3, item in sorted(countries.items()):
        logger.info(
            "validate L3 policy country=%s source=%s",
            iso3,
            item["topology_source_id"],
        )
        assert item["topology_source_id"]
        assert item["population_source_id"]
        assert item["reference_framework"]
        assert item["small_parent_policy"] == (
            "no_l3_without_two_explicit_children"
        )


def test_l3_partition_policy_preserves_strategic_safety_boundary() -> None:
    logger.info(
        "test_l3_partition_policy_preserves_strategic_safety_boundary"
    )
    safety = _policy()["safety"]

    assert safety["partition_is_strategic_aggregate"] is True
    assert safety["tactical_routes"] is False
    assert safety["facility_targeting"] is False
    assert safety["weapon_selection"] is False
    assert safety["operational_execution"] is False



def test_l3_partition_policy_source_ids_exist_in_provenance_registry() -> None:
    logger.info(
        "test_l3_partition_policy_source_ids_exist_in_provenance_registry"
    )
    provenance = load_yaml(
        ROOT / "data/provenance/snapshot_v1_sources.yaml"
    )
    sources = provenance["sources"]

    for iso3, item in sorted(_policy()["countries"].items()):
        logger.info("validate provenance country=%s", iso3)
        assert item["topology_source_id"] in sources
        assert item["population_source_id"] in sources
