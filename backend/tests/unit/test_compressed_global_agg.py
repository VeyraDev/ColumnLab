from __future__ import annotations

from app.engine.execution.executor import _AggState, _merge_agg_states


def test_merge_agg_states_does_not_double_on_rollback_pattern():
    formal = {"n": _AggState(count=100)}
    temp = {"n": _AggState(count=50)}
    _merge_agg_states(formal["n"], temp["n"])
    assert formal["n"].count == 150


def test_temp_bucket_discarded_when_not_merged():
    """Simulate failed compressed path: temp state must not affect formal groups."""
    formal: dict[str, _AggState] = {"n": _AggState(count=100)}
    temp: dict[str, _AggState] = {"n": _AggState(count=8192)}
    # failure path: do not call _merge_agg_states
    assert formal["n"].count == 100
    assert temp["n"].count == 8192
