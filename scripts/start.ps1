#!/usr/bin/env pwsh
# ColumnLab one-click start (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> ColumnLab start (migrate + backend + frontend)"

Push-Location (Join-Path $Root "backend")
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic migration failed" }

Start-Process pwsh -ArgumentList "-NoExit", "-Command", "Set-Location '$Root/backend'; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Pop-Location

Push-Location (Join-Path $Root "frontend")
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "Set-Location '$Root/frontend'; npm run dev"
Pop-Location

Write-Host "Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:5173"
Write-Host "See docs/DEMO_SCRIPT.md for demo flow."
