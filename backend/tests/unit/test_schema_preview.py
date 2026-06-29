"""Unit tests for schema preview and index stats encoding."""

from app.engine.format.constants import BLOCK_HEADER_SIZE
from app.engine.format.headers import BlockIndexEntry, decode_stats, encode_stats, pack_index, unpack_index
from app.engine.import_pipeline.schema_preview import infer_schema_from_path
from app.engine.types import Encoding, LogicalType


def test_index_stats_offset_roundtrip_int_one():
    stats = encode_stats(LogicalType.int64(), 1, 100)
    entry = BlockIndexEntry(
        block_id=0,
        row_group_id=0,
        offset=64,
        total_block_length=200,
        row_start=0,
        row_count=512,
        encoding=Encoding.RAW,
        null_count=0,
        payload_crc32=0x12345678,
        stats_offset=BLOCK_HEADER_SIZE,
        stats_length=len(stats),
    )
    restored = unpack_index(pack_index([entry]))[0]
    assert restored.stats_offset == BLOCK_HEADER_SIZE
    assert restored.stats_length == len(stats)
    min_value, max_value = decode_stats(LogicalType.int64(), stats)
    assert min_value == 1
    assert max_value == 100


def test_infer_schema_from_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("id,name,qty\n1,alice,10\n2,bob,20\n", encoding="utf-8")
    columns = infer_schema_from_path(csv_path)
    names = {c["name"]: c["logical_type"] for c in columns}
    assert names["id"] == "INT64"
    assert names["name"] == "UTF8"
    assert names["qty"] == "INT64"
