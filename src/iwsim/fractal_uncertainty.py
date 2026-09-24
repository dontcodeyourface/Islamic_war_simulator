from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from .config import canonical_hash
from .fractal_child_state import FractalChildStateStore
from .fractal_materialization import FractalTopologyNode, FractalTopologyState
from .rng import RNGManager
from .state import EngineState, extract_latent_registry
from .trace import TraceLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FractalUncertaintyRecord:
    variation_id: str
    parent_node_id: str
    day: int
    group_id: str
    rng_stream: str
    draw_indices: tuple[tuple[str, int], ...]
    normalized_offsets: tuple[tuple[str, float], ...]
    variable_amplitudes: tuple[tuple[str, float], ...]
    child_state_hashes_before: tuple[tuple[str, str], ...]
    child_state_hashes_after: tuple[tuple[str, str], ...]
    policy_id: str
    parameter_id: str
    config_hash: str

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalUncertaintyRecord.to_dict variation_id=%s group=%s",
            self.variation_id,
            self.group_id,
        )
        return {
            "variation_id": self.variation_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "group_id": self.group_id,
            "rng_stream": self.rng_stream,
            "draw_indices": dict(self.draw_indices),
            "normalized_offsets": dict(self.normalized_offsets),
            "variable_amplitudes": dict(self.variable_amplitudes),
            "child_state_hashes_before": dict(self.child_state_hashes_before),
            "child_state_hashes_after": dict(self.child_state_hashes_after),
            "policy_id": self.policy_id,
            "parameter_id": self.parameter_id,
            "config_hash": self.config_hash,
        }


@dataclass(frozen=True)
class FractalUncertaintyAuditRecord:
    audit_id: str
    parent_node_id: str
    day: int
    parent_values: tuple[tuple[str, float], ...]
    weighted_child_values: tuple[tuple[str, float], ...]
    max_abs_error: float
    tolerance: float
    preserved: bool

    def to_dict(self) -> dict[str, Any]:
        logger.info(
            "FractalUncertaintyAuditRecord.to_dict audit_id=%s parent=%s",
            self.audit_id,
            self.parent_node_id,
        )
        return {
            "audit_id": self.audit_id,
            "parent_node_id": self.parent_node_id,
            "day": self.day,
            "parent_values": dict(self.parent_values),
            "weighted_child_values": dict(self.weighted_child_values),
            "max_abs_error": self.max_abs_error,
            "tolerance": self.tolerance,
            "preserved": self.preserved,
        }


@dataclass(frozen=True)
class FractalUncertaintyResult:
    store: FractalChildStateStore
    records: tuple[FractalUncertaintyRecord, ...]
    audits: tuple[FractalUncertaintyAuditRecord, ...]


def _parameter_id(profile: str) -> str:
    logger.info("_parameter_id profile=%s", profile)
    if profile == "synthetic_smoke_v1":
        return "FRACTAL_L2_LOCAL_VARIATION_SYN_V1"
    if profile == "calibrated_v1":
        return "FRACTAL_L2_LOCAL_VARIATION_CAL_V1"
    raise ValueError(f"Unknown parameter profile: {profile}")


def _parameter_value(
    parameter_registry: dict[str, Any],
    *,
    profile: str,
    parameter_id: str,
) -> dict[str, Any]:
    logger.info(
        "_parameter_value profile=%s parameter_id=%s",
        profile,
        parameter_id,
    )
    parameter_set = parameter_registry.get("parameter_sets", {}).get(profile)
    if not isinstance(parameter_set, dict):
        raise ValueError(f"Unknown parameter profile: {profile}")
    parameter = parameter_set.get("parameters", {}).get(parameter_id)
    if not isinstance(parameter, dict):
        raise ValueError(
            f"Missing fractal uncertainty parameter {parameter_id} for {profile}"
        )
    value = parameter.get("value")
    if not isinstance(value, dict):
        raise ValueError(
            f"Fractal uncertainty parameter {parameter_id} "
            "must contain a mapping value"
        )
    return value


