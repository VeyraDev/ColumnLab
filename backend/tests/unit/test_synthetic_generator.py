from __future__ import annotations

from app.engine.benchmark.synthetic import generate_dataset, generate_int_column


def test_synthetic_seed_reproducible():
    a = generate_int_column("uniform", 100, seed=99)
    b = generate_int_column("uniform", 100, seed=99)
    c = generate_int_column("uniform", 100, seed=100)
    assert a == b
    assert a != c


def test_run_length_has_long_runs():
    values = generate_int_column("run_length", 512, seed=7)
    max_run = 1
    run = 1
    for i in range(1, len(values)):
        if values[i] == values[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    assert max_run >= 8


def test_mixed_business_dataset_shape():
    ds = generate_dataset("mixed_business", 256, seed=1)
    assert len(ds["qty"]) == 256
    assert len(ds["region"]) == 256
