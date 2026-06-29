from pathlib import Path

import pytest

from app.engine.import_pipeline.csv_parser import detect_csv_encoding, iter_csv_rows


def test_detect_csv_encoding_utf8(tmp_path: Path):
    path = tmp_path / "utf8.csv"
    path.write_text("name,value\nalice,1\n", encoding="utf-8")
    assert detect_csv_encoding(path) in {"utf-8", "utf-8-sig"}


def test_detect_csv_encoding_cp1252(tmp_path: Path):
    path = tmp_path / "win.csv"
    # byte 0xA0 is non-breaking space in cp1252, invalid utf-8 start byte
    path.write_bytes(b"name,note\nalice,caf\xe0\n")
    assert detect_csv_encoding(path) == "cp1252"
    rows = list(iter_csv_rows(path))
    assert len(rows) == 2