def _validate_config(
    *,
    uncertainty_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
) -> dict[str, Any]:
    logger.info("_validate_config profile=%s", profile)
    mode = uncertainty_config.get("mode", {})
    required_true = (
        "enabled",
        "apply_only_on_new_children",
        "physical_stocks_immutable",
        "regimes_immutable",
        "preserve_parent_weighted_mean",
    )
    for key in required_true:
        if mode.get(key) is not True:
            raise ValueError(f"v0.22 requires {key}=true")
    if mode.get("child_dynamics_allowed") is not False:
        raise ValueError("v0.22 child dynamics must remain disabled")
    if mode.get("calibrated_fallback_allowed") is not False:
        raise ValueError("v0.22 forbids calibrated fallback")

    policy_id = str(uncertainty_config.get("policy_id", ""))
    topology_policy_id = str(
        uncertainty_config.get("topology_uncertainty_policy_id", "")
    )
    if not policy_id or not topology_policy_id:
        raise ValueError("Fractal uncertainty policy IDs are required")

    parameter_id = _parameter_id(profile)
    configured_ids = uncertainty_config.get("parameter_id_by_profile")
    if not isinstance(configured_ids, dict):
        raise ValueError("parameter_id_by_profile must be a mapping")
    if configured_ids.get(profile) != parameter_id:
        raise ValueError(
            "Fractal uncertainty parameter/profile contract mismatch"
        )
    parameter = _parameter_value(
        parameter_registry,
        profile=profile,
        parameter_id=parameter_id,
    )
    if parameter.get("distribution") != "normal":
        raise ValueError("v0.22 supports normal local-variation draws only")
    mean = float(parameter.get("mean"))
    sd = float(parameter.get("sd"))
    tolerance = float(parameter.get("mean_tolerance"))
    if not all(math.isfinite(value) for value in (mean, sd, tolerance)):
        raise ValueError("Fractal uncertainty distribution must be finite")
    if sd <= 0.0 or tolerance <= 0.0:
        raise ValueError("Fractal uncertainty sd/tolerance must be positive")

    width_map = parameter.get("group_width_fraction")
    groups_raw = uncertainty_config.get("groups")
    if not isinstance(width_map, dict) or not isinstance(groups_raw, dict):
        raise ValueError("Fractal uncertainty groups/widths must be mappings")
    if not groups_raw:
        raise ValueError("Fractal uncertainty requires at least one group")
    if set(width_map) != set(groups_raw):
        raise ValueError(
            "Fractal uncertainty group widths must cover groups exactly"
        )

    latent_registry = extract_latent_registry(engine_state_registry)
    seen: set[str] = set()
    groups: dict[str, tuple[tuple[str, str], ...]] = {}
    widths: dict[str, float] = {}
    for group_id in sorted(groups_raw):
        group = groups_raw[group_id]
        if not isinstance(group, dict):
            raise ValueError(f"Fractal uncertainty group {group_id} invalid")
        variables = group.get("variables")
        if not isinstance(variables, dict) or not variables:
            raise ValueError(
                f"Fractal uncertainty group {group_id} requires variables"
            )
        normalized: list[tuple[str, str]] = []
        for variable, direction_raw in sorted(variables.items()):
            variable_id = str(variable)
            direction = str(direction_raw)
            if variable_id not in latent_registry:
                raise ValueError(
                    f"Unknown fractal uncertainty latent {variable_id}"
                )
            if variable_id in seen:
                raise ValueError(
                    f"Fractal uncertainty latent {variable_id} "
                    "appears in multiple groups"
                )
            if direction not in {"same", "inverse"}:
                raise ValueError(
                    f"Invalid fractal uncertainty direction {direction}"
                )
            seen.add(variable_id)
            normalized.append((variable_id, direction))
        width = float(width_map[group_id])
        if not math.isfinite(width) or not 0.0 < width <= 1.0:
            raise ValueError(
                f"Invalid fractal uncertainty width for {group_id}"
            )
        groups[group_id] = tuple(normalized)
        widths[group_id] = width

    safety = uncertainty_config.get("safety", {})
    forbidden = (
        "civilian_identity_direct_variation_input",
        "religion_direct_variation_input",
        "ethnicity_direct_variation_input",
        "political_identity_direct_variation_input",
        "tactical_target_selection",
        "route_planning",
        "weapon_selection",
    )
    if any(safety.get(key) is not False for key in forbidden):
        raise ValueError("Fractal uncertainty safety contract violated")
    if safety.get("variation_is_uncertainty_not_local_fact") is not True:
        raise ValueError(
            "Fractal local variation must remain uncertainty, not local fact"
        )

    return {
        "policy_id": policy_id,
        "topology_policy_id": topology_policy_id,
        "parameter_id": parameter_id,
        "mean": mean,
        "sd": sd,
        "tolerance": tolerance,
        "groups": groups,
        "widths": widths,
        "config_hash": canonical_hash(uncertainty_config),
    }


