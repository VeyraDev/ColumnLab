from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.query.expr import (
    And,
    Between,
    ColumnRef,
    Compare,
    CompareOp,
    In,
    IsNull,
    Literal,
    Not,
    Or,
)
from app.engine.query.logical import Aggregate, Filter, Limit, Project, Scan, Sort
from app.engine.query.optimizer import collect_column_refs
from app.engine.storage.reader import ColumnReader
from app.engine.types import Encoding

NUMERIC_TYPES = {"INT64", "DOUBLE", "FLOAT64", "DECIMAL64"}


class BlockVerdict(StrEnum):
    ALWAYS_FALSE = "always_false"
    MAYBE = "maybe"
    ALWAYS_TRUE = "always_true"


class BlockPruneState(StrEnum):
    UNDETERMINED = "undetermined"
    METADATA_CHECK = "metadata_check"
    SKIPPED = "skipped"
    TO_READ = "to_read"


@dataclass(frozen=True, slots=True)
class BlockStatsSnapshot:
    block_id: int
    encoding: str
    row_count: int
    null_count: int
    min_repr: str | None
    max_repr: str | None
    dictionary_count: int
    column_file_path: str


@dataclass(frozen=True, slots=True)
class ColumnBlocksSnapshot:
    name: str
    logical_type: str
    blocks: tuple[BlockStatsSnapshot, ...]


@dataclass(frozen=True, slots=True)
class TableBlocksSnapshot:
    table_name: str
    columns: tuple[ColumnBlocksSnapshot, ...]


@dataclass(frozen=True, slots=True)
class BlockPruningEntry:
    column: str
    block_id: int
    state: BlockPruneState
    verdict: BlockVerdict
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "block_id": self.block_id,
            "state": self.state.value,
            "verdict": self.verdict.value,
            "reason": self.reason,
        }


def prune_blocks(plan: Any, snapshot: TableBlocksSnapshot) -> tuple[BlockPruningEntry, ...]:
    required = _required_columns(plan)
    predicate = _find_filter_predicate(plan)
    entries: list[BlockPruningEntry] = []
    for col in snapshot.columns:
        if col.name not in required:
            for block in col.blocks:
                entries.append(
                    BlockPruningEntry(
                        column=col.name,
                        block_id=block.block_id,
                        state=BlockPruneState.SKIPPED,
                        verdict=BlockVerdict.ALWAYS_FALSE,
                        reason="projection_pruned",
                    )
                )
            continue
        col_pred = extract_column_predicate(predicate, col.name) if predicate else None
        for block in col.blocks:
            entries.append(_prune_block(col.name, col.logical_type, block, col_pred))
    return tuple(entries)


def pruning_summary(entries: tuple[BlockPruningEntry, ...]) -> dict[str, int]:
    total = len(entries)
    skipped = sum(1 for e in entries if e.state == BlockPruneState.SKIPPED)
    return {"total_blocks": total, "pruned_blocks": skipped, "to_read_blocks": total - skipped}


def all_blocks_to_read(snapshot: TableBlocksSnapshot) -> tuple[BlockPruningEntry, ...]:
    entries: list[BlockPruningEntry] = []
    for col in snapshot.columns:
        for block in col.blocks:
            entries.append(
                BlockPruningEntry(
                    column=col.name,
                    block_id=block.block_id,
                    state=BlockPruneState.TO_READ,
                    verdict=BlockVerdict.MAYBE,
                    reason="pruning_disabled",
                )
            )
    return tuple(entries)


def _required_columns(plan: Any) -> set[str]:
    refs = collect_column_refs(plan)
    if isinstance(plan, Scan):
        ann = dict(plan.annotations)
        if "required_columns" in ann:
            return set(ann["required_columns"])
    return _scan_required(plan) or refs


