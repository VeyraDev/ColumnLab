from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuerySubmitRequest(BaseModel):
    dataset_id: int
    sql: str = Field(min_length=1)
    table_id: int | None = None


class QueryErrorOut(BaseModel):
    code: str
    message: str
    line: int | None = None
    col: int | None = None


class LogicalPlanNode(BaseModel):
    type: str
    label: str
    details: dict[str, Any] = Field(default_factory=dict)
    children: list[LogicalPlanNode] = Field(default_factory=list)


class OptimizerTraceEntry(BaseModel):
    rule: str
    changed: bool
    detail: str = ""


class BlockPruningState(BaseModel):
    column: str
    block_id: int
    state: str
    verdict: str
    reason: str


class QuerySubmitOut(BaseModel):
    query_id: int
    status: str
    error: QueryErrorOut | None = None
    plan_summary: str | None = None
    total_blocks: int = 0
    pruned_blocks: int = 0


class QueryOut(BaseModel):
    id: int
    dataset_id: int
    table_id: int
    sql_text: str
    status: str
    error: QueryErrorOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryExplainOut(BaseModel):
    query_id: int
    status: str
    sql_text: str
    logical_plan: dict[str, Any] | None = None
    plan_tree: LogicalPlanNode | None = None
    optimized_plan: dict[str, Any] | None = None
    optimized_plan_tree: LogicalPlanNode | None = None
    optimizer_trace: list[OptimizerTraceEntry] = Field(default_factory=list)
    block_pruning: list[BlockPruningState] = Field(default_factory=list)
    total_blocks: int = 0
    pruned_blocks: int = 0
    error: QueryErrorOut | None = None


class QueryHistoryItem(BaseModel):
    id: int
    sql_text: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