def _clone_with_metadata(
    state: EngineState,
    *,
    policy: dict[str, Any],
) -> EngineState:
    logger.info("_clone_with_metadata child=%s", state.node_id)
    metadata = dict(state.metadata)
    metadata.update(
        {
            "fractal_uncertainty_policy_id": policy["policy_id"],
            "fractal_uncertainty_parameter_id": policy["parameter_id"],
            "fractal_uncertainty_config_hash": policy["config_hash"],
            "fractal_uncertainty_applied_day": state.day,
        }
    )
    return EngineState(
        node_id=state.node_id,
        day=state.day,
        physical_stocks=dict(state.physical_stocks),
        latents=dict(state.latents),
        regimes=dict(state.regimes),
        metadata=metadata,
    )


def _normalized_group_offsets(
    *,
    parent_node_id: str,
    day: int,
    group_id: str,
    children: tuple[FractalTopologyNode, ...],
    policy: dict[str, Any],
    rng: RNGManager,
) -> tuple[str, tuple[tuple[str, int], ...], dict[str, float]]:
    logger.info(
        "_normalized_group_offsets parent=%s day=%s group=%s",
        parent_node_id,
        day,
        group_id,
    )
    stream_name = f"fractal_uncertainty:{parent_node_id}:{group_id}:{day}"
    stream = rng.stream(stream_name)
    raw: dict[str, float] = {}
    draw_indices: list[tuple[str, int]] = []
    for child in children:
        draw_index = stream.draw_index
        raw[child.node_id] = stream.normalvariate(
            policy["mean"],
            policy["sd"],
        )
        draw_indices.append((child.node_id, draw_index))

    weighted_mean = math.fsum(
        child.initialization_weight * raw[child.node_id]
        for child in children
    )
    centered = {
        child.node_id: raw[child.node_id] - weighted_mean
        for child in children
    }
    max_abs = max(abs(value) for value in centered.values())
    if max_abs <= policy["tolerance"]:
        offsets = {child.node_id: 0.0 for child in children}
    else:
        offsets = {
            child.node_id: centered[child.node_id] / max_abs
            for child in children
        }

    weighted_offset = math.fsum(
        child.initialization_weight * offsets[child.node_id]
        for child in children
    )
    if abs(weighted_offset) > policy["tolerance"]:
        raise RuntimeError("Fractal uncertainty offset centering failed")
    return stream_name, tuple(draw_indices), offsets


def _amplitude(
    *,
    parent_value: float,
    low: float,
    high: float,
    oriented_offsets: dict[str, float],
    width_fraction: float,
    tolerance: float,
) -> float:
    logger.info(
        "_amplitude parent_value=%s low=%s high=%s width=%s",
        parent_value,
        low,
        high,
        width_fraction,
    )
    requested = width_fraction * (high - low)
    limits = [requested]
    for offset in oriented_offsets.values():
        if offset > tolerance:
            limits.append((high - parent_value) / offset)
        elif offset < -tolerance:
            limits.append((parent_value - low) / (-offset))
    amplitude = min(limits)
    if amplitude < -tolerance:
        raise RuntimeError("Fractal uncertainty produced negative amplitude")
    return max(0.0, amplitude)


def _audit_parent(
    *,
    parent_state: EngineState,
    children: tuple[FractalTopologyNode, ...],
    states: dict[str, EngineState],
    variables: tuple[str, ...],
    tolerance: float,
) -> FractalUncertaintyAuditRecord:
    logger.info(
        "_audit_parent parent=%s variables=%s",
        parent_state.node_id,
        len(variables),
    )
    parent_values: dict[str, float] = {}
    child_values: dict[str, float] = {}
    errors: list[float] = []
    for variable in variables:
        parent_value = float(parent_state.latents[variable])
        weighted = math.fsum(
            child.initialization_weight
            * float(states[child.node_id].latents[variable])
            for child in children
        )
        parent_values[variable] = parent_value
        child_values[variable] = weighted
        errors.append(abs(weighted - parent_value))

    max_error = max(errors, default=0.0)
    preserved = max_error <= tolerance
    payload = {
        "parent_node_id": parent_state.node_id,
        "day": parent_state.day,
        "parent_values": dict(sorted(parent_values.items())),
        "weighted_child_values": dict(sorted(child_values.items())),
        "tolerance": tolerance,
        "contract": "FRACTAL_L2_WEIGHTED_MEAN_AUDIT_V1",
    }
    audit_id = f"fractal-uncertainty-audit-{canonical_hash(payload)[:24]}"
    return FractalUncertaintyAuditRecord(
        audit_id=audit_id,
        parent_node_id=parent_state.node_id,
        day=parent_state.day,
        parent_values=tuple(sorted(parent_values.items())),
        weighted_child_values=tuple(sorted(child_values.items())),
        max_abs_error=max_error,
        tolerance=tolerance,
        preserved=preserved,
    )


