from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engine.query.binder import TableSchema
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
from app.engine.query.logical import (
    Aggregate,
    Filter,
    Limit,
    Project,
    Scan,
    Sort,
    plan_to_dict,
)


@dataclass(frozen=True, slots=True)
class OptimizerTraceEntry:
    rule: str
    changed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "changed": self.changed, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class OptimizeResult:
    plan: Any
    trace: tuple[OptimizerTraceEntry, ...]


class RuleOptimizer:
    def optimize(self, plan: Any, schema: TableSchema) -> OptimizeResult:
        trace: list[OptimizerTraceEntry] = []
        plan = self._apply_rule("constant_folding", plan, self._constant_folding, trace)
        plan = self._apply_rule("predicate_normalization", plan, self._predicate_normalization, trace)
        refs = collect_column_refs(plan)
        plan = self._apply_rule(
            "projection_pruning",
            plan,
            lambda p: self._projection_pruning(p, refs, schema),
            trace,
        )
        plan = self._apply_rule("predicate_pushdown", plan, self._predicate_pushdown, trace)
        plan = self._apply_rule("aggregate_pushdown", plan, self._aggregate_pushdown, trace)
        plan = self._apply_rule("limit_pushdown", plan, self._limit_pushdown, trace)
        return OptimizeResult(plan=plan, trace=tuple(trace))

    def _apply_rule(self, name: str, plan: Any, fn, trace: list[OptimizerTraceEntry]) -> Any:
        before = plan_to_dict(plan)
        after_plan = fn(plan)
        after = plan_to_dict(after_plan)
        trace.append(
            OptimizerTraceEntry(
                rule=name,
                changed=before != after,
                detail="" if before == after else f"applied {name}",
            )
        )
        return after_plan

    def _constant_folding(self, plan: Any) -> Any:
        return map_plan(plan, on_filter=self._fold_filter)

    def _fold_filter(self, node: Filter) -> Filter:
        folded = fold_expr(node.predicate)
        return Filter(predicate=folded, child=node.child, annotations=node.annotations)

    def _predicate_normalization(self, plan: Any) -> Any:
        return map_plan(plan, on_filter=lambda n: Filter(predicate=normalize_predicate(n.predicate), child=n.child, annotations=n.annotations))

    def _projection_pruning(self, plan: Any, refs: set[str], schema: TableSchema) -> Any:
        pruned = sorted(refs)
        return map_plan(
            plan,
            on_scan=lambda n: Scan(
                table=n.table,
                annotations=(("required_columns", pruned),),
            ),
        )

    def _predicate_pushdown(self, plan: Any) -> Any:
        return push_filter_to_scan(plan)

    def _aggregate_pushdown(self, plan: Any) -> Any:
        return plan

    def _limit_pushdown(self, plan: Any) -> Any:
        return push_limit_down(plan)


def optimize_plan(plan: Any, schema: TableSchema) -> OptimizeResult:
    return RuleOptimizer().optimize(plan, schema)


def collect_column_refs(plan: Any) -> set[str]:
    refs: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, Scan):
            return
        if isinstance(node, Filter):
            collect_expr_refs(node.predicate, refs)
            walk(node.child)
        elif isinstance(node, Project):
            for item in node.items:
                collect_expr_refs(item.expr, refs)
                if item.alias:
                    refs.add(item.alias)
            walk(node.child)
        elif isinstance(node, Aggregate):
            for key in node.group_keys:
                collect_expr_refs(key, refs)
            for agg in node.aggregates:
                collect_expr_refs(agg, refs)
                if isinstance(agg, AggregateExpr) and agg.arg is not None:
                    collect_expr_refs(agg.arg, refs)
            walk(node.child)
        elif isinstance(node, Sort):
            for key in node.keys:
                collect_expr_refs(key.expr, refs)
            walk(node.child)
        elif isinstance(node, Limit):
            walk(node.child)

    walk(plan)
    return refs


