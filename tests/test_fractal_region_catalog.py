from __future__ import annotations

import logging
import math
from pathlib import Path

from iwsim.config import load_yaml

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "ESP": 19,
    "FRA": 18,
    "DEU": 16,
    "GBR": 4,
    "MAR": 12,
}


def _catalog() -> dict:
    logger.info("_catalog")
    return load_yaml(ROOT / "config/engine/fractal_region_catalog_v1.yaml")


def test_canonical_l2_catalog_covers_snapshot_v1_exactly() -> None:
    logger.info("test_canonical_l2_catalog_covers_snapshot_v1_exactly")
    catalog = _catalog()
    parents = catalog["parents"]
    country_files = {
        path.stem
        for path in (ROOT / "config/countries").glob("*.yaml")
        if not path.name.startswith("_")
    }
    snapshot_iso3 = {
        load_yaml(ROOT / "config/countries" / f"{name}.yaml")["identity"]["iso3"]
        for name in country_files
    }
    assert set(parents) == snapshot_iso3 == set(EXPECTED)


def test_canonical_l2_children_are_complete_namespaced_and_weighted() -> None:
    logger.info(
        "test_canonical_l2_children_are_complete_namespaced_and_weighted"
    )
    for parent_id, parent in _catalog()["parents"].items():
        children = parent["children"]
        assert len(children) == EXPECTED[parent_id]
        ids = [item["child_id"] for item in children]
        assert len(ids) == len(set(ids))
        assert all(item.startswith(f"{parent_id}::") for item in ids)
        weights = [float(item["initialization_weight"]) for item in children]
        assert all(math.isfinite(item) and item > 0.0 for item in weights)
        assert math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-9)
        assert parent["source_id"]
        assert parent["topology_source_id"]
        assert parent["administrative_level"]
        assert parent["weight_reference_date"]
        assert parent["weight_quality"]


def test_catalog_child_ids_never_embed_runtime_generation() -> None:
    logger.info("test_catalog_child_ids_never_embed_runtime_generation")
    for parent in _catalog()["parents"].values():
        for child in parent["children"]:
            assert "::g" not in child["child_id"].lower()
