from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from app.engine.import_pipeline.csv_parser import iter_csv_rows
from app.engine.import_pipeline.type_infer import infer_from_samples, logical_type_name
from app.engine.import_pipeline.xlsx_parser import iter_xlsx_rows


def infer_schema_from_path(source_path: Path, *, sample_rows: int = 500) -> list[dict[str, Any]]:
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
    return [
        {
            "name": col.name,
            "logical_type": logical_type_name(col.logical_type),
            "scale": col.logical_type.scale,
            "nullable": col.nullable,
            "inferred": True,
        }
        for col in inferred
    ]


def infer_schema_from_upload(filename: str, data: bytes, *, sample_rows: int = 500) -> list[dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return infer_schema_from_path(tmp_path, sample_rows=sample_rows)
    finally:
        tmp_path.unlink(missing_ok=True)
