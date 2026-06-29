from __future__ import annotations

from typing import Any

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
    SelectItem,
)


def expr_from_dict(data: dict[str, Any]) -> Any:
    etype = data.get("type")
    if etype == "ColumnRef":
        return ColumnRef(name=data["name"], table=data.get("table"))
    if etype == "Literal":
        return Literal(value=data["value"], logical_type=data.get("logical_type", "UTF8"))
    if etype == "Compare":
        return Compare(
            op=CompareOp(data["op"]),
            left=expr_from_dict(data["left"]),
            right=expr_from_dict(data["right"]),
        )
    if etype == "And":
        return And(left=expr_from_dict(data["left"]), right=expr_from_dict(data["right"]))
    if etype == "Or":
        return Or(left=expr_from_dict(data["left"]), right=expr_from_dict(data["right"]))
    if etype == "Not":
        return Not(operand=expr_from_dict(data["operand"]))
    if etype == "In":
        return In(
            expr=expr_from_dict(data["expr"]),
            values=tuple(expr_from_dict(v) for v in data.get("values", [])),
            negated=bool(data.get("negated", False)),
        )
    if etype == "Between":
        return Between(
            expr=expr_from_dict(data["expr"]),
            low=expr_from_dict(data["low"]),
            high=expr_from_dict(data["high"]),
            negated=bool(data.get("negated", False)),
        )
    if etype == "IsNull":
        return IsNull(expr=expr_from_dict(data["expr"]), negated=bool(data.get("negated", False)))
    if etype == "AggregateExpr":
        arg = data.get("arg")
        return AggregateExpr(
            func=AggFunc(data["func"]),
            arg=None if arg is None else expr_from_dict(arg),
            distinct=bool(data.get("distinct", False)),
            alias=data.get("alias"),
        )
    raise TypeError(f"unsupported expr type: {etype!r}")


def select_item_from_dict(data: dict[str, Any]) -> SelectItem:
    return SelectItem(expr=expr_from_dict(data["expr"]), alias=data.get("alias"))


def order_key_from_dict(data: dict[str, Any]) -> OrderKey:
    return OrderKey(expr=expr_from_dict(data["expr"]), ascending=bool(data.get("ascending", True)))
