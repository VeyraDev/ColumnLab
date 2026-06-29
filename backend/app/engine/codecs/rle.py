from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Any

from app.engine.binary import pack_varuint, unpack_varuint
from app.engine.codecs.base import (
    NOT_SUPPORTED,
    AggregateOp,
    CodecCapabilities,
    EncodedBlock,
    PartialAggregate,
    PredicateEq,
    PredicateIn,
    PredicateRange,
)
from app.engine.codecs.raw import RawCodec
from app.engine.types import Encoding, LogicalType
from app.engine.vectors import (
    NullBitmap,
    SelectionVector,
    ValueVector,
    deserialize_typed_value,
    serialize_typed_value,
    sort_key,
    values_equal,
)


@dataclass(slots=True)
class Run:
    value: Any
    length: int
    start: int


class RleCodec:
    encoding_id = Encoding.RLE

    @classmethod
    def encode(cls, values: ValueVector, nulls: NullBitmap) -> EncodedBlock:
        if values.length != nulls.length:
            raise ValueError("values and null bitmap length mismatch")
        start = time.perf_counter_ns()
        runs = _build_runs(values, nulls)
        body = bytearray()
        body.extend(struct.pack("<I", len(runs)))
        for run in runs:
            body.extend(serialize_typed_value(values.logical_type, run.value))
            body.extend(pack_varuint(run.length))
        payload = nulls.serialize() + bytes(body)
        null_count = sum(1 for v in values.values if v is None)
        non_null = [v for v in values.values if v is not None]
        distinct_count = len({serialize_typed_value(values.logical_type, v) for v in non_null})
        min_value = min(non_null, default=None, key=lambda v: sort_key(values.logical_type, v))
        max_value = max(non_null, default=None, key=lambda v: sort_key(values.logical_type, v))
        raw_block = RawCodec.encode(values, nulls)
        encode_ns = time.perf_counter_ns() - start
        return EncodedBlock(
            encoding=Encoding.RLE,
            logical_type=values.logical_type,
            payload=payload,
            raw_bytes=raw_block.raw_bytes,
            encoded_bytes=len(payload),
            null_count=null_count,
            distinct_count=distinct_count,
            min_value=min_value,
            max_value=max_value,
            run_count=len(runs),
            encode_ns=encode_ns,
        )

    @classmethod
    def decode(cls, block: EncodedBlock) -> ValueVector:
        nulls, runs, _ = _parse_rle_payload(block)
        values: list[Any] = [None] * nulls.length
        for run in runs:
            row = run.start
            for _ in range(run.length):
                values[row] = run.value
                row += 1
        return ValueVector(logical_type=block.logical_type, values=tuple(values))

    @classmethod
    def estimate_capabilities(cls) -> CodecCapabilities:
        return CodecCapabilities(supports_filter=True, supports_aggregate=True)

    @classmethod
    def filter(cls, block: EncodedBlock, predicate: object) -> SelectionVector | object:
        if isinstance(predicate, PredicateEq):
            return cls._filter_eq(block, predicate.value)
        if isinstance(predicate, PredicateRange):
            return cls._filter_range(block, predicate)
        if isinstance(predicate, PredicateIn):
            return cls._filter_in(block, predicate.values)
        return NOT_SUPPORTED

    @classmethod
    def aggregate(cls, block: EncodedBlock, aggregate: object) -> PartialAggregate | object:
        if not isinstance(aggregate, AggregateOp):
            return NOT_SUPPORTED
        _, runs, _ = _parse_rle_payload(block)
        logical_type = block.logical_type
        partial = PartialAggregate()
        for run in runs:
            if aggregate == AggregateOp.COUNT:
                partial.count += run.length
            elif aggregate == AggregateOp.SUM:
                partial.count += run.length
                if partial.sum is None:
                    partial.sum = run.value * run.length
                else:
                    partial.sum = partial.sum + run.value * run.length
            elif aggregate == AggregateOp.MIN:
                partial.count += run.length
                partial.min = run.value if partial.min is None else min(partial.min, run.value, key=lambda v: sort_key(logical_type, v))
            elif aggregate == AggregateOp.MAX:
                partial.count += run.length
                partial.max = run.value if partial.max is None else max(partial.max, run.value, key=lambda v: sort_key(logical_type, v))
            elif aggregate == AggregateOp.AVG:
                partial.count += run.length
                if partial.sum is None:
                    partial.sum = run.value * run.length
                else:
                    partial.sum = partial.sum + run.value * run.length
        return partial

    @classmethod
    def _filter_eq(cls, block: EncodedBlock, target: Any) -> SelectionVector:
        nulls, runs, _ = _parse_rle_payload(block)
        buf = bytearray((nulls.length + 7) // 8)
        for run in runs:
            if values_equal(block.logical_type, run.value, target):
                for i in range(run.start, run.start + run.length):
                    if not nulls.is_null(i):
                        buf[i // 8] |= 1 << (i % 8)
        return SelectionVector(length=nulls.length, bits=bytes(buf))

    @classmethod
    def _filter_in(cls, block: EncodedBlock, targets: tuple[Any, ...]) -> SelectionVector:
        nulls, runs, _ = _parse_rle_payload(block)
        buf = bytearray((nulls.length + 7) // 8)
        for run in runs:
            if any(values_equal(block.logical_type, run.value, target) for target in targets):
                for i in range(run.start, run.start + run.length):
                    if not nulls.is_null(i):
                        buf[i // 8] |= 1 << (i % 8)
        return SelectionVector(length=nulls.length, bits=bytes(buf))

    @classmethod
    def _filter_range(cls, block: EncodedBlock, predicate: PredicateRange) -> SelectionVector:
        nulls, runs, _ = _parse_rle_payload(block)
        logical_type = block.logical_type
        buf = bytearray((nulls.length + 7) // 8)
        for run in runs:
            if _value_in_range(logical_type, run.value, predicate):
                for i in range(run.start, run.start + run.length):
                    if not nulls.is_null(i):
                        buf[i // 8] |= 1 << (i % 8)
        return SelectionVector(length=nulls.length, bits=bytes(buf))


def _build_runs(values: ValueVector, nulls: NullBitmap) -> list[Run]:
    runs: list[Run] = []
    i = 0
    n = values.length
    while i < n:
        if nulls.is_null(i):
            i += 1
            continue
        value = values.values[i]
        start = i
        length = 1
        i += 1
        while i < n and not nulls.is_null(i) and values_equal(values.logical_type, values.values[i], value):
            length += 1
            i += 1
        runs.append(Run(value=value, length=length, start=start))
    return runs


def _parse_rle_payload(block: EncodedBlock) -> tuple[NullBitmap, list[Run], int]:
    nulls, offset = NullBitmap.deserialize(block.payload)
    if len(block.payload) < offset + 4:
        raise ValueError("truncated RLE header")
    (run_count,) = struct.unpack_from("<I", block.payload, offset)
    pos = offset + 4
    runs: list[Run] = []
    row = 0
    logical_type = block.logical_type
    for _ in range(run_count):
        value, pos = deserialize_typed_value(logical_type, block.payload, pos)
        run_length, pos = unpack_varuint(block.payload, pos)
        while row < nulls.length and nulls.is_null(row):
            row += 1
        runs.append(Run(value=value, length=run_length, start=row))
        row += run_length
    return nulls, runs, pos


def _value_in_range(logical_type: LogicalType, value: Any, predicate: PredicateRange) -> bool:
    key = sort_key(logical_type, value)
    if predicate.lower is not None:
        lower_key = sort_key(logical_type, predicate.lower)
        if predicate.lower_inclusive:
            if key < lower_key:
                return False
        elif key <= lower_key:
            return False
    if predicate.upper is not None:
        upper_key = sort_key(logical_type, predicate.upper)
        if predicate.upper_inclusive:
            if key > upper_key:
                return False
        elif key >= upper_key:
            return False
    return True


def extract_rle_runs_for_preview(block: EncodedBlock) -> list[dict[str, Any]]:
    _, runs, _ = _parse_rle_payload(block)
    return [{"value": run.value, "run_length": run.length, "start": run.start} for run in runs]
