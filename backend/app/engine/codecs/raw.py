from __future__ import annotations

import struct
import time
from typing import Any

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
from app.engine.types import Encoding, LogicalType, LogicalTypeId
from app.engine.vectors import (
    NullBitmap,
    SelectionVector,
    ValueVector,
    canonical_key,
    pack_boolean_bits,
    serialize_typed_value,
    sort_key,
    unpack_boolean_bits,
    deserialize_typed_value,
    values_equal,
)


class RawCodec:
    encoding_id = Encoding.RAW

    @classmethod
    def encode(cls, values: ValueVector, nulls: NullBitmap) -> EncodedBlock:
        if values.length != nulls.length:
            raise ValueError("values and null bitmap length mismatch")
        start = time.perf_counter_ns()
        codec_payload = _encode_raw_payload(values, nulls)
        payload = nulls.serialize() + codec_payload
        null_count = sum(1 for v in values.values if v is None)
        non_null_values = [v for v in values.values if v is not None]
        distinct_count = len(set(canonical_key(values.logical_type, v) for v in non_null_values))
        min_value = min(non_null_values, default=None, key=lambda v: sort_key(values.logical_type, v))
        max_value = max(non_null_values, default=None, key=lambda v: sort_key(values.logical_type, v))
        raw_bytes = _estimate_raw_bytes(values, nulls)
        encoded_bytes = len(payload)
        encode_ns = time.perf_counter_ns() - start
        return EncodedBlock(
            encoding=Encoding.RAW,
            logical_type=values.logical_type,
            payload=payload,
            raw_bytes=raw_bytes,
            encoded_bytes=encoded_bytes,
            null_count=null_count,
            distinct_count=distinct_count,
            min_value=min_value,
            max_value=max_value,
            encode_ns=encode_ns,
        )

    @classmethod
    def decode(cls, block: EncodedBlock) -> ValueVector:
        nulls, offset = NullBitmap.deserialize(block.payload)
        values = _decode_raw_payload(block.logical_type, nulls, block.payload, offset)
        return ValueVector(logical_type=block.logical_type, values=values)

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
        values = cls.decode(block)
        partial = PartialAggregate()
        lt = block.logical_type
        for i, value in enumerate(values.values):
            if value is None:
                continue
            if aggregate == AggregateOp.COUNT:
                partial.count += 1
            elif aggregate == AggregateOp.SUM:
                partial.count += 1
                partial.sum = value if partial.sum is None else partial.sum + value
            elif aggregate == AggregateOp.MIN:
                partial.count += 1
                partial.min = value if partial.min is None else min(partial.min, value, key=lambda v: sort_key(lt, v))
            elif aggregate == AggregateOp.MAX:
                partial.count += 1
                partial.max = value if partial.max is None else max(partial.max, value, key=lambda v: sort_key(lt, v))
            elif aggregate == AggregateOp.AVG:
                partial.count += 1
                partial.sum = value if partial.sum is None else partial.sum + value
        return partial

    @classmethod
    def _filter_eq(cls, block: EncodedBlock, value: Any) -> SelectionVector:
        decoded = cls.decode(block)
        lt = block.logical_type
        bits = [values_equal(lt, v, value) if v is not None else False for v in decoded.values]
        return _bits_to_selection(bits)

    @classmethod
    def _filter_range(cls, block: EncodedBlock, predicate: PredicateRange) -> SelectionVector:
        decoded = cls.decode(block)
        lt = block.logical_type
        bits: list[bool] = []
        for v in decoded.values:
            if v is None:
                bits.append(False)
                continue
            ok = True
            if predicate.lower is not None:
                cmp = sort_key(lt, v) >= sort_key(lt, predicate.lower) if predicate.lower_inclusive else sort_key(lt, v) > sort_key(lt, predicate.lower)
                ok = ok and cmp
            if predicate.upper is not None:
                cmp = sort_key(lt, v) <= sort_key(lt, predicate.upper) if predicate.upper_inclusive else sort_key(lt, v) < sort_key(lt, predicate.upper)
                ok = ok and cmp
            bits.append(ok)
        return _bits_to_selection(bits)

    @classmethod
    def _filter_in(cls, block: EncodedBlock, values: tuple[Any, ...]) -> SelectionVector:
        decoded = cls.decode(block)
        lt = block.logical_type
        keys = {canonical_key(lt, v) for v in values}
        bits = [v is not None and canonical_key(lt, v) in keys for v in decoded.values]
        return _bits_to_selection(bits)

