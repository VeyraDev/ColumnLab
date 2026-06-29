from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.engine.codecs.base import DECODE_COST, EncodedBlock
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.types import Encoding, LogicalType, LogicalTypeId
from app.engine.vectors import NullBitmap, ValueVector


@dataclass(slots=True)
class CodecCandidateResult:
    encoding: Encoding
    encoded_bytes: int
    raw_bytes: int
    gain: float
    encode_ns: int
    selected: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "encoding": self.encoding.name,
            "encoded_bytes": self.encoded_bytes,
            "raw_bytes": self.raw_bytes,
            "gain": round(self.gain, 6),
            "encode_ns": self.encode_ns,
            "selected": self.selected,
            "reason": self.reason,
        }


@dataclass(slots=True)
class CodecSelectionResult:
    winner: EncodedBlock
    candidates: list[CodecCandidateResult]
    selection_reason: str
    rle_runs: list[dict[str, Any]] = field(default_factory=list)
    dictionary_preview: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from app.engine.codecs.dictionary import extract_dictionary_for_preview
        from app.engine.codecs.rle import extract_rle_runs_for_preview

        preview: dict[str, Any] = {
            "selection_reason": self.selection_reason,
            "winner_encoding": self.winner.encoding.name,
            "candidates": [c.to_dict() for c in self.candidates],
        }
        if self.winner.encoding == Encoding.RLE:
            preview["rle_runs"] = self.rle_runs or extract_rle_runs_for_preview(self.winner)
        if self.winner.encoding == Encoding.DICTIONARY:
            preview["dictionary"] = self.dictionary_preview or extract_dictionary_for_preview(self.winner)
        return preview

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


CODEC_ORDER = (RawCodec, RleCodec, DictionaryCodec)


def select_codec(
    values: ValueVector,
    nulls: NullBitmap,
    *,
    min_gain: float = 0.05,
    tie_threshold: float = 0.02,
) -> CodecSelectionResult:
    encoded_blocks: list[EncodedBlock] = []
    for codec_cls in CODEC_ORDER:
        if not _supports_encoding(values.logical_type, codec_cls):
            continue
        encoded_blocks.append(codec_cls.encode(values, nulls))

    raw_block = next(b for b in encoded_blocks if b.encoding == Encoding.RAW)
    raw_bytes = raw_block.encoded_bytes
    candidates: list[CodecCandidateResult] = []
    for block in encoded_blocks:
        gain = 0.0 if raw_bytes == 0 else 1.0 - (block.encoded_bytes / raw_bytes)
        candidates.append(
            CodecCandidateResult(
                encoding=block.encoding,
                encoded_bytes=block.encoded_bytes,
                raw_bytes=raw_bytes,
                gain=gain,
                encode_ns=block.encode_ns,
            )
        )

    ranked = sorted(
        candidates,
        key=lambda c: (c.encoded_bytes, DECODE_COST[Encoding[c.encoding.name]]),
    )
    winner_candidate = ranked[0]
    winner_block = next(b for b in encoded_blocks if b.encoding == winner_candidate.encoding)

    selection_reason = "smallest_encoded_bytes"
    if winner_candidate.encoding != Encoding.RAW:
        gain_vs_raw = 0.0 if raw_bytes == 0 else 1.0 - (winner_candidate.encoded_bytes / raw_bytes)
        if gain_vs_raw < min_gain:
            winner_block = raw_block
            winner_candidate = next(c for c in candidates if c.encoding == Encoding.RAW)
            selection_reason = f"gain_below_min_gain({min_gain})"
        elif len(ranked) > 1:
            second = ranked[1]
            if raw_bytes > 0:
                diff_ratio = abs(second.encoded_bytes - winner_candidate.encoded_bytes) / raw_bytes
                if diff_ratio < tie_threshold:
                    if DECODE_COST[second.encoding] < DECODE_COST[winner_candidate.encoding]:
                        winner_candidate = second
                        winner_block = next(b for b in encoded_blocks if b.encoding == second.encoding)
                        selection_reason = f"tie_break_decode_cost({tie_threshold})"

    for candidate in candidates:
        candidate.selected = candidate.encoding == winner_block.encoding
        if candidate.selected:
            candidate.reason = selection_reason
        elif candidate.encoding == Encoding.RAW:
            candidate.reason = "baseline"
        else:
            candidate.reason = "not_selected"

    from app.engine.codecs.dictionary import extract_dictionary_for_preview
    from app.engine.codecs.rle import extract_rle_runs_for_preview

    rle_runs: list[dict[str, Any]] = []
    dictionary_preview: dict[str, Any] = {}
    if winner_block.encoding == Encoding.RLE:
        rle_runs = extract_rle_runs_for_preview(winner_block)
    if winner_block.encoding == Encoding.DICTIONARY:
        dictionary_preview = extract_dictionary_for_preview(winner_block)

    return CodecSelectionResult(
        winner=winner_block,
        candidates=candidates,
        selection_reason=selection_reason,
        rle_runs=rle_runs,
        dictionary_preview=dictionary_preview,
    )


def _supports_encoding(logical_type: LogicalType, codec_cls: type) -> bool:
    if codec_cls is DictionaryCodec and logical_type.type_id == LogicalTypeId.BOOLEAN:
        return True
    return True
