from app.engine.query.binder import ColumnSchema, TableSchema, bind_query
from app.engine.query.errors import TypeMismatchError


TABLE = TableSchema(
    name="data",
    columns=(
        ColumnSchema(name="id", logical_type="INT64"),
        ColumnSchema(name="price", logical_type="FLOAT64"),
    ),
)


def test_float64_compare_int_literal():
    q = bind_query("SELECT price FROM data WHERE price > 50", TABLE)
    assert q.where is not None