def _scan_required(plan: Any) -> set[str] | None:
    if isinstance(plan, Scan):
        ann = dict(plan.annotations)
        cols = ann.get("required_columns")
        return set(cols) if cols else None
    if isinstance(plan, Filter):
        return _scan_required(plan.child)
    if isinstance(plan, Project):
        return _scan_required(plan.child)
    if isinstance(plan, Aggregate):
        return _scan_required(plan.child)
    if isinstance(plan, Sort):
        return _scan_required(plan.child)
    if isinstance(plan, Limit):
        return _scan_required(plan.child)
    return None


def _find_filter_predicate(plan: Any) -> Any | None:
    if isinstance(plan, Filter):
        return plan.predicate
    if isinstance(plan, (Project, Aggregate, Sort, Limit)):
        return _find_filter_predicate(plan.child)
    return None


def extract_column_predicate(predicate: Any, column: str) -> Any | None:
    if predicate is None:
        return None
    if _predicate_uses_column(predicate, column):
        return predicate
    return None


def _predicate_uses_column(expr: Any, column: str) -> bool:
    if isinstance(expr, ColumnRef):
        return expr.name == column
    if isinstance(expr, Compare):
        return _predicate_uses_column(expr.left, column) or _predicate_uses_column(expr.right, column)
    if isinstance(expr, (And, Or)):
        return _predicate_uses_column(expr.left, column) or _predicate_uses_column(expr.right, column)
    if isinstance(expr, Not):
        return _predicate_uses_column(expr.operand, column)
    if isinstance(expr, In):
        return _predicate_uses_column(expr.expr, column)
    if isinstance(expr, Between):
        return _predicate_uses_column(expr.expr, column)
    if isinstance(expr, IsNull):
        return _predicate_uses_column(expr.expr, column)
    return False


def _prune_block(column: str, logical_type: str, block: BlockStatsSnapshot, predicate: Any | None) -> BlockPruningEntry:
    if predicate is None:
        return BlockPruningEntry(
            column=column,
            block_id=block.block_id,
            state=BlockPruneState.TO_READ,
            verdict=BlockVerdict.MAYBE,
            reason="no_predicate",
        )
    verdict, reason, used_metadata = evaluate_predicate(predicate, logical_type, block)
    if verdict == BlockVerdict.ALWAYS_FALSE:
        return BlockPruningEntry(
            column=column,
            block_id=block.block_id,
            state=BlockPruneState.SKIPPED,
            verdict=verdict,
            reason=reason if not used_metadata else f"metadata:{reason}",
        )
    if verdict == BlockVerdict.ALWAYS_TRUE:
        return BlockPruningEntry(
            column=column,
            block_id=block.block_id,
            state=BlockPruneState.TO_READ,
            verdict=verdict,
            reason=reason,
        )
    return BlockPruningEntry(
        column=column,
        block_id=block.block_id,
        state=BlockPruneState.TO_READ,
        verdict=BlockVerdict.MAYBE,
        reason=reason or "maybe",
    )


