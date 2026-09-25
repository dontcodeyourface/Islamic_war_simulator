from __future__ import annotations

import logging
import math
from pathlib import Path

from iwsim.config import canonical_hash, load_yaml
from iwsim.fractal import (
    FractalRefinementActionProposal,
    FractalRefinementPersistenceState,
)
from iwsim.fractal_materialization import (
    FractalTopologyNode,
    FractalTopologyState,
    materialize_next_level,
)
from iwsim.manifest import build_manifest
from iwsim.trace import TraceLedger

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MULTI_PROVINCE = {
    "ESP::AN": {
        "04": 788934,
        "11": 1267916,
        "14": 772913,
        "18": 959738,
        "21": 543302,
        "23": 620254,
        "29": 1820507,
        "41": 2004487,
    },
    "ESP::AR": {
        "22": 234361,
        "44": 137488,
        "50": 1017449,
    },
    "ESP::CN": {
        "35": 1182281,
        "38": 1095424,
    },
    "ESP::CL": {
        "05": 162743,
        "09": 367864,
        "24": 450910,
        "34": 160620,
        "37": 331264,
        "40": 161261,
        "42": 90559,
        "47": 536425,
        "49": 165510,
    },
    "ESP::CM": {
        "02": 394702,
        "13": 500441,
        "16": 201233,
        "19": 293762,
        "45": 779103,
    },
    "ESP::CT": {
        "08": 6028373,
        "17": 840086,
        "25": 467938,
        "43": 897391,
    },
    "ESP::VC": {
        "03": 2099866,
        "12": 647819,
        "46": 2827263,
    },
    "ESP::EX": {
        "06": 667584,
        "10": 388265,
    },
    "ESP::GA": {
        "15": 1146768,
        "27": 328547,
        "32": 307119,
        "36": 952060,
    },
    "ESP::PV": {
        "01": 345912,
        "20": 736532,
        "48": 1174948,
    },
}

EXPECTED_SINGLE_OR_UNPARTITIONED = {
    "ESP::AS",
    "ESP::IB",
    "ESP::CB",
    "ESP::MD",
    "ESP::MC",
    "ESP::NC",
    "ESP::RI",
    "ESP::CE",
    "ESP::ML",
}


def _catalog() -> dict:
    logger.info("_catalog")
    return load_yaml(
        ROOT / "config/engine/fractal_region_catalog_v1.yaml"
    )


def _materialization_config() -> dict:
    logger.info("_materialization_config")
    return load_yaml(
        ROOT / "config/engine/fractal_materialization_v1.yaml"
    )


def _manifest():
    logger.info("_manifest")
    parameters = load_yaml(
        ROOT / "config/engine/parameter_registry_v1.yaml"
    )
    return build_manifest(
        run_id="spain-l3-catalog-test",
        created_at="2026-09-25T00:00:00+00:00",
        engine_version="0.34.5",
        git_commit="TEST",
        snapshot_schema_version="1.0",
        snapshot_bundle_hash=canonical_hash({"test": True}),
        country_file_hashes={"ESP": canonical_hash({"test": True})},
        graph_hash=canonical_hash({"graph": "test"}),
        scenario_id="SCN-ESP-L3-CATALOG",
        scenario_hash=canonical_hash({"scenario": "spain-l3"}),
        parameter_set_id="synthetic_smoke_v1",
        parameter_set_hash=canonical_hash(
            parameters["parameter_sets"]["synthetic_smoke_v1"]
        ),
        calibration_version="UNSCALED_SYNTHETIC",
        rng_master_seed=3450,
        rng_algorithm="PCG64",
        time_step_days=1,
        start_date="2026-09-25",
        horizon_days=10,
        enabled_modules=("fractal_materialization",),
        normalization_version="test",
        execution_order_version="EXEC_ORDER_V1",
    )


def _ct_parent() -> FractalTopologyNode:
    logger.info("_ct_parent")
    return FractalTopologyNode(
        node_id="ESP::CT",
        label="Cataluña",
        parent_node_id="ESP",
        level="L2_REGION",
        created_day=1,
        refinement_action_id="expand-esp-l2",
        refinement_reason="test",
        source_variables=("public_order_stress",),
        initialization_weight=0.165099140914,
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
        catalog_source_id="ES-INE-ECP-L2-2026",
        catalog_child_id="ESP::CT",
        lineage_generation=1,
        lineage_policy_id="FRACTAL_TOPOLOGY_GENERATION_V1",
    )


