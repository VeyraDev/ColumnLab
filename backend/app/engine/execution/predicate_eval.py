from __future__ import annotations

from typing import Any

from app.engine.codecs.base import PredicateEq, PredicateIn, PredicateRange
from app.engine.query.expr import (
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
)


def expr_to_codec_predicate(expr: Any) -> object | None:
    if isinstance(expr, Compare):
        return _compare_to_predicate(expr)
    if isinstance(expr, In):
        values = tuple(_literal_value(v) for v in expr.values)
        if expr.negated:
            return ("not_in", values)
        return PredicateIn(values=values)
    if isinstance(expr, Between):
        low = _literal_value(expr.low)
        high = _literal_value(expr.high)
        pred = PredicateRange(lower=low, upper=high, lower_inclusive=True, upper_inclusive=True)
        if expr.negated:
            return ("not_range", pred)
        return pred
    if isinstance(expr, IsNull):
        return ("is_null", expr.negated)
    return None


def predicate_dict_to_codec(pred: dict[str, Any]) -> object | None:
    ptype = pred.get("type")
    if ptype == "Compare":
        op = CompareOp(pred["op"])
        left = pred["left"]
        right = pred["right"]
        col_side = left if left.get("type") == "ColumnRef" else right
        lit_side = right if left.get("type") == "ColumnRef" else left
        if col_side.get("type") != "ColumnRef":
            return None
        value = lit_side.get("value")
        if op == CompareOp.EQ:
            return PredicateEq(value=value)
        if op == CompareOp.NE:
            return ("not_eq", value)
        if op == CompareOp.GT:
            return PredicateRange(lower=value, lower_inclusive=False)
        if op == CompareOp.GE:
            return PredicateRange(lower=value, lower_inclusive=True)
        if op == CompareOp.LT:
            return PredicateRange(upper=value, upper_inclusive=False)
        if op == CompareOp.LE:
            return PredicateRange(upper=value, upper_inclusive=True)
    if ptype == "In":
        values = tuple(v.get("value") for v in pred.get("values", []))
        if pred.get("negated"):
            return ("not_in", values)
        return PredicateIn(values=values)
    if ptype == "IsNull":
        return ("is_null", pred.get("negated", False))
    if ptype == "Not":
        inner = predicate_dict_to_codec(pred.get("operand", {}))
        if inner is not None:
            return ("not", inner)
    return None


def _compare_to_predicate(expr: Compare) -> object:
    col = expr.left if isinstance(expr.left, ColumnRef) else expr.right
    lit = expr.right if isinstance(expr.left, ColumnRef) else expr.left
    value = _literal_value(lit)
    op = expr.op
    if op == CompareOp.EQ:
        return PredicateEq(value=value)
    if op == CompareOp.NE:
        return ("not_eq", value)
    if op == CompareOp.GT:
        return PredicateRange(lower=value, lower_inclusive=False)
    if op == CompareOp.GE:
        return PredicateRange(lower=value, lower_inclusive=True)
    if op == CompareOp.LT:
        return PredicateRange(upper=value, upper_inclusive=False)
    if op == CompareOp.LE:
        return PredicateRange(upper=value, upper_inclusive=True)
    raise ValueError(f"unsupported compare op: {op}")


def _literal_value(expr: Any) -> Any:
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, dict):
        return expr.get("value")
    raise TypeError(f"expected literal, got {type(expr)!r}")
