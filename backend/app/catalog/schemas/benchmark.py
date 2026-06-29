from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class BenchmarkSubmitRequest(BaseModel):
    kind: Literal["codec", "query"] = "codec"
    seed: int = 42
    warmup_runs: int = Field(default=1, ge=0, le=10)
    repeat_runs: int = Field(default=3, ge=1, le=20)
    distribution: str = "run_length"
    row_count: int = Field(default=4096, ge=256, le=1_000_000)
    block_sizes: list[int] | None = None
    cache_mode: Literal["cold", "hot"] = "cold"
    pruning_enabled: bool = True
    dataset_id: int | None = None
    sql: str | None = None


class BenchmarkRunOut(BaseModel):
    id: int
    kind: str
    status: str
    config: dict[str, Any]
    env: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
