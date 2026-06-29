from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class LogicalTypeId(IntEnum):
    INT64 = 1
    FLOAT64 = 2
    BOOLEAN = 3
    UTF8 = 4
    DATE32 = 5
    TIMESTAMP64 = 6
    DECIMAL64 = 7


class Encoding(IntEnum):
    RAW = 0
    RLE = 1
    DICTIONARY = 2


@dataclass(frozen=True, slots=True)
class LogicalType:
    type_id: LogicalTypeId
    scale: int = 0

    def __post_init__(self) -> None:
        if self.type_id == LogicalTypeId.DECIMAL64 and self.scale < 0:
            raise ValueError("DECIMAL64 scale must be non-negative")

    @classmethod
    def int64(cls) -> LogicalType:
        return cls(LogicalTypeId.INT64)

    @classmethod
    def float64(cls) -> LogicalType:
        return cls(LogicalTypeId.FLOAT64)

    @classmethod
    def boolean(cls) -> LogicalType:
        return cls(LogicalTypeId.BOOLEAN)

    @classmethod
    def utf8(cls) -> LogicalType:
        return cls(LogicalTypeId.UTF8)

    @classmethod
    def date32(cls) -> LogicalType:
        return cls(LogicalTypeId.DATE32)

    @classmethod
    def timestamp64(cls) -> LogicalType:
        return cls(LogicalTypeId.TIMESTAMP64)

    @classmethod
    def decimal64(cls, scale: int) -> LogicalType:
        return cls(LogicalTypeId.DECIMAL64, scale=scale)

    @property
    def fixed_width(self) -> int | None:
        widths = {
            LogicalTypeId.INT64: 8,
            LogicalTypeId.FLOAT64: 8,
            LogicalTypeId.DATE32: 4,
            LogicalTypeId.TIMESTAMP64: 8,
            LogicalTypeId.DECIMAL64: 8,
        }
        return widths.get(self.type_id)
