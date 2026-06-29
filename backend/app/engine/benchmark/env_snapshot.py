from __future__ import annotations

import csv
import io
import json
import platform
import subprocess
import sys
from typing import Any


def capture_env(*, engine_version: str = "0.1") -> dict[str, Any]:
    commit = "unknown"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            commit = result.stdout.strip() or commit
    except Exception:
        pass
    return {
        "engine_version": engine_version,
        "git_commit": commit,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_count": __import__("os").cpu_count() or 1,
        "machine": platform.machine(),
    }


def samples_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "iteration,phase,metric_name,value,extra_json\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["iteration", "phase", "metric_name", "value", "extra_json"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def summary_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2)
