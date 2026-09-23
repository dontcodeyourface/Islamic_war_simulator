from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML document and require a mapping root."""
    logger.info("load_yaml path=%s", path)
    resolved = Path(path)
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping root in {resolved}")
    return data


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize data deterministically for hashing/replay."""
    logger.info("canonical_json_bytes type=%s", type(value).__name__)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    """Return SHA-256 over deterministic JSON serialization."""
    logger.info("canonical_hash type=%s", type(value).__name__)
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    """Return SHA-256 for raw file bytes."""
    logger.info("file_sha256 path=%s", path)
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_path(root: dict[str, Any], dotted_path: str) -> Any:
    """Resolve a dotted path in nested mappings."""
    logger.info("get_path dotted_path=%s", dotted_path)
    current: Any = root
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise KeyError(dotted_path)
        current = current[key]
    return current


def get_value(root: dict[str, Any], dotted_path: str, default: Any = None) -> Any:
    """Resolve Snapshot datum records and return their value field when present."""
    logger.info("get_value dotted_path=%s", dotted_path)
    try:
        current = get_path(root, dotted_path)
    except KeyError:
        return default
    if isinstance(current, dict) and "value" in current:
        return current["value"]
    return current
