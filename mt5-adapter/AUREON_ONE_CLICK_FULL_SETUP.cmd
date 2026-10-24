@echo off
setlocal EnableExtensions
title AUREON OMEGA - FULL MT5 + OLLAMA SETUP
set "ROOT=C:\Users\jerry\OneDrive\Desktop\AUREON - AI TRADING"
set "BRANCH=feature/mt5-broker-intelligence-adapter"
set "BASE=https://raw.githubusercontent.com/jerryllee421-lab/aureon-omega/%BRANCH%/mt5-adapter"
echo.
echo ==============================================================
echo  AUREON OMEGA - FULL MT5 + OLLAMA ONE-CLICK SETUP
echo ==============================================================
echo Root: "%ROOT%"
echo Ollama AI is local research-only. No trades are sent.
echo Live and demo order sending remain disabled by default.
echo This setup will download qwen2.5:3b if it is not already installed.
echo The model download may be about 2 GB and requires internet access.
echo.
if not exist "%ROOT%" mkdir "%ROOT%"
if errorlevel 1 goto fail
for %%D in (config logs reports data data\broker data\market runtime scripts research research\ollama evidence backups mt5-adapter) do if not exist "%ROOT%\%%D" mkdir "%ROOT%\%%D"
set "SRC=%ROOT%\runtime\full-setup-source"
if not exist "%SRC%" mkdir "%SRC%"
echo [1/8] Downloading AUREON adapter and Ollama integration...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $b='%BASE%'; $d='%SRC%'; $files=@('adapter.py','requirements.txt','README.md','AUREON_MT5_CONTROL_CENTER.cmd','config\mt5_adapter.json','ollama_intelligence.py','AUREON_OLLAMA_CONTROL_CENTER.cmd','config\ollama_config.json','OLLAMA_RESEARCH_GUIDE.md'); foreach($f in $files){$p=Join-Path $d $f; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; Invoke-WebRequest -UseBasicParsing -Uri ($b+'/'+$f.Replace('\','/')) -OutFile $p}; Write-Host 'Download complete.'"
if errorlevel 1 goto fail
echo [2/8] Locating a valid Python installation...
set "PYEXE="
for /f "usebackq delims=" %%P in (`powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $c=@(); $c+=Get-Command python.exe -All | ForEach-Object { $_.Source }; $c+=Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python*\python.exe'),(Join-Path $env:ProgramFiles 'Python*\python.exe'),(Join-Path ${env:ProgramFiles(x86)} 'Python*\python.exe') -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }; foreach($p in ($c | Select-Object -Unique)){ if($p -and (Test-Path -LiteralPath $p)){ try { $v=& $p -c 'import sys; print("%d.%d" %% (sys.version_info.major,sys.version_info.minor))' 2>$null; if($LASTEXITCODE -eq 0 -and $v -match '^(3)\.(1[1-9]|[2-9][0-9])
echo [4/8] Installing MT5 adapter requirements...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%SRC%\requirements.txt"
if errorlevel 1 goto fail
echo [5/8] Installing scripts and preserving existing configuration...
for %%F in (mt5_adapter.py ollama_intelligence.py) do if exist "%ROOT%\scripts\%%F" copy /Y "%ROOT%\scripts\%%F" "%ROOT%\backups\%%F_%RANDOM%.bak" >nul
if exist "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" copy /Y "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\backups\mt5_center_%RANDOM%.bak" >nul
if exist "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd" copy /Y "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd" "%ROOT%\backups\ollama_center_%RANDOM%.bak" >nul
copy /Y "%SRC%\adapter.py" "%ROOT%\scripts\mt5_adapter.py" >nul
if errorlevel 1 goto fail
copy /Y "%SRC%\ollama_intelligence.py" "%ROOT%\scripts\ollama_intelligence.py" >nul
if errorlevel 1 goto fail
copy /Y "%SRC%\README.md" "%ROOT%\mt5-adapter\README.md" >nul
copy /Y "%SRC%\OLLAMA_RESEARCH_GUIDE.md" "%ROOT%\mt5-adapter\OLLAMA_RESEARCH_GUIDE.md" >nul
copy /Y "%SRC%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" >nul
copy /Y "%SRC%\AUREON_OLLAMA_CONTROL_CENTER.cmd" "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd" >nul
if not exist "%ROOT%\config\mt5_adapter.json" copy /Y "%SRC%\config\mt5_adapter.json" "%ROOT%\config\mt5_adapter.json" >nul
if not exist "%ROOT%\config\ollama_config.json" copy /Y "%SRC%\config\ollama_config.json" "%ROOT%\config\ollama_config.json" >nul
echo [6/8] Verifying Ollama CLI and local API...
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama CLI is not on PATH. Start Ollama from the Windows Start menu and rerun.
  echo This installer does not reinstall an existing Ollama installation.
  goto fail
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo Starting Ollama server in a separate minimized window...
  start "AUREON Ollama Server" /min cmd /c "ollama serve"
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 20;$i++){try{Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null; $ok=$true; break}catch{Start-Sleep -Seconds 2}}; if($ok){exit 0}else{exit 1}"
  if errorlevel 1 (
    echo Ollama API did not become available. Start Ollama manually and rerun.
    goto fail
  )
)
echo [7/8] Checking compact local model...
ollama list | findstr /I "qwen2.5:3b" >nul
if errorlevel 1 (
  echo Downloading qwen2.5:3b. This is a one-time model download...
  ollama pull qwen2.5:3b
  if errorlevel 1 goto fail
) else (
  echo qwen2.5:3b already installed.
)
echo [8/8] Running syntax checks and non-trading health checks...
"%ROOT%\.venv\Scripts\python.exe" -m py_compile "%ROOT%\scripts\mt5_adapter.py" "%ROOT%\scripts\ollama_intelligence.py"
if errorlevel 1 goto fail
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\ollama_intelligence.py" doctor
if errorlevel 1 goto fail
echo Running a structured-output smoke test (synthetic input only)...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\ollama_intelligence.py" smoke
if errorlevel 1 goto fail
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\mt5_adapter.py" doctor --json
echo.
echo ==============================================================
echo SETUP FINISHED. Review reports before any further action.
echo MT5 report: "%ROOT%\reports\mt5_doctor.json"
echo Ollama report: "%ROOT%\reports\ollama_doctor.json"
echo Control centers:
echo   "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd"
echo   "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd"
echo No order was sent. Live and demo order sending remain disabled.
echo ==============================================================
pause
exit /b 0
:fail
echo.
echo SETUP BLOCKED OR INCOMPLETE. No orders were sent.
echo Correct the reported issue and rerun this setup CMD.
pause
exit /b 1
){ Write-Output $p; exit 0 } } catch {} } }; exit 1"` ) do if not defined PYEXE set "PYEXE=%%P"
if not defined PYEXE (
  echo No working Python 3.11+ installation was found.
  where winget >nul 2>nul
  if errorlevel 1 goto fail
  echo Installing Python 3.12 for the current Windows user...
  winget install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto fail
  echo Python installed. Rerun this setup CMD in a new window.
  goto fail
)
echo Using Python: "%PYEXE%"
"%PYEXE%" --version
if errorlevel 1 goto fail
echo [3/8] Creating project-local Python environment...
if not exist "%ROOT%\.venv\Scripts\python.exe" (
  "%PYEXE%" -m venv "%ROOT%\.venv"
  if errorlevel 1 goto fail
)
echo [4/8] Installing MT5 adapter requirements...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%SRC%\requirements.txt"
if errorlevel 1 goto fail
echo [5/8] Installing scripts and preserving existing configuration...
for %%F in (mt5_adapter.py ollama_intelligence.py) do if exist "%ROOT%\scripts\%%F" copy /Y "%ROOT%\scripts\%%F" "%ROOT%\backups\%%F_%RANDOM%.bak" >nul
if exist "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" copy /Y "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\backups\mt5_center_%RANDOM%.bak" >nul
if exist "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd" copy /Y "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd" "%ROOT%\backups\ollama_center_%RANDOM%.bak" >nul
copy /Y "%SRC%\adapter.py" "%ROOT%\scripts\mt5_adapter.py" >nul
if errorlevel 1 goto fail
copy /Y "%SRC%\ollama_intelligence.py" "%ROOT%\scripts\ollama_intelligence.py" >nul
if errorlevel 1 goto fail
copy /Y "%SRC%\README.md" "%ROOT%\mt5-adapter\README.md" >nul
copy /Y "%SRC%\OLLAMA_RESEARCH_GUIDE.md" "%ROOT%\mt5-adapter\OLLAMA_RESEARCH_GUIDE.md" >nul
copy /Y "%SRC%\AUREON_MT5_CONTROL_CENTER.cmd" "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd" >nul
copy /Y "%SRC%\AUREON_OLLAMA_CONTROL_CENTER.cmd" "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd" >nul
if not exist "%ROOT%\config\mt5_adapter.json" copy /Y "%SRC%\config\mt5_adapter.json" "%ROOT%\config\mt5_adapter.json" >nul
if not exist "%ROOT%\config\ollama_config.json" copy /Y "%SRC%\config\ollama_config.json" "%ROOT%\config\ollama_config.json" >nul
echo [6/8] Verifying Ollama CLI and local API...
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama CLI is not on PATH. Start Ollama from the Windows Start menu and rerun.
  echo This installer does not reinstall an existing Ollama installation.
  goto fail
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo Starting Ollama server in a separate minimized window...
  start "AUREON Ollama Server" /min cmd /c "ollama serve"
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 20;$i++){try{Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2 | Out-Null; $ok=$true; break}catch{Start-Sleep -Seconds 2}}; if($ok){exit 0}else{exit 1}"
  if errorlevel 1 (
    echo Ollama API did not become available. Start Ollama manually and rerun.
    goto fail
  )
)
echo [7/8] Checking compact local model...
ollama list | findstr /I "qwen2.5:3b" >nul
if errorlevel 1 (
  echo Downloading qwen2.5:3b. This is a one-time model download...
  ollama pull qwen2.5:3b
  if errorlevel 1 goto fail
) else (
  echo qwen2.5:3b already installed.
)
echo [8/8] Running syntax checks and non-trading health checks...
"%ROOT%\.venv\Scripts\python.exe" -m py_compile "%ROOT%\scripts\mt5_adapter.py" "%ROOT%\scripts\ollama_intelligence.py"
if errorlevel 1 goto fail
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\ollama_intelligence.py" doctor
if errorlevel 1 goto fail
echo Running a structured-output smoke test (synthetic input only)...
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\ollama_intelligence.py" smoke
if errorlevel 1 goto fail
"%ROOT%\.venv\Scripts\python.exe" "%ROOT%\scripts\mt5_adapter.py" doctor --json
echo.
echo ==============================================================
echo SETUP FINISHED. Review reports before any further action.
echo MT5 report: "%ROOT%\reports\mt5_doctor.json"
echo Ollama report: "%ROOT%\reports\ollama_doctor.json"
echo Control centers:
echo   "%ROOT%\AUREON_MT5_CONTROL_CENTER.cmd"
echo   "%ROOT%\AUREON_OLLAMA_CONTROL_CENTER.cmd"
echo No order was sent. Live and demo order sending remain disabled.
echo ==============================================================
pause
exit /b 0
:fail
echo.
echo SETUP BLOCKED OR INCOMPLETE. No orders were sent.
echo Correct the reported issue and rerun this setup CMD.
pause
exit /b 1
