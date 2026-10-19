@echo off
setlocal EnableExtensions
title AUREON Omega - Adaptive Research Lab
cd /d "%~dp0.."
set "AUREON_ROOT=%CD%"
set "DATA=%~1"
if not defined DATA set "DATA=research_data\XAUUSD\canonical\XAUUSD_M5.parquet"
set "OUT=research_results\adaptive_lab"
if not exist ".venv\Scripts\python.exe" (
  echo [AUREON] Creating isolated Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :error
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import pandas, pyarrow" >nul 2>nul
if errorlevel 1 (
  echo [AUREON] Installing minimal parquet research dependencies...
  "%PY%" -m pip install --disable-pip-version-check "pandas>=2.2,<3" "pyarrow>=19,<22"
  if errorlevel 1 goto :error
)
if not exist "%DATA%" (
  echo [AUREON] ERROR: Dataset not found:
  echo   %DATA%
  echo.
  echo Usage: scripts\run_adaptive_lab.cmd "C:\path\to\XAUUSD_M5.parquet"
  echo Default expected: research_data\XAUUSD\canonical\XAUUSD_M5.parquet
  exit /b 2
)
echo [AUREON] Running research-only adaptive walk-forward and cost stress.
echo [AUREON] Input: %DATA%
echo [AUREON] Output: %OUT%\adaptive_lab_report.json
"%PY%" research\evolution\run_adaptive_lab.py --data "%DATA%" --out "%OUT%" --side bid --horizon 5 --stride 60 --lookback 1500 --cost-bps 8 --cost-grid-bps 4,8,12,20
if errorlevel 1 goto :error
echo.
echo [AUREON] Research complete. No trades were submitted.
echo [AUREON] Review %OUT%\adaptive_lab_report.json before any further decision.
exit /b 0

:error
echo.
echo [AUREON] FAILED. Review the error above. No trades were submitted.
exit /b 1
