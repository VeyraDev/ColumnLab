from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

# Order: UTF-8 variants first, then common Windows / CJK fallbacks.
_CSV_ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "gbk", "cp1252", "latin-1")


def detect_csv_encoding(path: Path, sample_bytes: int = 65536) -> str:
    """Pick the first encoding that decodes a prefix of the file without error."""
    raw = path.read_bytes()[:sample_bytes]
    for encoding in _CSV_ENCODING_CANDIDATES:
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    # latin-1 never fails on bytes; last resort.
    return "latin-1"


def iter_csv_rows(
    path: Path,
    *,
    delimiter: str = ",",
    quotechar: str = '"',
    encoding: str | None = None,
) -> Iterator[list[str]]:
    chosen = encoding or detect_csv_encoding(path)
    with path.open("r", encoding=chosen, newline="", errors="strict") as fh:
        reader = csv.reader(fh, delimiter=delimiter, quotechar=quotechar)
        for row in reader:
            yield row


def read_csv_header(path: Path, **kwargs) -> list[str]:
    for row in iter_csv_rows(path, **kwargs):
        return [cell.strip() for cell in row]
    return []


def count_csv_data_rows(path: Path, **kwargs) -> int:
    count = 0
    for idx, _row in enumerate(iter_csv_rows(path, **kwargs)):
        if idx == 0:
            continue
        count += 1
    return count
