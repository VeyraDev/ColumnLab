from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.engine.types import LogicalType, LogicalTypeId

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")

BOOL_TRUE = {"true", "1", "yes", "y", "t"}
BOOL_FALSE = {"false", "0", "no", "n", "f"}


@dataclass(slots=True)
class InferredColumn:
    name: str
    logical_type: LogicalType
    nullable: bool = True


def parse_logical_type(name: str, scale: int = 0) -> LogicalType:
    key = name.upper()
    mapping = {
        "INT64": LogicalType.int64,
        "FLOAT64": LogicalType.float64,
        "BOOLEAN": LogicalType.boolean,
        "UTF8": LogicalType.utf8,
        "DATE32": LogicalType.date32,
        "TIMESTAMP64": LogicalType.timestamp64,
    }
    if key == "DECIMAL64":
        return LogicalType.decimal64(scale)
    factory = mapping.get(key)
    if factory is None:
        raise ValueError(f"unsupported logical type {name}")
    return factory()


def logical_type_name(lt: LogicalType) -> str:
    if lt.type_id == LogicalTypeId.DECIMAL64:
        return "DECIMAL64"
    return lt.type_id.name


def infer_from_samples(column_names: list[str], rows: list[list[str]]) -> list[InferredColumn]:
    inferred: list[InferredColumn] = []
    for col_idx, name in enumerate(column_names):
        samples = [row[col_idx] if col_idx < len(row) else "" for row in rows]
        inferred.append(InferredColumn(name=name, logical_type=_infer_column(samples)))
    return inferred


def _infer_column(samples: list[str]) -> LogicalType:
    non_empty = [s.strip() for s in samples if s is not None and str(s).strip() != ""]
    if not non_empty:
        return LogicalType.utf8()

    if all(_is_bool(s) for s in non_empty):
        return LogicalType.boolean()
    if all(_is_int(s) for s in non_empty):
        return LogicalType.int64()
    if all(_is_float(s) for s in non_empty):
        return LogicalType.float64()
    if all(_is_date(s) for s in non_empty):
        return LogicalType.date32()
    if all(_is_timestamp(s) for s in non_empty):
        return LogicalType.timestamp64()
    if all(_is_decimal(s) for s in non_empty):
        return LogicalType.decimal64(_decimal_scale(non_empty))
    return LogicalType.utf8()


def _is_bool(value: str) -> bool:
    return value.lower() in BOOL_TRUE or value.lower() in BOOL_FALSE


def _is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _is_timestamp(value: str) -> bool:
    if not TIMESTAMP_RE.match(value):
        return False
    try:
        datetime.fromisoformat(value.replace(" ", "T"))
        return True
    except ValueError:
        return False


def _is_decimal(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except InvalidOperation:
        return False


def _decimal_scale(values: list[str]) -> int:
    scale = 0
    for value in values:
        if "." in value:
            scale = max(scale, len(value.split(".", 1)[1]))
    return scale
