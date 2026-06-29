from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.catalog.models.catalog import Column, ColumnBlockCatalog
from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.codecs.selector import select_codec
from app.engine.storage.reader import ColumnReader
from app.engine.types import Encoding
from app.engine.vectors import NullBitmap

CODEC_BY_ENCODING = {
    Encoding.RAW: RawCodec,
    Encoding.RLE: RleCodec,
    Encoding.DICTIONARY: DictionaryCodec,
}


class BlockInspectorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.catalog = CatalogRepository(db)
        self.datasets = DatasetRepository(db)

    def get_block(self, *, user_id: int, column_id: int, block_id: int) -> dict[str, Any]:
        col, block = self._resolve_block(user_id, column_id, block_id)
        return {
            "column_id": col.id,
            "column_name": col.name,
            "logical_type": col.logical_type,
            "block_id": block.block_id,
            "row_start": block.row_start,
            "row_count": block.row_count,
            "encoding": block.encoding,
            "raw_bytes": block.raw_bytes,
            "encoded_bytes": block.encoded_bytes,
            "compressed_bytes": block.total_block_length,
            "null_count": block.null_count,
            "distinct_count": block.distinct_count,
            "min_repr": block.min_repr,
            "max_repr": block.max_repr,
            "dictionary_count": block.dictionary_count,
            "run_count": block.run_count,
            "payload_crc32": block.payload_crc32,
        }

    def get_block_preview(self, *, user_id: int, column_id: int, block_id: int) -> dict[str, Any]:
        col, catalog_block = self._resolve_block(user_id, column_id, block_id)
        reader = ColumnReader.open(Path(col.column_file_path))
        encoded = reader.read_block(block_id)
        codec = CODEC_BY_ENCODING[encoded.encoding]
        decoded = codec.decode(encoded)
        nulls = NullBitmap.from_flags([v is None for v in decoded.values])
        selection = select_codec(decoded, nulls)
        preview = selection.to_dict()
        preview["block"] = {
            "encoding": catalog_block.encoding,
            "row_start": catalog_block.row_start,
            "row_count": catalog_block.row_count,
            "crc32": catalog_block.payload_crc32,
        }
        preview["column"] = {
            "id": col.id,
            "name": col.name,
            "logical_type": col.logical_type,
        }
        preview["stats"] = {
            "null_count": catalog_block.null_count,
            "distinct_count": catalog_block.distinct_count,
            "min_repr": catalog_block.min_repr,
            "max_repr": catalog_block.max_repr,
            "raw_bytes": catalog_block.raw_bytes,
            "encoded_bytes": catalog_block.encoded_bytes,
        }
        return preview

    def _resolve_block(
        self, user_id: int, column_id: int, block_id: int
    ) -> tuple[Column, ColumnBlockCatalog]:
        col = self.db.get(Column, column_id)
        if col is None:
            raise HTTPException(status_code=404, detail="列不存在")
        table = self.catalog.get_table(col.table_id)
        if table is None:
            raise HTTPException(status_code=404, detail="表不存在")
        version = self.catalog.get_version(table.dataset_version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="版本不存在")
        dataset = self.datasets.get_for_user(version.dataset_id, user_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="数据集不存在")
        block = next((b for b in self.catalog.list_blocks(column_id) if b.block_id == block_id), None)
        if block is None:
            raise HTTPException(status_code=404, detail="块不存在")
        return col, block
