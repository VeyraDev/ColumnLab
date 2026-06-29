from app.engine.vectors import SelectionVector


def test_selection_and_or():
    a = SelectionVector.all_true(8)
    b = SelectionVector.all_false(8)
    b.bits = bytes([0b00001111] + [0] * (len(b.bits) - 1))
    merged = a.and_with(b)
    assert merged.selected_count() == 4
    c = SelectionVector.all_false(8)
    c.bits = bytes([0b11110000] + [0] * (len(c.bits) - 1))
    assert merged.or_with(c).selected_count() == 8


def test_selection_invert_and_indices():
    sel = SelectionVector.all_false(5)
    buf = bytearray(sel.bits)
    buf[0] = 0b00010100
    sel = SelectionVector(length=5, bits=bytes(buf))
    assert sel.to_indices() == (2, 4)
    assert sel.invert().selected_count() == 3
