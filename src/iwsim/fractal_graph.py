from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_runtime import FractalRuntimeAuthorityNode, FractalRuntimePlan
from .graph import (
    CANONICAL_CHANNELS,
    DIRECTED_CHANNELS,
    SYMMETRIC_CHANNELS,
    CountryGraph,
    DirectedChannelValue,
    GraphEdge,
    SymmetricChannelValue,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalGraphNode:
    runtime_node_id: str
    level: str
    parent_node_id: str | None
    catalog_node_id: str
    lineage_generation: int | None
    authority_scope: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalGraphNode.to_dict node=%s level=%s",
            self.runtime_node_id,
            self.level,
        )
        return {
            "runtime_node_id": self.runtime_node_id,
            "level": self.level,
            "parent_node_id": self.parent_node_id,
            "catalog_node_id": self.catalog_node_id,
            "lineage_generation": self.lineage_generation,
            "authority_scope": self.authority_scope,
        }


@dataclass(frozen=True)
class FractalChannelProjectionRecord:
    channel: str
    direction: str
    mode: str
    source_value: float | None
    projection_factor: float | None
    projected_value: float | None
    source_parameter_id: str | None
    projection_parameter_id: str | None
    evidence_id: str | None

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalChannelProjectionRecord.to_dict channel=%s direction=%s mode=%s",
            self.channel,
            self.direction,
            self.mode,
        )
        return {
            "channel": self.channel,
            "direction": self.direction,
            "mode": self.mode,
            "source_value": self.source_value,
            "projection_factor": self.projection_factor,
            "projected_value": self.projected_value,
            "source_parameter_id": self.source_parameter_id,
            "projection_parameter_id": self.projection_parameter_id,
            "evidence_id": self.evidence_id,
        }


