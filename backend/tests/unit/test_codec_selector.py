import json

import pytest

from app.engine.codecs.selector import select_codec
from app.engine.types import Encoding, LogicalType
from app.engine.vectors import ValueVector


def test_selector_prefers_rle_for_long_runs():
    values = [42] * 300
    vector = ValueVector.from_typed(LogicalType.int64(), values)
    result = select_codec(vector, vector.null_bitmap())
    assert result.winner.encoding == Encoding.RLE


def test_selector_prefers_dictionary_for_low_cardinality():
    values = ["alpha", "beta", "gamma"] * 80
    vector = ValueVector.from_typed(LogicalType.utf8(), values)
    result = select_codec(vector, vector.null_bitmap())
    assert result.winner.encoding == Encoding.DICTIONARY


def test_selector_falls_back_to_raw_for_high_cardinality():
    values = list(range(200))
    vector = ValueVector.from_typed(LogicalType.int64(), values)
    result = select_codec(vector, vector.null_bitmap())
    assert result.winner.encoding == Encoding.RAW


def test_selector_is_deterministic():
    values = [1, 1, 2, 2, 3, 3] * 10
    vector = ValueVector.from_typed(LogicalType.int64(), values)
    first = select_codec(vector, vector.null_bitmap())
    second = select_codec(vector, vector.null_bitmap())
    assert first.winner.encoding == second.winner.encoding
    assert first.selection_reason == second.selection_reason


def test_selector_to_dict_json_roundtrip():
    vector = ValueVector.from_typed(LogicalType.int64(), [1, 1, 1, 2, 2])
    result = select_codec(vector, vector.null_bitmap())
    payload = result.to_dict()
    json.dumps(payload)
    assert len(payload["candidates"]) == 3
    assert any(c["selected"] for c in payload["candidates"])
