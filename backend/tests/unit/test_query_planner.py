import json

from app.engine.query.binder import ColumnSchema, TableSchema
from app.engine.query.logical import plan_to_dict
from app.engine.query.planner import plan_query


TABLE = TableSchema(
    name="data",
    columns=(
        ColumnSchema(name="id", logical_type="INT64"),
        ColumnSchema(name="name", logical_type="UTF8"),
        ColumnSchema(name="region", logical_type="UTF8"),
        ColumnSchema(name="qty", logical_type="INT64"),
    ),
)

SQL = (
    "SELECT region, COUNT(*) AS cnt FROM data "
    "WHERE qty > 0 GROUP BY region ORDER BY cnt DESC LIMIT 10"
)


def test_plan_deterministic():
    plan1 = plan_to_dict(plan_query(SQL, TABLE))
    plan2 = plan_to_dict(plan_query(SQL, TABLE))
    assert plan1 == plan2


def test_plan_structure_golden():
    plan = plan_to_dict(plan_query(SQL, TABLE))
    assert plan["type"] == "Limit"
    assert plan["child"]["type"] == "Sort"
    inner = plan["child"]["child"]
    assert inner["type"] == "Project"
    assert inner["child"]["type"] == "Aggregate"
    assert inner["child"]["child"]["type"] == "Filter"
    assert inner["child"]["child"]["child"]["type"] == "Scan"
    assert inner["child"]["child"]["child"]["table"] == "data"
    serialized = json.dumps(plan, sort_keys=True)
    assert "Scan" in serialized
    assert "Filter" in serialized
