from __future__ import annotations

from app.engine.benchmark.stats import summarize, summarize_by_metric


def test_summarize_basic():
    stats = summarize([1.0, 2.0, 3.0, 4.0, 100.0])
    assert stats["count"] == 5
    assert stats["mean"] == 22.0
    assert stats["median"] == 3.0
    assert stats["p95"] == 100.0
    assert stats["min"] == 1.0
    assert stats["max"] == 100.0


def test_summarize_empty():
    stats = summarize([])
    assert stats["count"] == 0
    assert stats["mean"] == 0.0


def test_summarize_by_metric():
    rows = [("a", 1.0), ("a", 3.0), ("b", 10.0)]
    grouped = summarize_by_metric(rows)
    assert grouped["a"]["mean"] == 2.0
    assert grouped["b"]["mean"] == 10.0
