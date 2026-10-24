@echo off
setlocal EnableExtensions
title AUREON MT5 Control Center
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set "ADAPTER=%ROOT%scripts\mt5_adapter.py"
if not exist "%PY%" (
  echo Project Python environment missing. Run AUREON_ONE_CLICK_MT5_SETUP.cmd first.
  pause
  exit /b 1
)
if not exist "%ADAPTER%" (
  echo MT5 adapter missing. Run AUREON_ONE_CLICK_MT5_SETUP.cmd first.
  pause
  exit /b 1
)
:menu
cls
echo ==============================================================
echo  AUREON OMEGA - MT5 CONTROL CENTER
echo ==============================================================
echo Root: %ROOT%
echo Live trading and order submission are disabled by default.
echo.
echo  1. Environment / MT5 diagnostic
echo  2. Broker and account intelligence
echo  3. Discover broker symbols
echo  4. Read latest quote
echo  5. Read positions and pending orders
echo  6. Generate Strategy Tester config (no launch)
echo  7. Generate and launch Strategy Tester
echo  8. Exit
echo.
set /p "CHOICE=Select: "
if "%CHOICE%"=="1" goto doctor
if "%CHOICE%"=="2" goto status
if "%CHOICE%"=="3" goto symbols
if "%CHOICE%"=="4" goto quote
if "%CHOICE%"=="5" goto positions
if "%CHOICE%"=="6" goto tester_config
if "%CHOICE%"=="7" goto tester_run
if "%CHOICE%"=="8" exit /b 0
goto menu

:doctor
"%PY%" "%ADAPTER%" doctor
pause
goto menu
:status
"%PY%" "%ADAPTER%" status
pause
goto menu
:symbols
set /p "FILTER=Filter (e.g. XAU or gold; blank for all): "
"%PY%" "%ADAPTER%" symbols --filter "%FILTER%"
pause
goto menu
:quote
set /p "SYMBOL=Exact broker symbol [XAUUSD]: "
if "%SYMBOL%"=="" set "SYMBOL=XAUUSD"
"%PY%" "%ADAPTER%" quote --symbol "%SYMBOL%"
pause
goto menu
:positions
"%PY%" "%ADAPTER%" positions
pause
goto menu
:tester_config
call :ask_tester
if errorlevel 1 goto menu
"%PY%" "%ADAPTER%" tester --expert "%EXPERT%" --symbol "%SYMBOL%" --period "%PERIOD%" --start "%START%" --end "%END%" --model real_ticks --deposit "%DEPOSIT%" --currency "%CURRENCY%" --leverage "%LEVERAGE%"
pause
goto menu
:tester_run
echo.
echo WARNING: This launches the MT5 Strategy Tester. It does not place a live order.
call :ask_tester
if errorlevel 1 goto menu
set /p "LAUNCH=Launch tester now? Type YES to confirm: "
if /I not "%LAUNCH%"=="YES" goto menu
"%PY%" "%ADAPTER%" tester --expert "%EXPERT%" --symbol "%SYMBOL%" --period "%PERIOD%" --start "%START%" --end "%END%" --model real_ticks --deposit "%DEPOSIT%" --currency "%CURRENCY%" --leverage "%LEVERAGE%" --run --confirm
pause
goto menu

:ask_tester
echo.
echo Use the exact EA name/path registered in MT5 Strategy Tester.
set /p "EXPERT=EA name/path: "
if "%EXPERT%"=="" exit /b 1
set /p "SYMBOL=Exact broker symbol [XAUUSD]: "
if "%SYMBOL%"=="" set "SYMBOL=XAUUSD"
set /p "PERIOD=Period [M1]: "
if "%PERIOD%"=="" set "PERIOD=M1"
set /p "START=Start date YYYY-MM-DD: "
set /p "END=End date YYYY-MM-DD: "
set /p "DEPOSIT=Tester deposit [10000]: "
if "%DEPOSIT%"=="" set "DEPOSIT=10000"
set /p "CURRENCY=Deposit currency [USD]: "
if "%CURRENCY%"=="" set "CURRENCY=USD"
set /p "LEVERAGE=Tester leverage [1:100]: "
if "%LEVERAGE%"=="" set "LEVERAGE=1:100"
if "%START%"=="" exit /b 1
if "%END%"=="" exit /b 1
exit /b 0
