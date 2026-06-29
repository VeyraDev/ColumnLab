import math
from datetime import date, datetime, timezone
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.codecs.raw import RawCodec
from app.engine.types import LogicalType
from app.engine.vectors import ValueVector


def _assert_roundtrip(logical_type: LogicalType, values: list) -> None:
    vector = ValueVector.from_typed(logical_type, values)
    nulls = vector.null_bitmap()
    decoded = RawCodec.decode(RawCodec.encode(vector, nulls))
    assert list(decoded.values) == values


@given(st.lists(st.integers(min_value=-(2**63), max_value=2**63 - 1), min_size=0, max_size=128))
@settings(max_examples=200)
def test_property_int64(values):
    _assert_roundtrip(LogicalType.int64(), values)


@given(
    st.lists(
        st.one_of(
            st.floats(allow_nan=False, allow_infinity=False, width=64),
            st.none(),
        ),
        min_size=0,
        max_size=128,
    )
)
@settings(max_examples=200)
def test_property_float64(values):
    normalized = [None if v is None else float(v) for v in values]
    _assert_roundtrip(LogicalType.float64(), normalized)


@given(st.lists(st.one_of(st.booleans(), st.none()), min_size=0, max_size=128))
@settings(max_examples=200)
def test_property_boolean(values):
    _assert_roundtrip(LogicalType.boolean(), values)


@given(st.lists(st.one_of(st.text(), st.none()), min_size=0, max_size=64))
@settings(max_examples=200)
def test_property_utf8(values):
    _assert_roundtrip(LogicalType.utf8(), values)


@given(st.lists(st.one_of(st.integers(min_value=-100000, max_value=100000), st.none()), min_size=0, max_size=64))
@settings(max_examples=100)
def test_property_date32(values):
    converted = [
        None if v is None else date(1970, 1, 1).fromordinal(date(1970, 1, 1).toordinal() + v) for v in values
    ]
    _assert_roundtrip(LogicalType.date32(), converted)


@given(
    st.lists(
        st.one_of(
            st.datetimes(
                timezones=st.just(timezone.utc),
                min_value=datetime(1970, 1, 2),
                max_value=datetime(2099, 12, 31),
            ),
            st.none(),
        ),
        min_size=0,
        max_size=64,
    )
)
@settings(max_examples=100)
def test_property_timestamp64(values):
    _assert_roundtrip(LogicalType.timestamp64(), values)


@given(
    st.lists(
        st.one_of(
            st.decimals(
                allow_nan=False,
                allow_infinity=False,
                places=2,
                min_value=Decimal("-92233720368547"),
                max_value=Decimal("92233720368547"),
            ),
            st.none(),
        ),
        min_size=0,
        max_size=64,
    )
)
@settings(max_examples=100)
def test_property_decimal64(values):
    _assert_roundtrip(LogicalType.decimal64(2), values)


@given(st.data(), st.integers(min_value=0, max_value=64))
@settings(max_examples=200)
def test_property_mixed_nulls(data, size):
    values = data.draw(
        st.lists(
            st.one_of(st.integers(min_value=-1000, max_value=1000), st.none()),
            min_size=size,
            max_size=size,
        )
    )
    _assert_roundtrip(LogicalType.int64(), values)
