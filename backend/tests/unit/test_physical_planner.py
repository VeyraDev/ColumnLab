from app.engine.query.binder import ColumnSchema, TableSchema
from app.engine.query.optimizer import optimize_plan
from app.engine.query.physical_planner import (
    ColumnCatalogInfo,
    PhysicalPlanContext,
    plan_physical,
    physical_plan_to_dict,
)
from app.engine.query.planner import plan_query
from app.engine.query.pruning import BlockStatsSnapshot, ColumnBlocksSnapshot, TableBlocksSnapshot, prune_blocks


TABLE = TableSchema(
    name="data",
    columns=(
        ColumnSchema(name="id", logical_type="INT64"),
        ColumnSchema(name="name", logical_type="UTF8"),
        ColumnSchema(name="status", logical_type="INT64"),
        ColumnSchema(name="qty", logical_type="INT64"),
    ),
)


def _snapshot() -> TableBlocksSnapshot:
    blocks = (
        BlockStatsSnapshot(
            block_id=0,
            encoding="RAW",
            row_count=100,
            null_count=0,
            min_repr="1",
            max_repr="100",
            dictionary_count=0,
            column_file_path="/tmp/id.col",
        ),
    )
    return TableBlocksSnapshot(
        table_name="data",
        columns=(
            ColumnBlocksSnapshot(name="id", logical_type="INT64", blocks=blocks),
            ColumnBlocksSnapshot(name="name", logical_type="UTF8", blocks=blocks),
            ColumnBlocksSnapshot(name="status", logical_type="INT64", blocks=blocks),
            ColumnBlocksSnapshot(name="qty", logical_type="INT64", blocks=blocks),
        ),
    )


def _ctx() -> PhysicalPlanContext:
    snap = _snapshot()
    pruning = prune_blocks(
        optimize_plan(plan_query("SELECT id FROM data WHERE id > 1", TABLE), TABLE).plan,
        snap,
    )
    cols = tuple(
        ColumnCatalogInfo(name=c.name, column_id=i + 1, file_path=c.blocks[0].column_file_path)
        for i, c in enumerate(snap.columns)
    )
    return PhysicalPlanContext(snapshot=snap, pruning=pruning, columns=cols, version_id=1)


def test_physical_plan_has_block_scan():
    logical = optimize_plan(plan_query("SELECT id FROM data WHERE id > 1 LIMIT 10", TABLE), TABLE).plan
    plan = plan_physical(logical, _ctx())
    d = physical_plan_to_dict(plan)
    assert d["type"] == "Limit"
    assert d["child"]["type"] == "Materialize"
    filter_node = d["child"]["child"]
    assert filter_node["type"] in {"RawFilter", "RleFilter", "DictionaryFilter"}
    assert filter_node["child"]["type"] == "BlockScan"


def test_physical_plan_and_predicate():
    logical = optimize_plan(
        plan_query("SELECT id FROM data WHERE id > 1 AND qty > 0", TABLE),
        TABLE,
    ).plan
    plan = plan_physical(logical, _ctx())
    d = physical_plan_to_dict(plan)
    filter_root = d["child"] if d["type"] == "Materialize" else d
    assert filter_root["type"] == "BitmapAnd"
    assert len(filter_root["children"]) == 2


def test_physical_plan_aggregate():
    sql = "SELECT status, COUNT(*) AS cnt FROM data GROUP BY status"
    logical = optimize_plan(plan_query(sql, TABLE), TABLE).plan
    plan = plan_physical(logical, _ctx())
    d = physical_plan_to_dict(plan)
    assert d["type"] == "Materialize"
    assert d["child"]["type"] == "HashAggregate"
