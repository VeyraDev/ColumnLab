from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp

from app.engine.query.errors import ParseError, UnsupportedSyntaxError
from app.engine.query.expr import (
    AggFunc,
    AggregateExpr,
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
    OrderKey,
    ParsedQuery,
    SelectItem,
)


def parse_sql(sql: str) -> ParsedQuery:
    try:
        tree = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError as exc:
        raise ParseError(message=str(exc)) from exc

    if not isinstance(tree, exp.Select):
        raise UnsupportedSyntaxError(message="仅支持 SELECT 语句")

    _reject_unsupported(tree)

    from_table = _extract_from_table(tree)
    select_items = _extract_select(tree)
    where = _extract_where(tree)
    group_by = _extract_group_by(tree)
    order_by = _extract_order_by(tree)
    limit, offset = _extract_limit_offset(tree)

    return ParsedQuery(
        select=select_items,
        from_table=from_table,
        where=where,
        group_by=group_by,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )


def _reject_unsupported(tree: exp.Select) -> None:
    if tree.args.get("joins"):
        raise UnsupportedSyntaxError(
            message="暂不支持 JOIN，请使用单表查询",
            **_pos(tree.args["joins"][0]),
        )
    if tree.args.get("having"):
        raise UnsupportedSyntaxError(
            message="暂不支持 HAVING，请改写查询",
            **_pos(tree.args["having"]),
        )
    if tree.find(exp.Subquery):
        raise UnsupportedSyntaxError(message="暂不支持子查询")
    if tree.find(exp.Union):
        raise UnsupportedSyntaxError(message="暂不支持 UNION")
    if tree.find(exp.Window):
        raise UnsupportedSyntaxError(message="暂不支持窗口函数")


def _pos(node: exp.Expression) -> dict[str, int | None]:
    line = getattr(node, "line", None)
    col = getattr(node, "col", None)
    return {"line": line, "col": col}


def _extract_from_table(tree: exp.Select) -> str:
    from_ = tree.args.get("from_") or tree.args.get("from")
    if from_ is None:
        raise ParseError(message="缺少 FROM 子句")
    table = from_.this
    if isinstance(table, exp.Table):
        return table.name
    raise UnsupportedSyntaxError(message="暂不支持该 FROM 语法", **_pos(from_))


def _extract_select(tree: exp.Select) -> tuple[SelectItem, ...]:
    items: list[SelectItem] = []
    for expr in tree.expressions:
        items.append(_select_item(expr))
    if not items:
        raise ParseError(message="SELECT 列表不能为空")
    return tuple(items)


def _select_item(expr: exp.Expression) -> SelectItem:
    alias = None
    inner = expr
    if isinstance(expr, exp.Alias):
        alias = expr.alias
        inner = expr.this
    converted = _value_expr(inner, allow_aggregate=True)
    if isinstance(converted, AggregateExpr) and alias:
        converted = AggregateExpr(
            func=converted.func,
            arg=converted.arg,
            distinct=converted.distinct,
            alias=alias,
        )
        return SelectItem(expr=converted, alias=alias)
    return SelectItem(expr=converted, alias=alias)


def _extract_where(tree: exp.Select) -> Any | None:
    where = tree.args.get("where")
    if where is None:
        return None
    return _bool_expr(where.this)


def _extract_group_by(tree: exp.Select) -> tuple[Any, ...]:
    group = tree.args.get("group")
    if group is None:
        return ()
    return tuple(_value_expr(e, allow_aggregate=False) for e in group.expressions)


def _extract_order_by(tree: exp.Select) -> tuple[OrderKey, ...]:
    order = tree.args.get("order")
    if order is None:
        return ()
    keys: list[OrderKey] = []
    for item in order.expressions:
        ascending = True
        inner = item
        if isinstance(item, exp.Ordered):
            ascending = item.args.get("desc") is not True
            inner = item.this
        keys.append(OrderKey(expr=_value_expr(inner, allow_aggregate=False), ascending=ascending))
    return tuple(keys)


def _extract_limit_offset(tree: exp.Select) -> tuple[int | None, int | None]:
    limit_expr = tree.args.get("limit")
    if limit_expr is None:
        return None, None
    limit_val = _int_literal(limit_expr.expression, "LIMIT")
    offset_val = 0
    offset_expr = tree.args.get("offset")
    if offset_expr is not None:
        offset_val = _int_literal(offset_expr.expression, "OFFSET")
    return limit_val, offset_val


