from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.codecs.base import NOT_SUPPORTED, AggregateOp, PartialAggregate
from app.engine.codecs.dictionary import DictionaryCodec
from app.engine.codecs.raw import RawCodec
from app.engine.codecs.rle import RleCodec
from app.engine.execution.bitmap import bitmap_and, bitmap_or
from app.engine.execution.block_scan import read_block
from app.engine.execution.context import ExecutionContext, QueryCancelledError
from app.engine.execution.filters import filter_from_dict
from app.engine.query.expr import AggFunc
from app.engine.query.physical import (
    BitmapAnd,
    BitmapOr,
    BlockScan,
    DictionaryFilter,
    HashAggregate,
    Limit,
    Materialize,
    RawFilter,
    RleFilter,
    Sort,
)
from app.engine.types import Encoding
from app.engine.vectors import SelectionVector, ValueVector, sort_key

CODEC_BY_ENCODING = {
    Encoding.RAW: RawCodec,
    Encoding.RLE: RleCodec,
    Encoding.DICTIONARY: DictionaryCodec,
}

AGG_TO_OP = {
    AggFunc.COUNT: AggregateOp.COUNT,
    AggFunc.SUM: AggregateOp.SUM,
    AggFunc.MIN: AggregateOp.MIN,
    AggFunc.MAX: AggregateOp.MAX,
    AggFunc.AVG: AggregateOp.AVG,
}


@dataclass(slots=True)
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    metrics: Any


@dataclass(slots=True)
class _AggState:
    count: int = 0
    sum: float | int | None = None
    min: Any | None = None
    max: Any | None = None


class QueryExecutor:
    def execute(self, plan: Any, ctx: ExecutionContext) -> QueryResult:
        limit_node = _find_node(plan, Limit)
        sort_node = _find_node(plan, Sort)
        mat_node = _find_node(plan, Materialize)
        agg_node = _find_node(plan, HashAggregate)
        filter_root = _filter_root(plan)

        output_cols = list(mat_node.columns) if mat_node else []
        block_ids = _collect_block_ids(filter_root)
        groups: dict[tuple[Any, ...], dict[str, _AggState]] = {}
        flat_rows: list[list[Any]] = []

        limit_cap = None
        offset_skip = 0
        if limit_node:
            limit_cap = limit_node.limit + limit_node.offset
            offset_skip = limit_node.offset

        for block_id in block_ids:
            ctx.check_cancel()
            selection = _eval_filter(filter_root, ctx, block_id)
            if selection.selected_count() == 0:
                continue
            if agg_node:
                _accumulate_block(ctx, block_id, selection, agg_node, groups, filter_root)
            elif mat_node:
                flat_rows.extend(_materialize_block(ctx, block_id, selection, output_cols))
            if limit_cap is not None and not agg_node and len(flat_rows) >= limit_cap:
                break

        if agg_node:
            flat_rows = _finalize_groups(groups, output_cols, agg_node)
        if sort_node:
            flat_rows = _sort_rows(flat_rows, output_cols, sort_node)
        total = len(flat_rows)
        if limit_node:
            flat_rows = flat_rows[offset_skip : offset_skip + limit_node.limit]
        ctx.metrics.rows_output = len(flat_rows)
        ctx.metrics.peak_memory = _estimate_memory(flat_rows)
        return QueryResult(columns=output_cols, rows=flat_rows, total_rows=total, metrics=ctx.metrics)


def _accumulate_block(
    ctx: ExecutionContext,
    block_id: int,
    selection: SelectionVector,
    agg_node: HashAggregate,
    groups: dict[tuple[Any, ...], dict[str, _AggState]],
    filter_root: Any,
) -> None:
    group_cols = list(agg_node.group_keys)
    full_block = selection.selected_count() == selection.length

    if full_block and not group_cols and _compressed_global_agg(ctx, block_id, agg_node, groups, filter_root):
        return

    if full_block and len(group_cols) == 1 and _dict_group_by_block(ctx, block_id, group_cols[0], agg_node, groups):
        return

    _accumulate_decoded(ctx, block_id, selection, agg_node, group_cols, groups)


