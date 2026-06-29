from __future__ import annotations

import random
from pathlib import Path

from app.engine.storage.reader import ColumnReader
from app.engine.types import LogicalType


class VerificationError(Exception):
    pass


def verify_column_files(
    paths: dict[str, Path],
    logical_types: dict[str, LogicalType],
    *,
    full_verify: bool = False,
) -> None:
    if not paths:
        raise VerificationError("no column files")
    row_counts: list[int] = []
    for name, path in paths.items():
        reader = ColumnReader.open(path)
        row_counts.append(reader.header.total_rows)
        if reader.header.block_count != len(reader.index):
            raise VerificationError(f"{name}: block_count mismatch")
        block_ids = list(range(len(reader.index)))
        sample = block_ids if full_verify else _sample_blocks(block_ids)
        for block_id in sample:
            decoded = reader.decode_block(block_id)
            if decoded.length != reader.index[block_id].row_count:
                raise VerificationError(f"{name} block {block_id}: row count mismatch")
        if logical_types[name].type_id != reader.header.logical_type.type_id:
            raise VerificationError(f"{name}: logical type mismatch")
    if len(set(row_counts)) != 1:
        raise VerificationError(f"column row counts differ: {row_counts}")
    _verify_shared_row_groups(paths)


def _sample_blocks(block_ids: list[int]) -> list[int]:
    if not block_ids:
        return []
    picks = {0, block_ids[-1]}
    if len(block_ids) > 2:
        picks.add(random.choice(block_ids[1:-1]))
    return sorted(picks)


def _verify_shared_row_groups(paths: dict[str, Path]) -> None:
    readers = [ColumnReader.open(p) for p in paths.values()]
    ref = readers[0].index
    for reader in readers[1:]:
        if len(reader.index) != len(ref):
            raise VerificationError("block count mismatch across columns")
        for left, right in zip(ref, reader.index, strict=True):
            if left.row_start != right.row_start or left.row_count != right.row_count:
                raise VerificationError("row group boundaries mismatch")
