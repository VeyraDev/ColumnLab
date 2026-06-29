from __future__ import annotations

import random
from pathlib import Path

from app.engine.storage.row_group import build_slices_from_columns
from app.engine.storage.writer import ColumnWriter
from app.engine.types import LogicalType

GOLDEN_EPOCH = 1_700_000_000
GOLDEN_ROW_COUNT = 8000
GOLDEN_TARGET_BYTES = 1536
GOLDEN_MIN_ROWS = 80
GOLDEN_MAX_ROWS = 800

GOLDEN_COLUMNS: dict[str, tuple[LogicalType, str]] = {
    "id": (LogicalType.int64(), "int64"),
    "status": (LogicalType.utf8(), "utf8"),
    "qty": (LogicalType.int64(), "int64"),
    "price": (LogicalType.float64(), "float64"),
    "flag": (LogicalType.boolean(), "boolean"),
    "score": (LogicalType.int64(), "int64"),
}


def _build_rle_plateau_values(count: int, rng: random.Random) -> list[int]:
    """Long repeated plateaus so select_codec picks RLE within row groups."""
    values: list[int] = []
    plateau = 0
    while len(values) < count:
        run_len = rng.randint(48, 128)
        token = plateau % 16
        values.extend([token] * min(run_len, count - len(values)))
        plateau += 1
    return values


def build_golden_row_data(seed: int = 42) -> dict[str, list]:
    rng = random.Random(seed)
    statuses = ["active", "pending", "done", "archived"]
    return {
        "id": list(range(GOLDEN_ROW_COUNT)),
        "status": [rng.choice(statuses) for _ in range(GOLDEN_ROW_COUNT)],
        "qty": _build_rle_plateau_values(GOLDEN_ROW_COUNT, rng),
        "price": [round(rng.uniform(1.0, 999.0), 2) for _ in range(GOLDEN_ROW_COUNT)],
        "flag": [rng.choice([True, False]) for _ in range(GOLDEN_ROW_COUNT)],
        "score": [rng.randint(0, 100) for _ in range(GOLDEN_ROW_COUNT)],
    }


def write_golden_column_files(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_golden_row_data()
    slices = build_slices_from_columns(
        rows,
        target_block_bytes=GOLDEN_TARGET_BYTES,
        min_rows=GOLDEN_MIN_ROWS,
        max_rows=GOLDEN_MAX_ROWS,
    )
    paths: dict[str, Path] = {}
    for idx, (name, (logical_type, _)) in enumerate(GOLDEN_COLUMNS.items()):
        path = output_dir / f"{name}.col"
        writer = ColumnWriter(
            path,
            logical_type,
            column_id=idx + 1,
            target_block_bytes=GOLDEN_TARGET_BYTES,
            schema_fingerprint=0xDEADBEEF,
            created_at_epoch=GOLDEN_EPOCH,
        )
        for slice_ in slices:
            writer.write_slice(slice_, name)
        writer.finalize()
        paths[name] = path
    return paths
