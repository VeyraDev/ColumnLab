from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Any

from app.engine.binary import pack_bits, unpack_bits
from app.engine.codecs.base import (
    NOT_SUPPORTED,
    AggregateOp,
    CodecCapabilities,
    EncodedBlock,
    PartialAggregate,
    PredicateEq,
    PredicateIn,
)
from app.engine.codecs.raw import RawCodec
from app.engine.types import Encoding, LogicalType
from app.engine.vectors import (
    NullBitmap,
    SelectionVector,
    ValueVector,
    canonical_key,
    deserialize_typed_value,
    serialize_typed_value,
    sort_key,
    values_equal,
)


@dataclass(slots=True)
class DictionaryIndex:
    entries: list[Any]
    value_to_code: dict[Any, int]
    bit_width: int


class DictionaryCodec:
    encoding_id = Encoding.DICTIONARY

    @classmethod
    def encode(cls, values: ValueVector, nulls: NullBitmap) -> EncodedBlock:
        if values.length != nulls.length:
            raise ValueError("values and null bitmap length mismatch")
        start = time.perf_counter_ns()
        index = _build_dictionary(values, nulls)
        codes = _assign_codes(values, nulls, index)
        packed = pack_bits(codes, index.bit_width)
        dict_body = bytearray()
        for entry in index.entries:
            dict_body.extend(serialize_typed_value(values.logical_type, entry))
        body = bytearray()
        body.extend(struct.pack("<I", len(index.entries)))
        body.extend(bytes(dict_body))
        body.extend(struct.pack("<BI", index.bit_width, len(packed)))
        body.extend(packed)
        payload = nulls.serialize() + bytes(body)
        null_count = sum(1 for v in values.values if v is None)
        non_null = [v for v in values.values if v is not None]
        min_value = min(non_null, default=None, key=lambda v: sort_key(values.logical_type, v))
        max_value = max(non_null, default=None, key=lambda v: sort_key(values.logical_type, v))
        raw_block = RawCodec.encode(values, nulls)
        encode_ns = time.perf_counter_ns() - start
        return EncodedBlock(
            encoding=Encoding.DICTIONARY,
            logical_type=values.logical_type,
            payload=payload,
            raw_bytes=raw_block.raw_bytes,
            encoded_bytes=len(payload),
            null_count=null_count,
            distinct_count=len(index.entries),
            min_value=min_value,
            max_value=max_value,
            dictionary_count=len(index.entries),
            encode_ns=encode_ns,
        )

    @classmethod
    def decode(cls, block: EncodedBlock) -> ValueVector:
        nulls, index, codes = _parse_dictionary_payload(block)
        values: list[Any] = [None] * nulls.length
        for i in range(nulls.length):
            if nulls.is_null(i):
                continue
            values[i] = index.entries[codes[i]]
        return ValueVector(logical_type=block.logical_type, values=tuple(values))

    @classmethod
    def estimate_capabilities(cls) -> CodecCapabilities:
        return CodecCapabilities(supports_filter=True, supports_aggregate=True)

    @classmethod
    def filter(cls, block: EncodedBlock, predicate: object) -> SelectionVector | object:
        if isinstance(predicate, PredicateEq):
            return cls._filter_eq(block, predicate.value)
        if isinstance(predicate, PredicateIn):
            return cls._filter_in(block, predicate.values)
        return NOT_SUPPORTED

    @classmethod
    def aggregate(cls, block: EncodedBlock, aggregate: object) -> PartialAggregate | object:
        if not isinstance(aggregate, AggregateOp):
            return NOT_SUPPORTED
        nulls, index, codes = _parse_dictionary_payload(block)
        logical_type = block.logical_type
        partial = PartialAggregate()
        for i in range(nulls.length):
            if nulls.is_null(i):
                continue
            value = index.entries[codes[i]]
            if aggregate == AggregateOp.COUNT:
                partial.count += 1
            elif aggregate == AggregateOp.MIN:
                partial.count += 1
                partial.min = value if partial.min is None else min(partial.min, value, key=lambda v: sort_key(logical_type, v))
            elif aggregate == AggregateOp.MAX:
                partial.count += 1
                partial.max = value if partial.max is None else max(partial.max, value, key=lambda v: sort_key(logical_type, v))
            else:
                return NOT_SUPPORTED
        return partial

    @classmethod
    def dictionary_negative_check(cls, block: EncodedBlock, value: Any) -> bool:
        _, index, _ = _parse_dictionary_payload(block)
        key = canonical_key(block.logical_type, value)
        return key not in index.value_to_code

    @classmethod
    def group_by_codes(cls, block: EncodedBlock) -> dict[int, int]:
        nulls, _, codes = _parse_dictionary_payload(block)
        counts: dict[int, int] = {}
        for i in range(nulls.length):
            if nulls.is_null(i):
                continue
            code = codes[i]
            counts[code] = counts.get(code, 0) + 1
        return counts

    @classmethod
    def _filter_eq(cls, block: EncodedBlock, target: Any) -> SelectionVector:
        nulls, index, codes = _parse_dictionary_payload(block)
        key = canonical_key(block.logical_type, target)
        if key not in index.value_to_code:
            return SelectionVector(length=nulls.length, bits=bytes((nulls.length + 7) // 8))
        target_code = index.value_to_code[key]
        buf = bytearray((nulls.length + 7) // 8)
        for i in range(nulls.length):
            if nulls.is_null(i):
                continue
            if codes[i] == target_code:
                buf[i // 8] |= 1 << (i % 8)
        return SelectionVector(length=nulls.length, bits=bytes(buf))

    @classmethod
    def _filter_in(cls, block: EncodedBlock, targets: tuple[Any, ...]) -> SelectionVector:
        nulls, index, codes = _parse_dictionary_payload(block)
        target_codes = {
            index.value_to_code[canonical_key(block.logical_type, value)]
            for value in targets
            if canonical_key(block.logical_type, value) in index.value_to_code
        }
        buf = bytearray((nulls.length + 7) // 8)
        for i in range(nulls.length):
            if nulls.is_null(i):
                continue
            if codes[i] in target_codes:
                buf[i // 8] |= 1 << (i % 8)
        return SelectionVector(length=nulls.length, bits=bytes(buf))


def _build_dictionary(values: ValueVector, nulls: NullBitmap) -> DictionaryIndex:
    unique: dict[Any, Any] = {}
    for i in range(values.length):
        if nulls.is_null(i):
            continue
        key = canonical_key(values.logical_type, values.values[i])
        if key not in unique:
            unique[key] = values.values[i]
    entries = sorted(unique.values(), key=lambda v: sort_key(values.logical_type, v))
    value_to_code = {canonical_key(values.logical_type, entry): idx for idx, entry in enumerate(entries)}
    dict_count = len(entries)
    bit_width = 0 if dict_count == 0 else max(1, (dict_count - 1).bit_length())
    return DictionaryIndex(entries=entries, value_to_code=value_to_code, bit_width=bit_width)


def _assign_codes(values: ValueVector, nulls: NullBitmap, index: DictionaryIndex) -> list[int]:
    codes = [0] * values.length
    for i in range(values.length):
        if nulls.is_null(i):
            continue
        key = canonical_key(values.logical_type, values.values[i])
        codes[i] = index.value_to_code[key]
    return codes


def _parse_dictionary_payload(block: EncodedBlock) -> tuple[NullBitmap, DictionaryIndex, list[int]]:
    nulls, offset = NullBitmap.deserialize(block.payload)
    if len(block.payload) < offset + 4:
        raise ValueError("truncated dictionary header")
    (dict_count,) = struct.unpack_from("<I", block.payload, offset)
    pos = offset + 4
    entries: list[Any] = []
    logical_type = block.logical_type
    for _ in range(dict_count):
        value, pos = deserialize_typed_value(logical_type, block.payload, pos)
        entries.append(value)
    if len(block.payload) < pos + 5:
        raise ValueError("truncated dictionary codes header")
    bit_width, packed_len = struct.unpack_from("<BI", block.payload, pos)
    pos += 5
    packed = block.payload[pos : pos + packed_len]
    pos += packed_len
    codes = unpack_bits(packed, nulls.length, bit_width)
    value_to_code = {canonical_key(logical_type, entry): idx for idx, entry in enumerate(entries)}
    index = DictionaryIndex(entries=entries, value_to_code=value_to_code, bit_width=bit_width)
    return nulls, index, codes


def extract_dictionary_for_preview(block: EncodedBlock) -> dict[str, Any]:
    nulls, index, codes = _parse_dictionary_payload(block)
    _, offset = NullBitmap.deserialize(block.payload)
    pos = offset + 4
    for _ in index.entries:
        _, pos = deserialize_typed_value(block.logical_type, block.payload, pos)
    bit_width, packed_len = struct.unpack_from("<BI", block.payload, pos)
    packed = block.payload[pos + 5 : pos + 5 + packed_len]
    return {
        "dictionary_count": len(index.entries),
        "bit_width": index.bit_width,
        "entries": index.entries,
        "packed_codes_hex": packed[:16].hex(),
        "sample_codes": codes[: min(8, len(codes))],
        "row_count": nulls.length,
    }
