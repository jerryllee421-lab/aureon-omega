@echo off
setlocal EnableExtensions
title AUREON OMEGA - MT5 SETUP (OLLAMA OPTIONAL)
set "ROOT=C:\Users\jerry\OneDrive\Desktop\AUREON - AI TRADING"
set "BRANCH=feature/mt5-broker-intelligence-adapter"
set "BASE=https://raw.githubusercontent.com/jerryllee421-lab/aureon-omega/%BRANCH%/mt5-adapter"
set "ENABLE_OLLAMA=0"
echo.
echo ==============================================================
echo  AUREON OMEGA - MT5 ADAPTER SETUP
echo ==============================================================
echo Root: "%ROOT%"
echo Ollama integration: SKIPPED by default. Can be enabled later.
echo Order sending: DISABLED. This setup sends no trades.
echo.
if not exist "%ROOT%" mkdir "%ROOT%"
if errorlevel 1 goto fail
for %%D in (config logs reports data data\broker data\market runtime scripts research research\ollama evidence backups mt5-adapter) do if not exist "%ROOT%\%%D" mkdir "%ROOT%\%%D"
set "SRC=%ROOT%\runtime\full-setup-source"
if not exist "%SRC%" mkdir "%SRC%"
echo [1/6] Downloading MT5 adapter files...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $b='%BASE%'; $d='%SRC%'; $files=@('adapter.py','requirements.txt','README.md','AUREON_MT5_CONTROL_CENTER.cmd','config\mt5_adapter.json'); foreach($f in $files){$p=Join-Path $d $f; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; Invoke-WebRequest -UseBasicParsing -Uri ($b+'/'+$f.Replace('\','/')) -OutFile $p}; Write-Host 'Download complete.'"
if errorlevel 1 goto fail
echo [2/6] Locating a working Python 3.11+ executable...
set "PYEXE="
for %%V in (314 313 312 311) do if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
for %%V in (314 313 312 311) do if not defined PYEXE if exist "%ProgramFiles%\Python%%V\python.exe" set "PYEXE=%ProgramFiles%\Python%%V\python.exe"
if not defined PYEXE (
  for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYEXE set "PYEXE=%%P"
)
if defined PYEXE (
  "%PYEXE%" -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
  if errorlevel 1 set "PYEXE="
)
if not defined PYEXE (
  echo No working Python 3.11+ installation was found.
  where winget >nul 2>nul
  if errorlevel 1 goto fail
  echo Installing Python 3.12 for the current Windows user...
  winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto fail
  echo Python installed. Close this window, open a new CMD, and rerun setup.
  goto fail
)
echo Using Python: "%PYEXE%"
"%PYEXE%" --version
if errorlevel 1 goto fail
echo [3/6] Creating project-local Python environment...
if not exist "%ROOT%\.venv\Scripts\python.exe" (
  "%PYEXE%" -m venv "%ROOT%\.venv"
  if errorlevel 1 goto fail
)
echo [4/6] Installing MT5 adapter requirements...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%SRC%\requirements.txt"
if errorlevel 1 goto fail
echo [5/6] Installing adapter files and preserving existing configuration...
if exist "%ROOT%\scripts\mt5_adapter.py" copy /Y "%ROOT%\scripts\mt5_adapter.py" "%ROOT%\backups\mt5_adapter_%RANDOM%.bak" >nul
if exist "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" copy /Y "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\backups\mt5_center_%RANDOM%.bak" >nul
copy /Y "%SRC%\adapter.py" "%ROOT%\scripts\mt5_adapter.py" >nul
if errorlevel 1 goto fail
copy /Y "%SRC%\README.md" "%ROOT%\mt5-adapter\README.md" >nul
copy /Y "%SRC%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" >nul
if errorlevel 1 goto fail
if not exist "%ROOT%\config\mt5_adapter.json" copy /Y "%SRC%\config\mt5_adapter.json" "%ROOT%\config\mt5_adapter.json" >nul
echo [6/6] Running Python syntax and non-trading adapter health checks...
"%ROOT%\.venv\Scripts\python.exe" -m py_compile "%ROOT%\scripts\mt5_adapter.py"
if errorlevel 1 goto fail
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\mt5_adapter.py" doctor
if errorlevel 1 echo WARNING: MT5 doctor reported a connection or terminal issue. Review the report below.
echo.
echo ==============================================================
echo MT5 ADAPTER SETUP STAGE FINISHED.
echo Ollama was skipped and is not required for this setup.
echo Review reports\mt5_doctor.json and the MT5 control center.
echo No order was sent. Order sending remains disabled.
echo ==============================================================
pause
exit /b 0
:fail
echo.
echo SETUP BLOCKED OR INCOMPLETE. No orders were sent.
echo Correct the reported issue and rerun this setup CMD.
pause
exit /b 1
