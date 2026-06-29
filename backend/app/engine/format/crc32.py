from __future__ import annotations

import zlib


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_crc32(data: bytes, expected: int) -> None:
    actual = crc32(data)
    if actual != expected:
        from app.engine.format.errors import CrcMismatchError

        raise CrcMismatchError(f"CRC mismatch: expected {expected:#010x}, got {actual:#010x}")
