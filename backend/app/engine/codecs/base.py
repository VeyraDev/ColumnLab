from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, NotRequired, Protocol, TypedDict, runtime_checkable

from app.engine.types import Encoding, LogicalType
from app.engine.vectors import NullBitmap, SelectionVector, ValueVector


class AggregateOp(str, Enum):
    COUNT = "COUNT"
    SUM = "SUM"
    MIN = "MIN"
    MAX = "MAX"
    AVG = "AVG"


@dataclass(frozen=True, slots=True)
class PredicateEq:
    value: Any


@dataclass(frozen=True, slots=True)
class PredicateRange:
    lower: Any | None = None
    upper: Any | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = True


@dataclass(frozen=True, slots=True)
class PredicateIn:
    values: tuple[Any, ...]


@dataclass(slots=True)
class PartialAggregate:
    count: int = 0
    sum: float | int | None = None
    min: Any | None = None
    max: Any | None = None

    def merge(self, other: PartialAggregate) -> PartialAggregate:
        count = self.count + other.count
        total_sum: float | int | None
        if self.sum is None:
            total_sum = other.sum
        elif other.sum is None:
            total_sum = self.sum
        else:
            total_sum = self.sum + other.sum
        merged_min = self.min if other.min is None else other.min if self.min is None else min(self.min, other.min, key=_agg_sort_key)
        merged_max = self.max if other.max is None else other.max if self.max is None else max(self.max, other.max, key=_agg_sort_key)
        return PartialAggregate(count=count, sum=total_sum, min=merged_min, max=merged_max)


def _agg_sort_key(value: Any) -> tuple[int, Any]:
    if isinstance(value, float) and value != value:
        return (1, 0)
    return (0, value)


@dataclass(slots=True)
class CodecCapabilities:
    supports_filter: bool = False
    supports_aggregate: bool = False
    supports_encoding: bool = True


@dataclass(slots=True)
class EncodedBlock:
    encoding: Encoding
    logical_type: LogicalType
    payload: bytes
    raw_bytes: int
    encoded_bytes: int
    null_count: int
    distinct_count: int = 0
    min_value: object | None = None
    max_value: object | None = None
    run_count: int = 0
    dictionary_count: int = 0
    encode_ns: int = 0
    diagnostics: dict[str, object] = field(default_factory=dict)


class NotSupported:
    __slots__ = ()


NOT_SUPPORTED = NotSupported()


@runtime_checkable
class Codec(Protocol):
    encoding_id: Encoding

    def encode(self, values: ValueVector, nulls: NullBitmap) -> EncodedBlock: ...

    def decode(self, block: EncodedBlock) -> ValueVector: ...

    def estimate_capabilities(self) -> CodecCapabilities: ...

    def filter(self, block: EncodedBlock, predicate: object) -> SelectionVector | NotSupported: ...

    def aggregate(self, block: EncodedBlock, aggregate: object) -> PartialAggregate | NotSupported: ...


class CodecDiagnostics(TypedDict, total=False):
    encoding: int
    raw_bytes: int
    encoded_bytes: int
    null_count: int


# decode cost rank: lower is cheaper
DECODE_COST: dict[Encoding, int] = {
    Encoding.RAW: 0,
    Encoding.RLE: 1,
    Encoding.DICTIONARY: 2,
}
