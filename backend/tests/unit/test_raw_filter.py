from app.engine.codecs.base import PredicateEq, PredicateIn, PredicateRange
from app.engine.codecs.raw import RawCodec
from app.engine.types import LogicalType
from app.engine.vectors import NullBitmap, SelectionVector, ValueVector


def _raw_block(values: tuple[int, ...]):
    nulls = NullBitmap.from_flags([False] * len(values))
    vec = ValueVector(logical_type=LogicalType.int64(), values=list(values))
    return RawCodec.encode(vec, nulls)


def test_raw_filter_eq_range_in():
    block = _raw_block((1, 2, 3, 4, 5))
    eq = RawCodec.filter(block, PredicateEq(value=3))
    assert isinstance(eq, SelectionVector)
    assert eq.to_indices() == (2,)
    rng = RawCodec.filter(
        block,
        PredicateRange(lower=2, lower_inclusive=True, upper=4, upper_inclusive=True),
    )
    assert isinstance(rng, SelectionVector)
    assert rng.to_indices() == (1, 2, 3)
    ins = RawCodec.filter(block, PredicateIn(values=(1, 5)))
    assert ins.to_indices() == (0, 4)
