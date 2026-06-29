#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine.storage.reader import ColumnReader

DEFAULT_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "golden" / "fixtures"


def export_storage_map(fixtures_dir: Path) -> dict:
    manifest_path = fixtures_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}. Run golden tests first.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    columns_out = []
    total_blocks = 0
    for name, meta in manifest["columns"].items():
        path = fixtures_dir / meta["path"]
        reader = ColumnReader.open(path)
        blocks = []
        for entry in reader.index:
            header_block = reader.read_block(entry.block_id)
            blocks.append(
                {
                    "block_id": entry.block_id,
                    "row_group_id": entry.row_group_id,
                    "encoding": entry.encoding.name,
                    "row_start": entry.row_start,
                    "row_count": entry.row_count,
                    "compressed_bytes": entry.total_block_length,
                    "encoded_bytes": header_block.encoded_bytes,
                    "raw_bytes": header_block.raw_bytes,
                    "null_count": entry.null_count,
                    "payload_crc32": f"{entry.payload_crc32:08x}",
                }
            )
        total_blocks += len(blocks)
        columns_out.append(
            {
                "name": name,
                "logical_type": meta["logical_type"],
                "block_count": len(blocks),
                "blocks": blocks,
            }
        )
    return {
        "source": "golden-fixtures",
        "row_count": manifest.get("row_count", 0),
        "column_count": len(columns_out),
        "total_blocks": total_blocks,
        "columns": columns_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export storage-map.json for frontend fixtures")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Directory containing golden .col files and manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for storage-map.json",
    )
    args = parser.parse_args()
    payload = export_storage_map(args.fixtures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} ({payload['column_count']} columns, {payload['total_blocks']} blocks)")


if __name__ == "__main__":
    main()
