from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.engine.format.constants import FILE_MAGIC, FOOTER_MAGIC
from app.engine.storage.reader import ColumnReader
from tests.golden.golden_data import (
    GOLDEN_COLUMNS,
    build_golden_row_data,
    write_golden_column_files,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_manifest() -> dict:
    from tests.golden.golden_data import GOLDEN_EPOCH, GOLDEN_ROW_COUNT

    paths = write_golden_column_files(FIXTURES_DIR)
    manifest: dict = {
        "format_version": 1,
        "created_at_epoch": GOLDEN_EPOCH,
        "row_count": GOLDEN_ROW_COUNT,
        "columns": {},
    }
    for name, path in paths.items():
        reader = ColumnReader.open(path)
        manifest["columns"][name] = {
            "path": path.name,
            "logical_type": GOLDEN_COLUMNS[name][1],
            "sha256": _file_sha256(path),
            "total_rows": reader.header.total_rows,
            "block_count": reader.header.block_count,
            "footer_offset": reader.header.footer_offset,
            "index_length": reader.footer.index_length,
            "blocks": [
                {
                    "block_id": entry.block_id,
                    "row_group_id": entry.row_group_id,
                    "row_start": entry.row_start,
                    "row_count": entry.row_count,
                    "encoding": entry.encoding.name,
                    "offset": entry.offset,
                    "total_block_length": entry.total_block_length,
                    "payload_crc32": f"{entry.payload_crc32:08x}",
                }
                for entry in reader.index
            ],
        }
    return manifest


@pytest.fixture(scope="session")
def golden_manifest(request) -> dict:
    if request.config.getoption("--update-golden"):
        manifest = _build_manifest()
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    if not MANIFEST_PATH.exists():
        manifest = _build_manifest()
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_golden_files_exist(golden_manifest: dict) -> None:
    for name, meta in golden_manifest["columns"].items():
        path = FIXTURES_DIR / meta["path"]
        assert path.exists(), f"missing golden file for {name}"


def test_golden_sha256(golden_manifest: dict) -> None:
    for name, meta in golden_manifest["columns"].items():
        path = FIXTURES_DIR / meta["path"]
        assert _file_sha256(path) == meta["sha256"], f"SHA256 mismatch for {name}"


def test_golden_header_footer_fields(golden_manifest: dict) -> None:
    for name, meta in golden_manifest["columns"].items():
        path = FIXTURES_DIR / meta["path"]
        data = path.read_bytes()
        assert data.startswith(FILE_MAGIC)
        reader = ColumnReader.open(path)
        assert reader.header.total_rows == meta["total_rows"]
        assert reader.header.block_count == meta["block_count"]
        assert reader.header.footer_offset == meta["footer_offset"]
        assert reader.footer.index_length == meta["index_length"]
        assert len(reader.index) == meta["block_count"]
        assert data[reader.header.footer_offset : reader.header.footer_offset + 8] == FOOTER_MAGIC


def test_golden_index_entries(golden_manifest: dict) -> None:
    for name, meta in golden_manifest["columns"].items():
        reader = ColumnReader.open(FIXTURES_DIR / meta["path"])
        expected = meta["blocks"]
        assert len(reader.index) == len(expected)
        for entry, exp in zip(reader.index, expected, strict=True):
            assert entry.block_id == exp["block_id"]
            assert entry.row_start == exp["row_start"]
            assert entry.row_count == exp["row_count"]
            assert entry.encoding.name == exp["encoding"]
            assert entry.offset == exp["offset"]
            assert f"{entry.payload_crc32:08x}" == exp["payload_crc32"]


def test_golden_decode_roundtrip(golden_manifest: dict) -> None:
    rows = build_golden_row_data()
    for name, meta in golden_manifest["columns"].items():
        reader = ColumnReader.open(FIXTURES_DIR / meta["path"])
        decoded: list = []
        for entry in reader.index:
            vec = reader.decode_block(entry.block_id)
            decoded.extend(vec.values)
        assert len(decoded) == len(rows[name])
        assert decoded == rows[name]
