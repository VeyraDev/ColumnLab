from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class QueryError(Exception):
    message: str
    line: int | None = None
    col: int | None = None
    code: str = "query_error"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "col": self.col,
        }


@dataclass(slots=True)
class ParseError(QueryError):
    code: str = field(default="parse_error", init=False)


@dataclass(slots=True)
class UnsupportedSyntaxError(QueryError):
    code: str = field(default="unsupported_syntax", init=False)


@dataclass(slots=True)
class UnknownColumnError(QueryError):
    code: str = field(default="unknown_column", init=False)


@dataclass(slots=True)
class UnknownTableError(QueryError):
    code: str = field(default="unknown_table", init=False)


@dataclass(slots=True)
class TypeMismatchError(QueryError):
    code: str = field(default="type_mismatch", init=False)
