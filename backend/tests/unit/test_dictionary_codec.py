import pytest

from app.engine.binary import pack_bits, unpack_bits
from app.engine.codecs.base import AggregateOp, PredicateEq, PredicateIn
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.types import LogicalType
from app.engine.vectors import ValueVector


def test_dictionary_roundtrip():
    values = ["a", "b", "a", None, "c", "b"]
    vector = ValueVector.from_typed(LogicalType.utf8(), values)
    nulls = vector.null_bitmap()
    block = DictionaryCodec.encode(vector, nulls)
    decoded = DictionaryCodec.decode(block)
    assert list(decoded.values) == values


def test_dictionary_bit_packing_non_multiple():
    values = ["x", "y"] * 5
    vector = ValueVector.from_typed(LogicalType.utf8(), values)
    block = DictionaryCodec.encode(vector, vector.null_bitmap())
    nulls, index, codes = __import__(
        "app.engine.codecs.dictionary", fromlist=["_parse_dictionary_payload"]
    )._parse_dictionary_payload(block)
    assert index.bit_width == 1
    assert len(codes) == 10


def test_dictionary_low_cardinality_smaller_than_raw():
    values = (["east", "west", "north"] * 50) + [None]
    vector = ValueVector.from_typed(LogicalType.utf8(), values)
    nulls = vector.null_bitmap()
    dict_block = DictionaryCodec.encode(vector, nulls)
    raw_block = RawCodec.encode(vector, nulls)
    assert dict_block.encoded_bytes < raw_block.encoded_bytes


def test_dictionary_negative_check():
    vector = ValueVector.from_typed(LogicalType.utf8(), ["a", "b", "a"])
    block = DictionaryCodec.encode(vector, vector.null_bitmap())
    assert DictionaryCodec.dictionary_negative_check(block, "missing")
    assert not DictionaryCodec.dictionary_negative_check(block, "a")


def test_dictionary_filter_in():
    vector = ValueVector.from_typed(LogicalType.utf8(), ["a", "b", "c", "a"])
    block = DictionaryCodec.encode(vector, vector.null_bitmap())
    sel = DictionaryCodec.filter(block, PredicateIn(("a", "c")))
    assert sel.is_selected(0)
    assert sel.is_selected(2)
    assert sel.is_selected(3)
    assert not sel.is_selected(1)


def test_dictionary_group_by_codes():
    vector = ValueVector.from_typed(LogicalType.int64(), [1, 2, 1, None, 2])
    block = DictionaryCodec.encode(vector, vector.null_bitmap())
    groups = DictionaryCodec.group_by_codes(block)
    assert sum(groups.values()) == 4
    assert len(groups) == 2


def test_dictionary_aggregate_min_max():
    vector = ValueVector.from_typed(LogicalType.int64(), [3, 1, 3])
    block = DictionaryCodec.encode(vector, vector.null_bitmap())
    partial_min = DictionaryCodec.aggregate(block, AggregateOp.MIN)
    partial_max = DictionaryCodec.aggregate(block, AggregateOp.MAX)
    assert partial_min.min == 1
    assert partial_max.max == 3