def _compressed_global_agg(
    ctx: ExecutionContext,
    block_id: int,
    agg_node: HashAggregate,
    groups: dict[tuple[Any, ...], dict[str, _AggState]],
    filter_root: Any,
) -> bool:
    temp: dict[tuple[Any, ...], dict[str, _AggState]] = {}
    temp_bucket = temp.setdefault((), {})
    compressed = 0

    for agg_spec in agg_node.aggregates:
        func = AggFunc(agg_spec["func"])
        name = agg_spec.get("alias") or _agg_default_name(agg_spec)
        state = temp_bucket.setdefault(name, _AggState())

        if func == AggFunc.COUNT and not agg_spec.get("arg"):
            scan = _first_scan(filter_root)
            if scan is None:
                return False
            block = read_block(
                ctx,
                column=scan.column,
                column_id=scan.column_id,
                block_id=block_id,
                operator_id=scan.operator_id,
            )
            if block is None:
                continue
            from app.engine.vectors import NullBitmap

            nulls, _ = NullBitmap.deserialize(block.payload)
            state.count += nulls.length
            compressed += 1
            continue

        arg = agg_spec.get("arg")
        if not arg or arg.get("type") != "ColumnRef":
            return False
        col = arg["name"]
        meta = ctx.columns.get(col)
        if meta is None:
            return False
        block = read_block(
            ctx,
            column=col,
            column_id=meta.column_id,
            block_id=block_id,
            operator_id=f"agg_{col}",
        )
        if block is None:
            continue
        op = AGG_TO_OP.get(func)
        if op is None:
            return False
        codec = CODEC_BY_ENCODING[block.encoding]
        if not codec.estimate_capabilities().supports_aggregate:
            return False
        partial = codec.aggregate(block, op)
        if partial is NOT_SUPPORTED or not isinstance(partial, PartialAggregate):
            return False
        _merge_partial(state, partial, func)
        compressed += 1

    bucket = groups.setdefault((), {})
    for name, temp_state in temp_bucket.items():
        _merge_agg_states(bucket.setdefault(name, _AggState()), temp_state)
    ctx.metrics.compressed_operator_blocks += compressed
    return True


def _dict_group_by_block(
    ctx: ExecutionContext,
    block_id: int,
    group_col: str,
    agg_node: HashAggregate,
    groups: dict[tuple[Any, ...], dict[str, _AggState]],
) -> bool:
    meta = ctx.columns.get(group_col)
    if meta is None:
        return False
    block = read_block(
        ctx,
        column=group_col,
        column_id=meta.column_id,
        block_id=block_id,
        operator_id=f"group_{group_col}",
    )
    if block is None or block.encoding != Encoding.DICTIONARY:
        return False

    agg_specs = list(agg_node.aggregates)
    if len(agg_specs) != 1:
        return False
    spec = agg_specs[0]
    func = AggFunc(spec["func"])
    if func != AggFunc.COUNT:
        return False
    if spec.get("arg") and spec["arg"].get("type") == "ColumnRef":
        if spec["arg"]["name"] != group_col:
            return False

    code_counts = DictionaryCodec.group_by_codes(block)
    from app.engine.codecs.dictionary import extract_dictionary_for_preview

    entries = extract_dictionary_for_preview(block)["entries"]
    name = spec.get("alias") or _agg_default_name(spec)
    for code, cnt in code_counts.items():
        value = entries[code]
        key = (value,)
        bucket = groups.setdefault(key, {})
        state = bucket.setdefault(name, _AggState())
        state.count += cnt
    ctx.metrics.compressed_operator_blocks += 1
    return True


def _accumulate_decoded(
    ctx: ExecutionContext,
    block_id: int,
    selection: SelectionVector,
    agg_node: HashAggregate,
    group_cols: list[str],
    groups: dict[tuple[Any, ...], dict[str, _AggState]],
) -> None:
    indices = selection.to_indices()
    col_cache: dict[str, ValueVector | None] = {}

    def values_for(col: str) -> ValueVector | None:
        if col not in col_cache:
            col_cache[col] = _decode_block_once(ctx, col, block_id)
        return col_cache[col]

    for i in indices:
        key_values: list[Any] = []
        for col in group_cols:
            vec = values_for(col)
            key_values.append(None if vec is None else vec.values[i])
        key = tuple(key_values)
        bucket = groups.setdefault(key, {})
        for agg_spec in agg_node.aggregates:
            name = agg_spec.get("alias") or _agg_default_name(agg_spec)
            state = bucket.setdefault(name, _AggState())
            func = AggFunc(agg_spec["func"])
            if func == AggFunc.COUNT and not agg_spec.get("arg"):
                state.count += 1
                continue
            arg = agg_spec.get("arg")
            if not arg or arg.get("type") != "ColumnRef":
                continue
            vec = values_for(arg["name"])
            if vec is None:
                continue
            val = vec.values[i]
            if val is None:
                continue
            if func == AggFunc.SUM:
                state.count += 1
                state.sum = val if state.sum is None else state.sum + val
            elif func == AggFunc.MIN:
                state.count += 1
                state.min = val if state.min is None else min(state.min, val)
            elif func == AggFunc.MAX:
                state.count += 1
                state.max = val if state.max is None else max(state.max, val)
            elif func == AggFunc.AVG:
                state.count += 1
                state.sum = val if state.sum is None else state.sum + val
            elif func == AggFunc.COUNT:
                state.count += 1


