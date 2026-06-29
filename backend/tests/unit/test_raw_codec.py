from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.engine.codecs.raw import RawCodec
from app.engine.types import LogicalType
from app.engine.vectors import ValueVector


def _roundtrip(logical_type: LogicalType, values: list) -> list:
    vector = ValueVector.from_typed(logical_type, values)
    nulls = vector.null_bitmap()
    block = RawCodec.encode(vector, nulls)
    assert isinstance(block.payload, bytes)
    assert len(block.payload) > 0
    decoded = RawCodec.decode(block)
    return list(decoded.values)


@pytest.mark.parametrize(
    "logical_type,values,expected",
    [
        (LogicalType.int64(), [1, -2**63, 2**63 - 1, None], [1, -2**63, 2**63 - 1, None]),
        (LogicalType.float64(), [0.0, -1.5, None], [0.0, -1.5, None]),
        (LogicalType.boolean(), [True, False, None, True], [True, False, None, True]),
        (LogicalType.utf8(), ["", "你好", None, "ascii"], ["", "你好", None, "ascii"]),
        (LogicalType.date32(), [date(1970, 1, 2), None], [date(1970, 1, 2), None]),
        (
            LogicalType.timestamp64(),
            [datetime(2020, 1, 1, tzinfo=timezone.utc), None],
            [datetime(2020, 1, 1, tzinfo=timezone.utc), None],
        ),
        (LogicalType.decimal64(2), [Decimal("12.34"), None, Decimal("-0.01")], [Decimal("12.34"), None, Decimal("-0.01")]),
    ],
)
def test_raw_roundtrip_types(logical_type, values, expected):
    assert _roundtrip(logical_type, values) == expected


def test_payload_is_bytes_not_pickle():
    vector = ValueVector.from_typed(LogicalType.utf8(), ["a"])
    block = RawCodec.encode(vector, vector.null_bitmap())
    assert block.payload[:2] != b"\x80\x04"
