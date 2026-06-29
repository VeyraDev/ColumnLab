import json

from app.engine.query.binder import ColumnSchema, TableSchema
from app.engine.query.logical import Filter, Limit, Project, Scan, plan_to_dict
from app.engine.query.optimizer import optimize_plan
from app.engine.query.planner import plan_query

TABLE = TableSchema(
    name="data",
    columns=(
        ColumnSchema(name="id", logical_type="INT64"),
        ColumnSchema(name="name", logical_type="UTF8"),
        ColumnSchema(name="qty", logical_type="INT64"),
    ),
)


def test_optimize_deterministic():
    plan = plan_query("SELECT id, name FROM data WHERE id > 1 LIMIT 10", TABLE)
    r1 = optimize_plan(plan, TABLE)
    r2 = optimize_plan(plan, TABLE)
    assert plan_to_dict(r1.plan) == plan_to_dict(r2.plan)
    assert [t.to_dict() for t in r1.trace] == [t.to_dict() for t in r2.trace]


def test_projection_pruning_annotation():
    plan = plan_query("SELECT id FROM data LIMIT 5", TABLE)
    result = optimize_plan(plan, TABLE)

    def find_scan(node):
        if isinstance(node, Scan):
            return node
        if isinstance(node, Filter):
            return find_scan(node.child)
        if isinstance(node, Project):
            return find_scan(node.child)
        if isinstance(node, Limit):
            return find_scan(node.child)
        return None

    scan = find_scan(result.plan)
    assert scan is not None
    ann = dict(scan.annotations)
    assert "required_columns" in ann
    assert set(ann["required_columns"]) == {"id"}


def test_filter_on_scan():
    plan = plan_query("SELECT id FROM data WHERE id > 1", TABLE)
    result = optimize_plan(plan, TABLE)
    node = result.plan
    if isinstance(node, Project):
        node = node.child
    assert isinstance(node, Filter)
    assert isinstance(node.child, Scan)


def test_limit_pushdown_without_sort():
    plan = plan_query("SELECT id FROM data WHERE id > 1 LIMIT 10", TABLE)
    result = optimize_plan(plan, TABLE)
    node = result.plan
    assert isinstance(node, Project)
    assert isinstance(node.child, Limit)
    assert isinstance(node.child.child, Filter)