def evaluate_predicate(
    predicate: Any, logical_type: str, block: BlockStatsSnapshot
) -> tuple[BlockVerdict, str, bool]:
    if isinstance(predicate, And):
        left_v, left_r, left_m = evaluate_predicate(predicate.left, logical_type, block)
        if left_v == BlockVerdict.ALWAYS_FALSE:
            return BlockVerdict.ALWAYS_FALSE, left_r, left_m
        right_v, right_r, right_m = evaluate_predicate(predicate.right, logical_type, block)
        if right_v == BlockVerdict.ALWAYS_FALSE:
            return BlockVerdict.ALWAYS_FALSE, right_r, right_m
        if left_v == BlockVerdict.ALWAYS_TRUE and right_v == BlockVerdict.ALWAYS_TRUE:
            return BlockVerdict.ALWAYS_TRUE, "and_always_true", left_m or right_m
        return BlockVerdict.MAYBE, "and_maybe", left_m or right_m
    if isinstance(predicate, Or):
        left_v, left_r, left_m = evaluate_predicate(predicate.left, logical_type, block)
        if left_v == BlockVerdict.ALWAYS_TRUE:
            return BlockVerdict.ALWAYS_TRUE, left_r, left_m
        right_v, right_r, right_m = evaluate_predicate(predicate.right, logical_type, block)
        if right_v == BlockVerdict.ALWAYS_TRUE:
            return BlockVerdict.ALWAYS_TRUE, right_r, right_m
        if left_v == BlockVerdict.ALWAYS_FALSE and right_v == BlockVerdict.ALWAYS_FALSE:
            return BlockVerdict.ALWAYS_FALSE, "or_all_false", left_m or right_m
        return BlockVerdict.MAYBE, "or_maybe", left_m or right_m
    if isinstance(predicate, Not):
        inner_v, inner_r, inner_m = evaluate_predicate(predicate.operand, logical_type, block)
        if inner_v == BlockVerdict.ALWAYS_FALSE:
            return BlockVerdict.ALWAYS_TRUE, f"not({inner_r})", inner_m
        if inner_v == BlockVerdict.ALWAYS_TRUE:
            return BlockVerdict.ALWAYS_FALSE, f"not({inner_r})", inner_m
        return BlockVerdict.MAYBE, "not_maybe", inner_m
    if isinstance(predicate, Compare):
        return _eval_compare(predicate, logical_type, block)
    if isinstance(predicate, IsNull):
        return _eval_is_null(predicate, block)
    if isinstance(predicate, In):
        return _eval_in(predicate, logical_type, block)
    if isinstance(predicate, Between):
        return _eval_between(predicate, logical_type, block)
    return BlockVerdict.MAYBE, "unsupported_predicate", False


def _eval_compare(pred: Compare, logical_type: str, block: BlockStatsSnapshot) -> tuple[BlockVerdict, str, bool]:
    if not isinstance(pred.left, ColumnRef):
        return BlockVerdict.MAYBE, "compare_shape", False
    if not isinstance(pred.right, Literal):
        return BlockVerdict.MAYBE, "compare_non_literal", False
    value = pred.right.value
    encoding = block.encoding.upper()
    if encoding in {"DICTIONARY", "DICT"} and pred.op == CompareOp.EQ:
        if block.column_file_path and Path(block.column_file_path).exists():
            try:
                reader = ColumnReader.open(block.column_file_path)
                encoded = reader.read_block(block.block_id)
                if DictionaryCodec.dictionary_negative_check(encoded, value):
                    return BlockVerdict.ALWAYS_FALSE, f"dictionary_missing_value={value!r}", True
                return BlockVerdict.MAYBE, "dictionary_contains_or_unknown", True
            except OSError:
                pass
    block = _ensure_min_max(block)
    if block.min_repr is None or block.max_repr is None:
        return BlockVerdict.MAYBE, "missing_min_max", False
    lo = parse_repr(block.min_repr, logical_type)
    hi = parse_repr(block.max_repr, logical_type)
    target = parse_repr(str(value), logical_type) if not isinstance(value, (int, float)) else value
    if pred.op == CompareOp.GT:
        if lo is not None and hi is not None and hi <= target:
            return BlockVerdict.ALWAYS_FALSE, f"max={block.max_repr} <= {value}", False
    elif pred.op == CompareOp.GE:
        if lo is not None and hi is not None and hi < target:
            return BlockVerdict.ALWAYS_FALSE, f"max={block.max_repr} < {value}", False
    elif pred.op == CompareOp.LT:
        if lo is not None and hi is not None and lo >= target:
            return BlockVerdict.ALWAYS_FALSE, f"min={block.min_repr} >= {value}", False
    elif pred.op == CompareOp.LE:
        if lo is not None and hi is not None and lo > target:
            return BlockVerdict.ALWAYS_FALSE, f"min={block.min_repr} > {value}", False
    elif pred.op == CompareOp.EQ:
        if lo is not None and hi is not None and (target < lo or target > hi):
            return BlockVerdict.ALWAYS_FALSE, f"{value} not in [{block.min_repr}, {block.max_repr}]", False
    elif pred.op == CompareOp.NE:
        if lo is not None and hi is not None and lo == hi == target:
            return BlockVerdict.ALWAYS_FALSE, f"single_value={target}", False
    return BlockVerdict.MAYBE, "range_overlap", False