def apply_fractal_uncertainty(
    *,
    parent_states: dict[str, EngineState],
    topology: FractalTopologyState,
    child_store: FractalChildStateStore,
    new_child_ids: tuple[str, ...],
    uncertainty_config: dict[str, Any],
    engine_state_registry: dict[str, Any],
    parameter_registry: dict[str, Any],
    profile: str,
    rng: RNGManager,
    trace: TraceLedger,
) -> FractalUncertaintyResult:
    """Apply one-time bounded L2 latent heterogeneity to newly created children."""
    logger.info(
        "apply_fractal_uncertainty day=%s new_children=%s profile=%s",
        child_store.last_initialized_day,
        len(new_child_ids),
        profile,
    )
    policy = _validate_config(
        uncertainty_config=uncertainty_config,
        engine_state_registry=engine_state_registry,
        parameter_registry=parameter_registry,
        profile=profile,
    )
    if topology.last_committed_day != child_store.last_initialized_day:
        raise ValueError("Fractal uncertainty topology/store day mismatch")

    latent_registry = extract_latent_registry(engine_state_registry)
    topology_by_id = {
        item.node_id: item for item in topology.nodes if item.active
    }
    states = child_store.state_map()
    requested_ids = tuple(sorted(new_child_ids))
    if len(requested_ids) != len(set(requested_ids)):
        raise ValueError("Duplicate new child ID for fractal uncertainty")
    unknown = set(requested_ids) - set(states)
    if unknown:
        raise ValueError(
            f"Unknown new child IDs for fractal uncertainty: {sorted(unknown)}"
        )
    topology_missing = set(requested_ids) - set(topology_by_id)
    if topology_missing:
        raise ValueError(
            "Fractal uncertainty children missing active topology: "
            f"{sorted(topology_missing)}"
        )

    if not requested_ids:
        return FractalUncertaintyResult(
            store=child_store,
            records=(),
            audits=(),
        )

    working = dict(states)
    original = {
        child_id: states[child_id].to_dict() for child_id in requested_ids
    }
    by_parent: dict[str, list[FractalTopologyNode]] = {}
    for child_id in requested_ids:
        topology_node = topology_by_id[child_id]
        if (
            topology_node.inherited_uncertainty_policy_id
            != policy["topology_policy_id"]
        ):
            raise ValueError(f"Child {child_id} uncertainty policy mismatch")
        by_parent.setdefault(
            topology_node.parent_node_id,
            [],
        ).append(topology_node)

    records: list[FractalUncertaintyRecord] = []
    audits: list[FractalUncertaintyAuditRecord] = []

    for parent_node_id, raw_children in sorted(by_parent.items()):
        if parent_node_id not in parent_states:
            raise ValueError(
                f"Unknown fractal uncertainty parent {parent_node_id}"
            )
        parent_state = parent_states[parent_node_id]
        if parent_state.day != child_store.last_initialized_day:
            raise ValueError(
                f"Fractal uncertainty parent {parent_node_id} day mismatch"
            )
        children = tuple(sorted(raw_children, key=lambda item: item.node_id))
        active_children = topology.active_children(parent_node_id)
        if tuple(item.node_id for item in children) != tuple(
            item.node_id for item in active_children
        ):
            raise ValueError(
                "Fractal uncertainty requires the complete newly initialized "
                f"sibling set for parent {parent_node_id}"
            )
        weight_sum = math.fsum(
            item.initialization_weight for item in children
        )
        if not math.isclose(
            weight_sum,
            1.0,
            rel_tol=0.0,
            abs_tol=policy["tolerance"],
        ):
            raise ValueError(
                f"Fractal uncertainty weights for {parent_node_id} "
                "must sum to 1"
            )

        for child in children:
            working[child.node_id] = _clone_with_metadata(
                working[child.node_id],
                policy=policy,
            )

        varied_variables: set[str] = set()
        for group_id, variable_specs in policy["groups"].items():
            before_hashes = tuple(
                (
                    child.node_id,
                    working[child.node_id].state_hash(),
                )
                for child in children
            )
            stream_name, draw_indices, offsets = _normalized_group_offsets(
                parent_node_id=parent_node_id,
                day=parent_state.day,
                group_id=group_id,
                children=children,
                policy=policy,
                rng=rng,
            )

            latents_by_child = {
                child.node_id: dict(working[child.node_id].latents)
                for child in children
            }
            amplitudes: list[tuple[str, float]] = []
            width = policy["widths"][group_id]
            for variable, direction in variable_specs:
                varied_variables.add(variable)
                parent_value = float(parent_state.latents[variable])
                low, high = latent_registry[variable]
                sign = 1.0 if direction == "same" else -1.0
                oriented = {
                    child.node_id: offsets[child.node_id] * sign
                    for child in children
                }
                amplitude = _amplitude(
                    parent_value=parent_value,
                    low=low,
                    high=high,
                    oriented_offsets=oriented,
                    width_fraction=width,
                    tolerance=policy["tolerance"],
                )
                amplitudes.append((variable, amplitude))
                for child in children:
                    value = (
                        parent_value + amplitude * oriented[child.node_id]
                    )
                    if value < low and low - value <= policy["tolerance"]:
                        value = low
                    if value > high and value - high <= policy["tolerance"]:
                        value = high
                    latents_by_child[child.node_id][variable] = value

            for child in children:
                prior = working[child.node_id]
                updated = EngineState(
                    node_id=prior.node_id,
                    day=prior.day,
                    physical_stocks=dict(prior.physical_stocks),
                    latents=latents_by_child[child.node_id],
                    regimes=dict(prior.regimes),
                    metadata=dict(prior.metadata),
                )
                updated.validate(latent_registry)
                working[child.node_id] = updated

            after_hashes = tuple(
                (
                    child.node_id,
                    working[child.node_id].state_hash(),
                )
                for child in children
            )
            payload = {
                "parent_node_id": parent_node_id,
                "day": parent_state.day,
                "group_id": group_id,
                "rng_stream": stream_name,
                "draw_indices": dict(draw_indices),
                "normalized_offsets": dict(sorted(offsets.items())),
                "variable_amplitudes": dict(sorted(amplitudes)),
                "policy_id": policy["policy_id"],
                "parameter_id": policy["parameter_id"],
                "config_hash": policy["config_hash"],
                "contract": "FRACTAL_L2_LOCAL_VARIATION_V1",
            }
            record = FractalUncertaintyRecord(
                variation_id=(
                    "fractal-uncertainty-"
                    f"{canonical_hash(payload)[:24]}"
                ),
                parent_node_id=parent_node_id,
                day=parent_state.day,
                group_id=group_id,
                rng_stream=stream_name,
                draw_indices=draw_indices,
                normalized_offsets=tuple(sorted(offsets.items())),
                variable_amplitudes=tuple(sorted(amplitudes)),
                child_state_hashes_before=before_hashes,
                child_state_hashes_after=after_hashes,
                policy_id=policy["policy_id"],
                parameter_id=policy["parameter_id"],
                config_hash=policy["config_hash"],
            )
            records.append(record)
            trace.append(
                "fractal_uncertainty_applied",
                **record.to_dict(),
            )

        audit = _audit_parent(
            parent_state=parent_state,
            children=children,
            states=working,
            variables=tuple(sorted(varied_variables)),
            tolerance=policy["tolerance"],
        )
        if not audit.preserved:
            raise RuntimeError(
                f"Fractal weighted-mean conservation failed for "
                f"{parent_node_id}: max_error={audit.max_abs_error}"
            )
        audits.append(audit)
        trace.append("fractal_uncertainty_audit", **audit.to_dict())

    for child_id in requested_ids:
        before = original[child_id]
        after = working[child_id]
        if after.physical_stocks != before["physical_stocks"]:
            raise RuntimeError(
                f"Fractal uncertainty changed physical stocks for {child_id}"
            )
        if after.regimes != before["regimes"]:
            raise RuntimeError(
                f"Fractal uncertainty changed regimes for {child_id}"
            )
        if after.day != before["day"]:
            raise RuntimeError(
                f"Fractal uncertainty changed day for {child_id}"
            )

    return FractalUncertaintyResult(
        store=FractalChildStateStore(
            last_initialized_day=child_store.last_initialized_day,
            states=tuple(working[node_id] for node_id in sorted(working)),
        ),
        records=tuple(
            sorted(records, key=lambda item: item.variation_id)
        ),
        audits=tuple(sorted(audits, key=lambda item: item.audit_id)),
    )
