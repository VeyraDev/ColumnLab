from __future__ import annotations

import hashlib
import json
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.catalog.models.catalog import (
    ColumnBlockCatalog,
    DatasetStatus,
    ImportJob,
    ImportJobStatus,
    VersionStatus,
)
from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository, ImportJobRepository
from app.core.config import get_settings
from app.engine.import_pipeline.normalizer import NormalizationError
from app.engine.import_pipeline.pipeline import ImportPipeline
from app.engine.import_pipeline.type_infer import logical_type_name


@dataclass
class JobEvent:
    job_id: int
    stage: str
    status: str
    rows_processed: int
    bytes_processed: int
    current_column: str
    error_count: int
    message: str = ""


_cancel_flags: dict[int, bool] = {}
_event_buffers: dict[int, list[JobEvent]] = {}
_event_lock = threading.Lock()
_runner_lock = threading.Lock()


class ImportCoordinator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.datasets = DatasetRepository(db)
        self.jobs = ImportJobRepository(db)
        self.catalog = CatalogRepository(db)

    def begin_upload(
        self,
        *,
        user_id: int,
        filename: str,
        staging_dir: Path,
        table_name: str = "data",
        import_mode: str = "strict",
        schema_overrides: list[dict] | None = None,
        target_block_bytes: int = 65536,
    ) -> tuple[ImportJob, Path]:
        staging_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix.lower()
        source_path = staging_dir / f"source{suffix}"
        dataset_name = Path(filename).stem or "dataset"
        dataset = self.datasets.create(user_id=user_id, name=dataset_name, source_file_name=filename)
        job = self.jobs.create(
            user_id=user_id,
            dataset_id=dataset.id,
            source_path=str(source_path),
            staging_path=str(staging_dir),
            table_name=table_name,
            import_mode=import_mode,
            schema_json=json.dumps(schema_overrides or [], ensure_ascii=False),
            target_block_bytes=target_block_bytes,
        )
        _cancel_flags[job.id] = False
        with _event_lock:
            _event_buffers[job.id] = []
        return job, source_path

    def finalize_upload(self, job: ImportJob, sha256: str) -> ImportJob:
        dataset = self.datasets.get(job.dataset_id)
        assert dataset is not None
        dataset.source_sha256 = sha256
        self.datasets.update(dataset)
        self._start_background(job.id)
        return self.jobs.get(job.id)  # type: ignore[return-value]

    def cancel(self, job: ImportJob) -> ImportJob:
        _cancel_flags[job.id] = True
        job.status = ImportJobStatus.CANCELLED
        job.stage = ImportJobStatus.CANCELLED
        self.jobs.update(job)
        self._cleanup_staging(Path(job.staging_path))
        self._publish(job, "cancelled")
        return job

    def get_events(self, job_id: int, after: int = 0) -> list[JobEvent]:
        with _event_lock:
            events = _event_buffers.get(job_id, [])
            return events[after:]

    def _start_background(self, job_id: int) -> None:
        bind = self.db.get_bind()

        def runner() -> None:
            from sqlalchemy.orm import sessionmaker

            Session = sessionmaker(autocommit=False, autoflush=False, bind=bind)
            db = Session()
            try:
                ImportCoordinator(db)._run_job(job_id)
            finally:
                db.close()

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

    def _run_job(self, job_id: int) -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        dataset = self.datasets.get(job.dataset_id)
        if dataset is None:
            return
        staging = Path(job.staging_path)
        version_dir = staging / "version"
        version_dir.mkdir(parents=True, exist_ok=True)
        schema_overrides = json.loads(job.schema_json) if job.schema_json else []

        def on_progress(stage: str, rows: int, bytes_: int, column: str, errors: int) -> None:
            fresh = self.jobs.get(job_id)
            if fresh is None:
                return
            fresh.stage = stage
            if stage in {s.value for s in ImportJobStatus}:
                fresh.status = stage
            fresh.rows_processed = rows
            fresh.bytes_processed = bytes_
            fresh.current_column = column
            fresh.error_count = errors
            self.jobs.update(fresh)
            self._publish(fresh, stage)

        try:
            self.jobs.set_status(job, ImportJobStatus.PARSING, stage=ImportJobStatus.PARSING)
            pipeline = ImportPipeline(
                source_path=Path(job.source_path),
                output_dir=version_dir,
                import_mode=job.import_mode,
                target_block_bytes=job.target_block_bytes,
                schema_overrides=schema_overrides,
                on_progress=on_progress,
                should_cancel=lambda: _cancel_flags.get(job_id, False),
            )
            result = pipeline.run()
            self.jobs.set_status(job, ImportJobStatus.COMMITTING, stage=ImportJobStatus.COMMITTING)
            self._commit(job, dataset, result, version_dir)
            job = self.jobs.get(job_id)
            assert job is not None
            job.status = ImportJobStatus.COMPLETED
            job.stage = ImportJobStatus.COMPLETED
            job.rows_processed = result.row_count
            job.error_count = result.error_count
            job.error_samples_json = json.dumps(result.error_samples, ensure_ascii=False)
            self.jobs.update(job)
            dataset.status = DatasetStatus.READY
            self.datasets.update(dataset)
            self._publish(job, ImportJobStatus.COMPLETED)
            shutil.rmtree(staging, ignore_errors=True)
        except NormalizationError as exc:
            self._fail(job, "type_error", str(exc))
        except UnicodeDecodeError as exc:
            self._fail(job, "encoding_error", f"文件编码无法识别，请另存为 UTF-8 CSV 后重试: {exc}")
        except RuntimeError as exc:
            if str(exc) == "cancelled":
                return
            self._fail(job, "cancelled_runtime", str(exc))
        except Exception as exc:
            self._fail(job, "import_failed", str(exc))

    def _commit(self, job: ImportJob, dataset, result, version_dir: Path) -> None:
        from app.catalog.models.catalog import DatasetVersion

        final_root = self.settings.resolve_path(self.settings.DATASETS_DIR) / str(dataset.id)
        final_root.mkdir(parents=True, exist_ok=True)
        version_no = self.db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset.id).count() + 1
        final_path = final_root / f"v{version_no}"
        if final_path.exists():
            shutil.rmtree(final_path)
        shutil.move(str(version_dir), str(final_path))

        version = self.catalog.create_version(
            dataset_id=dataset.id,
            version_no=version_no,
            storage_path=str(final_path),
        )
        table = self.catalog.create_table(
            version_id=version.id,
            name=job.table_name,
            row_count=result.row_count,
            row_group_count=result.row_group_count,
        )
        total_raw = 0
        total_encoded = 0
        for ordinal, col_result in enumerate(result.columns):
            rel_path = str(final_path / col_result.path.name)
            col = self.catalog.create_column(
                table_id=table.id,
                ordinal=ordinal,
                name=col_result.name,
                logical_type=logical_type_name(col_result.logical_type),
                nullable=1,
                scale=col_result.logical_type.scale,
                column_file_path=rel_path,
                block_count=col_result.block_count,
                raw_bytes=col_result.raw_bytes,
                encoded_bytes=col_result.encoded_bytes,
            )
            blocks = [
                ColumnBlockCatalog(
                    column_id=col.id,
                    block_id=b["block_id"],
                    row_start=b["row_start"],
                    row_count=b["row_count"],
                    encoding=b["encoding"],
                    raw_bytes=b["raw_bytes"],
                    encoded_bytes=b["encoded_bytes"],
                    null_count=b["null_count"],
                    payload_crc32=b["payload_crc32"],
                    total_block_length=b["total_block_length"],
                    run_count=b.get("run_count", 0),
                    dictionary_count=b.get("dictionary_count", 0),
                    min_repr=b.get("min_repr"),
                    max_repr=b.get("max_repr"),
                )
                for b in col_result.blocks
            ]
            self.catalog.bulk_create_blocks(blocks)
            total_raw += col_result.raw_bytes
            total_encoded += col_result.encoded_bytes

        self.catalog.finalize_version(
            version,
            row_count=result.row_count,
            table_count=1,
            raw_bytes=total_raw,
            encoded_bytes=total_encoded,
        )
        dataset.active_version_id = version.id
        self.datasets.update(dataset)

    def _fail(self, job: ImportJob, code: str, message: str) -> None:
        job.status = ImportJobStatus.FAILED
        job.stage = ImportJobStatus.FAILED
        job.error_code = code
        job.error_message = message
        self.jobs.update(job)
        dataset = self.datasets.get(job.dataset_id)
        if dataset:
            dataset.status = DatasetStatus.FAILED
            self.datasets.update(dataset)
        self._cleanup_staging(Path(job.staging_path))
        self._publish(job, ImportJobStatus.FAILED, message=message)

    def _cleanup_staging(self, staging: Path) -> None:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    def _publish(self, job: ImportJob, stage: str, message: str = "") -> None:
        event = JobEvent(
            job_id=job.id,
            stage=stage,
            status=job.status,
            rows_processed=job.rows_processed,
            bytes_processed=job.bytes_processed,
            current_column=job.current_column,
            error_count=job.error_count,
            message=message,
        )
        with _event_lock:
            _event_buffers.setdefault(job.id, []).append(event)


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
