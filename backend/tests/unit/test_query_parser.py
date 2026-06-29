import pytest

from app.engine.query.errors import ParseError, UnsupportedSyntaxError
from app.engine.query.expr import AggFunc, And, Between, ColumnRef, Compare, CompareOp, In, IsNull, Literal, Not, Or
from app.engine.query.parser import parse_sql


def test_parse_simple_select():
    q = parse_sql("SELECT id, name FROM data WHERE id > 1 LIMIT 10")
    assert q.from_table == "data"
    assert len(q.select) == 2
    assert isinstance(q.select[0].expr, ColumnRef)
    assert q.select[0].expr.name == "id"
    assert isinstance(q.where, Compare)
    assert q.limit == 10
    assert q.offset == 0


def test_parse_where_and_or_not():
    q = parse_sql(
        "SELECT id FROM data WHERE id > 1 AND name = 'a' OR NOT flag IS NULL"
    )
    assert isinstance(q.where, Or)
    assert isinstance(q.where.left, And)
    assert isinstance(q.where.right, Not)
    assert isinstance(q.where.right.operand, IsNull)


def test_parse_in_between():
    q = parse_sql("SELECT id FROM data WHERE id IN (1, 2, 3) AND qty BETWEEN 1 AND 10")
    assert isinstance(q.where, And)
    assert isinstance(q.where.left, In)
    assert isinstance(q.where.right, Between)


def test_parse_group_by_aggregate():
    q = parse_sql(
        "SELECT region, COUNT(*) AS cnt FROM data GROUP BY region ORDER BY cnt DESC LIMIT 5 OFFSET 2"
    )
    assert q.from_table == "data"
    assert len(q.group_by) == 1
    assert q.select[1].alias == "cnt"
    assert q.select[1].expr.func == AggFunc.COUNT
    assert q.order_by[0].ascending is False
    assert q.limit == 5
    assert q.offset == 2


def test_reject_join():
    with pytest.raises(UnsupportedSyntaxError) as exc:
        parse_sql("SELECT a.id FROM a JOIN b ON a.id = b.id")
    assert "JOIN" in exc.value.message


def test_reject_select_star():
    with pytest.raises(UnsupportedSyntaxError):
        parse_sql("SELECT * FROM data")


def test_reject_having():
    with pytest.raises(UnsupportedSyntaxError) as exc:
        parse_sql("SELECT region FROM data GROUP BY region HAVING COUNT(*) > 1")
    assert "HAVING" in exc.value.message


def test_missing_from():
    with pytest.raises(ParseError):
        parse_sql("SELECT id")