def collect_expr_refs(expr: Any, refs: set[str]) -> None:
    if isinstance(expr, ColumnRef):
        refs.add(expr.name)
    elif isinstance(expr, Compare):
        collect_expr_refs(expr.left, refs)
        collect_expr_refs(expr.right, refs)
    elif isinstance(expr, And):
        collect_expr_refs(expr.left, refs)
        collect_expr_refs(expr.right, refs)
    elif isinstance(expr, Or):
        collect_expr_refs(expr.left, refs)
        collect_expr_refs(expr.right, refs)
    elif isinstance(expr, Not):
        collect_expr_refs(expr.operand, refs)
    elif isinstance(expr, In):
        collect_expr_refs(expr.expr, refs)
        for v in expr.values:
            collect_expr_refs(v, refs)
    elif isinstance(expr, Between):
        collect_expr_refs(expr.expr, refs)
        collect_expr_refs(expr.low, refs)
        collect_expr_refs(expr.high, refs)
    elif isinstance(expr, IsNull):
        collect_expr_refs(expr.expr, refs)
    elif isinstance(expr, AggregateExpr) and expr.arg is not None:
        collect_expr_refs(expr.arg, refs)


def fold_expr(expr: Any) -> Any:
    if isinstance(expr, Compare):
        left = fold_expr(expr.left)
        right = fold_expr(expr.right)
        if isinstance(left, Literal) and isinstance(right, Literal):
            result = eval_compare(left, right, expr.op)
            return Literal(value=result, logical_type="BOOLEAN")
        return Compare(op=expr.op, left=left, right=right)
    if isinstance(expr, And):
        left = fold_expr(expr.left)
        right = fold_expr(expr.right)
        if isinstance(left, Literal) and left.value is False:
            return Literal(value=False, logical_type="BOOLEAN")
        if isinstance(right, Literal) and right.value is False:
            return Literal(value=False, logical_type="BOOLEAN")
        if isinstance(left, Literal) and left.value is True:
            return right
        if isinstance(right, Literal) and right.value is True:
            return left
        return And(left=left, right=right)
    if isinstance(expr, Or):
        left = fold_expr(expr.left)
        right = fold_expr(expr.right)
        if isinstance(left, Literal) and left.value is True:
            return Literal(value=True, logical_type="BOOLEAN")
        if isinstance(right, Literal) and right.value is True:
            return Literal(value=True, logical_type="BOOLEAN")
        if isinstance(left, Literal) and left.value is False:
            return right
        if isinstance(right, Literal) and right.value is False:
            return left
        return Or(left=left, right=right)
    if isinstance(expr, Not):
        inner = fold_expr(expr.operand)
        if isinstance(inner, Literal) and inner.logical_type == "BOOLEAN":
            return Literal(value=not inner.value, logical_type="BOOLEAN")
        return Not(operand=inner)
    return expr


def eval_compare(left: Literal, right: Literal, op: CompareOp) -> bool:
    lv, rv = left.value, right.value
    if op == CompareOp.EQ:
        return lv == rv
    if op == CompareOp.NE:
        return lv != rv
    if op == CompareOp.GT:
        return lv > rv
    if op == CompareOp.GE:
        return lv >= rv
    if op == CompareOp.LT:
        return lv < rv
    if op == CompareOp.LE:
        return lv <= rv
    raise ValueError(f"unknown op {op}")


def normalize_predicate(expr: Any) -> Any:
    if isinstance(expr, And):
        parts = flatten_and(expr)
        out = parts[0]
        for part in parts[1:]:
            out = And(left=out, right=part)
        return out
    if isinstance(expr, Not) and isinstance(expr.operand, Or):
        left = normalize_predicate(Not(operand=expr.operand.left))
        right = normalize_predicate(Not(operand=expr.operand.right))
        return And(left=left, right=right)
    if isinstance(expr, Not) and isinstance(expr.operand, And):
        left = normalize_predicate(Not(operand=expr.operand.left))
        right = normalize_predicate(Not(operand=expr.operand.right))
        return Or(left=left, right=right)
    if isinstance(expr, And):
        return And(left=normalize_predicate(expr.left), right=normalize_predicate(expr.right))
    if isinstance(expr, Or):
        return Or(left=normalize_predicate(expr.left), right=normalize_predicate(expr.right))
    if isinstance(expr, Not):
        return Not(operand=normalize_predicate(expr.operand))
    return expr


def flatten_and(expr: Any) -> list[Any]:
    if isinstance(expr, And):
        return flatten_and(expr.left) + flatten_and(expr.right)
    return [expr]


def push_filter_to_scan(plan: Any) -> Any:
    predicates: list[Any] = []

    def peel_filters(node: Any) -> Any:
        if isinstance(node, Filter):
            predicates.append(node.predicate)
            return peel_filters(node.child)
        return node

    core = peel_filters(plan)
    if not predicates:
        return plan
    predicate = predicates[0]
    for extra in predicates[1:]:
        predicate = And(left=predicate, right=extra)
    filtered = Filter(predicate=predicate, child=core)
    return rebuild_without_filters(plan, filtered)


