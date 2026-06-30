from __future__ import annotations

import json
import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.application.query_runner import get_query_runner
from app.catalog.models.catalog import QueryExecutionStatus
from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository
from app.catalog.repositories.query_repo import QueryRepository
from app.catalog.schemas.query import LogicalPlanNode, QueryErrorOut
from app.engine.query.binder import ColumnSchema, TableSchema
from app.engine.query.errors import QueryError
from app.engine.query.logical import plan_to_dict
from app.engine.query.optimizer import optimize_plan
from app.engine.query.planner import plan_query
from app.engine.query.pruning import (
    BlockStatsSnapshot,
    ColumnBlocksSnapshot,
    TableBlocksSnapshot,
    prune_blocks,
    pruning_summary,
)


class QueryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.datasets = DatasetRepository(db)
        self.catalog = CatalogRepository(db)
        self.queries = QueryRepository(db)

    def submit(
        self,
        *,
        user_id: int,
        dataset_id: int,
        sql: str,
        table_id: int | None,
        pruning_enabled: bool = True,
    ) -> dict[str, Any]:
        dataset = self.datasets.get_for_user(dataset_id, user_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="数据集不存在")
        if dataset.status != "ready":
            raise HTTPException(status_code=400, detail="数据集尚未就绪")

        table = self._resolve_table(dataset, table_id)
        schema = self._table_schema(table.id)

        try:
            t0 = time.perf_counter()
            plan = plan_query(sql, schema)
            parse_time = time.perf_counter() - t0
            plan_json = json.dumps(plan_to_dict(plan), sort_keys=True)
            t1 = time.perf_counter()
            opt_result = optimize_plan(plan, schema)
            optimize_time = time.perf_counter() - t1
            optimized_json = json.dumps(plan_to_dict(opt_result.plan), sort_keys=True)
            trace_json = json.dumps([t.to_dict() for t in opt_result.trace], sort_keys=True)
            blocks_snapshot = self._blocks_snapshot(table.id)
            if pruning_enabled:
                pruning = prune_blocks(opt_result.plan, blocks_snapshot)
            else:
                from app.engine.query.pruning import all_blocks_to_read

                pruning = all_blocks_to_read(blocks_snapshot)
            pruning_json = json.dumps([e.to_dict() for e in pruning], sort_keys=True)
            summary = pruning_summary(pruning)
            timing_json = json.dumps(
                {"parse_time": parse_time, "optimize_time": optimize_time},
                sort_keys=True,
            )
            record = self.queries.create(
                user_id=user_id,
                dataset_id=dataset_id,
                table_id=table.id,
                sql_text=sql,
                status=QueryExecutionStatus.RUNNING,
                logical_plan_json=plan_json,
                optimized_plan_json=optimized_json,
                optimizer_trace_json=trace_json,
                block_pruning_json=pruning_json,
                parse_error_json=None,
                metrics_json=timing_json,
            )
            get_query_runner().schedule(self.db, record.id)
            return {
                "query_id": record.id,
                "status": record.status,
                "error": None,
                "plan_summary": _plan_summary(optimized_json),
                "total_blocks": summary["total_blocks"],
                "pruned_blocks": summary["pruned_blocks"],
            }
        except QueryError as exc:
            error = QueryErrorOut(**exc.to_dict())
            record = self.queries.create(
                user_id=user_id,
                dataset_id=dataset_id,
                table_id=table.id,
                sql_text=sql,
                status=QueryExecutionStatus.FAILED,
                logical_plan_json=None,
                optimized_plan_json=None,
                optimizer_trace_json=None,
                block_pruning_json=None,
                parse_error_json=json.dumps(exc.to_dict()),
            )
            return {
                "query_id": record.id,
                "status": record.status,
                "error": error.model_dump(),
                "plan_summary": None,
                "total_blocks": 0,
                "pruned_blocks": 0,
            }

    def get_query(self, *, user_id: int, query_id: int) -> dict[str, Any]:
        record = self.queries.get_for_user(query_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="查询记录不存在")
        return _query_out(record)

    def get_result(
        self,
        *,
        user_id: int,
        query_id: int,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        record = self.queries.get_for_user(query_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="查询记录不存在")
        if record.status not in {
            QueryExecutionStatus.COMPLETED,
            QueryExecutionStatus.RUNNING,
            QueryExecutionStatus.CANCELLED,
        }:
            if record.status == QueryExecutionStatus.FAILED:
                err = json.loads(record.execution_error_json) if record.execution_error_json else {}
                raise HTTPException(status_code=400, detail=err.get("message", "查询执行失败"))
            raise HTTPException(status_code=400, detail="查询尚未完成")
        if not record.result_json:
            if record.status == QueryExecutionStatus.RUNNING:
                return {
                    "query_id": record.id,
                    "status": record.status,
                    "columns": [],
                    "rows": [],
                    "total_rows": 0,
                    "offset": offset,
                    "limit": limit,
                }
            raise HTTPException(status_code=404, detail="无查询结果")
        payload = json.loads(record.result_json)
        all_rows = payload.get("rows", [])
        page = all_rows[offset : offset + limit]
        return {
            "query_id": record.id,
            "status": record.status,
            "columns": payload.get("columns", []),
            "rows": page,
            "total_rows": payload.get("total_rows", len(all_rows)),
            "offset": offset,
            "limit": limit,
        }

    def cancel(self, *, user_id: int, query_id: int) -> dict[str, Any]:
        record = self.queries.get_for_user(query_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="查询记录不存在")
        if record.status != QueryExecutionStatus.RUNNING:
            raise HTTPException(status_code=400, detail="查询未在运行")
        get_query_runner().cancel(query_id)
        return {"query_id": query_id, "status": "cancelling"}

    def get_events(self, *, user_id: int, query_id: int, after: int = 0) -> list[dict[str, Any]]:
        record = self.queries.get_for_user(query_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="查询记录不存在")
        events = get_query_runner().get_events(query_id, after)
        return [e.to_dict() for e in events]

    def explain(self, *, user_id: int, query_id: int) -> dict[str, Any]:
        record = self.queries.get_for_user(query_id, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="查询记录不存在")
        plan = json.loads(record.logical_plan_json) if record.logical_plan_json else None
        optimized = json.loads(record.optimized_plan_json) if record.optimized_plan_json else None
        trace_raw = json.loads(record.optimizer_trace_json) if record.optimizer_trace_json else []
        pruning_raw = json.loads(record.block_pruning_json) if record.block_pruning_json else []
        physical = json.loads(record.physical_plan_json) if record.physical_plan_json else None
        metrics = json.loads(record.metrics_json) if record.metrics_json else None
        error = _parse_error(record.parse_error_json)
        pruned = sum(1 for p in pruning_raw if p.get("state") == "skipped")
        return {
            "query_id": record.id,
            "status": record.status,
            "sql_text": record.sql_text,
            "logical_plan": plan,
            "plan_tree": plan_to_tree(plan) if plan else None,
            "optimized_plan": optimized,
            "optimized_plan_tree": plan_to_tree(optimized) if optimized else None,
            "physical_plan": physical,
            "physical_plan_tree": physical_plan_to_tree(physical) if physical else None,
            "optimizer_trace": trace_raw,
            "block_pruning": pruning_raw,
            "metrics": metrics,
            "total_blocks": len(pruning_raw),
            "pruned_blocks": pruned,
            "error": error.model_dump() if error else None,
        }

    def execute_sync(
        self,
        *,
        user_id: int,
        dataset_id: int,
        sql: str,
        table_id: int | None = None,
        pruning_enabled: bool = True,
    ) -> dict[str, Any]:
        """Run query inline for benchmarks/tests without background thread."""
        from app.engine.cache.block_cache import get_block_cache
        from app.engine.execution.context import ColumnExecMeta, ExecutionContext
        from app.engine.execution.executor import QueryExecutor
        from app.engine.query.physical_planner import ColumnCatalogInfo, PhysicalPlanContext, plan_physical

        dataset = self.datasets.get_for_user(dataset_id, user_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="数据集不存在")
        if dataset.status != "ready":
            raise HTTPException(status_code=400, detail="数据集尚未就绪")
        table = self._resolve_table(dataset, table_id)
        schema = self._table_schema(table.id)
        version = self.catalog.get_active_version(dataset)
        if version is None:
            raise HTTPException(status_code=400, detail="数据集没有可用版本")

        t0 = time.perf_counter()
        plan = plan_query(sql, schema)
        parse_time = time.perf_counter() - t0
        t1 = time.perf_counter()
        opt_result = optimize_plan(plan, schema)
        optimize_time = time.perf_counter() - t1
        blocks_snapshot = self._blocks_snapshot(table.id)
        if pruning_enabled:
            pruning = prune_blocks(opt_result.plan, blocks_snapshot)
        else:
            from app.engine.query.pruning import all_blocks_to_read

            pruning = all_blocks_to_read(blocks_snapshot)

        columns_meta: list[ColumnCatalogInfo] = []
        for col in self.catalog.list_columns(table.id):
            columns_meta.append(
                ColumnCatalogInfo(name=col.name, column_id=col.id, file_path=col.column_file_path)
            )
        ctx_info = PhysicalPlanContext(
            snapshot=blocks_snapshot,
            pruning=pruning,
            columns=tuple(columns_meta),
            version_id=version.id,
        )
        physical = plan_physical(opt_result.plan, ctx_info)
        cache = get_block_cache()
        cache.set_version(version.id)
        exec_ctx = ExecutionContext(
            version_id=version.id,
            columns={
                c.name: ColumnExecMeta(
                    name=c.name,
                    column_id=c.column_id,
                    file_path=c.file_path,
                    logical_type=next(
                        col.logical_type for col in blocks_snapshot.columns if col.name == c.name
                    ),
                )
                for c in columns_meta
            },
            pruning={(e.column, e.block_id): e for e in pruning},
        )
        try:
            t2 = time.perf_counter()
            result = QueryExecutor().execute(physical, exec_ctx)
            execute_time = time.perf_counter() - t2
            metrics = result.metrics.to_dict()
            metrics["parse_time"] = parse_time
            metrics["optimize_time"] = optimize_time
            metrics["execute_time"] = execute_time
            metrics["total_time"] = parse_time + optimize_time + execute_time
            return metrics
        finally:
            exec_ctx.close()

    def history(self, *, user_id: int, dataset_id: int, limit: int = 20) -> list[dict[str, Any]]:
        dataset = self.datasets.get_for_user(dataset_id, user_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="数据集不存在")
        rows = self.queries.list_for_dataset(dataset_id, limit=limit)
        return [
            {
                "id": row.id,
                "sql_text": row.sql_text,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def _resolve_table(self, dataset, table_id: int | None):
        version = self.catalog.get_active_version(dataset)
        if version is None:
            raise HTTPException(status_code=400, detail="数据集没有可用版本")
        tables = self.catalog.list_tables_for_version(version.id)
        if not tables:
            raise HTTPException(status_code=400, detail="数据集没有可用表")
        if table_id is not None:
            for table in tables:
                if table.id == table_id:
                    return table
            raise HTTPException(status_code=404, detail="表不存在")
        return tables[0]

    def _table_schema(self, table_id: int) -> TableSchema:
        table = self.catalog.get_table(table_id)
        if table is None:
            raise HTTPException(status_code=404, detail="表不存在")
        columns = self.catalog.list_columns(table_id)
        return TableSchema(
            name=table.name,
            columns=tuple(ColumnSchema(name=c.name, logical_type=c.logical_type) for c in columns),
        )

    def _blocks_snapshot(self, table_id: int) -> TableBlocksSnapshot:
        table = self.catalog.get_table(table_id)
        if table is None:
            raise HTTPException(status_code=404, detail="表不存在")
        columns: list[ColumnBlocksSnapshot] = []
        for col in self.catalog.list_columns(table_id):
            blocks = self.catalog.list_blocks(col.id)
            columns.append(
                ColumnBlocksSnapshot(
                    name=col.name,
                    logical_type=col.logical_type,
                    blocks=tuple(
                        BlockStatsSnapshot(
                            block_id=b.block_id,
                            encoding=b.encoding,
                            row_count=b.row_count,
                            null_count=b.null_count,
                            min_repr=b.min_repr,
                            max_repr=b.max_repr,
                            dictionary_count=b.dictionary_count,
                            column_file_path=col.column_file_path,
                        )
                        for b in blocks
                    ),
                )
            )
        return TableBlocksSnapshot(table_name=table.name, columns=tuple(columns))


def plan_to_tree(plan: dict[str, Any] | None) -> LogicalPlanNode | None:
    if plan is None:
        return None
    node_type = plan.get("type", "Unknown")
    label = node_type
    details: dict[str, Any] = {}

    if node_type == "Scan":
        details["table"] = plan.get("table")
        if plan.get("annotations"):
            details["annotations"] = plan["annotations"]
    elif node_type == "Filter":
        details["predicate"] = plan.get("predicate")
    elif node_type == "Project":
        details["items"] = plan.get("items")
    elif node_type == "Aggregate":
        details["group_keys"] = plan.get("group_keys")
        details["aggregates"] = plan.get("aggregates")
    elif node_type == "Sort":
        details["keys"] = plan.get("keys")
    elif node_type == "Limit":
        details["limit"] = plan.get("limit")
        details["offset"] = plan.get("offset")

    child = plan.get("child")
    children = [plan_to_tree(child)] if child else []
    children = [c for c in children if c is not None]

    return LogicalPlanNode(type=node_type, label=label, details=details, children=children)


def _plan_summary(plan_json: str) -> str:
    plan = json.loads(plan_json)
    types: list[str] = []
    node = plan
    while node:
        types.append(node.get("type", "?"))
        node = node.get("child")
    return " → ".join(types)


def _parse_error(raw: str | None) -> QueryErrorOut | None:
    if not raw:
        return None
    data = json.loads(raw)
    return QueryErrorOut(**data)


def _query_out(record) -> dict[str, Any]:
    metrics = json.loads(record.metrics_json) if record.metrics_json else None
    exec_error = json.loads(record.execution_error_json) if record.execution_error_json else None
    return {
        "id": record.id,
        "dataset_id": record.dataset_id,
        "table_id": record.table_id,
        "sql_text": record.sql_text,
        "status": record.status,
        "error": _parse_error(record.parse_error_json).model_dump()
        if record.parse_error_json
        else None,
        "execution_error": exec_error,
        "metrics": metrics,
        "created_at": record.created_at,
    }


def physical_plan_to_tree(plan: dict[str, Any] | None) -> LogicalPlanNode | None:
    if plan is None:
        return None
    node_type = plan.get("type", "Unknown")
    details: dict[str, Any] = {}
    for key in ("column", "columns", "limit", "offset", "predicate", "group_keys", "aggregates", "keys", "operator_id"):
        if key in plan:
            details[key] = plan[key]
    children: list[LogicalPlanNode | None] = []
    if "child" in plan:
        children.append(physical_plan_to_tree(plan["child"]))
    for child in plan.get("children", []):
        children.append(physical_plan_to_tree(child))
    return LogicalPlanNode(
        type=node_type,
        label=node_type,
        details=details,
        children=[c for c in children if c is not None],
    )
