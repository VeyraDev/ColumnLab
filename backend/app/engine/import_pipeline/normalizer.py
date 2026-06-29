from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.engine.import_pipeline.type_infer import BOOL_FALSE, BOOL_TRUE
from app.engine.types import LogicalType, LogicalTypeId


@dataclass(slots=True)
class NormalizationError(Exception):
    row_number: int
    column: str
    raw_value: str
    reason: str

    def __str__(self) -> str:
        return f"row {self.row_number} col {self.column}: {self.reason}"


@dataclass
class Normalizer:
    logical_type: LogicalType
    column_name: str
    mode: str = "strict"
    error_samples: list[dict] = field(default_factory=list)
    error_count: int = 0

    def normalize(self, raw: str, *, row_number: int) -> object | None:
        text = "" if raw is None else str(raw).strip()
        if text == "":
            return None
        try:
            return _convert(self.logical_type, text)
        except ValueError as exc:
            if self.mode == "strict":
                raise NormalizationError(row_number, self.column_name, text, str(exc)) from exc
            self.error_count += 1
            if len(self.error_samples) < 20:
                self.error_samples.append(
                    {
                        "row": row_number,
                        "column": self.column_name,
                        "value": text,
                        "reason": str(exc),
                    }
                )
            return None


def _convert(logical_type: LogicalType, text: str) -> object:
    tid = logical_type.type_id
    if tid == LogicalTypeId.INT64:
        return int(text)
    if tid == LogicalTypeId.FLOAT64:
        return float(text)
    if tid == LogicalTypeId.BOOLEAN:
        low = text.lower()
        if low in BOOL_TRUE:
            return True
        if low in BOOL_FALSE:
            return False
        raise ValueError("invalid boolean")
    if tid == LogicalTypeId.UTF8:
        return text
    if tid == LogicalTypeId.DATE32:
        return date.fromisoformat(text)
    if tid == LogicalTypeId.TIMESTAMP64:
        return datetime.fromisoformat(text.replace(" ", "T"))
    if tid == LogicalTypeId.DECIMAL64:
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise ValueError("invalid decimal") from exc
    raise ValueError(f"unsupported type {tid}")
