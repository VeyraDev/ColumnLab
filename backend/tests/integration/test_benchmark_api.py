from __future__ import annotations

import time


def _auth_headers(client) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={"username": "bench_user", "email": "bench@example.com", "password": "secret12"},
    )
    if reg.status_code != 200:
        login = client.post("/api/auth/login", json={"username": "bench_user", "password": "secret12"})
        token = login.json()["data"]["access_token"]
    else:
        token = reg.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _wait_benchmark(client, headers, run_id: int, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/benchmarks/{run_id}", headers=headers)
        body = resp.json()["data"]
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body
        time.sleep(0.3)
    raise TimeoutError("benchmark did not finish")


def test_benchmark_submit_samples_summary(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    headers = _auth_headers(client)

    start = time.perf_counter()
    resp = client.post(
        "/api/benchmarks",
        headers=headers,
        json={
            "kind": "codec",
            "seed": 7,
            "warmup_runs": 0,
            "repeat_runs": 2,
            "distribution": "run_length",
            "row_count": 1024,
        },
    )
    assert resp.status_code == 200
    run_id = resp.json()["data"]["id"]

    result = _wait_benchmark(client, headers, run_id)
    assert result["status"] == "completed"
    elapsed = time.perf_counter() - start
    assert elapsed < 30.0, "codec benchmark regression guard"

    summary = result["summary"]
    assert summary["seed"] == 7
    assert "metrics" in summary
    sample_metric = next(iter(summary["metrics"].values()))
    assert "mean" in sample_metric
    assert "p95" in sample_metric
    assert "stdev" in sample_metric
    assert result["env"] is not None
    assert "git_commit" in result["env"]

    samples_resp = client.get(f"/api/benchmarks/{run_id}/samples", headers=headers)
    assert samples_resp.status_code == 200
    samples = samples_resp.json()["data"]
    assert samples["total"] > 0

    csv_resp = client.get(f"/api/benchmarks/{run_id}/export.csv", headers=headers)
    assert csv_resp.status_code == 200
    assert "metric_name" in csv_resp.text

    json_resp = client.get(f"/api/benchmarks/{run_id}/export.json", headers=headers)
    assert json_resp.status_code == 200
    assert "summary" in json_resp.text
