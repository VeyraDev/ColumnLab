from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from app.engine.codecs.base import EncodedBlock
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.format.constants import BLOCK_HEADER_SIZE, FILE_HEADER_SIZE, FOOTER_SIZE
from app.engine.format.crc32 import verify_crc32
from app.engine.format.errors import CrcMismatchError, TruncatedFileError
from app.engine.format.headers import (
    BlockHeader,
    BlockIndexEntry,
    FileFooter,
    FileHeader,
    decode_stats,
    unpack_index,
)
from app.engine.types import Encoding, LogicalType


CODEC_BY_ENCODING = {
    Encoding.RAW: RawCodec,
    Encoding.RLE: RleCodec,
    Encoding.DICTIONARY: DictionaryCodec,
}


@dataclass(slots=True)
class ColumnReader:
    path: Path
    header: FileHeader
    footer: FileFooter
    index: list[BlockIndexEntry]
    _fh: BinaryIO | None = field(default=None, repr=False)

    @classmethod
    def open(cls, path: Path | str) -> ColumnReader:
        path = Path(path)
        fh = open(path, "rb")
        try:
            header_bytes = fh.read(FILE_HEADER_SIZE)
            if len(header_bytes) < FILE_HEADER_SIZE:
                raise TruncatedFileError("column file too short")
            header = FileHeader.unpack(header_bytes)
            fh.seek(header.footer_offset)
            footer_bytes = fh.read(FOOTER_SIZE)
            if len(footer_bytes) < FOOTER_SIZE:
                raise TruncatedFileError("footer truncated")
            footer = FileFooter.unpack(footer_bytes, 0)
            fh.seek(footer.index_offset)
            index_bytes = fh.read(footer.index_length)
            if len(index_bytes) < footer.index_length:
                raise TruncatedFileError("index truncated")
            verify_crc32(index_bytes, footer.index_crc32)
            index = unpack_index(index_bytes)
        except Exception:
            fh.close()
            raise
        return cls(path=path, header=header, footer=footer, index=index, _fh=fh)

    @classmethod
    def load_index_only(cls, path: Path | str) -> list[BlockIndexEntry]:
        reader = cls.open(path)
        try:
            return list(reader.index)
        finally:
            reader.close()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _file(self) -> BinaryIO:
        if self._fh is None:
            self._fh = open(self.path, "rb")
        return self._fh

    def read_block(self, block_id: int) -> EncodedBlock:
        entry = self._get_entry(block_id)
        fh = self._file()
        fh.seek(entry.offset)
        chunk = fh.read(entry.total_block_length)
        if len(chunk) < entry.total_block_length:
            raise TruncatedFileError("block extends beyond file")
        header, pos = BlockHeader.unpack(chunk, 0)
        stats = chunk[pos : pos + header.stats_bytes]
        payload = chunk[pos + header.stats_bytes :]
        verify_crc32(payload, entry.payload_crc32)
        if header.payload_crc32 != entry.payload_crc32:
            raise CrcMismatchError("block header payload crc mismatch")
        min_value, max_value = decode_stats(self.header.logical_type, stats)
        return self._encoded_from_parts(header, payload, min_value, max_value)

    def read_entry_minmax(self, entry: BlockIndexEntry) -> tuple[object | None, object | None]:
        if entry.stats_length == 0:
            return None, None
        fh = self._file()
        fh.seek(entry.offset + entry.stats_offset)
        stats = fh.read(entry.stats_length)
        if len(stats) < entry.stats_length:
            raise TruncatedFileError("block stats truncated")
        return decode_stats(self.header.logical_type, stats)

    def read_column_minmax(self) -> tuple[object | None, object | None]:
        if self.footer.column_stats_length == 0:
            return None, None
        fh = self._file()
        fh.seek(self.footer.column_stats_offset)
        stats = fh.read(self.footer.column_stats_length)
        if len(stats) < self.footer.column_stats_length:
            raise TruncatedFileError("column stats truncated")
        return decode_stats(self.header.logical_type, stats)

    def _encoded_from_parts(
        self,
        header: BlockHeader,
        payload: bytes,
        min_value: object | None,
        max_value: object | None,
    ) -> EncodedBlock:
        run_count = header.run_count_or_dict_count if header.encoding == Encoding.RLE else 0
        dict_count = header.run_count_or_dict_count if header.encoding == Encoding.DICTIONARY else 0
        return EncodedBlock(
            encoding=header.encoding,
            logical_type=self.header.logical_type,
            payload=payload,
            raw_bytes=header.raw_bytes,
            encoded_bytes=header.encoded_bytes,
            null_count=header.null_count,
            distinct_count=header.distinct_count,
            min_value=min_value,
            max_value=max_value,
            run_count=run_count,
            dictionary_count=dict_count,
        )

    def decode_block(self, block_id: int):
        block = self.read_block(block_id)
        codec = CODEC_BY_ENCODING[block.encoding]
        return codec.decode(block)

    def _get_entry(self, block_id: int) -> BlockIndexEntry:
        for entry in self.index:
            if entry.block_id == block_id:
                return entry
        raise KeyError(f"block {block_id} not found")
