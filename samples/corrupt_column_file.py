#!/usr/bin/env python3
"""复制一个 .col 文件并翻转 payload 附近的一个字节，用于验证 CRC32 损坏检测。"""
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("column_file", help="ColumnLab 生成的 .col 文件路径")
parser.add_argument("--offset", type=int, default=128, help="要翻转的字节偏移，默认 128")
args = parser.parse_args()

src = Path(args.column_file)
if not src.exists():
    raise SystemExit(f"文件不存在: {src}")

data = bytearray(src.read_bytes())
if len(data) <= args.offset:
    raise SystemExit(f"文件太短，无法修改 offset={args.offset}")

data[args.offset] ^= 0x01
dst = src.with_name(src.stem + ".corrupted" + src.suffix)
dst.write_bytes(data)
print(dst)
