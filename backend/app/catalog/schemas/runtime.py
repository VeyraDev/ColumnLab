from __future__ import annotations

from pydantic import BaseModel


class RuntimeOut(BaseModel):
    engine_version: str
    memory_used_bytes: int
    memory_total_bytes: int
    process_rss_bytes: int
