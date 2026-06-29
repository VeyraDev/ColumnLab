from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.catalog.models.benchmark import BenchmarkRun, BenchmarkSample, BenchmarkStatus
from app.catalog.repositories.benchmark_repo import BenchmarkRepository


class BenchmarkService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BenchmarkRepository(db)

    def submit(self, user_id: int, config: dict[str, Any]) -> dict[str, Any]:
        from app.application.benchmark_runner import get_benchmark_runner

        record = self.repo.create(
            user_id=user_id,
            kind=config.get("kind", "codec"),
            status=BenchmarkStatus.PENDING,
            config_json=json.dumps(config, sort_keys=True),
        )
        get_benchmark_runner().schedule(self.db, record.id)
        return self._to_dict(record)

    def get(self, run_id: int, user_id: int) -> dict[str, Any] | None:
        record = self.repo.get_for_user(run_id, user_id)
        if record is None:
            return None
        return self._to_dict(record)

    def list_samples(
        self,
        run_id: int,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 500,
    ) -> dict[str, Any] | None:
        record = self.repo.get_for_user(run_id, user_id)
        if record is None:
            return None
        samples, total = self.repo.list_samples(run_id, offset=offset, limit=limit)
        return {
            "run_id": run_id,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [self._sample_dict(s) for s in samples],
        }

    def export_csv(self, run_id: int, user_id: int) -> str | None:
        record = self.repo.get_for_user(run_id, user_id)
        if record is None:
            return None
        samples, _ = self.repo.list_samples(run_id, offset=0, limit=100_000)
        from app.engine.benchmark.export import export_samples_csv

        rows = [self._sample_dict(s) for s in samples]
        return export_samples_csv(rows)

    def export_json(self, run_id: int, user_id: int) -> str | None:
        record = self.repo.get_for_user(run_id, user_id)
        if record is None:
            return None
        summary = json.loads(record.summary_json or "{}")
        env = json.loads(record.env_json or "{}")
        from app.engine.benchmark.export import export_summary_json

        payload = {"run_id": run_id, "status": record.status, "env": env, "summary": summary}
        return export_summary_json(payload)

    def _to_dict(self, record: BenchmarkRun) -> dict[str, Any]:
        return {
            "id": record.id,
            "kind": record.kind,
            "status": record.status,
            "config": json.loads(record.config_json or "{}"),
            "env": json.loads(record.env_json or "{}") if record.env_json else None,
            "summary": json.loads(record.summary_json or "{}") if record.summary_json else None,
            "error_message": record.error_message,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    @staticmethod
    def _sample_dict(sample: BenchmarkSample) -> dict[str, Any]:
        return {
            "iteration": sample.iteration,
            "phase": sample.phase,
            "metric_name": sample.metric_name,
            "value": sample.value,
            "extra_json": sample.extra_json or "",
        }
