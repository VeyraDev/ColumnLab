$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VenvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $Python = $VenvPython
    $PyArgs = @()
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
    $PyArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
    $PyArgs = @()
} else {
    throw "未找到 Python。请安装 Python 3.11+，或在 backend 目录执行: python -m venv .venv"
}

if (-not $PyArgs) { $PyArgs = @() }

Write-Host "生成 ColumnLab PPT 剩余三张性能图..." -ForegroundColor Cyan
& $Python @PyArgs (Join-Path $Root "scripts\run_ppt_remaining_benchmarks.py") @args

if ($LASTEXITCODE -ne 0) {
    throw "Benchmark 运行失败，退出码：$LASTEXITCODE"
}

Write-Host "`n完成。结果位于 benchmark_output\ppt_remaining" -ForegroundColor Green
