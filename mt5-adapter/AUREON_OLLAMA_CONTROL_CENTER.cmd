@echo off
setlocal EnableExtensions
title AUREON OMEGA - Ollama Intelligence
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set "AI=%ROOT%scripts\ollama_intelligence.py"
if not exist "%PY%" (
  echo Project Python environment missing. Run AUREON_ONE_CLICK_FULL_SETUP.cmd first.
  pause
  exit /b 1
)
if not exist "%AI%" (
  echo Ollama analyst missing. Run AUREON_ONE_CLICK_FULL_SETUP.cmd first.
  pause
  exit /b 1
)
:menu
cls
echo ==============================================================
echo  AUREON OMEGA - LOCAL OLLAMA INTELLIGENCE
echo ==============================================================
echo Research-only. It cannot place orders or authorize trading.
echo.
echo  1. Check Ollama API and model
echo  2. Analyse MT5 doctor report
echo  3. Analyse broker intelligence report
echo  4. Analyse latest quote report
echo  5. Analyse another JSON report
echo  6. Open latest AI report folder
echo  7. Exit
echo.
set /p "C=Select: "
if "%C%"=="1" goto doctor
if "%C%"=="2" set "FILE=%ROOT%reports\mt5_doctor.json"&goto analyse
if "%C%"=="3" set "FILE=%ROOT%reports\broker_intelligence.json"&goto analyse
if "%C%"=="4" set "FILE=%ROOT%reports\latest_quote.json"&goto analyse
if "%C%"=="5" goto custom
if "%C%"=="6" start "" explorer "%ROOT%reports"&goto menu
if "%C%"=="7" exit /b 0
goto menu
:doctor
"%PY%" "%AI%" doctor
pause
goto menu
:analyse
if not exist "%FILE%" (
  echo Evidence file not found: "%FILE%"
  echo Run MT5 Control Center first to create the report.
  pause
  goto menu
)
"%PY%" "%AI%" analyze --input "%FILE%"
pause
goto menu
:custom
set /p "FILE=Full path to an existing JSON report: "
if not exist "%FILE%" echo File not found.&pause&goto menu
"%PY%" "%AI%" analyze --input "%FILE%"
pause
goto menu
