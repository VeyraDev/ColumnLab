from __future__ import annotations


def pack_varuint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varuint must be non-negative")
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def unpack_varuint(data: bytes, offset: int = 0) -> tuple[int, int]:
    result = 0
    shift = 0
    pos = offset
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if byte < 0x80:
            return result, pos
        shift += 7
        if shift > 63:
            raise ValueError("varuint overflow")
    raise ValueError("truncated varuint")


def pack_bits(codes: list[int], bit_width: int) -> bytes:
    if bit_width == 0:
        return b""
    if bit_width > 64:
        raise ValueError("bit_width too large")
    total_bits = len(codes) * bit_width
    buf = bytearray((total_bits + 7) // 8)
    bit_pos = 0
    mask = (1 << bit_width) - 1
    for code in codes:
        value = code & mask
        for bit in range(bit_width):
            if value & (1 << bit):
                byte_index = bit_pos // 8
                buf[byte_index] |= 1 << (bit_pos % 8)
            bit_pos += 1
    return bytes(buf)


def unpack_bits(data: bytes, count: int, bit_width: int) -> list[int]:
    if bit_width == 0:
        return [0] * count
    codes: list[int] = []
    bit_pos = 0
    mask = (1 << bit_width) - 1
    for _ in range(count):
        value = 0
        for bit in range(bit_width):
            byte_index = bit_pos // 8
            if byte_index < len(data) and (data[byte_index] & (1 << (bit_pos % 8))):
                value |= 1 << bit
            bit_pos += 1
        codes.append(value & mask)
    return codes
