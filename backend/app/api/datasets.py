from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.catalog.access import resolve_table_for_user
from app.application.block_inspector_service import BlockInspectorService
from app.application.import_coordinator import ImportCoordinator, hash_file
from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository, ImportJobRepository
from app.catalog.schemas.catalog import (
    ColumnOut,
    DatasetOut,
    ImportJobOut,
    StorageMapColumnOut,
    StorageMapOut,
    StorageBlockOut,
    TableOut,
    UploadResponse,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api", tags=["datasets"])
settings = get_settings()


def _dataset_out(ds, version) -> dict:
    return DatasetOut(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        source_file_name=ds.source_file_name,
        source_sha256=ds.source_sha256,
        status=ds.status,
        active_version_id=ds.active_version_id,
        row_count=version.row_count if version else 0,
        table_count=version.table_count if version else 0,
        storage_path=version.storage_path if version else None,
    ).model_dump()


def _job_out(job) -> dict:
    samples = json.loads(job.error_samples_json) if job.error_samples_json else []
    return ImportJobOut(
        id=job.id,
        dataset_id=job.dataset_id,
        status=job.status,
        stage=job.stage,
        bytes_processed=job.bytes_processed,
        rows_processed=job.rows_processed,
        current_column=job.current_column,
        error_count=job.error_count,
        error_code=job.error_code,
        error_message=job.error_message,
        error_samples=samples,
    ).model_dump()


@router.post("/datasets/schema-preview")
async def schema_preview(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    del user
    filename = file.filename or "upload.csv"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="仅支持 CSV 或 XLSX 文件")
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    preview_cap = min(max_bytes, 2 * 1024 * 1024)
    from app.engine.import_pipeline.schema_preview import infer_schema_from_upload_stream

    try:
        columns, row_sample_count = await infer_schema_from_upload_stream(
            filename,
            file.file,
            sample_rows=500,
            max_bytes=preview_cap,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return success({"columns": columns, "row_sample_count": row_sample_count})


@router.post("/datasets/uploads")
async def upload_dataset(
    file: UploadFile = File(...),
    table_name: str = Form(default="data"),
    import_mode: str = Form(default="strict"),
    schema_overrides: str = Form(default="[]"),
    target_block_bytes: int = Form(default=65536),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filename = file.filename or "upload.csv"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="仅支持 CSV 或 XLSX 文件")
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    overrides = json.loads(schema_overrides) if schema_overrides else []

    coordinator = ImportCoordinator(db)
    job, source_path = coordinator.begin_upload(
        user_id=user.id,
        filename=filename,
        table_name=table_name,
        import_mode=import_mode,
        schema_overrides=overrides,
        target_block_bytes=target_block_bytes,
    )
    total = 0
    with source_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                coordinator.cancel(job)
                raise HTTPException(status_code=413, detail="文件超过大小限制")
            out.write(chunk)

    sha = hash_file(source_path)
    job = coordinator.finalize_upload(job, sha)
    return success(
        UploadResponse(job_id=job.id, dataset_id=job.dataset_id, source_sha256=sha).model_dump()
    )


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = DatasetRepository(db)
    catalog = CatalogRepository(db)
    items = []
    for ds in repo.list_for_user(user.id, ready_only=True):
        version = catalog.get_active_version(ds)
        items.append(_dataset_out(ds, version))
    return success(items)


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = DatasetRepository(db)
    catalog = CatalogRepository(db)
    ds = repo.get_for_user(dataset_id, user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    version = catalog.get_active_version(ds)
    return success(_dataset_out(ds, version))


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.catalog.models.catalog import QueryExecution, QueryExecutionStatus
    from app.catalog.repositories.query_repo import QueryRepository

    repo = DatasetRepository(db)
    ds = repo.get_for_user(dataset_id, user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    active = (
        db.query(QueryExecution)
        .filter(
            QueryExecution.dataset_id == dataset_id,
            QueryExecution.status == QueryExecutionStatus.RUNNING,
        )
        .count()
    )
    if active:
        raise HTTPException(status_code=409, detail="数据集上有活动查询，无法删除")
    repo.delete(ds)
    return success(None, msg="deleted")


@router.get("/datasets/{dataset_id}/tables")
def list_tables(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds_repo = DatasetRepository(db)
    ds = ds_repo.get_for_user(dataset_id, user.id)
    if ds is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    catalog = CatalogRepository(db)
    if ds.active_version_id:
        tables = catalog.list_tables_for_version(ds.active_version_id)
    else:
        tables = []
    return success([TableOut.model_validate(t).model_dump() for t in tables])


@router.get("/tables/{table_id}/columns")
def list_columns(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resolve_table_for_user(db, user.id, table_id)
    catalog = CatalogRepository(db)
    cols = catalog.list_columns(table_id)
    return success(
        [
            ColumnOut(
                id=c.id,
                name=c.name,
                logical_type=c.logical_type,
                scale=c.scale,
                nullable=bool(c.nullable),
                block_count=c.block_count,
                raw_bytes=c.raw_bytes,
                encoded_bytes=c.encoded_bytes,
            ).model_dump()
            for c in cols
        ]
    )


@router.get("/tables/{table_id}/storage-map")
def storage_map(table_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resolve_table_for_user(db, user.id, table_id)
    catalog = CatalogRepository(db)
    table = catalog.get_table(table_id)
    assert table is not None
    columns_out: list[StorageMapColumnOut] = []
    total_blocks = 0
    for col in catalog.list_columns(table_id):
        blocks = catalog.list_blocks(col.id)
        total_blocks += len(blocks)
        columns_out.append(
            StorageMapColumnOut(
                name=col.name,
                logical_type=col.logical_type,
                block_count=len(blocks),
                blocks=[
                    StorageBlockOut(
                        block_id=b.block_id,
                        encoding=b.encoding,
                        row_start=b.row_start,
                        row_count=b.row_count,
                        compressed_bytes=b.total_block_length,
                        encoded_bytes=b.encoded_bytes,
                        raw_bytes=b.raw_bytes,
                        null_count=b.null_count,
                        payload_crc32=b.payload_crc32,
                    )
                    for b in blocks
                ],
            )
        )
    return success(
        StorageMapOut(
            source="catalog",
            row_count=table.row_count,
            column_count=len(columns_out),
            total_blocks=total_blocks,
            columns=columns_out,
        ).model_dump()
    )


@router.get("/columns/{column_id}/blocks/{block_id}")
def get_column_block(
    column_id: int,
    block_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BlockInspectorService(db)
    return success(service.get_block(user_id=user.id, column_id=column_id, block_id=block_id))


@router.get("/columns/{column_id}/blocks/{block_id}/preview")
def get_column_block_preview(
    column_id: int,
    block_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BlockInspectorService(db)
    return success(service.get_block_preview(user_id=user.id, column_id=column_id, block_id=block_id))


import_router = APIRouter(prefix="/api/import-jobs", tags=["import-jobs"])


@import_router.get("/{job_id}")
def get_import_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = ImportJobRepository(db).get_for_user(job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return success(_job_out(job))


@import_router.post("/{job_id}/cancel")
def cancel_import_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = ImportJobRepository(db)
    job = repo.get_for_user(job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    job = ImportCoordinator(db).cancel(job)
    return success(_job_out(job))


@import_router.get("/{job_id}/events")
def import_job_events(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = ImportJobRepository(db).get_for_user(job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    coordinator = ImportCoordinator(db)

    def event_stream():
        from app.core.database import SessionLocal

        cursor = 0
        import time

        while True:
            events = coordinator.get_events(job_id, cursor)
            for event in events:
                cursor += 1
                payload = {
                    "stage": event.stage,
                    "status": event.status,
                    "rows_processed": event.rows_processed,
                    "bytes_processed": event.bytes_processed,
                    "current_column": event.current_column,
                    "error_count": event.error_count,
                    "message": event.message,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            sess = SessionLocal()
            try:
                fresh = ImportJobRepository(sess).get(job_id)
            finally:
                sess.close()
            if fresh and fresh.status in {"completed", "failed", "cancelled"}:
                if not events:
                    payload = _job_out(fresh)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break
            time.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