def _ct_expand_action() -> FractalRefinementActionProposal:
    logger.info("_ct_expand_action")
    return FractalRefinementActionProposal(
        action_id="expand-esp-ct-l3",
        node_id="ESP::CT",
        day=2,
        action="EXPAND",
        from_level="L2_REGION",
        to_level="L3_METRO_OR_LOGISTICS_AREA",
        refinement_pressure=0.9,
        threshold=0.62,
        persistence_required=1,
        persistence_observed=1,
        refinement_reason="localized_stress",
        component_scores=(),
        source_variables=("public_order_stress",),
        equation_id="REFINEMENT_TRIGGER_V1",
        parameter_id="FRACTAL_REFINEMENT_SYN_V1",
        initialization_weight_policy_id="FRACTAL_CHILD_INIT_WEIGHTS_V1",
        inherited_uncertainty_policy_id="FRACTAL_UNCERTAINTY_WIDENING_V1",
        aggregation_rule_id="FRACTAL_PARENT_REAGGREGATION_V1",
    )


def test_spanish_l3_catalog_contains_exact_multi_province_parent_set() -> None:
    logger.info(
        "test_spanish_l3_catalog_contains_exact_multi_province_parent_set"
    )
    l3_parent_ids = {
        parent_id
        for parent_id in _catalog()["parents"]
        if parent_id.startswith("ESP::")
    }
    assert l3_parent_ids == set(EXPECTED_MULTI_PROVINCE)
    assert l3_parent_ids.isdisjoint(EXPECTED_SINGLE_OR_UNPARTITIONED)


def test_spanish_l3_counts_weights_and_parent_totals_reconcile() -> None:
    logger.info(
        "test_spanish_l3_counts_weights_and_parent_totals_reconcile"
    )
    parents = _catalog()["parents"]

    for parent_id, expected in sorted(EXPECTED_MULTI_PROVINCE.items()):
        parent = parents[parent_id]
        assert parent["source_id"] == "ES-INE-ECP-PROVINCES-2026"
        assert parent["topology_source_id"] == "EU-EUROSTAT-NUTS-2024"
        assert parent["administrative_level"] == "province"
        assert parent["weight_reference_date"] == "2026-07-01"
        assert parent["weight_quality"] == "official_provisional"

        children = parent["children"]
        assert 2 <= len(children) <= 20
        observed = {
            item["child_id"].rsplit("::", 1)[1]: int(
                item["population_reference_count"]
            )
            for item in children
        }
        assert observed == expected

        total = sum(expected.values())
        assert int(parent["population_reference_total"]) == total
        assert sum(observed.values()) == total

        weights = [
            float(item["initialization_weight"])
            for item in children
        ]
        assert math.isclose(
            math.fsum(weights),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        for item in children:
            count = int(item["population_reference_count"])
            expected_weight = count / total
            assert math.isclose(
                float(item["initialization_weight"]),
                expected_weight,
                rel_tol=0.0,
                abs_tol=1e-12,
            )


def test_spanish_l3_ids_use_official_two_digit_province_codes() -> None:
    logger.info(
        "test_spanish_l3_ids_use_official_two_digit_province_codes"
    )
    parents = _catalog()["parents"]
    observed_codes: set[str] = set()

    for parent_id in sorted(EXPECTED_MULTI_PROVINCE):
        for child in parents[parent_id]["children"]:
            child_id = child["child_id"]
            assert child_id.startswith(f"{parent_id}::")
            code = child_id.rsplit("::", 1)[1]
            assert len(code) == 2
            assert code.isdigit()
            assert "::g" not in child_id.lower()
            assert code not in observed_codes
            observed_codes.add(code)

    expected_codes = {
        code
        for province_map in EXPECTED_MULTI_PROVINCE.values()
        for code in province_map
    }
    assert observed_codes == expected_codes
    assert len(observed_codes) == 43


def test_production_catalog_materializes_catalonia_to_four_l3_provinces() -> None:
    logger.info(
        "test_production_catalog_materializes_catalonia_to_four_l3_provinces"
    )
    topology = FractalTopologyState(
        last_committed_day=1,
        nodes=(_ct_parent(),),
    )
    persistence = FractalRefinementPersistenceState(
        node_id="ESP::CT",
        current_level="L2_REGION",
        last_evaluated_day=2,
        expand_streak=1,
        collapse_streak=0,
    )
    trace = TraceLedger()

    after, persistence_after, record = materialize_next_level(
        action=_ct_expand_action(),
        persistence=persistence,
        topology=topology,
        child_catalog=_catalog(),
        materialization_config=_materialization_config(),
        manifest=_manifest(),
        trace=trace,
    )

    children = after.active_children("ESP::CT")
    assert persistence_after.current_level == (
        "L3_METRO_OR_LOGISTICS_AREA"
    )
    assert record.lineage_generation == 1
    assert set(record.child_node_ids) == {
        "ESP::CT::08",
        "ESP::CT::17",
        "ESP::CT::25",
        "ESP::CT::43",
    }
    assert {item.catalog_child_id for item in children} == set(
        record.child_node_ids
    )
    assert all(
        item.catalog_source_id == "ES-INE-ECP-PROVINCES-2026"
        for item in children
    )
    assert all(
        item.level == "L3_METRO_OR_LOGISTICS_AREA"
        and item.parent_node_id == "ESP::CT"
        for item in children
    )
