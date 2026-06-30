from __future__ import annotations

import csv
import io
import asyncio
import tempfile
from pathlib import Path
from typing import Any

from app.engine.import_pipeline.csv_parser import _CSV_ENCODING_CANDIDATES, iter_csv_rows
from app.engine.import_pipeline.type_infer import infer_from_samples, logical_type_name
from app.engine.import_pipeline.xlsx_parser import iter_xlsx_rows
_SCHEMA_PREVIEW_MAX_BYTES = 2 * 1024 * 1024
_XLSX_PREVIEW_MAX_BYTES = 8 * 1024 * 1024


def infer_schema_from_path(source_path: Path, *, sample_rows: int = 500) -> tuple[list[dict[str, Any]], int]:
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        row_iter = iter_csv_rows(source_path)
    elif suffix == ".xlsx":
        row_iter = iter_xlsx_rows(source_path)
    else:
        raise ValueError(f"unsupported file type: {suffix}")

    header = [c.strip() for c in next(row_iter)]
    samples: list[list[str]] = []
    for cells in row_iter:
        samples.append(cells)
        if len(samples) >= sample_rows:
            break

    inferred = infer_from_samples(header, samples)
    columns = [
        {
            "name": col.name,
            "logical_type": logical_type_name(col.logical_type),
            "scale": col.logical_type.scale,
            "nullable": col.nullable,
            "inferred": True,
        }
        for col in inferred
    ]
    return columns, len(samples)


def infer_schema_from_upload(filename: str, data: bytes, *, sample_rows: int = 500) -> tuple[list[dict[str, Any]], int]:
    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return infer_schema_from_path(tmp_path, sample_rows=sample_rows)
    finally:
        tmp_path.unlink(missing_ok=True)


async def infer_schema_from_upload_stream(
    filename: str,
    upload: Any,
    *,
    sample_rows: int = 500,
    max_bytes: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return await _infer_schema_from_csv_stream(upload, sample_rows=sample_rows, max_bytes=max_bytes)
    if suffix == ".xlsx":
        return await _infer_schema_from_xlsx_stream(upload, sample_rows=sample_rows, max_bytes=max_bytes)
    raise ValueError(f"unsupported file type: {suffix}")


async def _read_preview_bytes(upload: Any, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    read = getattr(upload, "read", None)
    if read is None:
        raise TypeError("upload stream has no read()")
    while total < max_bytes:
        chunk = read(65536)
        if asyncio.iscoroutine(chunk):
            chunk = await chunk
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


async def _infer_schema_from_csv_stream(
    upload: Any,
    *,
    sample_rows: int,
    max_bytes: int | None,
) -> tuple[list[dict[str, Any]], int]:
    cap = max_bytes or _SCHEMA_PREVIEW_MAX_BYTES
    data = await _read_preview_bytes(upload, cap)
    encoding = _detect_encoding_from_bytes(data)
    text = io.TextIOWrapper(io.BytesIO(data), encoding=encoding, newline="")
    reader = csv.reader(text)
    try:
        header = [c.strip() for c in next(reader)]
    except StopIteration:
        return [], 0
    samples: list[list[str]] = []
    for row in reader:
        samples.append(row)
        if len(samples) >= sample_rows:
            break
    inferred = infer_from_samples(header, samples)
    columns = [
        {
            "name": col.name,
            "logical_type": logical_type_name(col.logical_type),
            "scale": col.logical_type.scale,
            "nullable": col.nullable,
            "inferred": True,
        }
        for col in inferred
    ]
    return columns, len(samples)


async def _infer_schema_from_xlsx_stream(
    upload: Any,
    *,
    sample_rows: int,
    max_bytes: int | None,
) -> tuple[list[dict[str, Any]], int]:
    cap = max_bytes or _XLSX_PREVIEW_MAX_BYTES
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        total = 0
        read = upload.read
        while total < cap:
            chunk = read(65536)
            if asyncio.iscoroutine(chunk):
                chunk = await chunk
            if not chunk:
                break
            tmp.write(chunk)
            total += len(chunk)
        tmp_path = Path(tmp.name)
    try:
        return infer_schema_from_path(tmp_path, sample_rows=sample_rows)
    finally:
        tmp_path.unlink(missing_ok=True)


def _detect_encoding_from_bytes(data: bytes) -> str:
    for encoding in _CSV_ENCODING_CANDIDATES:
        try:
            data.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"
