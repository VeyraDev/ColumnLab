from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.query.expr import (
    And,
    ColumnRef,
    Compare,
    In,
    IsNull,
    Literal,
    Not,
    Or,
    SelectItem,
    AggregateExpr,
    OrderKey,
    _expr_dict,
)
from app.engine.query.logical import Aggregate, Filter, Limit, Project, Scan, Sort
from app.engine.query.physical import (
    BitmapAnd,
    BitmapOr,
    BlockScan,
    DictionaryFilter,
    HashAggregate,
    Limit as PhysicalLimit,
    Materialize,
    RawFilter,
    RleFilter,
    Sort as PhysicalSort,
    new_operator_id,
    physical_to_dict,
)
from app.engine.query.pruning import BlockPruneState, BlockPruningEntry, TableBlocksSnapshot
from app.engine.types import Encoding


@dataclass(frozen=True, slots=True)
class ColumnCatalogInfo:
    name: str
    column_id: int
    file_path: str


@dataclass(frozen=True, slots=True)
class PhysicalPlanContext:
    snapshot: TableBlocksSnapshot
    pruning: tuple[BlockPruningEntry, ...]
    columns: tuple[ColumnCatalogInfo, ...]
    version_id: int


def plan_physical(logical: Any, ctx: PhysicalPlanContext) -> Any:
    limit_node = _find_limit(logical)
    sort_node = _find_sort(logical)
    aggregate_node = _find_aggregate(logical)
    project_node = _find_project(logical)
    filter_pred = _find_filter_predicate(logical)

    col_map = {c.name: c for c in ctx.columns}
    snap_map = {c.name: c for c in ctx.snapshot.columns}
    prune_map = _prune_lookup(ctx.pruning)

    output_cols = _output_column_names(project_node, aggregate_node)
    scan_cols = _scan_columns(filter_pred, output_cols, aggregate_node, logical)
    scan_cols = {c for c in scan_cols if c in snap_map}

    if filter_pred is not None:
        filter_root = _build_filter_tree(filter_pred, scan_cols, col_map, snap_map, prune_map)
    else:
        filter_root = _all_pass(scan_cols, col_map, snap_map, prune_map)

    root: Any = filter_root

    if aggregate_node is not None:
        group_keys = tuple(
            k.name if isinstance(k, ColumnRef) else str(k) for k in aggregate_node.group_keys
        )
        aggs = tuple(_expr_dict(a) if hasattr(a, "to_dict") else a for a in aggregate_node.aggregates)
        root = HashAggregate(
            operator_id=new_operator_id("hash_agg"),
            group_keys=group_keys,
            aggregates=aggs,
            child=root,
        )
        mat_cols = _select_output_names(project_node)
        root = Materialize(
            operator_id=new_operator_id("materialize"),
            columns=mat_cols,
            child=root,
        )
    elif project_node is not None:
        mat_cols = _select_output_names(project_node)
        root = Materialize(
            operator_id=new_operator_id("materialize"),
            columns=mat_cols,
            child=root,
        )

    if sort_node is not None:
        keys = tuple(
            {"expr": _expr_dict(k.expr) if hasattr(k.expr, "to_dict") else k.expr, "ascending": k.ascending}
            for k in sort_node.keys
        )
        root = PhysicalSort(operator_id=new_operator_id("sort"), keys=keys, child=root)

    if limit_node is not None:
        root = PhysicalLimit(
            operator_id=new_operator_id("limit"),
            limit=limit_node.limit,
            offset=limit_node.offset,
            child=root,
        )

    return root


def physical_plan_to_dict(plan: Any) -> dict[str, Any]:
    return physical_to_dict(plan)


def _prune_lookup(entries: tuple[BlockPruningEntry, ...]) -> dict[tuple[str, int], BlockPruningEntry]:
    return {(e.column, e.block_id): e for e in entries}


