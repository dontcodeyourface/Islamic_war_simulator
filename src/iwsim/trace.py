from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TraceLedger:
    records: list[dict[str, Any]] = field(default_factory=list)

    def append(self, record_type: str, **payload: Any) -> None:
        logger.info("TraceLedger.append record_type=%s", record_type)
        self.records.append({"record_type": record_type, **payload})

    def append_initialization(
        self,
        *,
        node_id: str,
        variable: str,
        value: float,
        init_rule_id: str,
        prior_id: str | None,
        rng_stream: str | None,
        draw_index: int | None,
        source_type: str = "prior",
        normalization_rule_id: str | None = None,
        parameter_ids: tuple[str, ...] = (),
        snapshot_field_refs: tuple[str, ...] = (),
        source_ids: tuple[str, ...] = (),
        data_quality: str | None = None,
        freshness: str | None = None,
        uncertainty_multiplier: float | None = None,
        empirical_fraction: float = 0.0,
        prior_fraction: float = 1.0,
        baseline_fraction: float = 0.0,
    ) -> None:
        logger.info(
            "TraceLedger.append_initialization node_id=%s variable=%s",
            node_id,
            variable,
        )
        self.append(
            "initialization",
            node_id=node_id,
            variable=variable,
            value=value,
            init_rule_id=init_rule_id,
            prior_id=prior_id,
            rng_stream=rng_stream,
            draw_index=draw_index,
            source_type=source_type,
            normalization_rule_id=normalization_rule_id,
            parameter_ids=list(parameter_ids),
            snapshot_field_refs=list(snapshot_field_refs),
            source_ids=list(source_ids),
            data_quality=data_quality,
            freshness=freshness,
            uncertainty_multiplier=uncertainty_multiplier,
            empirical_fraction=empirical_fraction,
            prior_fraction=prior_fraction,
            baseline_fraction=baseline_fraction,
        )

    def append_daily_checkpoint(
        self,
        *,
        run_id: str,
        day: int,
        node_id: str,
        state_hash_before: str,
        state_hash_after: str,
        module_deltas: tuple[str, ...] = (),
        event_ids_applied: tuple[str, ...] = (),
        spillover_ids_applied: tuple[str, ...] = (),
        agent_action_ids: tuple[str, ...] = (),
        refinement_actions: tuple[str, ...] = (),
        constraint_clamps: tuple[str, ...] = (),
    ) -> None:
        logger.info(
            "TraceLedger.append_daily_checkpoint run_id=%s day=%s node_id=%s",
            run_id,
            day,
            node_id,
        )
        self.append(
            "daily_checkpoint",
            run_id=run_id,
            day=day,
            node_id=node_id,
            state_hash_before=state_hash_before,
            state_hash_after=state_hash_after,
            module_deltas=list(module_deltas),
            event_ids_applied=list(event_ids_applied),
            spillover_ids_applied=list(spillover_ids_applied),
            agent_action_ids=list(agent_action_ids),
            refinement_actions=list(refinement_actions),
            constraint_clamps=list(constraint_clamps),
        )

    def extend_from(self, other: "TraceLedger") -> None:
        logger.info("TraceLedger.extend_from records=%s", len(other.records))
        self.records.extend(dict(record) for record in other.records)

    def to_jsonl(self, path: str | Path) -> None:
        logger.info("TraceLedger.to_jsonl path=%s records=%s", path, len(self.records))
        with Path(path).open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
                handle.write("\n")
