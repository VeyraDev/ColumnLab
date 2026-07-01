from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.catalog.models.benchmark import BenchmarkRun, BenchmarkStatus
from app.catalog.repositories.benchmark_repo import BenchmarkRepository
from app.engine.benchmark.codec_benchmark import run_codec_benchmark
from app.engine.benchmark.config import BenchmarkConfig
from app.engine.benchmark.env_snapshot import capture_env
from app.engine.benchmark.export import sample_row_to_dict
from app.engine.benchmark.query_benchmark import run_query_benchmark


@dataclass
class BenchmarkEvent:
    run_id: int
    stage: str
    message: str
    progress: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "stage": self.stage,
            "message": self.message,
            "progress": self.progress,
        }


_event_buffers: dict[int, list[BenchmarkEvent]] = {}
_lock = threading.Lock()


class BenchmarkRunner:
    def schedule(self, db: Session, run_id: int) -> None:
        bind = db.get_bind()

        def runner() -> None:
            from sqlalchemy.orm import sessionmaker

            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
            session = SessionLocal()
            try:
                BenchmarkRunner()._execute(session, run_id)
            finally:
                session.close()

        with _lock:
            _event_buffers[run_id] = []
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

    def get_events(self, run_id: int, after: int = 0) -> list[BenchmarkEvent]:
        with _lock:
            return _event_buffers.get(run_id, [])[after:]

    def _execute(self, db: Session, run_id: int) -> None:
        repo = BenchmarkRepository(db)
        record = repo.get(run_id)
        if record is None:
            return
        record.status = BenchmarkStatus.RUNNING
        repo.update(record)
        self._publish(run_id, "running", "开始 benchmark", 0.1)

        try:
            config = BenchmarkConfig.from_dict(json.loads(record.config_json))
            env = capture_env()
            record.env_json = json.dumps(env, sort_keys=True)
            repo.update(record)
            self._publish(run_id, "env", "环境快照已采集", 0.2)

            if config.kind == "query" and config.dataset_id:
                self._publish(run_id, "query", "运行 query benchmark", 0.35)
                result = self._run_query_benchmark(db, config, record)
            else:
                self._publish(run_id, "codec", "运行 codec benchmark", 0.25)

                def on_codec_progress(fraction: float, message: str) -> None:
                    self._publish(run_id, "codec", message, 0.25 + 0.55 * fraction)

                result = run_codec_benchmark(config, on_progress=on_codec_progress)

            self._publish(run_id, "persist", "写入样本", 0.8)
            for sample in result.samples:
                repo.add_sample(
                    run_id=run_id,
                    iteration=sample.iteration,
                    phase=sample.phase,
                    metric_name=sample.metric_name,
                    value=sample.value,
                    extra_json=sample.extra_json,
                )

            summary = dict(result.summary)
            summary["env"] = env
            summary["config"] = config.to_dict()
            record.summary_json = json.dumps(summary, sort_keys=True, ensure_ascii=False)
            record.status = BenchmarkStatus.COMPLETED
            repo.update(record)
            self._publish(run_id, "completed", "benchmark 完成", 1.0)
        except Exception as exc:
            record.status = BenchmarkStatus.FAILED
            record.error_message = str(exc)
            repo.update(record)
            self._publish(run_id, "failed", str(exc), 1.0)

    def _run_query_benchmark(self, db: Session, config: BenchmarkConfig, record: BenchmarkRun):
        from app.application.query_service import QueryService

        service = QueryService(db)

        def execute_fn(*, warmup: bool = False) -> dict[str, Any]:
            sql = config.sql or "SELECT COUNT(*) AS cnt FROM data"
            metrics = service.execute_sync(
                user_id=record.user_id,
                dataset_id=config.dataset_id,
                sql=sql,
                table_id=None,
                pruning_enabled=config.pruning_enabled,
            )
            metrics["warmup"] = warmup
            return metrics

        return run_query_benchmark(config, execute_fn=execute_fn)

    def _publish(self, run_id: int, stage: str, message: str, progress: float) -> None:
        event = BenchmarkEvent(run_id=run_id, stage=stage, message=message, progress=progress)
        with _lock:
            _event_buffers.setdefault(run_id, []).append(event)


_runner = BenchmarkRunner()


def get_benchmark_runner() -> BenchmarkRunner:
    return _runner
