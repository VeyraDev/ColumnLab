from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CompareOp(StrEnum):
    EQ = "="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="


class AggFunc(StrEnum):
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"


@dataclass(frozen=True, slots=True)
class ColumnRef:
    name: str
    table: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"type": "ColumnRef", "name": self.name, "table": self.table}


@dataclass(frozen=True, slots=True)
class Literal:
    value: Any
    logical_type: str = "UTF8"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "Literal", "value": self.value, "logical_type": self.logical_type}


@dataclass(frozen=True, slots=True)
class Compare:
    op: CompareOp
    left: Any
    right: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "Compare",
            "op": self.op.value,
            "left": _expr_dict(self.left),
            "right": _expr_dict(self.right),
        }


@dataclass(frozen=True, slots=True)
class And:
    left: Any
    right: Any

    def to_dict(self) -> dict[str, Any]:
        return {"type": "And", "left": _expr_dict(self.left), "right": _expr_dict(self.right)}


@dataclass(frozen=True, slots=True)
class Or:
    left: Any
    right: Any

    def to_dict(self) -> dict[str, Any]:
        return {"type": "Or", "left": _expr_dict(self.left), "right": _expr_dict(self.right)}


@dataclass(frozen=True, slots=True)
class Not:
    operand: Any

    def to_dict(self) -> dict[str, Any]:
        return {"type": "Not", "operand": _expr_dict(self.operand)}


@dataclass(frozen=True, slots=True)
class In:
    expr: Any
    values: tuple[Any, ...]
    negated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "In",
            "expr": _expr_dict(self.expr),
            "values": [_expr_dict(v) for v in self.values],
            "negated": self.negated,
        }


@dataclass(frozen=True, slots=True)
class Between:
    expr: Any
    low: Any
    high: Any
    negated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "Between",
            "expr": _expr_dict(self.expr),
            "low": _expr_dict(self.low),
            "high": _expr_dict(self.high),
            "negated": self.negated,
        }


@dataclass(frozen=True, slots=True)
class IsNull:
    expr: Any
    negated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "IsNull",
            "expr": _expr_dict(self.expr),
            "negated": self.negated,
        }


@dataclass(frozen=True, slots=True)
class AggregateExpr:
    func: AggFunc
    arg: Any | None = None
    distinct: bool = False
    alias: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "AggregateExpr",
            "func": self.func.value,
            "arg": None if self.arg is None else _expr_dict(self.arg),
            "distinct": self.distinct,
            "alias": self.alias,
        }


@dataclass(frozen=True, slots=True)
class SelectItem:
    expr: Any
    alias: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"expr": _expr_dict(self.expr), "alias": self.alias}


@dataclass(frozen=True, slots=True)
class OrderKey:
    expr: Any
    ascending: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"expr": _expr_dict(self.expr), "ascending": self.ascending}


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    select: tuple[SelectItem, ...]
    from_table: str
    where: Any | None = None
    group_by: tuple[Any, ...] = ()
    order_by: tuple[OrderKey, ...] = ()
    limit: int | None = None
    offset: int | None = None


def _expr_dict(expr: Any) -> dict[str, Any]:
    if hasattr(expr, "to_dict"):
        return expr.to_dict()
    raise TypeError(f"unsupported expr type: {type(expr)!r}")