def rebuild_without_filters(node: Any, inner: Any) -> Any:
    if isinstance(node, Filter):
        return rebuild_without_filters(node.child, inner)
    if isinstance(node, Scan):
        return inner
    if isinstance(node, Project):
        return Project(items=node.items, child=rebuild_without_filters(node.child, inner), annotations=node.annotations)
    if isinstance(node, Aggregate):
        return Aggregate(
            group_keys=node.group_keys,
            aggregates=node.aggregates,
            child=rebuild_without_filters(node.child, inner),
            annotations=node.annotations,
        )
    if isinstance(node, Sort):
        return Sort(keys=node.keys, child=rebuild_without_filters(node.child, inner), annotations=node.annotations)
    if isinstance(node, Limit):
        return Limit(
            limit=node.limit,
            offset=node.offset,
            child=rebuild_without_filters(node.child, inner),
            annotations=node.annotations,
        )
    return inner


def push_limit_down(plan: Any) -> Any:
    if not isinstance(plan, Limit):
        return plan
    if isinstance(plan.child, Sort):
        return plan
    limit = plan
    return _push_limit_past(limit, limit.child)


def _push_limit_past(limit: Limit, node: Any) -> Any:
    if isinstance(node, Project):
        return Project(
            items=node.items,
            child=Limit(limit=limit.limit, offset=limit.offset, child=_push_limit_past(limit, node.child), annotations=limit.annotations),
            annotations=node.annotations,
        )
    if isinstance(node, Aggregate):
        return Aggregate(
            group_keys=node.group_keys,
            aggregates=node.aggregates,
            child=Limit(limit=limit.limit, offset=limit.offset, child=_push_limit_past(limit, node.child), annotations=limit.annotations),
            annotations=node.annotations,
        )
    if isinstance(node, Filter):
        return Filter(
            predicate=node.predicate,
            child=Limit(limit=limit.limit, offset=limit.offset, child=node.child, annotations=limit.annotations),
            annotations=node.annotations,
        )
    if isinstance(node, Scan):
        return Limit(limit=limit.limit, offset=limit.offset, child=node, annotations=limit.annotations)
    return limit


def map_plan(
    plan: Any,
    *,
    on_scan=None,
    on_filter=None,
    on_project=None,
    on_aggregate=None,
    on_sort=None,
    on_limit=None,
) -> Any:
    if isinstance(plan, Limit):
        child = map_plan(plan.child, on_scan=on_scan, on_filter=on_filter, on_project=on_project, on_aggregate=on_aggregate, on_sort=on_sort, on_limit=on_limit)
        if on_limit:
            return on_limit(plan)
        return Limit(limit=plan.limit, offset=plan.offset, child=child, annotations=plan.annotations)
    if isinstance(plan, Sort):
        child = map_plan(plan.child, on_scan=on_scan, on_filter=on_filter, on_project=on_project, on_aggregate=on_aggregate, on_sort=on_sort, on_limit=on_limit)
        if on_sort:
            return on_sort(plan)
        return Sort(keys=plan.keys, child=child, annotations=plan.annotations)
    if isinstance(plan, Project):
        child = map_plan(plan.child, on_scan=on_scan, on_filter=on_filter, on_project=on_project, on_aggregate=on_aggregate, on_sort=on_sort, on_limit=on_limit)
        if on_project:
            return on_project(plan)
        return Project(items=plan.items, child=child, annotations=plan.annotations)
    if isinstance(plan, Aggregate):
        child = map_plan(plan.child, on_scan=on_scan, on_filter=on_filter, on_project=on_project, on_aggregate=on_aggregate, on_sort=on_sort, on_limit=on_limit)
        if on_aggregate:
            return on_aggregate(plan)
        return Aggregate(group_keys=plan.group_keys, aggregates=plan.aggregates, child=child, annotations=plan.annotations)
    if isinstance(plan, Filter):
        child = map_plan(plan.child, on_scan=on_scan, on_filter=on_filter, on_project=on_project, on_aggregate=on_aggregate, on_sort=on_sort, on_limit=on_limit)
        if on_filter:
            return on_filter(plan)
        return Filter(predicate=plan.predicate, child=child, annotations=plan.annotations)
    if isinstance(plan, Scan):
        if on_scan:
            return on_scan(plan)
        return plan
    return plan
