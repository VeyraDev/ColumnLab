from __future__ import annotations

from app.engine.execution.executor import _bitmap_and_with_na
from app.engine.vectors import SelectionVector


def test_bitmap_and_na_branch_is_all_false():
    left = SelectionVector.all_false(0)
    right = SelectionVector.all_true(128)
    result = _bitmap_and_with_na(left, right)
    assert result.length == 128
    assert result.selected_count() == 0


def test_bitmap_and_pruned_left_returns_false_not_right():
    """When amount branch is N/A (length 0) and region has rows, AND must be all false."""
    left = SelectionVector.all_false(0)
    right = SelectionVector.all_true(512)
    result = _bitmap_and_with_na(left, right)
    assert result.length == 512
    assert result.selected_count() == 0
