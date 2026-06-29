from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.engine.types import LogicalType, LogicalTypeId


from app.engine.binary import pack_varuint as _pack_varuint
from app.engine.binary import unpack_varuint as _unpack_varuint
@dataclass(slots=True)
class NullBitmap:
    length: int
    bits: bytes

    def is_null(self, index: int) -> bool:
        if index < 0 or index >= self.length:
            raise IndexError(index)
        byte_index = index // 8
        bit_index = index % 8
        return bool(self.bits[byte_index] & (1 << bit_index))

    @classmethod
    def from_flags(cls, flags: list[bool]) -> NullBitmap:
        length = len(flags)
        buf = bytearray((length + 7) // 8)
        for i, is_null in enumerate(flags):
            if is_null:
                buf[i // 8] |= 1 << (i % 8)
        return cls(length=length, bits=bytes(buf))

    def serialize(self) -> bytes:
        return struct.pack("<II", self.length, len(self.bits)) + self.bits

    @classmethod
    def deserialize(cls, data: bytes, offset: int = 0) -> tuple[NullBitmap, int]:
        if len(data) < offset + 8:
            raise ValueError("truncated null bitmap header")
        logical_length, bitmap_len = struct.unpack_from("<II", data, offset)
        start = offset + 8
        end = start + bitmap_len
        if end > len(data):
            raise ValueError("truncated null bitmap payload")
        return cls(length=logical_length, bits=data[start:end]), end


@dataclass(slots=True)
class SelectionVector:
    length: int
    bits: bytes

    def is_selected(self, index: int) -> bool:
        if index < 0 or index >= self.length:
            raise IndexError(index)
        byte_index = index // 8
        bit_index = index % 8
        return bool(self.bits[byte_index] & (1 << bit_index))

    @classmethod
    def all_true(cls, length: int) -> SelectionVector:
        buf = bytearray((length + 7) // 8)
        for i in range(length):
            buf[i // 8] |= 1 << (i % 8)
        return cls(length=length, bits=bytes(buf))

    @classmethod
    def all_false(cls, length: int) -> SelectionVector:
        return cls(length=length, bits=bytes((length + 7) // 8))

    def selected_count(self) -> int:
        count = 0
        for i in range(self.length):
            if self.is_selected(i):
                count += 1
        return count

    def to_indices(self) -> tuple[int, ...]:
        return tuple(i for i in range(self.length) if self.is_selected(i))

    def invert(self) -> SelectionVector:
        buf = bytearray(self.bits)
        full_bytes = self.length // 8
        for i in range(full_bytes):
            buf[i] = (~buf[i]) & 0xFF
        remainder = self.length % 8
        if remainder:
            mask = (1 << remainder) - 1
            buf[full_bytes] = (~buf[full_bytes]) & mask
        return SelectionVector(length=self.length, bits=bytes(buf))

    def and_with(self, other: SelectionVector) -> SelectionVector:
        if self.length != other.length:
            raise ValueError("selection length mismatch")
        buf = bytes(a & b for a, b in zip(self.bits, other.bits, strict=True))
        return SelectionVector(length=self.length, bits=buf)

    def or_with(self, other: SelectionVector) -> SelectionVector:
        if self.length != other.length:
            raise ValueError("selection length mismatch")
        buf = bytes(a | b for a, b in zip(self.bits, other.bits, strict=True))
        return SelectionVector(length=self.length, bits=buf)


@dataclass(slots=True)
class ValueVector:
    logical_type: LogicalType
    values: tuple[Any, ...]

    @property
    def length(self) -> int:
        return len(self.values)

    def null_bitmap(self) -> NullBitmap:
        return NullBitmap.from_flags([v is None for v in self.values])

    @classmethod
    def from_typed(cls, logical_type: LogicalType, values: list[Any]) -> ValueVector:
        normalized = tuple(_normalize_value(logical_type, v) for v in values)
        return cls(logical_type=logical_type, values=normalized)


def canonical_key(logical_type: LogicalType, value: Any) -> Any:
    normalized = _normalize_value(logical_type, value)
    if logical_type.type_id == LogicalTypeId.FLOAT64 and isinstance(normalized, float) and normalized != normalized:
        return ("nan",)
    return normalized


def sort_key(logical_type: LogicalType, value: Any) -> tuple[int, Any]:
    key = canonical_key(logical_type, value)
    if isinstance(key, float) and key != key:
        return (1, 0)
    return (0, key)


def values_equal(logical_type: LogicalType, left: Any, right: Any) -> bool:
    return canonical_key(logical_type, left) == canonical_key(logical_type, right)


def _normalize_value(logical_type: LogicalType, value: Any) -> Any:
    if value is None:
        return None
    tid = logical_type.type_id
    if tid == LogicalTypeId.INT64:
        return int(value)
    if tid == LogicalTypeId.FLOAT64:
        result = float(value)
        if math.isnan(result):
            return result
        return result
    if tid == LogicalTypeId.BOOLEAN:
        return bool(value)
    if tid == LogicalTypeId.UTF8:
        if not isinstance(value, str):
            raise TypeError("UTF8 values must be str")
        return value
    if tid == LogicalTypeId.DATE32:
        if isinstance(value, date) and not isinstance(value, datetime):
            epoch = date(1970, 1, 1)
            return (value - epoch).days
        return int(value)
    if tid == LogicalTypeId.TIMESTAMP64:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            delta = value - epoch
            return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds
        return int(value)
    if tid == LogicalTypeId.DECIMAL64:
        if isinstance(value, int):
            return value
        if isinstance(value, Decimal):
            scaled = int(value * (10**logical_type.scale))
        else:
            scaled = int(round(float(value) * (10**logical_type.scale)))
        return scaled
    raise ValueError(f"unsupported logical type {tid}")


def _denormalize_value(logical_type: LogicalType, value: Any) -> Any:
    if value is None:
        return None
    tid = logical_type.type_id
    if tid == LogicalTypeId.INT64:
        return int(value)
    if tid == LogicalTypeId.FLOAT64:
        return float(value)
    if tid == LogicalTypeId.BOOLEAN:
        return bool(value)
    if tid == LogicalTypeId.UTF8:
        return str(value)
    if tid == LogicalTypeId.DATE32:
        epoch = date(1970, 1, 1)
        return epoch.fromordinal(epoch.toordinal() + int(value))
    if tid == LogicalTypeId.TIMESTAMP64:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return epoch + timedelta(microseconds=int(value))
    if tid == LogicalTypeId.DECIMAL64:
        return Decimal(int(value)) / (Decimal(10) ** logical_type.scale)
    raise ValueError(f"unsupported logical type {tid}")


def serialize_typed_value(logical_type: LogicalType, value: Any) -> bytes:
    normalized = _normalize_value(logical_type, value)
    tid = logical_type.type_id
    if tid == LogicalTypeId.INT64:
        return struct.pack("<q", int(normalized))
    if tid == LogicalTypeId.FLOAT64:
        return struct.pack("<d", float(normalized))
    if tid == LogicalTypeId.BOOLEAN:
        return b"\x01" if normalized else b"\x00"
    if tid == LogicalTypeId.DATE32:
        return struct.pack("<i", int(normalized))
    if tid == LogicalTypeId.TIMESTAMP64:
        return struct.pack("<q", int(normalized))
    if tid == LogicalTypeId.DECIMAL64:
        return struct.pack("<q", int(normalized))
    if tid == LogicalTypeId.UTF8:
        encoded = str(normalized).encode("utf-8")
        return struct.pack("<I", len(encoded)) + encoded
    raise ValueError(f"serialize_typed_value does not support {tid}")


def deserialize_typed_value(logical_type: LogicalType, data: bytes, offset: int = 0) -> tuple[Any, int]:
    tid = logical_type.type_id
    if tid == LogicalTypeId.INT64:
        (value,) = struct.unpack_from("<q", data, offset)
        return _denormalize_value(logical_type, value), offset + 8
    if tid == LogicalTypeId.FLOAT64:
        (value,) = struct.unpack_from("<d", data, offset)
        return _denormalize_value(logical_type, value), offset + 8
    if tid == LogicalTypeId.BOOLEAN:
        return _denormalize_value(logical_type, data[offset] != 0), offset + 1
    if tid == LogicalTypeId.DATE32:
        (value,) = struct.unpack_from("<i", data, offset)
        return _denormalize_value(logical_type, value), offset + 4
    if tid == LogicalTypeId.TIMESTAMP64:
        (value,) = struct.unpack_from("<q", data, offset)
        return _denormalize_value(logical_type, value), offset + 8
    if tid == LogicalTypeId.DECIMAL64:
        (value,) = struct.unpack_from("<q", data, offset)
        return _denormalize_value(logical_type, value), offset + 8
    if tid == LogicalTypeId.UTF8:
        (length,) = struct.unpack_from("<I", data, offset)
        start = offset + 4
        end = start + length
        return _denormalize_value(logical_type, data[start:end].decode("utf-8")), end
    raise ValueError(f"deserialize_typed_value does not support {tid}")


def pack_boolean_bits(values: list[bool]) -> bytes:
    buf = bytearray((len(values) + 7) // 8)
    for i, value in enumerate(values):
        if value:
            buf[i // 8] |= 1 << (i % 8)
    return bytes(buf)


def unpack_boolean_bits(data: bytes, length: int) -> list[bool]:
    return [bool(data[i // 8] & (1 << (i % 8))) for i in range(length)]