@dataclass(frozen=True)
class FractalGraphEdge:
    a: str
    b: str
    relation_type: str
    parent_edge_id: str | None
    distance_km: float | None
    direct_land_border: bool | None
    symmetric_channels: tuple[SymmetricChannelValue, ...]
    directed_channels: tuple[DirectedChannelValue, ...]
    projection_records: tuple[FractalChannelProjectionRecord, ...]
    metadata: tuple[tuple[str, Any], ...]

    def edge_id(self) -> str:
        logger.info("FractalGraphEdge.edge_id a=%s b=%s", self.a, self.b)
        return "--".join(sorted((self.a, self.b)))

    def _validate_endpoints(self, source: str, target: str) -> None:
        logger.info(
            "FractalGraphEdge._validate_endpoints edge=%s source=%s target=%s",
            self.edge_id(),
            source,
            target,
        )
        if source == target:
            raise ValueError("source and target must differ")
        if {source, target} != {self.a, self.b}:
            raise ValueError(
                f"{source}->{target} does not match edge {self.a}/{self.b}"
            )

    def channel(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> float | None:
        logger.info(
            "FractalGraphEdge.channel edge=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)
        for channel in self.symmetric_channels:
            if channel.name == channel_name:
                return channel.value
        for channel in self.directed_channels:
            if channel.name == channel_name:
                return (
                    channel.a_to_b
                    if source == self.a and target == self.b
                    else channel.b_to_a
                )
        raise KeyError(channel_name)

    def channel_parameter_id(
        self,
        source: str,
        target: str,
        channel_name: str,
    ) -> str | None:
        logger.info(
            "FractalGraphEdge.channel_parameter_id edge=%s source=%s target=%s channel=%s",
            self.edge_id(),
            source,
            target,
            channel_name,
        )
        self._validate_endpoints(source, target)
        for channel in self.symmetric_channels:
            if channel.name == channel_name:
                return channel.parameter_id
        for channel in self.directed_channels:
            if channel.name == channel_name:
                return (
                    channel.parameter_id_a_to_b
                    if source == self.a and target == self.b
                    else channel.parameter_id_b_to_a
                )
        raise KeyError(channel_name)

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalGraphEdge.to_dict edge=%s relation=%s",
            self.edge_id(),
            self.relation_type,
        )
        return {
            "edge_id": self.edge_id(),
            "a": self.a,
            "b": self.b,
            "relation_type": self.relation_type,
            "parent_edge_id": self.parent_edge_id,
            "distance_km": self.distance_km,
            "direct_land_border": self.direct_land_border,
            "symmetric_channels": {
                item.name: {
                    "value": item.value,
                    "parameter_id": item.parameter_id,
                }
                for item in sorted(
                    self.symmetric_channels,
                    key=lambda value: value.name,
                )
            },
            "directed_channels": {
                item.name: {
                    "a_to_b": item.a_to_b,
                    "b_to_a": item.b_to_a,
                    "parameter_id_a_to_b": item.parameter_id_a_to_b,
                    "parameter_id_b_to_a": item.parameter_id_b_to_a,
                }
                for item in sorted(
                    self.directed_channels,
                    key=lambda value: value.name,
                )
            },
            "projection_records": [
                item.to_dict()
                for item in sorted(
                    self.projection_records,
                    key=lambda value: (value.channel, value.direction),
                )
            ],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class FractalProjectedGraph:
    schema_version: str
    policy_id: str
    day: int
    country_graph_hash: str
    runtime_plan_hash: str
    projection_config_hash: str
    regional_graph_data_hash: str
    nodes: tuple[FractalGraphNode, ...]
    edges: tuple[FractalGraphEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalProjectedGraph.to_dict day=%s nodes=%s edges=%s",
            self.day,
            len(self.nodes),
            len(self.edges),
        )
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "day": self.day,
            "country_graph_hash": self.country_graph_hash,
            "runtime_plan_hash": self.runtime_plan_hash,
            "projection_config_hash": self.projection_config_hash,
            "regional_graph_data_hash": self.regional_graph_data_hash,
            "nodes": [
                item.to_dict()
                for item in sorted(
                    self.nodes,
                    key=lambda value: value.runtime_node_id,
                )
            ],
            "edges": [
                item.to_dict()
                for item in sorted(
                    self.edges,
                    key=lambda value: value.edge_id(),
                )
            ],
        }

    def graph_hash(self) -> str:
        logger.info(
            "FractalProjectedGraph.graph_hash day=%s policy=%s",
            self.day,
            self.policy_id,
        )
        return canonical_hash(self.to_dict())

    def edge(self, a: str, b: str) -> FractalGraphEdge:
        logger.info("FractalProjectedGraph.edge a=%s b=%s", a, b)
        edge_id = "--".join(sorted((a, b)))
        for edge in self.edges:
            if edge.edge_id() == edge_id:
                return edge
        raise KeyError(edge_id)

    def validate(self) -> None:
        logger.info(
            "FractalProjectedGraph.validate nodes=%s edges=%s",
            len(self.nodes),
            len(self.edges),
        )
        node_ids = [item.runtime_node_id for item in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate fractal graph runtime node")
        expected_edges = len(node_ids) * (len(node_ids) - 1) // 2
        if len(self.edges) != expected_edges:
            raise ValueError(
                "Incomplete fractal runtime pair coverage: "
                f"expected={expected_edges} actual={len(self.edges)}"
            )

        expected_projection_keys = {
            *((name, "SYMMETRIC") for name in SYMMETRIC_CHANNELS),
            *((name, "A_TO_B") for name in DIRECTED_CHANNELS),
            *((name, "B_TO_A") for name in DIRECTED_CHANNELS),
        }
        seen_edges: set[str] = set()
        node_set = set(node_ids)
        for edge in self.edges:
            if edge.a == edge.b:
                raise ValueError("Fractal graph self edge forbidden")
            if edge.a not in node_set or edge.b not in node_set:
                raise ValueError(
                    f"Fractal edge {edge.edge_id()} references unknown node"
                )
            if edge.edge_id() in seen_edges:
                raise ValueError(
                    f"Duplicate fractal graph edge {edge.edge_id()}"
                )
            seen_edges.add(edge.edge_id())

            sym_names = {
                item.name for item in edge.symmetric_channels
            }
            dir_names = {
                item.name for item in edge.directed_channels
            }
            if sym_names != set(SYMMETRIC_CHANNELS):
                raise ValueError(
                    f"Fractal edge {edge.edge_id()} symmetric channel coverage mismatch"
                )
            if dir_names != set(DIRECTED_CHANNELS):
                raise ValueError(
                    f"Fractal edge {edge.edge_id()} directed channel coverage mismatch"
                )

            for item in edge.symmetric_channels:
                _validate_optional_unit_interval(
                    value=item.value,
                    label=f"{edge.edge_id()}:{item.name}",
                )
            for item in edge.directed_channels:
                _validate_optional_unit_interval(
                    value=item.a_to_b,
                    label=f"{edge.edge_id()}:{item.name}:a_to_b",
                )
                _validate_optional_unit_interval(
                    value=item.b_to_a,
                    label=f"{edge.edge_id()}:{item.name}:b_to_a",
                )

            keys = {
                (item.channel, item.direction)
                for item in edge.projection_records
            }
            if keys != expected_projection_keys:
                raise ValueError(
                    f"Fractal edge {edge.edge_id()} projection record coverage mismatch"
                )


def _validate_optional_unit_interval(
    *,
    value: float | None,
    label: str,
) -> None:
    logger.info(
        "_validate_optional_unit_interval label=%s value=%s",
        label,
        value,
    )
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} outside [0,1]: {value}")


def _validate_projection_config(
    config: dict[str, Any],
) -> dict[str, Any]:
    logger.info("_validate_projection_config")
    mode = config.get("mode", {})
    required_true = (
        "enabled",
        "projection_is_read_only",
        "complete_runtime_pair_coverage_required",
        "refined_l1_parent_excluded_from_regional_graph",
        "coarse_l1_edges_copy_exact",
        "stable_catalog_ids_in_data",
        "output_uses_runtime_lineage_ids",
        "unresolved_channel_is_null_not_zero",
        "explicit_regional_evidence_required",
        "country_edge_clone_to_children_forbidden",
        "cross_parent_l2_requires_explicit_edge_data",
    )
    for key in required_true:
        if mode.get(key) is not True:
            raise ValueError(
                f"v0.29 graph projection requires {key}=true"
            )
    if mode.get("graph_execution_allowed") is not False:
        raise ValueError(
            "v0.29 graph projection must remain read-only until v0.30"
        )

    policy_id = str(config.get("policy_id", "")).strip()
    if policy_id != "FRACTAL_GRAPH_PROJECTION_V1":
        raise ValueError("Unsupported fractal graph projection policy")

    rules = config.get("projection_rules", {})
    required_rule_true = (
        "parent_scaled_requires_distinct_parent_country_edge",
        "unresolved_parent_channel_remains_null_after_scaling",
        "pair_distance_requires_explicit_regional_data",
        "pair_land_border_requires_explicit_regional_data",
    )
    for key in required_rule_true:
        if rules.get(key) is not True:
            raise ValueError(
                f"v0.29 graph projection rule {key} must be true"
            )
    if rules.get("omitted_l2_channel_mode") != "unresolved":
        raise ValueError(
            "v0.29 omitted L2 graph channels must remain unresolved"
        )
    bounds = rules.get("explicit_value_bounds")
    factor_bounds = rules.get("parent_scaled_factor_bounds")
    if bounds != [0.0, 1.0]:
        raise ValueError(
            "v0.29 explicit graph values must remain bounded to [0,1]"
        )
    if factor_bounds != [0.0, 1.0]:
        raise ValueError(
            "v0.29 parent-scaled factors must remain bounded to [0,1]"
        )

    raw_modes = config.get("channel_modes")
    if not isinstance(raw_modes, dict):
        raise ValueError("fractal graph channel_modes must be a mapping")
    if set(raw_modes) != set(CANONICAL_CHANNELS):
        raise ValueError(
            "fractal graph channel_modes must cover canonical channels"
        )
    allowed_modes: dict[str, tuple[str, ...]] = {}
    known_modes = {"explicit", "parent_scaled", "unresolved"}
    for channel in CANONICAL_CHANNELS:
        values = tuple(str(item) for item in raw_modes[channel])
        if not values or set(values) - known_modes:
            raise ValueError(
                f"Invalid projection modes for {channel}: {values}"
            )
        allowed_modes[channel] = values

    safety = config.get("safety", {})
    required_safety_true = (
        "regional_graph_is_aggregate_connectivity_not_operational_route",
    )
    for key in required_safety_true:
        if safety.get(key) is not True:
            raise ValueError(
                f"Fractal graph safety invariant {key} must be true"
            )
    forbidden = (
        "population_identity_must_not_create_extremist_edge",
        "religious_similarity_must_not_create_extremist_edge",
        "ethnicity_must_not_create_criminal_edge",
        "political_identity_must_not_create_graph_edge",
    )
    if any(safety.get(key) is not True for key in forbidden):
        raise ValueError("Fractal graph identity-safety contract missing")
    for key in (
        "tactical_target_selection",
        "weapon_selection",
        "route_planning",
        "operational_execution",
    ):
        if safety.get(key) is not False:
            raise ValueError(
                f"Fractal graph safety invariant {key} must remain false"
            )

    return {
        "policy_id": policy_id,
        "allowed_modes": allowed_modes,
        "copy_policy_id": str(
            config["coarse_l1"]["copy_policy_id"]
        ),
    }


def _catalog_parent_index(
    region_catalog: dict[str, Any],
) -> dict[str, str]:
    logger.info("_catalog_parent_index")
    parents = region_catalog.get("parents")
    if not isinstance(parents, dict):
        raise ValueError("fractal region catalog parents must be a mapping")
    result: dict[str, str] = {}
    for parent_id, payload in sorted(parents.items()):
        if not isinstance(payload, dict):
            raise ValueError(
                f"Regional catalog parent {parent_id} must be a mapping"
            )
        children = payload.get("children", [])
        if not isinstance(children, list):
            raise ValueError(
                f"Regional catalog parent {parent_id} children must be a list"
            )
        for child in children:
            child_id = str(child.get("child_id", ""))
            if not child_id:
                raise ValueError(
                    f"Regional catalog parent {parent_id} has empty child ID"
                )
            if child_id in result:
                raise ValueError(
                    f"Duplicate stable regional catalog ID {child_id}"
                )
            result[child_id] = str(parent_id)
    return result


def _active_runtime_nodes(
    plan: FractalRuntimePlan,
) -> tuple[FractalGraphNode, ...]:
    logger.info(
        "_active_runtime_nodes day=%s plan_nodes=%s",
        plan.day,
        len(plan.nodes),
    )
    nodes: list[FractalGraphNode] = []
    for item in plan.nodes:
        include = (
            item.level == "L2_REGION"
            or (
                item.level == "L1_COUNTRY"
                and item.authority_scope == "FULL"
            )
        )
        if not include:
            continue
        nodes.append(
            FractalGraphNode(
                runtime_node_id=item.runtime_node_id,
                level=item.level,
                parent_node_id=item.parent_node_id,
                catalog_node_id=item.catalog_node_id,
                lineage_generation=item.lineage_generation,
                authority_scope=item.authority_scope,
            )
        )
    return tuple(
        sorted(nodes, key=lambda value: value.runtime_node_id)
    )


def _runtime_parent_id(node: FractalGraphNode) -> str:
    logger.info(
        "_runtime_parent_id node=%s level=%s",
        node.runtime_node_id,
        node.level,
    )
    if node.level == "L1_COUNTRY":
        return node.runtime_node_id
    if node.parent_node_id is None:
        raise ValueError(
            f"L2 runtime node {node.runtime_node_id} has no parent"
        )
    return node.parent_node_id


def _relation_type(
    a: FractalGraphNode,
    b: FractalGraphNode,
) -> str:
    logger.info(
        "_relation_type a=%s b=%s",
        a.runtime_node_id,
        b.runtime_node_id,
    )
    if a.level == "L1_COUNTRY" and b.level == "L1_COUNTRY":
        return "COARSE_L1"
    if a.level == "L2_REGION" and b.level == "L2_REGION":
        return (
            "INTERNAL_L2"
            if a.parent_node_id == b.parent_node_id
            else "CROSS_PARENT_L2"
        )
    return "L2_TO_COARSE_L1"


def _endpoint_key(endpoint: dict[str, Any]) -> tuple[str, str]:
    logger.info("_endpoint_key endpoint=%s", endpoint)
    if not isinstance(endpoint, dict):
        raise ValueError("Regional graph endpoint must be a mapping")
    kind = str(endpoint.get("kind", ""))
    node_id = str(endpoint.get("id", ""))
    if kind not in {"country", "regional_catalog"} or not node_id:
        raise ValueError(
            f"Invalid regional graph endpoint {endpoint}"
        )
    return kind, node_id


def _validate_graph_data(
    *,
    data: dict[str, Any],
    country_graph: CountryGraph,
    region_catalog: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    logger.info("_validate_graph_data")
    catalog_parent = _catalog_parent_index(region_catalog)
    country_ids = {item.iso3 for item in country_graph.nodes}
    raw_edges = data.get("edges")
    if not isinstance(raw_edges, list):
        raise ValueError("fractal region graph edges must be a list")

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    for raw in raw_edges:
        if not isinstance(raw, dict):
            raise ValueError("Regional graph edge must be a mapping")
        a_key = _endpoint_key(raw.get("a", {}))
        b_key = _endpoint_key(raw.get("b", {}))
        if a_key == b_key:
            raise ValueError("Regional graph self edge forbidden")
        pair = tuple(sorted((a_key, b_key)))
        if pair in seen:
            raise ValueError(
                f"Duplicate regional graph data edge {pair}"
            )
        seen.add(pair)

        for kind, node_id in (a_key, b_key):
            if kind == "country" and node_id not in country_ids:
                raise ValueError(
                    f"Unknown regional graph country endpoint {node_id}"
                )
            if (
                kind == "regional_catalog"
                and node_id not in catalog_parent
            ):
                raise ValueError(
                    f"Unknown regional catalog endpoint {node_id}"
                )

        if a_key[0] == "country" and b_key[0] == "country":
            raise ValueError(
                "Country-country graph overrides are forbidden in v0.29"
            )
        if a_key[0] != b_key[0]:
            regional = a_key if a_key[0] == "regional_catalog" else b_key
            country = a_key if a_key[0] == "country" else b_key
            if catalog_parent[regional[1]] == country[1]:
                raise ValueError(
                    "Regional-to-own-parent country graph edge is forbidden"
                )

        source_id = str(raw.get("source_id", "")).strip()
        if not source_id:
            raise ValueError(
                f"Regional graph edge {pair} requires source_id"
            )
        normalized.append(
            {
                **raw,
                "_a_key": a_key,
                "_b_key": b_key,
                "_source_id": source_id,
            }
        )
    return tuple(normalized)


def _resolve_endpoint(
    *,
    key: tuple[str, str],
    active_country_ids: set[str],
    active_catalog_to_runtime: dict[str, str],
) -> str | None:
    logger.info("_resolve_endpoint key=%s", key)
    kind, node_id = key
    if kind == "country":
        return node_id if node_id in active_country_ids else None
    return active_catalog_to_runtime.get(node_id)


def _explicit_edge_index(
    *,
    raw_edges: tuple[dict[str, Any], ...],
    runtime_nodes: dict[str, FractalGraphNode],
) -> dict[frozenset[str], dict[str, Any]]:
    logger.info(
        "_explicit_edge_index raw_edges=%s runtime_nodes=%s",
        len(raw_edges),
        len(runtime_nodes),
    )
    active_country_ids = {
        node.runtime_node_id
        for node in runtime_nodes.values()
        if node.level == "L1_COUNTRY"
    }
    active_catalog_to_runtime = {
        node.catalog_node_id: node.runtime_node_id
        for node in runtime_nodes.values()
        if node.level == "L2_REGION"
    }
    if len(active_catalog_to_runtime) != len(
        [
            node
            for node in runtime_nodes.values()
            if node.level == "L2_REGION"
        ]
    ):
        raise ValueError(
            "Active regional catalog IDs must map one-to-one to runtime nodes"
        )

    result: dict[frozenset[str], dict[str, Any]] = {}
    for raw in raw_edges:
        runtime_a = _resolve_endpoint(
            key=raw["_a_key"],
            active_country_ids=active_country_ids,
            active_catalog_to_runtime=active_catalog_to_runtime,
        )
        runtime_b = _resolve_endpoint(
            key=raw["_b_key"],
            active_country_ids=active_country_ids,
            active_catalog_to_runtime=active_catalog_to_runtime,
        )
        if runtime_a is None or runtime_b is None:
            continue
        if runtime_a == runtime_b:
            raise ValueError(
                "Regional graph data resolved to a self edge"
            )
        key = frozenset((runtime_a, runtime_b))
        if key in result:
            raise ValueError(
                f"Multiple graph-data records resolve to {sorted(key)}"
            )
        result[key] = {
            **raw,
            "_runtime_a": runtime_a,
            "_runtime_b": runtime_b,
        }
    return result


def _country_source_edge(
    *,
    country_graph: CountryGraph,
    a: FractalGraphNode,
    b: FractalGraphNode,
) -> GraphEdge | None:
    logger.info(
        "_country_source_edge a=%s b=%s",
        a.runtime_node_id,
        b.runtime_node_id,
    )
    parent_a = _runtime_parent_id(a)
    parent_b = _runtime_parent_id(b)
    if parent_a == parent_b:
        return None
    return country_graph.edge(parent_a, parent_b)


def _projection_spec(
    *,
    raw_edge: dict[str, Any] | None,
    channel: str,
    direction: str,
    output_a: str,
    output_b: str,
) -> tuple[dict[str, Any], str | None]:
    logger.info(
        "_projection_spec channel=%s direction=%s has_edge=%s",
        channel,
        direction,
        raw_edge is not None,
    )
    if raw_edge is None:
        return {"mode": "unresolved"}, None
    evidence_default = raw_edge["_source_id"]

    if channel in SYMMETRIC_CHANNELS:
        raw = raw_edge.get("symmetric_channels", {}).get(channel)
        if raw is None:
            return {"mode": "unresolved"}, evidence_default
        if not isinstance(raw, dict):
            raise ValueError(
                f"Symmetric projection {channel} must be a mapping"
            )
        return raw, str(raw.get("evidence_id") or evidence_default)

    raw_channel = raw_edge.get("directed_channels", {}).get(channel)
    if raw_channel is None:
        return {"mode": "unresolved"}, evidence_default
    if not isinstance(raw_channel, dict):
        raise ValueError(
            f"Directed projection {channel} must be a mapping"
        )

    runtime_a = raw_edge["_runtime_a"]
    runtime_b = raw_edge["_runtime_b"]
    if direction == "A_TO_B":
        source = output_a
        target = output_b
    elif direction == "B_TO_A":
        source = output_b
        target = output_a
    else:
        raise ValueError(f"Invalid directed projection direction {direction}")

    if source == runtime_a and target == runtime_b:
        raw = raw_channel.get("a_to_b")
    elif source == runtime_b and target == runtime_a:
        raw = raw_channel.get("b_to_a")
    else:
        raise ValueError("Projection data/runtime orientation mismatch")
    if raw is None:
        return {"mode": "unresolved"}, evidence_default
    if not isinstance(raw, dict):
        raise ValueError(
            f"Directed projection {channel}:{direction} must be a mapping"
        )
    return raw, str(raw.get("evidence_id") or evidence_default)


def _source_channel(
    *,
    source_edge: GraphEdge | None,
    source_parent: str,
    target_parent: str,
    channel: str,
) -> tuple[float | None, str | None]:
    logger.info(
        "_source_channel source_parent=%s target_parent=%s channel=%s has_edge=%s",
        source_parent,
        target_parent,
        channel,
        source_edge is not None,
    )
    if source_edge is None:
        return None, None
    return (
        source_edge.channel(source_parent, target_parent, channel),
        source_edge.channel_parameter_id(
            source_parent,
            target_parent,
            channel,
        ),
    )


def _project_value(
    *,
    channel: str,
    direction: str,
    spec: dict[str, Any],
    evidence_id: str | None,
    source_value: float | None,
    source_parameter_id: str | None,
    allowed_modes: dict[str, tuple[str, ...]],
) -> tuple[float | None, str | None, FractalChannelProjectionRecord]:
    logger.info(
        "_project_value channel=%s direction=%s mode=%s",
        channel,
        direction,
        spec.get("mode", "unresolved"),
    )
    mode = str(spec.get("mode", "unresolved"))
    if mode not in allowed_modes[channel]:
        raise ValueError(
            f"Projection mode {mode} is not allowed for {channel}"
        )

    factor: float | None = None
    projected: float | None
    projection_parameter_id = (
        str(spec["parameter_id"])
        if spec.get("parameter_id") is not None
        else None
    )

    if mode == "unresolved":
        projected = None
        projection_parameter_id = None
    elif mode == "explicit":
        if "value" not in spec:
            raise ValueError(
                f"Explicit projection {channel}:{direction} requires value"
            )
        projected = float(spec["value"])
        _validate_optional_unit_interval(
            value=projected,
            label=f"{channel}:{direction}:explicit",
        )
    elif mode == "parent_scaled":
        if "factor" not in spec:
            raise ValueError(
                f"parent_scaled projection {channel}:{direction} requires factor"
            )
        factor = float(spec["factor"])
        _validate_optional_unit_interval(
            value=factor,
            label=f"{channel}:{direction}:factor",
        )
        projected = (
            None
            if source_value is None
            else source_value * factor
        )
    else:
        raise ValueError(f"Unknown projection mode {mode}")

    output_parameter_id = (
        projection_parameter_id
        if projection_parameter_id is not None
        else source_parameter_id
    )
    if projected is None and mode == "unresolved":
        output_parameter_id = None

    record = FractalChannelProjectionRecord(
        channel=channel,
        direction=direction,
        mode=mode.upper(),
        source_value=source_value,
        projection_factor=factor,
        projected_value=projected,
        source_parameter_id=source_parameter_id,
        projection_parameter_id=projection_parameter_id,
        evidence_id=evidence_id,
    )
    return projected, output_parameter_id, record


def _copy_coarse_edge(
    *,
    source: GraphEdge,
    a: FractalGraphNode,
    b: FractalGraphNode,
    copy_policy_id: str,
) -> FractalGraphEdge:
    logger.info(
        "_copy_coarse_edge source=%s a=%s b=%s",
        source.edge_id(),
        a.runtime_node_id,
        b.runtime_node_id,
    )
    records: list[FractalChannelProjectionRecord] = []
    for channel in SYMMETRIC_CHANNELS:
        value = source.channel(a.runtime_node_id, b.runtime_node_id, channel)
        parameter_id = source.channel_parameter_id(
            a.runtime_node_id,
            b.runtime_node_id,
            channel,
        )
        records.append(
            FractalChannelProjectionRecord(
                channel=channel,
                direction="SYMMETRIC",
                mode="COARSE_L1_COPY",
                source_value=value,
                projection_factor=None,
                projected_value=value,
                source_parameter_id=parameter_id,
                projection_parameter_id=None,
                evidence_id=copy_policy_id,
            )
        )
    for channel in DIRECTED_CHANNELS:
        for direction, source_id, target_id in (
            ("A_TO_B", a.runtime_node_id, b.runtime_node_id),
            ("B_TO_A", b.runtime_node_id, a.runtime_node_id),
        ):
            value = source.channel(source_id, target_id, channel)
            parameter_id = source.channel_parameter_id(
                source_id,
                target_id,
                channel,
            )
            records.append(
                FractalChannelProjectionRecord(
                    channel=channel,
                    direction=direction,
                    mode="COARSE_L1_COPY",
                    source_value=value,
                    projection_factor=None,
                    projected_value=value,
                    source_parameter_id=parameter_id,
                    projection_parameter_id=None,
                    evidence_id=copy_policy_id,
                )
            )

    return FractalGraphEdge(
        a=a.runtime_node_id,
        b=b.runtime_node_id,
        relation_type="COARSE_L1",
        parent_edge_id=source.edge_id(),
        distance_km=source.distance_km,
        direct_land_border=source.direct_land_border,
        symmetric_channels=source.symmetric_channels,
        directed_channels=source.directed_channels,
        projection_records=tuple(records),
        metadata=tuple(
            sorted(
                {
                    **dict(source.metadata),
                    "projection_policy": copy_policy_id,
                    "source_country_edge_id": source.edge_id(),
                }.items()
            )
        ),
    )


def _project_l2_edge(
    *,
    country_graph: CountryGraph,
    a: FractalGraphNode,
    b: FractalGraphNode,
    raw_edge: dict[str, Any] | None,
    allowed_modes: dict[str, tuple[str, ...]],
    policy_id: str,
) -> FractalGraphEdge:
    logger.info(
        "_project_l2_edge a=%s b=%s has_data=%s",
        a.runtime_node_id,
        b.runtime_node_id,
        raw_edge is not None,
    )
    source_edge = _country_source_edge(
        country_graph=country_graph,
        a=a,
        b=b,
    )
    parent_a = _runtime_parent_id(a)
    parent_b = _runtime_parent_id(b)
    relation_type = _relation_type(a, b)

    symmetric: list[SymmetricChannelValue] = []
    directed: list[DirectedChannelValue] = []
    records: list[FractalChannelProjectionRecord] = []

    for channel in SYMMETRIC_CHANNELS:
        spec, evidence_id = _projection_spec(
            raw_edge=raw_edge,
            channel=channel,
            direction="SYMMETRIC",
            output_a=a.runtime_node_id,
            output_b=b.runtime_node_id,
        )
        source_value, source_parameter_id = _source_channel(
            source_edge=source_edge,
            source_parent=parent_a,
            target_parent=parent_b,
            channel=channel,
        )
        if (
            str(spec.get("mode", "unresolved")) == "parent_scaled"
            and source_edge is None
        ):
            raise ValueError(
                "parent_scaled projection requires a distinct parent-country "
                f"source edge for {a.runtime_node_id}/{b.runtime_node_id}"
            )
        value, parameter_id, record = _project_value(
            channel=channel,
            direction="SYMMETRIC",
            spec=spec,
            evidence_id=evidence_id,
            source_value=source_value,
            source_parameter_id=source_parameter_id,
            allowed_modes=allowed_modes,
        )
        symmetric.append(
            SymmetricChannelValue(
                name=channel,
                value=value,
                parameter_id=parameter_id,
            )
        )
        records.append(record)

    for channel in DIRECTED_CHANNELS:
        values: dict[str, float | None] = {}
        parameter_ids: dict[str, str | None] = {}
        for direction, source_parent, target_parent in (
            ("A_TO_B", parent_a, parent_b),
            ("B_TO_A", parent_b, parent_a),
        ):
            spec, evidence_id = _projection_spec(
                raw_edge=raw_edge,
                channel=channel,
                direction=direction,
                output_a=a.runtime_node_id,
                output_b=b.runtime_node_id,
            )
            source_value, source_parameter_id = _source_channel(
                source_edge=source_edge,
                source_parent=source_parent,
                target_parent=target_parent,
                channel=channel,
            )
            if (
                str(spec.get("mode", "unresolved")) == "parent_scaled"
                and source_edge is None
            ):
                raise ValueError(
                    "parent_scaled projection requires a distinct "
                    "parent-country source edge for "
                    f"{a.runtime_node_id}/{b.runtime_node_id}"
                )
            value, parameter_id, record = _project_value(
                channel=channel,
                direction=direction,
                spec=spec,
                evidence_id=evidence_id,
                source_value=source_value,
                source_parameter_id=source_parameter_id,
                allowed_modes=allowed_modes,
            )
            values[direction] = value
            parameter_ids[direction] = parameter_id
            records.append(record)
        directed.append(
            DirectedChannelValue(
                name=channel,
                a_to_b=values["A_TO_B"],
                b_to_a=values["B_TO_A"],
                parameter_id_a_to_b=parameter_ids["A_TO_B"],
                parameter_id_b_to_a=parameter_ids["B_TO_A"],
            )
        )

    distance_km: float | None = None
    direct_land_border: bool | None = None
    source_id: str | None = None
    if raw_edge is not None:
        source_id = raw_edge["_source_id"]
        if raw_edge.get("distance_km") is not None:
            distance_km = float(raw_edge["distance_km"])
            if not math.isfinite(distance_km) or distance_km < 0.0:
                raise ValueError(
                    "Regional graph distance_km must be finite/non-negative"
                )
        if raw_edge.get("direct_land_border") is not None:
            direct_land_border = bool(
                raw_edge["direct_land_border"]
            )

    land_border_value = next(
        item.value
        for item in symmetric
        if item.name == "land_border"
    )
    if (
        direct_land_border is not None
        and land_border_value is not None
        and land_border_value in {0.0, 1.0}
        and direct_land_border != bool(land_border_value)
    ):
        raise ValueError(
            "Regional direct_land_border disagrees with land_border channel"
        )

    unresolved = tuple(
        sorted(
            item.channel
            if item.direction == "SYMMETRIC"
            else f"{item.channel}:{item.direction}"
            for item in records
            if item.projected_value is None
        )
    )
    return FractalGraphEdge(
        a=a.runtime_node_id,
        b=b.runtime_node_id,
        relation_type=relation_type,
        parent_edge_id=(
            source_edge.edge_id()
            if source_edge is not None
            else None
        ),
        distance_km=distance_km,
        direct_land_border=direct_land_border,
        symmetric_channels=tuple(symmetric),
        directed_channels=tuple(directed),
        projection_records=tuple(records),
        metadata=(
            ("projection_policy_id", policy_id),
            ("regional_graph_source_id", source_id),
            ("unresolved_projections", unresolved),
        ),
    )


def build_fractal_projected_graph(
    *,
    country_graph: CountryGraph,
    runtime_plan: FractalRuntimePlan,
    projection_config: dict[str, Any],
    regional_graph_data: dict[str, Any],
    region_catalog: dict[str, Any],
) -> FractalProjectedGraph:
    """Build the deterministic complete runtime graph without executing it."""
    logger.info(
        "build_fractal_projected_graph day=%s country_nodes=%s runtime_nodes=%s",
        runtime_plan.day,
        len(country_graph.nodes),
        len(runtime_plan.nodes),
    )
    country_graph.validate()
    policy = _validate_projection_config(projection_config)
    raw_edges = _validate_graph_data(
        data=regional_graph_data,
        country_graph=country_graph,
        region_catalog=region_catalog,
    )
    nodes = _active_runtime_nodes(runtime_plan)
    runtime_by_id = {
        item.runtime_node_id: item for item in nodes
    }
    explicit = _explicit_edge_index(
        raw_edges=raw_edges,
        runtime_nodes=runtime_by_id,
    )

    country_ids = {item.iso3 for item in country_graph.nodes}
    coarse_runtime_ids = {
        item.runtime_node_id
        for item in nodes
        if item.level == "L1_COUNTRY"
    }
    unknown_coarse = coarse_runtime_ids - country_ids
    if unknown_coarse:
        raise ValueError(
            f"Runtime plan has L1 graph nodes absent from country graph: {sorted(unknown_coarse)}"
        )

    edges: list[FractalGraphEdge] = []
    sorted_ids = sorted(runtime_by_id)
    for index, a_id in enumerate(sorted_ids):
        for b_id in sorted_ids[index + 1 :]:
            a = runtime_by_id[a_id]
            b = runtime_by_id[b_id]
            if a.level == "L1_COUNTRY" and b.level == "L1_COUNTRY":
                source = country_graph.edge(a_id, b_id)
                edges.append(
                    _copy_coarse_edge(
                        source=source,
                        a=a,
                        b=b,
                        copy_policy_id=policy["copy_policy_id"],
                    )
                )
                continue

            edges.append(
                _project_l2_edge(
                    country_graph=country_graph,
                    a=a,
                    b=b,
                    raw_edge=explicit.get(
                        frozenset((a_id, b_id))
                    ),
                    allowed_modes=policy["allowed_modes"],
                    policy_id=policy["policy_id"],
                )
            )

    graph = FractalProjectedGraph(
        schema_version=str(projection_config["schema_version"]),
        policy_id=policy["policy_id"],
        day=runtime_plan.day,
        country_graph_hash=country_graph.graph_hash(),
        runtime_plan_hash=runtime_plan.plan_hash(),
        projection_config_hash=canonical_hash(projection_config),
        regional_graph_data_hash=canonical_hash(regional_graph_data),
        nodes=nodes,
        edges=tuple(edges),
    )
    graph.validate()
    return graph


def trace_fractal_projected_graph(
    *,
    graph: FractalProjectedGraph,
    phase: str,
    trace: Any,
) -> None:
    logger.info(
        "trace_fractal_projected_graph day=%s phase=%s edges=%s",
        graph.day,
        phase,
        len(graph.edges),
    )
    for edge in sorted(graph.edges, key=lambda item: item.edge_id()):
        trace.append(
            "fractal_graph_projection_edge",
            phase=phase,
            graph_hash=graph.graph_hash(),
            **edge.to_dict(),
        )
    trace.append(
        "fractal_projected_graph",
        phase=phase,
        graph_hash=graph.graph_hash(),
        **graph.to_dict(),
    )
