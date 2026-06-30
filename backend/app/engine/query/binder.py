from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.query.errors import TypeMismatchError, UnknownColumnError, UnknownTableError
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
    ParsedQuery,
    SelectItem,
)
from app.engine.query.parser import parse_sql


NUMERIC_TYPES = {"INT64", "DOUBLE", "FLOAT64", "DECIMAL64"}


def _is_numeric(logical_type: str) -> bool:
    return logical_type in NUMERIC_TYPES


@dataclass(frozen=True, slots=True)
class ColumnSchema:
    name: str
    logical_type: str


@dataclass(frozen=True, slots=True)
class TableSchema:
    name: str
    columns: tuple[ColumnSchema, ...]

    def column_map(self) -> dict[str, ColumnSchema]:
        return {c.name: c for c in self.columns}


class CatalogBinder:
    def __init__(self, table: TableSchema) -> None:
        self._table = table
        self._columns = table.column_map()

    def bind(self, sql: str) -> ParsedQuery:
        parsed = parse_sql(sql)
        if parsed.from_table != self._table.name:
            raise UnknownTableError(message=f"未知表: {parsed.from_table}")
        return self._bind_query(parsed)

    def bind_parsed(self, parsed: ParsedQuery) -> ParsedQuery:
        if parsed.from_table != self._table.name:
            raise UnknownTableError(message=f"未知表: {parsed.from_table}")
        return self._bind_query(parsed)

    def _bind_query(self, parsed: ParsedQuery) -> ParsedQuery:
        select = tuple(self._bind_select_item(item) for item in parsed.select)
        select_aliases = {item.alias for item in select if item.alias}
        where = self._bind_bool(parsed.where) if parsed.where else None
        group_by = tuple(self._bind_column_ref(k, ctx="GROUP BY") for k in parsed.group_by)
        order_by = tuple(
            type(k)(
                expr=self._bind_order_expr(k.expr, select_aliases=select_aliases),
                ascending=k.ascending,
            )
            for k in parsed.order_by
        )
        return ParsedQuery(
            select=select,
            from_table=parsed.from_table,
            where=where,
            group_by=group_by,
            order_by=order_by,
            limit=parsed.limit,
            offset=parsed.offset,
        )

    def _bind_select_item(self, item: SelectItem) -> SelectItem:
        if isinstance(item.expr, AggregateExpr):
            bound = self._bind_aggregate(item.expr)
        else:
            bound = self._bind_column_ref(item.expr, ctx="SELECT")
        return SelectItem(expr=bound, alias=item.alias)

    def _bind_aggregate(self, agg: AggregateExpr) -> AggregateExpr:
        if agg.func == AggFunc.COUNT and agg.arg is None:
            return agg
        if agg.arg is None:
            raise TypeMismatchError(message=f"{agg.func.value} 需要列参数")
        arg = self._bind_value(agg.arg, ctx="SELECT")
        arg_type = self._expr_type(arg)
        if agg.func in {AggFunc.SUM, AggFunc.AVG} and not _is_numeric(arg_type):
            raise TypeMismatchError(message=f"{agg.func.value} 需要数值列")
        return AggregateExpr(func=agg.func, arg=arg, distinct=agg.distinct, alias=agg.alias)

    def _bind_bool(self, expr) -> Any:
        if isinstance(expr, And):
            return And(left=self._bind_bool(expr.left), right=self._bind_bool(expr.right))
        if isinstance(expr, Or):
            return Or(left=self._bind_bool(expr.left), right=self._bind_bool(expr.right))
        if isinstance(expr, Not):
            return Not(operand=self._bind_bool(expr.operand))
        if isinstance(expr, In):
            col = self._bind_column_ref(expr.expr, ctx="WHERE")
            values = tuple(self._bind_literal_for_column(v, col) for v in expr.values)
            return In(expr=col, values=values, negated=expr.negated)
        if isinstance(expr, Between):
            col = self._bind_column_ref(expr.expr, ctx="WHERE")
            low = self._bind_literal_for_column(expr.low, col)
            high = self._bind_literal_for_column(expr.high, col)
            return Between(expr=col, low=low, high=high, negated=expr.negated)
        if isinstance(expr, IsNull):
            col = self._bind_column_ref(expr.expr, ctx="WHERE")
            return IsNull(expr=col, negated=expr.negated)
        if isinstance(expr, Compare):
            left = self._bind_value(expr.left, ctx="WHERE")
            right = self._bind_value(expr.right, ctx="WHERE")
            self._check_compare_types(left, right, expr.op)
            return Compare(op=expr.op, left=left, right=right)
        raise TypeMismatchError(message="无法绑定的谓词表达式")

    def _bind_value(self, expr, *, ctx: str):
        if isinstance(expr, ColumnRef):
            return self._bind_column_ref(expr, ctx=ctx)
        if isinstance(expr, Literal):
            return expr
        raise TypeMismatchError(message=f"{ctx} 中存在无法绑定的表达式")

    def _bind_column_ref(self, expr, *, ctx: str) -> ColumnRef:
        if not isinstance(expr, ColumnRef):
            raise TypeMismatchError(message=f"{ctx} 需要列引用")
        if expr.table and expr.table != self._table.name:
            raise UnknownTableError(message=f"未知表: {expr.table}")
        col = self._columns.get(expr.name)
        if col is None:
            raise UnknownColumnError(message=f"未知列: {expr.name}")
        return ColumnRef(name=col.name, table=self._table.name)

    def _bind_order_expr(self, expr, *, select_aliases: set[str]):
        if isinstance(expr, ColumnRef) and expr.name in select_aliases:
            return ColumnRef(name=expr.name, table=self._table.name)
        return self._bind_column_ref(expr, ctx="ORDER BY")

    def _bind_literal_for_column(self, lit, col: ColumnRef) -> Literal:
        if not isinstance(lit, Literal):
            raise TypeMismatchError(message="IN/BETWEEN 需要字面量")
        schema = self._columns[col.name]
        if lit.value is None:
            return lit
        if _is_numeric(schema.logical_type) and lit.logical_type == "UTF8":
            raise TypeMismatchError(message=f"列 {col.name} 为 {schema.logical_type}，不能与字符串比较")
        return lit

    def _check_compare_types(self, left, right, op: CompareOp) -> None:
        left_type = self._expr_type(left)
        right_type = self._expr_type(right)
        if left_type == "NULL" or right_type == "NULL":
            return
        if left_type == right_type:
            return
        if _is_numeric(left_type) and _is_numeric(right_type):
            return
        raise TypeMismatchError(
            message=f"类型不兼容: {left_type} {op.value} {right_type}",
        )

    def _expr_type(self, expr) -> str:
        if isinstance(expr, ColumnRef):
            return self._columns[expr.name].logical_type
        if isinstance(expr, Literal):
            return expr.logical_type
        raise TypeMismatchError(message="无法推断表达式类型")


def bind_query(sql: str, table: TableSchema) -> ParsedQuery:
    return CatalogBinder(table).bind(sql)