def _block_ids(column: str, snap_map: dict, prune_map: dict) -> tuple[int, ...]:
    col = snap_map[column]
    ids: list[int] = []
    for block in col.blocks:
        entry = prune_map.get((column, block.block_id))
        if entry and entry.state == BlockPruneState.SKIPPED:
            continue
        ids.append(block.block_id)
    return tuple(ids)


def _dominant_encoding(column: str, snap_map: dict, block_ids: tuple[int, ...]) -> str:
    col = snap_map[column]
    encodings: dict[str, int] = {}
    for block in col.blocks:
        if block.block_id in block_ids:
            encodings[block.encoding] = encodings.get(block.encoding, 0) + 1
    if not encodings:
        return "RAW"
    return max(encodings, key=encodings.get)


def _make_block_scan(
    column: str,
    col_map: dict[str, ColumnCatalogInfo],
    snap_map: dict,
    prune_map: dict,
) -> BlockScan:
    block_ids = _block_ids(column, snap_map, prune_map)
    info = col_map[column]
    return BlockScan(
        operator_id=new_operator_id("scan"),
        column=column,
        column_id=info.column_id,
        block_ids=block_ids,
        file_path=info.file_path,
    )


def _make_column_filter(
    column: str,
    predicate: Any,
    col_map: dict,
    snap_map: dict,
    prune_map: dict,
) -> Any:
    scan = _make_block_scan(column, col_map, snap_map, prune_map)
    pred_dict = _expr_dict(predicate) if hasattr(predicate, "to_dict") else predicate
    encoding = _dominant_encoding(column, snap_map, scan.block_ids)
    op_id = new_operator_id("filter")
    if encoding == Encoding.RLE.name or encoding == "RLE":
        return RleFilter(operator_id=op_id, column=column, predicate=pred_dict, child=scan)
    if encoding == Encoding.DICTIONARY.name or encoding == "DICTIONARY":
        return DictionaryFilter(operator_id=op_id, column=column, predicate=pred_dict, child=scan)
    return RawFilter(operator_id=op_id, column=column, predicate=pred_dict, child=scan)


def _build_filter_tree(
    pred: Any,
    columns: set[str],
    col_map: dict,
    snap_map: dict,
    prune_map: dict,
) -> Any:
    if isinstance(pred, And):
        left = _build_filter_tree(pred.left, columns, col_map, snap_map, prune_map)
        right = _build_filter_tree(pred.right, columns, col_map, snap_map, prune_map)
        return BitmapAnd(operator_id=new_operator_id("bitmap_and"), children=(left, right))
    if isinstance(pred, Or):
        left = _build_filter_tree(pred.left, columns, col_map, snap_map, prune_map)
        right = _build_filter_tree(pred.right, columns, col_map, snap_map, prune_map)
        return BitmapOr(operator_id=new_operator_id("bitmap_or"), children=(left, right))
    if isinstance(pred, Not):
        inner_col = _predicate_column(pred.operand)
        if inner_col and inner_col in snap_map:
            return _make_column_filter(inner_col, pred, col_map, snap_map, prune_map)
    col = _predicate_column(pred)
    if col and col in snap_map:
        return _make_column_filter(col, pred, col_map, snap_map, prune_map)
    ref_col = next(iter(columns)) if columns else next(iter(snap_map))
    return _make_column_filter(ref_col, pred, col_map, snap_map, prune_map)


def _all_pass(
    columns: set[str],
    col_map: dict,
    snap_map: dict,
    prune_map: dict,
) -> Any:
    if len(columns) == 1:
        col = next(iter(columns))
        return _make_block_scan(col, col_map, snap_map, prune_map)
    scans = tuple(_make_block_scan(c, col_map, snap_map, prune_map) for c in sorted(columns))
    if len(scans) == 1:
        return scans[0]
    return BitmapAnd(
        operator_id=new_operator_id("bitmap_and"),
        children=scans,
        annotations=(("all_pass", True),),
    )


