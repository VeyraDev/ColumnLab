@echo off
setlocal

set "ROOT=%~dp0.."
set "VENV_PY=%ROOT%\backend\.venv\Scripts\python.exe"

if exist "%VENV_PY%" (
  set "PYTHON=%VENV_PY%"
) else (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON=python"
  ) else (
    where py >nul 2>nul
    if not errorlevel 1 (
      set "PYTHON=py"
    ) else (
      echo 未找到 Python。请先创建 backend\.venv 或安装 Python。
      exit /b 1
    )
  )
)

echo 运行 ColumnLab PPT 图1正式 Codec 实验...
"%PYTHON%" "%ROOT%\scripts\run_ppt_codec_benchmark.py" %*
if errorlevel 1 (
  echo Benchmark 运行失败。
  exit /b 1
)

echo.
echo 完成。结果位于 benchmark_output\ppt_figure_1
endlocal
