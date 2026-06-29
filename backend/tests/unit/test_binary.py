import pytest

from app.engine.binary import pack_bits, pack_varuint, unpack_bits, unpack_varuint


def test_varuint_roundtrip():
    for value in [0, 1, 127, 128, 16_383, 16_384, 2_000_000]:
        data = pack_varuint(value)
        decoded, end = unpack_varuint(data)
        assert decoded == value
        assert end == len(data)


def test_pack_bits_widths():
    codes = [0, 1, 0, 1, 1]
    packed = pack_bits(codes, 1)
    assert unpack_bits(packed, 5, 1) == codes

    codes3 = [0, 1, 2, 3, 4, 5, 6, 7]
    packed3 = pack_bits(codes3, 3)
    assert unpack_bits(packed3, 8, 3) == codes3


def test_pack_bits_non_multiple_of_eight():
    codes = [1, 2, 3, 4, 5]
    packed = pack_bits(codes, 3)
    assert unpack_bits(packed, 5, 3) == codes
