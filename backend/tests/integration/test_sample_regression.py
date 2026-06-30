"""Regression tests driven by samples/expected_results.json (TEST_GUIDE.md)."""

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
FIXTURE = SAMPLES / "expected_results.json"
FIXTURE_DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "sample_user", "email": "sample@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "sample_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wait_job(client, headers, job_id: int, timeout: float = 180.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/import-jobs/{job_id}", headers=headers)
        body = resp.json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("import job did not finish")


def _wait_query(client, headers, query_id: int, timeout: float = 120.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/queries/{query_id}", headers=headers)
        body = resp.json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.2)
    raise TimeoutError("query did not finish")


def _type_override(name: str, spec: str) -> dict:
    m = re.match(r"DECIMAL64\(scale=(\d+)\)", spec, re.IGNORECASE)
    if m:
        return {"name": name, "logical_type": "DECIMAL64", "scale": int(m.group(1))}
    return {"name": name, "logical_type": spec}


def _schema_overrides(meta: dict) -> list[dict]:
    raw = meta.get("schema_override")
    if not raw:
        return []
    return [_type_override(name, spec) for name, spec in raw.items()]


def _import_dataset(
    client,
    headers,
    filename: str,
    meta: dict,
    *,
    import_mode: str = "strict",
) -> dict:
    path = SAMPLES / filename
    if not path.exists():
        pytest.skip(f"missing sample file: {filename}")
    block_bytes = str(meta.get("recommended_block_bytes", 65536))
    overrides = json.dumps(_schema_overrides(meta))
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if path.suffix == ".xlsx" else "text/csv"
    with path.open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": (filename, fh, mime)},
            data={
                "table_name": "data",
                "import_mode": import_mode,
                "target_block_bytes": block_bytes,
                "schema_overrides": overrides,
            },
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    timeout = 900.0 if meta.get("rows", 0) > 50000 else 180.0
    job = _wait_job(client, headers, data["job_id"], timeout=timeout)
    assert job["status"] == "completed", job
    tables = client.get(f"/api/datasets/{data['dataset_id']}/tables", headers=headers).json()["data"]
    return data["dataset_id"], tables[0]["id"]


def _run_query(client, headers, dataset_id: int, table_id: int, sql: str) -> list[list]:
    resp = client.post(
        "/api/queries",
        headers=headers,
        json={"dataset_id": dataset_id, "table_id": table_id, "sql": sql},
    )
    assert resp.status_code == 200, resp.text
    query_id = resp.json()["data"]["query_id"]
    status = _wait_query(client, headers, query_id)
    assert status["status"] == "completed", status
    result = client.get(f"/api/queries/{query_id}/result", headers=headers).json()["data"]
    return result["rows"]


def _rows_match(actual: list[list], expected: list[list], *, tol: float = 1e-6) -> bool:
    if len(actual) != len(expected):
        return False
    for a_row, e_row in zip(actual, expected, strict=True):
        if len(a_row) != len(e_row):
            return False
        for a, e in zip(a_row, e_row, strict=True):
            if isinstance(e, float) and isinstance(a, (int, float)):
                if not math.isclose(float(a), e, rel_tol=tol, abs_tol=tol):
                    return False
            elif a != e:
                return False
    return True


def test_06b_strict_and_coerce(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    meta = next(d for d in FIXTURE_DATA["datasets"] if d["file"] == "06b_invalid_strict_coerce.csv")
    path = SAMPLES / meta["file"]
    overrides = json.dumps(_schema_overrides(meta))
    block_bytes = str(meta.get("recommended_block_bytes", 4096))

    with path.open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": (meta["file"], fh, "text/csv")},
            data={
                "table_name": "data",
                "import_mode": "strict",
                "target_block_bytes": block_bytes,
                "schema_overrides": overrides,
            },
        )
    assert resp.status_code == 200
    strict_job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert strict_job["status"] == "failed"

    with path.open("rb") as fh:
        resp = client.post(
            "/api/datasets/uploads",
            headers=headers,
            files={"file": (meta["file"], fh, "text/csv")},
            data={
                "table_name": "data",
                "import_mode": "coerce",
                "target_block_bytes": block_bytes,
                "schema_overrides": overrides,
            },
        )
    assert resp.status_code == 200
    coerce_job = _wait_job(client, headers, resp.json()["data"]["job_id"])
    assert coerce_job["status"] == "completed"
    assert coerce_job["error_count"] == meta["expected"]["coerce_error_count"]


FAST_DATASETS = {
    "01_rle_runs.csv",
    "02_dictionary_low_cardinality.csv",
    "03_raw_high_cardinality.csv",
    "04_pruning_multicolumn.csv",
    "05_mixed_aggregate_dictionary.csv",
    "06_types_nulls_unicode.csv",
}


def _import_all(client, headers, *, filenames: set[str]) -> dict[str, tuple[int, int]]:
    meta_by_file = {d["file"]: d for d in FIXTURE_DATA["datasets"]}
    imported: dict[str, tuple[int, int]] = {}
    for filename in filenames:
        meta = meta_by_file[filename]
        try:
            imported[filename] = _import_dataset(client, headers, filename, meta)
        except TimeoutError as exc:
            pytest.fail(f"import timed out for {filename}: {exc}")
    return imported


def _run_expected_queries(client, headers, imported: dict[str, tuple[int, int]], *, datasets: set[str] | None = None) -> None:
    failures: list[str] = []
    for case in FIXTURE_DATA["queries"]:
        dataset_file = case["dataset"]
        if datasets is not None and dataset_file not in datasets:
            continue
        if dataset_file not in imported:
            continue
        label = case.get("name") or case["sql"]
        dataset_id, table_id = imported[dataset_file]
        try:
            rows = _run_query(client, headers, dataset_id, table_id, case["sql"])
            if not _rows_match(rows, case["expected_rows"]):
                failures.append(
                    f"[{dataset_file}] {label}\n"
                    f"  SQL: {case['sql']}\n"
                    f"  expected: {case['expected_rows']}\n"
                    f"  actual:   {rows}"
                )
        except AssertionError as exc:
            failures.append(f"[{dataset_file}] {label}\n  SQL: {case['sql']}\n  {exc}")
    if failures:
        pytest.fail("\n\n".join(failures))


def test_expected_results_queries_fast(client, tmp_path, monkeypatch):
    """TEST_GUIDE 快速回归：01～06 导入 + expected_results 查询."""
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    imported = _import_all(client, headers, filenames=FAST_DATASETS)
    _run_expected_queries(client, headers, imported, datasets=FAST_DATASETS)


@pytest.mark.slow
def test_expected_results_queries_07(client, tmp_path, monkeypatch):
    """TEST_GUIDE 综合数据：07_realistic_orders_100k（较慢）."""
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)
    imported = _import_all(client, headers, filenames={"07_realistic_orders_100k.csv"})
    _run_expected_queries(client, headers, imported, datasets={"07_realistic_orders_100k.csv"})
