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
        )

    def append_daily_checkpoint(
        self,
        *,
        run_id: str,
        day: int,
        node_id: str,
        state_hash_before: str,
        state_hash_after: str,
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
            module_deltas=[],
            event_ids_applied=[],
            spillover_ids_applied=[],
            agent_action_ids=[],
            refinement_actions=[],
            constraint_clamps=[],
        )

    def to_jsonl(self, path: str | Path) -> None:
        logger.info("TraceLedger.to_jsonl path=%s records=%s", path, len(self.records))
        with Path(path).open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
                handle.write("\n")
