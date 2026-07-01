$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Python = $VenvPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
} else {
    throw "未找到 Python。请先创建 backend/.venv 或安装 Python。"
}

Write-Host "运行 ColumnLab PPT 图1正式 Codec 实验..." -ForegroundColor Cyan
& $Python (Join-Path $Root "scripts\run_ppt_codec_benchmark.py") @args

if ($LASTEXITCODE -ne 0) {
    throw "Benchmark 运行失败，退出码：$LASTEXITCODE"
}

Write-Host "`n完成。结果位于 benchmark_output\ppt_figure_1" -ForegroundColor Green
