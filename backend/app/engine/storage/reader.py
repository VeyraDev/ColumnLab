from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    _data: bytes

    @classmethod
    def open(cls, path: Path | str) -> ColumnReader:
        path = Path(path)
        data = path.read_bytes()
        if len(data) < FILE_HEADER_SIZE + FOOTER_SIZE:
            raise TruncatedFileError("column file too short")
        header = FileHeader.unpack(data[:FILE_HEADER_SIZE])
        footer_offset = header.footer_offset
        if footer_offset + FOOTER_SIZE > len(data):
            raise TruncatedFileError("footer extends beyond file")
        footer = FileFooter.unpack(data, footer_offset)
        index_bytes = data[footer.index_offset : footer.index_offset + footer.index_length]
        verify_crc32(index_bytes, footer.index_crc32)
        index = unpack_index(index_bytes)
        return cls(path=path, header=header, footer=footer, index=index, _data=data)

    @classmethod
    def load_index_only(cls, path: Path | str) -> list[BlockIndexEntry]:
        return cls.open(path).index

    def read_block(self, block_id: int) -> EncodedBlock:
        entry = self._get_entry(block_id)
        start = entry.offset
        end = start + entry.total_block_length
        if end > len(self._data):
            raise TruncatedFileError("block extends beyond file")
        chunk = self._data[start:end]
        header, pos = BlockHeader.unpack(chunk, 0)
        stats = chunk[pos : pos + header.stats_bytes]
        payload = chunk[pos + header.stats_bytes :]
        verify_crc32(payload, entry.payload_crc32)
        if header.payload_crc32 != entry.payload_crc32:
            raise CrcMismatchError("block header payload crc mismatch")
        decode_stats(self.header.logical_type, stats)
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
            min_value=decode_stats(self.header.logical_type, stats)[0],
            max_value=decode_stats(self.header.logical_type, stats)[1],
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
