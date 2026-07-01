#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT/backend/.venv/bin/python" ]]; then
  PYTHON="$ROOT/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "未找到 Python。请先创建 backend/.venv 或安装 Python。" >&2
  exit 1
fi

echo "运行 ColumnLab PPT 图1正式 Codec 实验..."
"$PYTHON" "$ROOT/scripts/run_ppt_codec_benchmark.py" "$@"
echo
echo "完成。结果位于 benchmark_output/ppt_figure_1"
