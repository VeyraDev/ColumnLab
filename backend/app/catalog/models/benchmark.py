from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BenchmarkKind(StrEnum):
    CODEC = "codec"
    QUERY = "query"


class BenchmarkStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkPhase(StrEnum):
    WARMUP = "warmup"
    TIMED = "timed"


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=BenchmarkStatus.PENDING, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    env_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    samples: Mapped[list[BenchmarkSample]] = relationship("BenchmarkSample", back_populates="run")


class BenchmarkSample(Base):
    __tablename__ = "benchmark_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("benchmark_runs.id"), nullable=False, index=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[BenchmarkRun] = relationship("BenchmarkRun", back_populates="samples")
