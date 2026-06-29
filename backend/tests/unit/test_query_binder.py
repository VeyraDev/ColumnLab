import pytest

from app.engine.query.binder import ColumnSchema, TableSchema, bind_query
from app.engine.query.errors import TypeMismatchError, UnknownColumnError, UnknownTableError


TABLE = TableSchema(
    name="data",
    columns=(
        ColumnSchema(name="id", logical_type="INT64"),
        ColumnSchema(name="name", logical_type="UTF8"),
        ColumnSchema(name="qty", logical_type="INT64"),
        ColumnSchema(name="score", logical_type="DOUBLE"),
    ),
)


def test_bind_valid_query():
    q = bind_query("SELECT id, name FROM data WHERE id > 1", TABLE)
    assert q.from_table == "data"
    assert q.select[0].expr.name == "id"


def test_unknown_column():
    with pytest.raises(UnknownColumnError) as exc:
        bind_query("SELECT missing FROM data", TABLE)
    assert "missing" in exc.value.message


def test_unknown_table():
    with pytest.raises(UnknownTableError):
        bind_query("SELECT id FROM other", TABLE)


def test_type_mismatch_string_vs_int():
    with pytest.raises(TypeMismatchError) as exc:
        bind_query("SELECT id FROM data WHERE id = 'abc'", TABLE)
    assert "类型不兼容" in exc.value.message
