from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheKey:
    version_id: int
    column_id: int
    block_id: int
    representation: str


@dataclass(slots=True)
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    bytes_used: int = 0


class BlockCache:
    def __init__(self, *, max_bytes: int = 64 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes
        self._data: OrderedDict[CacheKey, tuple[Any, int]] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = CacheStats()
        self._version_id: int | None = None

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def set_version(self, version_id: int) -> None:
        with self._lock:
            if self._version_id != version_id:
                self._data.clear()
                self._stats.bytes_used = 0
                self._version_id = version_id

    def invalidate_all(self) -> None:
        with self._lock:
            self._data.clear()
            self._stats.bytes_used = 0

    def get(self, key: CacheKey) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            self._data.move_to_end(key)
            self._stats.hits += 1
            return entry[0]

    def put(self, key: CacheKey, value: Any, byte_size: int) -> None:
        with self._lock:
            if key in self._data:
                _, old_size = self._data.pop(key)
                self._stats.bytes_used -= old_size
            while self._data and self._stats.bytes_used + byte_size > self._max_bytes:
                _, (_, evicted_size) = self._data.popitem(last=False)
                self._stats.bytes_used -= evicted_size
                self._stats.evictions += 1
            self._data[key] = (value, byte_size)
            self._stats.bytes_used += byte_size


_global_cache: BlockCache | None = None
_global_lock = threading.Lock()


def get_block_cache() -> BlockCache:
    global _global_cache
    with _global_lock:
        if _global_cache is None:
            _global_cache = BlockCache()
        return _global_cache
