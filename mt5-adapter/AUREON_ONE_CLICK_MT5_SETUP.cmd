@echo off
setlocal EnableExtensions
title AUREON OMEGA - MT5 Adapter Bootstrap
set "ROOT=C:\Users\jerry\OneDrive\Desktop\AUREON - AI TRADING"
set "BRANCH=feature/mt5-broker-intelligence-adapter"
set "BASE=https://raw.githubusercontent.com/jerryllee421-lab/aureon-omega/%BRANCH%/mt5-adapter"
echo.
echo ==============================================================
echo  AUREON OMEGA - MT5 BROKER INTELLIGENCE / TESTER SETUP
echo ==============================================================
echo Root: "%ROOT%"
echo No trades will be submitted during setup.
echo Live trading remains disabled by default.
echo.
if not exist "%ROOT%" mkdir "%ROOT%"
if errorlevel 1 goto :fail
for %%D in (config logs reports data data\broker data\market runtime scripts research evidence backups mt5-adapter) do (
  if not exist "%ROOT%\%%D" mkdir "%ROOT%\%%D"
)
set "SRC=%ROOT%\runtime\mt5-adapter-source"
if not exist "%SRC%" mkdir "%SRC%"
echo [1/5] Downloading versioned adapter files...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $b='%BASE%'; $d='%SRC%'; $files=@('adapter.py','requirements.txt','README.md','AUREON_MT5_CONTROL_CENTER.cmd','config\mt5_adapter.json'); foreach($f in $files){$p=Join-Path $d $f; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; Invoke-WebRequest -UseBasicParsing -Uri ($b+'/'+$f.Replace('\','/')) -OutFile $p}; Write-Host 'Source files downloaded.'"
if errorlevel 1 goto :fail
echo [2/5] Locating Python...
where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3 was not found. Install Python 3.11 or 3.12 from python.org, enable PATH, then rerun.
    goto :fail
  )
  set "PY=python"
)
echo [3/5] Creating project-local virtual environment...
if not exist "%ROOT%\.venv\Scripts\python.exe" (
  %PY% -m venv "%ROOT%\.venv"
  if errorlevel 1 goto :fail
)
echo [4/5] Installing adapter dependency...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto :fail
"%ROOT%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%SRC%\requirements.txt"
if errorlevel 1 goto :fail
echo [5/5] Installing versioned adapter and config into project root...
if exist "%ROOT%\scripts\mt5_adapter.py" copy /Y "%ROOT%\scripts\mt5_adapter.py" "%ROOT%\backups\mt5_adapter_%RANDOM%.py.bak" >nul
if exist "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" copy /Y "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\backups\mt5_control_center_%RANDOM%.cmd.bak" >nul
copy /Y "%SRC%\adapter.py" "%ROOT%\scripts\mt5_adapter.py" >nul
if errorlevel 1 goto :fail
copy /Y "%SRC%\README.md" "%ROOT%\mt5-adapter\README.md" >nul
if errorlevel 1 goto :fail
copy /Y "%SRC%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" >nul
if errorlevel 1 goto :fail
if not exist "%ROOT%\config\mt5_adapter.json" (
  copy /Y "%SRC%\config\mt5_adapter.json" "%ROOT%\config\mt5_adapter.json" >nul
  if errorlevel 1 goto :fail
) else (
  echo Existing config preserved: "%ROOT%\config\mt5_adapter.json"
)
echo.
echo Running non-trading diagnostics...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\mt5_adapter.py" doctor --json
echo.
echo SETUP COMPLETE. Review the report above and "%ROOT%\reports".
echo To inspect broker state: run "%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\mt5_adapter.py" status
echo No order is sent by setup. Live order sending is disabled by default.
pause
exit /b 0
:fail
echo.
echo SETUP BLOCKED. No trades were submitted. Review the error above.
echo Check network access, Python installation, and write permissions.
pause
exit /b 1
