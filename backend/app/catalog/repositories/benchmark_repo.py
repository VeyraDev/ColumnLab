from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog.models.benchmark import BenchmarkRun, BenchmarkSample, BenchmarkStatus


class BenchmarkRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs) -> BenchmarkRun:
        record = BenchmarkRun(**kwargs)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, run_id: int) -> BenchmarkRun | None:
        return self.db.get(BenchmarkRun, run_id)

    def get_for_user(self, run_id: int, user_id: int) -> BenchmarkRun | None:
        return (
            self.db.query(BenchmarkRun)
            .filter(BenchmarkRun.id == run_id, BenchmarkRun.user_id == user_id)
            .first()
        )

    def update(self, record: BenchmarkRun) -> BenchmarkRun:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def add_sample(
        self,
        *,
        run_id: int,
        iteration: int,
        phase: str,
        metric_name: str,
        value: float,
        extra_json: str | None = None,
    ) -> BenchmarkSample:
        sample = BenchmarkSample(
            run_id=run_id,
            iteration=iteration,
            phase=phase,
            metric_name=metric_name,
            value=value,
            extra_json=extra_json,
        )
        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        return sample

    def list_samples(
        self,
        run_id: int,
        *,
        offset: int = 0,
        limit: int = 500,
    ) -> tuple[list[BenchmarkSample], int]:
        q = self.db.query(BenchmarkSample).filter(BenchmarkSample.run_id == run_id)
        total = q.count()
        items = (
            q.order_by(BenchmarkSample.id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total