def _estimate_raw_bytes(values: ValueVector, nulls: NullBitmap) -> int:
    tid = values.logical_type.type_id
    n = values.length
    if tid == LogicalTypeId.BOOLEAN:
        body = (n + 7) // 8
    elif tid == LogicalTypeId.UTF8:
        blob = sum(len(v.encode("utf-8")) if v is not None else 0 for v in values.values)
        offset_width = 4 if n < 2**32 else 8
        body = 1 + 4 + (n + 1) * offset_width + blob
    else:
        width = values.logical_type.fixed_width or 0
        body = n * width
    return len(nulls.serialize()) + body


def _encode_raw_payload(values: ValueVector, nulls: NullBitmap) -> bytes:
    tid = values.logical_type.type_id
    if tid == LogicalTypeId.BOOLEAN:
        bits = [
            bool(values.values[i]) if not nulls.is_null(i) else False for i in range(values.length)
        ]
        return pack_boolean_bits(bits)

    if tid == LogicalTypeId.UTF8:
        blob = bytearray()
        offsets: list[int] = [0]
        for i in range(values.length):
            if nulls.is_null(i):
                offsets.append(len(blob))
                continue
            chunk = values.values[i].encode("utf-8")
            blob.extend(chunk)
            offsets.append(len(blob))
        max_offset = offsets[-1]
        offset_width = 4 if max_offset <= 0xFFFFFFFF else 8
        header = struct.pack("<BI", offset_width, len(offsets) - 1)
        offset_bytes = bytearray()
        pack_fmt = "<I" if offset_width == 4 else "<Q"
        for offset in offsets:
            offset_bytes.extend(struct.pack(pack_fmt, offset))
        return header + bytes(offset_bytes) + bytes(blob)

    parts = bytearray()
    for i in range(values.length):
        if nulls.is_null(i):
            placeholder = 0
            if tid == LogicalTypeId.FLOAT64:
                parts.extend(struct.pack("<d", float(placeholder)))
            elif tid == LogicalTypeId.DATE32:
                parts.extend(struct.pack("<i", placeholder))
            else:
                parts.extend(struct.pack("<q", placeholder))
        else:
            parts.extend(serialize_typed_value(values.logical_type, values.values[i]))
    return bytes(parts)


def _decode_raw_payload(
    logical_type: LogicalType,
    nulls: NullBitmap,
    data: bytes,
    offset: int,
) -> tuple[Any, ...]:
    tid = logical_type.type_id
    n = nulls.length
    if tid == LogicalTypeId.BOOLEAN:
        needed = (n + 7) // 8
        bits = unpack_boolean_bits(data[offset : offset + needed], n)
        return tuple(None if nulls.is_null(i) else bits[i] for i in range(n))

    if tid == LogicalTypeId.UTF8:
        if len(data) < offset + 5:
            raise ValueError("truncated UTF8 payload")
        offset_width, offset_count = struct.unpack_from("<BI", data, offset)
        pos = offset + 5
        pack_fmt = "<I" if offset_width == 4 else "<Q"
        size = struct.calcsize(pack_fmt)
        offsets: list[int] = []
        for _ in range(offset_count + 1):
            if pos + size > len(data):
                raise ValueError("truncated UTF8 offsets")
            (off,) = struct.unpack_from(pack_fmt, data, pos)
            offsets.append(off)
            pos += size
        blob = data[pos:]
        values: list[Any] = []
        for i in range(n):
            if nulls.is_null(i):
                values.append(None)
                continue
            start = offsets[i]
            end = offsets[i + 1]
            values.append(blob[start:end].decode("utf-8"))
        return tuple(values)

    values: list[Any] = []
    pos = offset
    for i in range(n):
        if nulls.is_null(i):
            _, pos = deserialize_typed_value(logical_type, data, pos)
            values.append(None)
        else:
            value, pos = deserialize_typed_value(logical_type, data, pos)
            values.append(value)
    return tuple(values)


def _bits_to_selection(bits: list[bool]) -> SelectionVector:
    n = len(bits)
    buf = bytearray((n + 7) // 8)
    for i, selected in enumerate(bits):
        if selected:
            buf[i // 8] |= 1 << (i % 8)
    return SelectionVector(length=n, bits=bytes(buf))
