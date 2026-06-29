from __future__ import annotations

from app.engine.query.binder import TableSchema, bind_query
from app.engine.query.expr import AggregateExpr, ParsedQuery, SelectItem
from app.engine.query.logical import Aggregate, Filter, Limit, Project, Scan, Sort


class LogicalPlanner:
    def plan(self, parsed: ParsedQuery) -> object:
        root: object = Scan(table=parsed.from_table)
        if parsed.where is not None:
            root = Filter(predicate=parsed.where, child=root)
        aggregates = tuple(item.expr for item in parsed.select if isinstance(item.expr, AggregateExpr))
        plain_items = tuple(item for item in parsed.select if not isinstance(item.expr, AggregateExpr))
        if parsed.group_by or aggregates:
            root = Aggregate(group_keys=parsed.group_by, aggregates=aggregates, child=root)
            root = Project(items=parsed.select, child=root)
        elif plain_items:
            root = Project(items=parsed.select, child=root)
        if parsed.order_by:
            root = Sort(keys=parsed.order_by, child=root)
        if parsed.limit is not None:
            root = Limit(limit=parsed.limit, offset=parsed.offset or 0, child=root)
        return root


def plan_query(sql: str, table: TableSchema) -> object:
    bound = bind_query(sql, table)
    return LogicalPlanner().plan(bound)


def plan_parsed(parsed: ParsedQuery) -> object:
    return LogicalPlanner().plan(parsed)
