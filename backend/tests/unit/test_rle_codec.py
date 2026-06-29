import pytest

from app.engine.codecs.base import AggregateOp, PredicateEq, PredicateRange
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.types import LogicalType
from app.engine.vectors import ValueVector


def _roundtrip(values: list, logical_type=LogicalType.int64()):
    vector = ValueVector.from_typed(logical_type, values)
    nulls = vector.null_bitmap()
    block = RleCodec.encode(vector, nulls)
    decoded = RleCodec.decode(block)
    return list(decoded.values), block


def test_rle_roundtrip_with_null_break():
    result, _ = _roundtrip([1, 1, None, 1, 2, 2, 2])
    assert result == [1, 1, None, 1, 2, 2, 2]


def test_rle_long_run_smaller_than_raw():
    values = [7] * 200
    vector = ValueVector.from_typed(LogicalType.int64(), values)
    nulls = vector.null_bitmap()
    rle = RleCodec.encode(vector, nulls)
    raw = RawCodec.encode(vector, nulls)
    assert rle.encoded_bytes < raw.encoded_bytes


def test_rle_filter_eq():
    vector = ValueVector.from_typed(LogicalType.int64(), [1, 1, None, 2, 2])
    nulls = vector.null_bitmap()
    block = RleCodec.encode(vector, nulls)
    sel = RleCodec.filter(block, PredicateEq(2))
    assert sel.is_selected(3)
    assert sel.is_selected(4)
    assert not sel.is_selected(0)


def test_rle_aggregate_count_without_decode(monkeypatch):
    vector = ValueVector.from_typed(LogicalType.int64(), [3, 3, None, 4])
    block = RleCodec.encode(vector, vector.null_bitmap())

    def fail_decode(_block):
        raise AssertionError("decode should not be called")

    monkeypatch.setattr(RleCodec, "decode", fail_decode)
    partial = RleCodec.aggregate(block, AggregateOp.COUNT)
    assert partial.count == 3


def test_rle_aggregate_sum():
    vector = ValueVector.from_typed(LogicalType.int64(), [2, 2, 2])
    block = RleCodec.encode(vector, vector.null_bitmap())
    partial = RleCodec.aggregate(block, AggregateOp.SUM)
    assert partial.sum == 6
    assert partial.count == 3


def test_rle_filter_range():
    vector = ValueVector.from_typed(LogicalType.int64(), [1, 5, 5, 10])
    block = RleCodec.encode(vector, vector.null_bitmap())
    sel = RleCodec.filter(block, PredicateRange(lower=4, upper=6))
    assert sel.is_selected(1)
    assert sel.is_selected(2)
    assert not sel.is_selected(0)
