from app.engine.query.expr import And, Compare, CompareOp, ColumnRef, IsNull, Literal, SelectItem
from app.engine.query.pruning import (
    BlockPruneState,
    BlockStatsSnapshot,
    BlockVerdict,
    ColumnBlocksSnapshot,
    TableBlocksSnapshot,
    evaluate_predicate,
    prune_blocks,
    pruning_summary,
)
from app.engine.query.logical import Filter, Limit, Project, Scan


def _block(**kwargs) -> BlockStatsSnapshot:
    defaults = {
        "block_id": 0,
        "encoding": "RAW",
        "row_count": 100,
        "null_count": 0,
        "min_repr": "1",
        "max_repr": "10",
        "dictionary_count": 0,
        "column_file_path": "",
    }
    defaults.update(kwargs)
    return BlockStatsSnapshot(**defaults)


def test_prune_gt_always_false():
    pred = Compare(op=CompareOp.GT, left=ColumnRef(name="id"), right=Literal(value=100, logical_type="INT64"))
    block = _block(min_repr="1", max_repr="10")
    verdict, reason, _ = evaluate_predicate(pred, "INT64", block)
    assert verdict == BlockVerdict.ALWAYS_FALSE
    assert "max=" in reason


def test_prune_is_null_zero():
    pred = IsNull(expr=ColumnRef(name="id"))
    block = _block(null_count=0)
    verdict, reason, _ = evaluate_predicate(pred, "INT64", block)
    assert verdict == BlockVerdict.ALWAYS_FALSE
    assert reason == "null_count=0"


def test_prune_and_or():
    pred_and = And(
        left=Compare(op=CompareOp.GT, left=ColumnRef(name="id"), right=Literal(value=100, logical_type="INT64")),
        right=Compare(op=CompareOp.LT, left=ColumnRef(name="id"), right=Literal(value=200, logical_type="INT64")),
    )
    block = _block(min_repr="1", max_repr="10")
    verdict, _, _ = evaluate_predicate(pred_and, "INT64", block)
    assert verdict == BlockVerdict.ALWAYS_FALSE


def test_projection_pruned_column():
    plan = Limit(
        limit=10,
        offset=0,
        child=Project(
            items=(SelectItem(expr=ColumnRef(name="id")),),
            child=Filter(
                predicate=Compare(
                    op=CompareOp.GT,
                    left=ColumnRef(name="id"),
                    right=Literal(value=1, logical_type="INT64"),
                ),
                child=Scan(table="data", annotations=(("required_columns", ["id"]),)),
            ),
        ),
    )
    snapshot = TableBlocksSnapshot(
        table_name="data",
        columns=(
            ColumnBlocksSnapshot(name="id", logical_type="INT64", blocks=(_block(block_id=0),)),
            ColumnBlocksSnapshot(name="name", logical_type="UTF8", blocks=(_block(block_id=0),)),
        ),
    )
    entries = prune_blocks(plan, snapshot)
    name_entry = next(e for e in entries if e.column == "name")
    assert name_entry.state == BlockPruneState.SKIPPED
    assert name_entry.reason == "projection_pruned"
    summary = pruning_summary(entries)
    assert summary["pruned_blocks"] == 1
