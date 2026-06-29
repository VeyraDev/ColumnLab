from __future__ import annotations

import json
from typing import Any

from app.engine.benchmark.env_snapshot import samples_to_csv, summary_to_json


def export_samples_csv(rows: list[dict[str, Any]]) -> str:
    return samples_to_csv(rows)


def export_summary_json(summary: dict[str, Any]) -> str:
    return summary_to_json(summary)


def sample_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "iteration": row.iteration,
        "phase": row.phase,
        "metric_name": row.metric_name,
        "value": row.value,
        "extra_json": row.extra_json or "",
    }
