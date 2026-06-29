from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.catalog.models.catalog import QueryExecutionStatus
from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository
from app.catalog.repositories.query_repo import QueryRepository
from app.engine.cache.block_cache import get_block_cache
from app.engine.execution.context import ColumnExecMeta, ExecutionContext, QueryCancelledError
from app.engine.execution.executor import QueryExecutor
from app.engine.query.logical import plan_from_dict
from app.engine.query.physical_planner import ColumnCatalogInfo, PhysicalPlanContext, plan_physical, physical_plan_to_dict
from app.engine.query.pruning import BlockPruneState, BlockPruningEntry, BlockStatsSnapshot, BlockVerdict, ColumnBlocksSnapshot, TableBlocksSnapshot


@dataclass
class QueryEvent:
    query_id: int
    stage: str
    message: str
    scanned_blocks: int = 0
    active_column: str = ""
    active_block_id: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "stage": self.stage,
            "message": self.message,
            "scanned_blocks": self.scanned_blocks,
            "active_column": self.active_column,
            "active_block_id": self.active_block_id,
        }


_cancel_flags: dict[int, bool] = {}
_event_buffers: dict[int, list[QueryEvent]] = {}
_active_queries: dict[int, ExecutionContext] = {}
_lock = threading.Lock()


class QueryRunner:
    MAX_PREVIEW_ROWS = 10_000

    def schedule(self, db: Session, query_id: int) -> None:
        bind = db.get_bind()

        def runner() -> None:
            from sqlalchemy.orm import sessionmaker

            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bind)
            session = SessionLocal()
            try:
                QueryRunner()._execute(session, query_id)
            finally:
                session.close()

        with _lock:
            _cancel_flags[query_id] = False
            _event_buffers[query_id] = []
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

    def cancel(self, query_id: int) -> bool:
        with _lock:
            _cancel_flags[query_id] = True
            ctx = _active_queries.get(query_id)
            if ctx is not None:
                ctx.cancelled = True
        return True

    def get_events(self, query_id: int, after: int = 0) -> list[QueryEvent]:
        with _lock:
            return _event_buffers.get(query_id, [])[after:]

    def _execute(self, db: Session, query_id: int) -> None:
        queries = QueryRepository(db)
        catalog = CatalogRepository(db)
        record = queries.get(query_id)
        if record is None:
            return
        record.status = QueryExecutionStatus.RUNNING
        queries.update(record)
        self._publish(query_id, "running", "开始执行")

        try:
            dataset_repo = DatasetRepository(db)
            dataset = dataset_repo.get(record.dataset_id)
            if dataset is None:
                raise RuntimeError("数据集不存在")
            version = catalog.get_active_version(dataset)
            if version is None:
                raise RuntimeError("数据集没有可用版本")
            snapshot, columns, pruning = self._build_context(catalog, record)
            optimized = json.loads(record.optimized_plan_json or "{}")
            logical = plan_from_dict(optimized)
            ctx_info = PhysicalPlanContext(
                snapshot=snapshot,
                pruning=pruning,
                columns=columns,
                version_id=version.id,
            )
            physical = plan_physical(logical, ctx_info)
            record.physical_plan_json = json.dumps(physical_plan_to_dict(physical), sort_keys=True)

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
                            col.logical_type for col in snapshot.columns if col.name == c.name
                        ),
                    )
                    for c in columns
                },
                pruning={(e.column, e.block_id): e for e in ctx_info.pruning},
            )
            with _lock:
                _active_queries[query_id] = exec_ctx

            def poll_cancel() -> None:
                with _lock:
                    if _cancel_flags.get(query_id):
                        exec_ctx.cancelled = True

            start = time.perf_counter()
            poll_cancel()
            result = QueryExecutor().execute(physical, exec_ctx)
            poll_cancel()
            elapsed = time.perf_counter() - start

            metrics = result.metrics.to_dict()
            pre_metrics = json.loads(record.metrics_json or "{}")
            parse_time = float(pre_metrics.get("parse_time", 0.0))
            optimize_time = float(pre_metrics.get("optimize_time", 0.0))
            metrics["parse_time"] = parse_time
            metrics["optimize_time"] = optimize_time
            metrics["execute_time"] = elapsed
            metrics["total_time"] = parse_time + optimize_time + elapsed
            record.metrics_json = json.dumps(metrics, sort_keys=True)
            preview_rows = result.rows[: self.MAX_PREVIEW_ROWS]
            record.result_json = json.dumps(
                {
                    "columns": result.columns,
                    "rows": preview_rows,
                    "total_rows": result.total_rows,
                    "preview_rows": len(preview_rows),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            record.status = QueryExecutionStatus.COMPLETED
            queries.update(record)
            self._publish(query_id, "completed", f"输出 {result.total_rows} 行", scanned_blocks=metrics.get("scanned_blocks", 0))
        except QueryCancelledError:
            record.status = QueryExecutionStatus.CANCELLED
            record.execution_error_json = json.dumps({"code": "CANCELLED", "message": "查询已取消"})
            queries.update(record)
            self._publish(query_id, "cancelled", "查询已取消")
        except Exception as exc:
            record.status = QueryExecutionStatus.FAILED
            record.execution_error_json = json.dumps({"code": "EXECUTION_ERROR", "message": str(exc)})
            queries.update(record)
            self._publish(query_id, "failed", str(exc))
        finally:
            with _lock:
                _active_queries.pop(query_id, None)
                _cancel_flags.pop(query_id, None)

    def _build_context(self, catalog: CatalogRepository, record) -> tuple[TableBlocksSnapshot, tuple[ColumnCatalogInfo, ...], tuple]:
        table = catalog.get_table(record.table_id)
        if table is None:
            raise RuntimeError("表不存在")
        columns_meta: list[ColumnCatalogInfo] = []
        snap_columns: list[ColumnBlocksSnapshot] = []
        for col in catalog.list_columns(record.table_id):
            blocks = catalog.list_blocks(col.id)
            columns_meta.append(
                ColumnCatalogInfo(name=col.name, column_id=col.id, file_path=col.column_file_path)
            )
            snap_columns.append(
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
        snapshot = TableBlocksSnapshot(table_name=table.name, columns=tuple(snap_columns))
        pruning_raw = json.loads(record.block_pruning_json or "[]")
        pruning = tuple(
            BlockPruningEntry(
                column=e["column"],
                block_id=e["block_id"],
                state=BlockPruneState(e["state"]),
                verdict=BlockVerdict(e["verdict"]),
                reason=e["reason"],
            )
            for e in pruning_raw
        )
        return snapshot, tuple(columns_meta), pruning

    def _publish(self, query_id: int, stage: str, message: str, **kwargs: Any) -> None:
        event = QueryEvent(query_id=query_id, stage=stage, message=message, **kwargs)
        with _lock:
            _event_buffers.setdefault(query_id, []).append(event)


_runner = QueryRunner()


def get_query_runner() -> QueryRunner:
    return _runner