def _int_literal(node: exp.Expression, label: str) -> int:
    if isinstance(node, exp.Literal) and node.is_int:
        return int(node.this)
    raise ParseError(message=f"{label} 必须为整数", **_pos(node))


def _bool_expr(node: exp.Expression) -> Any:
    if isinstance(node, exp.And):
        return And(left=_bool_expr(node.left), right=_bool_expr(node.right))
    if isinstance(node, exp.Or):
        return Or(left=_bool_expr(node.left), right=_bool_expr(node.right))
    if isinstance(node, exp.Not):
        return Not(operand=_bool_expr(node.this))
    if isinstance(node, exp.In):
        values = tuple(_value_expr(v, allow_aggregate=False) for v in node.expressions)
        return In(expr=_value_expr(node.this, allow_aggregate=False), values=values, negated=bool(node.args.get("not")))
    if isinstance(node, exp.Between):
        return Between(
            expr=_value_expr(node.this, allow_aggregate=False),
            low=_value_expr(node.args["low"], allow_aggregate=False),
            high=_value_expr(node.args["high"], allow_aggregate=False),
            negated=bool(node.args.get("not")),
        )
    if isinstance(node, exp.Is):
        if isinstance(node.args.get("expression"), exp.Null):
            return IsNull(expr=_value_expr(node.this, allow_aggregate=False), negated=bool(node.args.get("not")))
    if isinstance(node, (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)):
        op_map = {
            exp.EQ: CompareOp.EQ,
            exp.NEQ: CompareOp.NE,
            exp.GT: CompareOp.GT,
            exp.GTE: CompareOp.GE,
            exp.LT: CompareOp.LT,
            exp.LTE: CompareOp.LE,
        }
        return Compare(
            op=op_map[type(node)],
            left=_value_expr(node.left, allow_aggregate=False),
            right=_value_expr(node.right, allow_aggregate=False),
        )
    raise UnsupportedSyntaxError(message=f"暂不支持 WHERE 表达式: {node.key}", **_pos(node))


def _value_expr(node: exp.Expression, *, allow_aggregate: bool) -> Any:
    if isinstance(node, exp.Column):
        table = node.table if node.table else None
        return ColumnRef(name=node.name, table=table)
    if isinstance(node, exp.Literal):
        if node.is_string:
            return Literal(value=node.this, logical_type="UTF8")
        if node.is_int:
            return Literal(value=int(node.this), logical_type="INT64")
        if node.is_number:
            return Literal(value=float(node.this), logical_type="DOUBLE")
        if node.this.upper() == "NULL":
            return Literal(value=None, logical_type="NULL")
        return Literal(value=node.this, logical_type="UTF8")
    if isinstance(node, exp.Star):
        raise UnsupportedSyntaxError(message="暂不支持 SELECT *，请列出具体列")
    if isinstance(node, exp.AggFunc):
        if not allow_aggregate:
            raise UnsupportedSyntaxError(message="聚合函数仅允许出现在 SELECT 或 HAVING", **_pos(node))
        return _aggregate_expr(node)
    if isinstance(node, exp.Paren):
        return _value_expr(node.this, allow_aggregate=allow_aggregate)
    raise UnsupportedSyntaxError(message=f"暂不支持表达式: {node.key}", **_pos(node))


def _aggregate_expr(node: exp.AggFunc) -> AggregateExpr:
    func_name = node.sql_name().upper()
    try:
        func = AggFunc(func_name)
    except ValueError as exc:
        raise UnsupportedSyntaxError(message=f"不支持的聚合函数: {func_name}", **_pos(node)) from exc

    arg = None
    if isinstance(node, exp.Count):
        if node.expressions:
            inner = node.expressions[0]
            if isinstance(inner, exp.Star):
                arg = None
            else:
                arg = _value_expr(inner, allow_aggregate=False)
        distinct = bool(node.args.get("distinct"))
    else:
        if node.expressions:
            arg = _value_expr(node.expressions[0], allow_aggregate=False)
        elif getattr(node, "this", None) is not None:
            arg = _value_expr(node.this, allow_aggregate=False)
        else:
            raise ParseError(message=f"{func_name} 需要参数", **_pos(node))
        distinct = bool(node.args.get("distinct"))

    return AggregateExpr(func=func, arg=arg, distinct=distinct)
