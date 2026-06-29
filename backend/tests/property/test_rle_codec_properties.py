from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.codecs.rle import RleCodec
from app.engine.types import LogicalType
from app.engine.vectors import ValueVector


@given(
    st.lists(
        st.one_of(st.integers(min_value=-1000, max_value=1000), st.none()),
        min_size=0,
        max_size=128,
    )
)
@settings(max_examples=200)
def test_rle_property_roundtrip(values):
    vector = ValueVector.from_typed(LogicalType.int64(), values)
    nulls = vector.null_bitmap()
    decoded = RleCodec.decode(RleCodec.encode(vector, nulls))
    assert list(decoded.values) == values