def _predicate_column(pred: Any) -> str | None:
    if isinstance(pred, ColumnRef):
        return pred.name
    if isinstance(pred, Compare):
        if isinstance(pred.left, ColumnRef):
            return pred.left.name
        if isinstance(pred.right, ColumnRef):
            return pred.right.name
    if isinstance(pred, In) and isinstance(pred.expr, ColumnRef):
        return pred.expr.name
    if isinstance(pred, IsNull) and isinstance(pred.expr, ColumnRef):
        return pred.expr.name
    if isinstance(pred, Not):
        return _predicate_column(pred.operand)
    if isinstance(pred, And):
        return _predicate_column(pred.left) or _predicate_column(pred.right)
    if isinstance(pred, Or):
        return _predicate_column(pred.left) or _predicate_column(pred.right)
    return None


def _scan_columns(
    filter_pred: Any | None,
    output_cols: tuple[str, ...],
    aggregate: Aggregate | None,
    logical: Any,
) -> set[str]:
    cols: set[str] = set()
    if filter_pred is not None:
        cols.update(_columns_in_predicate(filter_pred))
    if aggregate is not None:
        for k in aggregate.group_keys:
            if isinstance(k, ColumnRef):
                cols.add(k.name)
        for a in aggregate.aggregates:
            if isinstance(a, AggregateExpr) and a.arg is not None:
                if isinstance(a.arg, ColumnRef):
                    cols.add(a.arg.name)
    else:
        cols.update(output_cols)
    scan = _find_scan(logical)
    if scan and scan.annotations:
        ann = dict(scan.annotations)
        if "required_columns" in ann:
            cols.update(ann["required_columns"])
    return {c for c in cols if c}


def _columns_in_predicate(pred: Any) -> set[str]:
    col = _predicate_column(pred)
    result: set[str] = set()
    if col:
        result.add(col)
    if isinstance(pred, And):
        result.update(_columns_in_predicate(pred.left))
        result.update(_columns_in_predicate(pred.right))
    if isinstance(pred, Or):
        result.update(_columns_in_predicate(pred.left))
        result.update(_columns_in_predicate(pred.right))
    if isinstance(pred, Not):
        result.update(_columns_in_predicate(pred.operand))
    return result


def _output_column_names(project: Project | None, aggregate: Aggregate | None) -> tuple[str, ...]:
    if project is None:
        return ()
    return _select_output_names(project)


def _select_output_names(project: Project) -> tuple[str, ...]:
    names: list[str] = []
    for item in project.items:
        if isinstance(item, SelectItem):
            if item.alias:
                names.append(item.alias)
            elif isinstance(item.expr, ColumnRef):
                names.append(item.expr.name)
            elif isinstance(item.expr, AggregateExpr) and item.expr.alias:
                names.append(item.expr.alias)
            else:
                names.append("col")
        else:
            names.append("col")
    return tuple(names)


def _find_scan(plan: Any) -> Scan | None:
    if isinstance(plan, Scan):
        return plan
    child = getattr(plan, "child", None)
    if child is not None:
        return _find_scan(child)
    return None


def _find_limit(plan: Any) -> Limit | None:
    if isinstance(plan, Limit):
        return plan
    child = getattr(plan, "child", None)
    return _find_limit(child) if child else None


def _find_sort(plan: Any) -> Sort | None:
    if isinstance(plan, Sort):
        return plan
    child = getattr(plan, "child", None)
    if isinstance(child, Limit):
        return _find_sort(child.child)
    return _find_sort(child) if child else None


def _find_aggregate(plan: Any) -> Aggregate | None:
    if isinstance(plan, Aggregate):
        return plan
    child = getattr(plan, "child", None)
    if child is not None:
        return _find_aggregate(child)
    return None


def _find_project(plan: Any) -> Project | None:
    if isinstance(plan, Project):
        return plan
    child = getattr(plan, "child", None)
    if child is not None:
        return _find_project(child)
    return None


def _find_filter_predicate(plan: Any) -> Any | None:
    if isinstance(plan, Filter):
        return plan.predicate
    child = getattr(plan, "child", None)
    if child is not None:
        return _find_filter_predicate(child)
    return None
