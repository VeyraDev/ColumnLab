from pathlib import Path

import pytest

from app.engine.import_pipeline.csv_parser import count_csv_data_rows, iter_csv_rows, read_csv_header

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def test_read_csv_header():
    header = read_csv_header(SAMPLES / "basic.csv")
    assert header == ["id", "name", "status", "qty", "flag"]


def test_count_csv_rows():
    assert count_csv_data_rows(SAMPLES / "basic.csv") == 5


def test_iter_csv_rows_streaming():
    rows = list(iter_csv_rows(SAMPLES / "basic.csv"))
    assert len(rows) == 6
