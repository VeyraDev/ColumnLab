from app.engine.format.crc32 import crc32, verify_crc32
import pytest
from app.engine.format.errors import CrcMismatchError


def test_crc32_known():
    assert crc32(b"123456789") == 0xCBF43926


def test_verify_crc32_raises():
    with pytest.raises(CrcMismatchError):
        verify_crc32(b"abc", 0)
