from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DatasetStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class VersionStatus(StrEnum):
    STAGING = "staging"
    READY = "ready"
    FAILED = "failed"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    INFERRING = "inferring"
    PARTITIONING = "partitioning"
    ENCODING = "encoding"
    WRITING = "writing"
    VALIDATING = "validating"
    COMMITTING = "committing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=DatasetStatus.DRAFT, nullable=False)
    active_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    versions: Mapped[list[DatasetVersion]] = relationship(
        "DatasetVersion",
        back_populates="dataset",
        foreign_keys="DatasetVersion.dataset_id",
    )
    import_jobs: Mapped[list[ImportJob]] = relationship("ImportJob", back_populates="dataset")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    format_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    table_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    encoded_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=VersionStatus.STAGING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    dataset: Mapped[Dataset] = relationship(
        "Dataset",
        back_populates="versions",
        foreign_keys=[dataset_id],
    )
    tables: Mapped[list[Table]] = relationship("Table", back_populates="version")


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dataset_versions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_group_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    version: Mapped[DatasetVersion] = relationship("DatasetVersion", back_populates="tables")
    columns: Mapped[list[Column]] = relationship("Column", back_populates="table")


class Column(Base):
    __tablename__ = "columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("tables.id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logical_type: Mapped[str] = mapped_column(String(32), nullable=False)
    nullable: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scale: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    block_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    encoded_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_value_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_value_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    table: Mapped[Table] = relationship("Table", back_populates="columns")
    blocks: Mapped[list[ColumnBlockCatalog]] = relationship("ColumnBlockCatalog", back_populates="column")


class ColumnBlockCatalog(Base):
    __tablename__ = "column_block_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    column_id: Mapped[int] = mapped_column(Integer, ForeignKey("columns.id"), nullable=False, index=True)
    block_id: Mapped[int] = mapped_column(Integer, nullable=False)
    row_start: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    encoding: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    encoded_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    null_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    distinct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_repr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    max_repr: Mapped[str | None] = mapped_column(String(128), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dictionary_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload_crc32: Mapped[str] = mapped_column(String(16), nullable=False)
    total_block_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    column: Mapped[Column] = relationship("Column", back_populates="blocks")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=ImportJobStatus.PENDING, nullable=False)
    stage: Mapped[str] = mapped_column(String(32), default=ImportJobStatus.PENDING, nullable=False)
    source_path: Mapped[str] = mapped_column(String(512), nullable=False)
    staging_path: Mapped[str] = mapped_column(String(512), nullable=False)
    table_name: Mapped[str] = mapped_column(String(200), default="data", nullable=False)
    import_mode: Mapped[str] = mapped_column(String(16), default="strict", nullable=False)
    schema_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    bytes_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_column: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_samples_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_block_bytes: Mapped[int] = mapped_column(Integer, default=65536, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="import_jobs")


class QueryExecutionStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueryExecution(Base):
    __tablename__ = "query_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("tables.id"), nullable=False, index=True)
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=QueryExecutionStatus.PLANNED, nullable=False)
    logical_plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimized_plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimizer_trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    block_pruning_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    physical_plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