def _eval_is_null(pred: IsNull, block: BlockStatsSnapshot) -> tuple[BlockVerdict, str, bool]:
    if pred.negated:
        if block.null_count == block.row_count:
            return BlockVerdict.ALWAYS_FALSE, "all_null", False
        if block.null_count == 0:
            return BlockVerdict.ALWAYS_TRUE, "no_nulls", False
        return BlockVerdict.MAYBE, "some_nulls", False
    if block.null_count == 0:
        return BlockVerdict.ALWAYS_FALSE, "null_count=0", False
    if block.null_count == block.row_count:
        return BlockVerdict.ALWAYS_TRUE, "all_null", False
    return BlockVerdict.MAYBE, "partial_null", False


def _eval_in(pred: In, logical_type: str, block: BlockStatsSnapshot) -> tuple[BlockVerdict, str, bool]:
    block = _ensure_min_max(block)
    if block.min_repr is None or block.max_repr is None:
        return BlockVerdict.MAYBE, "missing_min_max", False
    lo = parse_repr(block.min_repr, logical_type)
    hi = parse_repr(block.max_repr, logical_type)
    if lo is None or hi is None:
        return BlockVerdict.MAYBE, "missing_min_max", False
    all_outside = True
    for lit in pred.values:
        if not isinstance(lit, Literal):
            return BlockVerdict.MAYBE, "in_non_literal", False
        val = lit.value
        target = parse_repr(str(val), logical_type) if not isinstance(val, (int, float)) else val
        if lo <= target <= hi:
            all_outside = False
            break
    if all_outside and not pred.negated:
        return BlockVerdict.ALWAYS_FALSE, "in_values_outside_range", False
    return BlockVerdict.MAYBE, "in_maybe", False


def _eval_between(pred: Between, logical_type: str, block: BlockStatsSnapshot) -> tuple[BlockVerdict, str, bool]:
    if not isinstance(pred.low, Literal) or not isinstance(pred.high, Literal):
        return BlockVerdict.MAYBE, "between_non_literal", False
    block = _ensure_min_max(block)
    if block.min_repr is None or block.max_repr is None:
        return BlockVerdict.MAYBE, "missing_min_max", False
    lo = parse_repr(block.min_repr, logical_type)
    hi = parse_repr(block.max_repr, logical_type)
    low = pred.low.value
    high = pred.high.value
    if lo is not None and hi is not None and (hi < low or lo > high):
        verdict = BlockVerdict.ALWAYS_FALSE if not pred.negated else BlockVerdict.ALWAYS_TRUE
        return verdict, f"block_range [{block.min_repr},{block.max_repr}] outside [{low},{high}]", False
    return BlockVerdict.MAYBE, "between_overlap", False


def _ensure_min_max(block: BlockStatsSnapshot) -> BlockStatsSnapshot:
    if block.min_repr is not None and block.max_repr is not None:
        return block
    if not block.column_file_path or not Path(block.column_file_path).exists():
        return block
    try:
        reader = ColumnReader.open(block.column_file_path)
        entry = next((e for e in reader.index if e.block_id == block.block_id), None)
        if entry is not None and entry.stats_length > 0:
            min_value, max_value = reader.read_entry_minmax(entry)
        else:
            encoded = reader.read_block(block.block_id)
            min_value, max_value = encoded.min_value, encoded.max_value
        reader.close()
        if min_value is None or max_value is None:
            return block
        return BlockStatsSnapshot(
            block_id=block.block_id,
            encoding=block.encoding,
            row_count=block.row_count,
            null_count=block.null_count,
            min_repr=str(min_value),
            max_repr=str(max_value),
            dictionary_count=block.dictionary_count,
            column_file_path=block.column_file_path,
        )
    except OSError:
        return block


def parse_repr(value: str, logical_type: str) -> Any:
    if logical_type in NUMERIC_TYPES:
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return float(value) if logical_type in {"DOUBLE", "FLOAT64", "DECIMAL64"} else value
    return value
