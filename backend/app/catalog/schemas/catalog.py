from __future__ import annotations

from pydantic import BaseModel, Field


class ColumnSchemaOverride(BaseModel):
    name: str
    logical_type: str
    scale: int = 0
    nullable: bool = True


class UploadResponse(BaseModel):
    job_id: int
    dataset_id: int
    source_sha256: str


class ImportJobOut(BaseModel):
    id: int
    dataset_id: int
    status: str
    stage: str
    bytes_processed: int
    rows_processed: int
    current_column: str
    error_count: int
    error_code: str | None = None
    error_message: str | None = None
    error_samples: list[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DatasetOut(BaseModel):
    id: int
    name: str
    description: str
    source_file_name: str
    source_sha256: str
    status: str
    active_version_id: int | None
    row_count: int = 0
    table_count: int = 0
    storage_path: str | None = None

    model_config = {"from_attributes": True}


class TableOut(BaseModel):
    id: int
    name: str
    row_count: int
    row_group_count: int

    model_config = {"from_attributes": True}


class ColumnOut(BaseModel):
    id: int
    name: str
    logical_type: str
    scale: int
    nullable: bool
    block_count: int
    raw_bytes: int
    encoded_bytes: int

    model_config = {"from_attributes": True}


class StorageBlockOut(BaseModel):
    block_id: int
    row_group_id: int = 0
    encoding: str
    row_start: int
    row_count: int
    compressed_bytes: int
    encoded_bytes: int
    raw_bytes: int
    null_count: int
    payload_crc32: str


class StorageMapColumnOut(BaseModel):
    name: str
    logical_type: str
    block_count: int
    blocks: list[StorageBlockOut]


class StorageMapOut(BaseModel):
    source: str
    row_count: int
    column_count: int
    total_blocks: int
    columns: list[StorageMapColumnOut]
