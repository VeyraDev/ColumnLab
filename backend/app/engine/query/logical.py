from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Scan:
    table: str
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": "Scan", "table": self.table}
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Filter:
    predicate: Any
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        from app.engine.query.expr import _expr_dict

        out = {
            "type": "Filter",
            "predicate": _expr_dict(self.predicate),
            "child": _plan_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Project:
    items: tuple[Any, ...]
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        from app.engine.query.expr import SelectItem

        out = {
            "type": "Project",
            "items": [item.to_dict() if isinstance(item, SelectItem) else item for item in self.items],
            "child": _plan_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Aggregate:
    group_keys: tuple[Any, ...]
    aggregates: tuple[Any, ...]
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        from app.engine.query.expr import _expr_dict

        out = {
            "type": "Aggregate",
            "group_keys": [_expr_dict(k) for k in self.group_keys],
            "aggregates": [_expr_dict(a) for a in self.aggregates],
            "child": _plan_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Sort:
    keys: tuple[Any, ...]
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        from app.engine.query.expr import OrderKey

        out = {
            "type": "Sort",
            "keys": [k.to_dict() if isinstance(k, OrderKey) else k for k in self.keys],
            "child": _plan_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Limit:
    limit: int
    offset: int
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "Limit",
            "limit": self.limit,
            "offset": self.offset,
            "child": _plan_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


def _plan_dict(node: Any) -> dict[str, Any]:
    if hasattr(node, "to_dict"):
        return node.to_dict()
    raise TypeError(f"unsupported plan node: {type(node)!r}")


def plan_to_dict(node: Any) -> dict[str, Any]:
    return _plan_dict(node)


def plan_from_dict(data: dict[str, Any]) -> Any:
    node_type = data.get("type")
    if node_type == "Scan":
        ann = data.get("annotations") or {}
        return Scan(table=data["table"], annotations=tuple(ann.items()))
    if node_type == "Filter":
        from app.engine.query.deserialize import expr_from_dict

        return Filter(
            predicate=expr_from_dict(data["predicate"]),
            child=plan_from_dict(data["child"]),
            annotations=_ann_tuple(data),
        )
    if node_type == "Project":
        from app.engine.query.deserialize import select_item_from_dict

        items = tuple(select_item_from_dict(i) for i in data.get("items", []))
        return Project(items=items, child=plan_from_dict(data["child"]), annotations=_ann_tuple(data))
    if node_type == "Aggregate":
        from app.engine.query.deserialize import expr_from_dict

        return Aggregate(
            group_keys=tuple(expr_from_dict(k) for k in data.get("group_keys", [])),
            aggregates=tuple(expr_from_dict(a) for a in data.get("aggregates", [])),
            child=plan_from_dict(data["child"]),
            annotations=_ann_tuple(data),
        )
    if node_type == "Sort":
        from app.engine.query.deserialize import order_key_from_dict

        return Sort(
            keys=tuple(order_key_from_dict(k) for k in data.get("keys", [])),
            child=plan_from_dict(data["child"]),
            annotations=_ann_tuple(data),
        )
    if node_type == "Limit":
        return Limit(
            limit=int(data["limit"]),
            offset=int(data.get("offset") or 0),
            child=plan_from_dict(data["child"]),
            annotations=_ann_tuple(data),
        )
    raise TypeError(f"unsupported plan type: {node_type!r}")


def _ann_tuple(data: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    ann = data.get("annotations") or {}
    return tuple(ann.items())