def _merge_partial(state: _AggState, partial: PartialAggregate, func: AggFunc) -> None:
    state.count += partial.count
    if partial.sum is not None:
        state.sum = partial.sum if state.sum is None else state.sum + partial.sum
    if partial.min is not None:
        state.min = partial.min if state.min is None else min(state.min, partial.min)
    if partial.max is not None:
        state.max = partial.max if state.max is None else max(state.max, partial.max)


def _merge_agg_states(dst: _AggState, src: _AggState) -> None:
    dst.count += src.count
    if src.sum is not None:
        dst.sum = src.sum if dst.sum is None else dst.sum + src.sum
    if src.min is not None:
        dst.min = src.min if dst.min is None else min(dst.min, src.min)
    if src.max is not None:
        dst.max = src.max if dst.max is None else max(dst.max, src.max)


def _bitmap_and_with_na(left: SelectionVector, right: SelectionVector) -> SelectionVector:
    """length==0 means the column scan does not cover this block (pruned / N/A)."""
    if left.length == 0 and right.length == 0:
        return SelectionVector.all_false(0)
    if left.length == 0:
        return SelectionVector.all_false(right.length)
    return SelectionVector.all_false(left.length)


def _pad_selection(sel: SelectionVector, n: int) -> SelectionVector:
    if sel.length >= n:
        return sel
    buf = bytearray((n + 7) // 8)
    buf[: len(sel.bits)] = sel.bits
    return SelectionVector(length=n, bits=bytes(buf))


def _decode_block_once(ctx: ExecutionContext, column: str, block_id: int) -> ValueVector | None:
    key = (column, block_id)
    if key in ctx.decoded_vectors:
        return ctx.decoded_vectors[key]
    meta = ctx.columns[column]
    block = read_block(
        ctx,
        column=column,
        column_id=meta.column_id,
        block_id=block_id,
        operator_id=f"decode_{column}",
    )
    if block is None:
        return None
    codec = CODEC_BY_ENCODING[block.encoding]
    decoded = codec.decode(block)
    if key not in ctx.metrics._decoded_ids:
        ctx.metrics._decoded_ids.add(key)
        ctx.metrics.decoded_blocks += 1
    ctx.decoded_vectors[key] = decoded
    return decoded


def _materialize_block(
    ctx: ExecutionContext,
    block_id: int,
    selection: SelectionVector,
    columns: list[str],
) -> list[list[Any]]:
    indices = selection.to_indices()
    if not indices:
        return []
    col_values: dict[str, list[Any]] = {}
    for col in columns:
        vec = _decode_block_once(ctx, col, block_id)
        if vec is None:
            col_values[col] = [None] * len(indices)
        else:
            col_values[col] = [vec.values[i] for i in indices]
    return [[col_values[col][row_idx] for col in columns] for row_idx in range(len(indices))]


def _eval_filter(node: Any, ctx: ExecutionContext, block_id: int) -> SelectionVector:
    if isinstance(node, BlockScan):
        if block_id not in node.block_ids:
            return SelectionVector.all_false(0)
        block = read_block(
            ctx,
            column=node.column,
            column_id=node.column_id,
            block_id=block_id,
            operator_id=node.operator_id,
        )
        if block is None:
            return SelectionVector.all_false(0)
        from app.engine.vectors import NullBitmap

        nulls, _ = NullBitmap.deserialize(block.payload)
        return SelectionVector.all_true(nulls.length)
    if isinstance(node, (RawFilter, RleFilter, DictionaryFilter)):
        scan = node.child
        if block_id not in scan.block_ids:
            return SelectionVector.all_false(0)
        block = read_block(
            ctx,
            column=scan.column,
            column_id=scan.column_id,
            block_id=block_id,
            operator_id=scan.operator_id,
        )
        if block is None:
            return SelectionVector.all_false(0)
        op_type = type(node).__name__
        return filter_from_dict(ctx, block, node.predicate, operator_id=node.operator_id, operator_type=op_type)
    if isinstance(node, BitmapAnd):
        left = _eval_filter(node.children[0], ctx, block_id)
        right = _eval_filter(node.children[1], ctx, block_id)
        if left.length == 0 or right.length == 0:
            return _bitmap_and_with_na(left, right)
        if left.length != right.length:
            n = max(left.length, right.length)
            left = _pad_selection(left, n)
            right = _pad_selection(right, n)
        return bitmap_and(ctx, left, right, operator_id=node.operator_id)
    if isinstance(node, BitmapOr):
        left = _eval_filter(node.children[0], ctx, block_id)
        right = _eval_filter(node.children[1], ctx, block_id)
        if left.length == 0:
            return right
        if right.length == 0:
            return left
        if left.length != right.length:
            n = max(left.length, right.length)
            if left.length < n:
                left = SelectionVector.all_true(n).and_with(left)
            if right.length < n:
                right = SelectionVector.all_true(n).and_with(right)
        return bitmap_or(ctx, left, right, operator_id=node.operator_id)
    return SelectionVector.all_false(0)


def _collect_block_ids(node: Any) -> tuple[int, ...]:
    scans = _collect_scans(node)
    if not scans:
        return ()
    ids: set[int] = set()
    for scan in scans:
        ids.update(scan.block_ids)
    return tuple(sorted(ids))


def _collect_scans(node: Any) -> list[BlockScan]:
    if isinstance(node, BlockScan):
        return [node]
    if isinstance(node, (RawFilter, RleFilter, DictionaryFilter)):
        return [node.child]
    if isinstance(node, (BitmapAnd, BitmapOr)):
        result: list[BlockScan] = []
        for child in node.children:
            result.extend(_collect_scans(child))
        return result
    return []


def _filter_root(plan: Any) -> Any:
    node = plan
    while isinstance(node, (Limit, Sort, Materialize, HashAggregate)):
        node = node.child
    return node


def _first_scan(node: Any) -> BlockScan | None:
    scans = _collect_scans(node)
    return scans[0] if scans else None


def _find_node(plan: Any, cls: type) -> Any | None:
    if isinstance(plan, cls):
        return plan
    child = getattr(plan, "child", None)
    if child is not None:
        return _find_node(child, cls)
    return None


def _finalize_groups(
    groups: dict[tuple[Any, ...], dict[str, _AggState]],
    output_cols: list[str],
    agg_node: HashAggregate,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    group_cols = list(agg_node.group_keys)
    agg_names = [a.get("alias") or _agg_default_name(a) for a in agg_node.aggregates]
    items = groups.items() if groups else [(() , {})]
    for key, bucket in sorted(items, key=lambda kv: kv[0]):
        row: list[Any] = list(key)
        for name in agg_names:
            state = bucket.get(name, _AggState())
            spec = next(a for a in agg_node.aggregates if (a.get("alias") or _agg_default_name(a)) == name)
            func = AggFunc(spec["func"])
            if func == AggFunc.COUNT:
                row.append(state.count)
            elif func == AggFunc.SUM:
                row.append(state.sum)
            elif func == AggFunc.MIN:
                row.append(state.min)
            elif func == AggFunc.MAX:
                row.append(state.max)
            elif func == AggFunc.AVG:
                row.append(None if state.count == 0 else (state.sum / state.count if state.sum is not None else None))
            else:
                row.append(None)
        rows.append(row)
    return rows


def _agg_default_name(spec: dict[str, Any]) -> str:
    func = spec.get("func", "AGG")
    arg = spec.get("arg")
    if arg and arg.get("type") == "ColumnRef":
        return f"{func}_{arg['name']}"
    return func


def _sort_rows(rows: list[list[Any]], columns: list[str], sort_node: Sort) -> list[list[Any]]:
    if not rows or not sort_node.keys:
        return rows
    key_spec = sort_node.keys[0]
    expr = key_spec["expr"]
    ascending = key_spec.get("ascending", True)
    col_name = expr.get("name") if expr.get("type") == "ColumnRef" else expr.get("alias")
    if col_name is None and expr.get("type") == "AggregateExpr":
        col_name = expr.get("alias")
    if col_name is None:
        col_name = columns[0]
    try:
        col_idx = columns.index(col_name)
    except ValueError:
        col_idx = 0

    def sort_key_fn(row: list[Any]) -> tuple[int, Any]:
        val = row[col_idx]
        if isinstance(val, float) and val != val:
            return (1, 0)
        return (0, val)

    return sorted(rows, key=sort_key_fn, reverse=not ascending)


def _estimate_memory(rows: list[list[Any]]) -> int:
    total = 0
    for row in rows:
        for val in row:
            if isinstance(val, str):
                total += len(val.encode("utf-8"))
            elif isinstance(val, (int, float, bool)):
                total += 8
            elif val is not None:
                total += 16
    return total
