from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

_op_counter = itertools.count(1)


def new_operator_id(prefix: str) -> str:
    return f"{prefix}_{next(_op_counter)}"


@dataclass(frozen=True, slots=True)
class BlockScan:
    operator_id: str
    column: str
    column_id: int
    block_ids: tuple[int, ...]
    file_path: str
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "type": "BlockScan",
            "operator_id": self.operator_id,
            "column": self.column,
            "column_id": self.column_id,
            "block_ids": list(self.block_ids),
            "file_path": self.file_path,
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class RawFilter:
    operator_id: str
    column: str
    predicate: dict[str, Any]
    child: BlockScan
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "RawFilter",
            "operator_id": self.operator_id,
            "column": self.column,
            "predicate": self.predicate,
            "child": self.child.to_dict(),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class RleFilter:
    operator_id: str
    column: str
    predicate: dict[str, Any]
    child: BlockScan
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "RleFilter",
            "operator_id": self.operator_id,
            "column": self.column,
            "predicate": self.predicate,
            "child": self.child.to_dict(),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class DictionaryFilter:
    operator_id: str
    column: str
    predicate: dict[str, Any]
    child: BlockScan
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "DictionaryFilter",
            "operator_id": self.operator_id,
            "column": self.column,
            "predicate": self.predicate,
            "child": self.child.to_dict(),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class BitmapAnd:
    operator_id: str
    children: tuple[Any, ...]
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "BitmapAnd",
            "operator_id": self.operator_id,
            "children": [_physical_dict(c) for c in self.children],
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class BitmapOr:
    operator_id: str
    children: tuple[Any, ...]
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "BitmapOr",
            "operator_id": self.operator_id,
            "children": [_physical_dict(c) for c in self.children],
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Materialize:
    operator_id: str
    columns: tuple[str, ...]
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "Materialize",
            "operator_id": self.operator_id,
            "columns": list(self.columns),
            "child": _physical_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class HashAggregate:
    operator_id: str
    group_keys: tuple[str, ...]
    aggregates: tuple[dict[str, Any], ...]
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "HashAggregate",
            "operator_id": self.operator_id,
            "group_keys": list(self.group_keys),
            "aggregates": list(self.aggregates),
            "child": _physical_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Sort:
    operator_id: str
    keys: tuple[dict[str, Any], ...]
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "Sort",
            "operator_id": self.operator_id,
            "keys": list(self.keys),
            "child": _physical_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


@dataclass(frozen=True, slots=True)
class Limit:
    operator_id: str
    limit: int
    offset: int
    child: Any
    annotations: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out = {
            "type": "Limit",
            "operator_id": self.operator_id,
            "limit": self.limit,
            "offset": self.offset,
            "child": _physical_dict(self.child),
        }
        if self.annotations:
            out["annotations"] = dict(self.annotations)
        return out


PhysicalNode = BlockScan | RawFilter | RleFilter | DictionaryFilter | BitmapAnd | BitmapOr | Materialize | HashAggregate | Sort | Limit


def physical_to_dict(node: PhysicalNode) -> dict[str, Any]:
    return _physical_dict(node)


def _physical_dict(node: Any) -> dict[str, Any]:
    if hasattr(node, "to_dict"):
        return node.to_dict()
    raise TypeError(f"unsupported physical node: {type(node)!r}")
