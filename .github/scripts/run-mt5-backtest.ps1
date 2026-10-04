Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) {
  Write-Host "[AUREON MT5] $Message"
}

function Mask-Text([string]$Text) {
  $s = $Text
  if ($env:PXBT_LOGIN) { $s = $s.Replace($env:PXBT_LOGIN, "***LOGIN***") }
  if ($env:PXBT_PASSWORD) { $s = $s.Replace($env:PXBT_PASSWORD, "***PASSWORD***") }
  if ($env:PXBT_SERVER) { $s = $s.Replace($env:PXBT_SERVER, "***SERVER***") }
  return $s
}

function Compile-Mql([string]$Source, [string]$MetaEditor) {
  Write-Info "Compiling $([IO.Path]::GetFileName($Source))"
  $args = @("/compile:`"$Source`"", "/log")
  $p = Start-Process -FilePath $MetaEditor -ArgumentList $args -PassThru
  if (-not $p.WaitForExit(180000)) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    throw "MetaEditor compile timed out: $Source"
  }

  $log = [IO.Path]::ChangeExtension($Source, ".log")
  if (Test-Path $log) {
    Get-Content $log | ForEach-Object { Write-Host (Mask-Text $_) }
  }

  $ex5 = [IO.Path]::ChangeExtension($Source, ".ex5")
  if (-not (Test-Path $ex5)) {
    throw "Compile failed; EX5 not produced: $Source"
  }
  return $ex5
}

$workspace = $env:GITHUB_WORKSPACE
$out = Join-Path $workspace "artifacts"
New-Item -ItemType Directory -Path $out -Force | Out-Null

$root = Join-Path $env:RUNNER_TEMP "AUREON_MT5"
$setup = Join-Path $env:RUNNER_TEMP "mt5setup.exe"
$cfgPreflight = Join-Path $root "aureon-preflight.ini"
$cfgTester = Join-Path $root "aureon-v10-1y.ini"
$eaBase = if ($env:EA_BASENAME) { $env:EA_BASENAME } else { "AUREON_OMEGA_V10_AUTONOMOUS_HYPER_SCALPER" }
$testFrom = if ($env:TEST_FROM) { $env:TEST_FROM } else { "2025.10.04" }
$testTo = if ($env:TEST_TO) { $env:TEST_TO } else { "2026.10.04" }

try {
  Write-Info "Installing official MetaTrader 5."
  if (Test-Path $root) { Remove-Item $root -Recurse -Force }
  New-Item -ItemType Directory -Path $root -Force | Out-Null

  Invoke-WebRequest -Uri "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe" -OutFile $setup
  $install = Start-Process -FilePath $setup -ArgumentList @("/auto", "/path:`"$root`"") -PassThru
  $install.WaitForExit()

  $deadline = (Get-Date).AddMinutes(5)
  $terminal = $null
  do {
    $terminal = Get-ChildItem -Path $root -Filter "terminal64.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($terminal) { break }
    Start-Sleep -Seconds 5
  } while ((Get-Date) -lt $deadline)

  Get-Process terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

  if (-not $terminal) { throw "MT5 terminal64.exe not found after automatic installation." }
  $metaeditor = Get-ChildItem -Path $root -Filter "metaeditor64.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $metaeditor) { throw "MetaEditor64.exe not found after automatic installation." }

  Write-Info "MT5 installed at $root"

  $experts = Join-Path $root "MQL5\Experts\AUREON"
  $scripts = Join-Path $root "MQL5\Scripts\AUREON"
  New-Item -ItemType Directory -Path $experts -Force | Out-Null
  New-Item -ItemType Directory -Path $scripts -Force | Out-Null

  $eaSrc = Join-Path $workspace "mt5\$eaBase.mq5"
  if (-not (Test-Path $eaSrc)) { throw "EA source missing: $eaSrc" }
  $eaDst = Join-Path $experts "$eaBase.mq5"
  Copy-Item $eaSrc $eaDst -Force

  $probe = Join-Path $scripts "AUREON_PREFLIGHT.mq5"
@'
#property strict

string FindGoldSymbol()
  {
   string xau="";
   string anygold="";
   int total=SymbolsTotal(false);
   for(int i=0;i<total;i++)
     {
      string s=SymbolName(i,false);
      string u=s;
      StringToUpper(u);
      if(u=="XAUUSD") return s;
      if(xau=="" && StringFind(u,"XAUUSD")>=0) xau=s;
      if(anygold=="" && (StringFind(u,"XAU")>=0 || StringFind(u,"GOLD")>=0)) anygold=s;
     }
   if(xau!="") return xau;
   return anygold;
  }

void OnStart()
  {
   bool connected=false;
   for(int i=0;i<60;i++)
     {
      if((bool)TerminalInfoInteger(TERMINAL_CONNECTED))
        {
         connected=true;
         break;
        }
      Sleep(1000);
     }

   string gold="";
   bool selected=false;
   bool tick_ok=false;
   MqlTick tick={};

   if(connected)
     {
      gold=FindGoldSymbol();
      if(gold!="")
        {
         selected=SymbolSelect(gold,true);
         if(selected)
           {
            for(int i=0;i<30;i++)
              {
               if(SymbolInfoTick(gold,tick) && tick.time_msc>0 && tick.bid>0.0 && tick.ask>0.0)
                 {
                  tick_ok=true;
                  break;
                 }
               Sleep(1000);
              }
           }
        }
     }

   int h=FileOpen("AUREON_PREFLIGHT.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h!=INVALID_HANDLE)
     {
      FileWriteString(h,"CONNECTED="+(connected?"1":"0")+"\r\n");
      FileWriteString(h,"GOLD_SYMBOL="+gold+"\r\n");
      FileWriteString(h,"SYMBOL_SELECTED="+(selected?"1":"0")+"\r\n");
      FileWriteString(h,"TICK_OK="+(tick_ok?"1":"0")+"\r\n");
      FileWriteString(h,"SERVER="+AccountInfoString(ACCOUNT_SERVER)+"\r\n");
      FileClose(h);
     }

   PrintFormat("[AUREON PREFLIGHT] connected=%d gold=%s selected=%d tick=%d",
               (connected?1:0),gold,(selected?1:0),(tick_ok?1:0));
   TerminalClose((connected && selected && tick_ok)?0:77);
  }
'@ | Set-Content -Path $probe -Encoding ASCII

  $eaEx5 = Compile-Mql $eaDst $metaeditor.FullName
  $probeEx5 = Compile-Mql $probe $metaeditor.FullName
  Write-Info "EA and connectivity probe compiled."

  $required = @("PXBT_LOGIN","PXBT_PASSWORD","PXBT_SERVER")
  $missing = @($required | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_)) })
  if ($missing.Count -gt 0) {
    Write-Info "Native compile PASS. Broker credential gate not ready: $($missing -join ', '). No broker connection attempted."
    Copy-Item $eaEx5 (Join-Path $out "$eaBase.ex5") -Force
    $compileLog = [IO.Path]::ChangeExtension($eaDst, ".log")
    if (Test-Path $compileLog) { Copy-Item $compileLog (Join-Path $out "AUREON_V10_2_COMPILE.log") -Force }
    "NATIVE_COMPILE_PASS=1" | Set-Content -Path (Join-Path $out "COMPILE_STATUS.txt") -Encoding UTF8
    exit 0
  }

  $preflightFile = Join-Path $root "MQL5\Files\AUREON_PREFLIGHT.txt"
  if (Test-Path $preflightFile) { Remove-Item $preflightFile -Force }

@"
[Common]
Login=$env:PXBT_LOGIN
Server=$env:PXBT_SERVER
Password=$env:PXBT_PASSWORD
KeepPrivate=0
NewsEnable=0

[Experts]
Enabled=1
AllowLiveTrading=0
AllowDllImport=0

[StartUp]
Script=AUREON\AUREON_PREFLIGHT.ex5
Symbol=EURUSD
Period=M1
ShutdownTerminal=1
"@ | Set-Content -Path $cfgPreflight -Encoding ASCII

  Write-Info "Starting read-only PXBT connectivity preflight."
  $pre = Start-Process -FilePath $terminal.FullName -ArgumentList @("/portable", "/config:`"$cfgPreflight`"") -PassThru
  if (-not $pre.WaitForExit(180000)) {
    Stop-Process -Id $pre.Id -Force -ErrorAction SilentlyContinue
    throw "PXBT preflight timed out."
  }

  if (-not (Test-Path $preflightFile)) {
    throw "PXBT preflight produced no status file. Login/server resolution likely failed before the probe started."
  }

  $kv = @{}
  Get-Content $preflightFile | ForEach-Object {
    if ($_ -match "^([^=]+)=(.*)$") { $kv[$matches[1]]=$matches[2] }
  }

  if ($kv["CONNECTED"] -ne "1") { throw "PXBT preflight: terminal did not connect." }
  if ($kv["SYMBOL_SELECTED"] -ne "1") { throw "PXBT preflight: broker Gold symbol could not be selected." }
  if ($kv["TICK_OK"] -ne "1") { throw "PXBT preflight: no valid Gold tick received." }
  $gold = $kv["GOLD_SYMBOL"]
  if ([string]::IsNullOrWhiteSpace($gold)) { throw "PXBT preflight: Gold symbol is empty." }

  Write-Info "Preflight passed; Gold symbol discovered: $gold"

  $reports = Join-Path $root "reports"
  New-Item -ItemType Directory -Path $reports -Force | Out-Null

@"
[Common]
Login=$env:PXBT_LOGIN
Server=$env:PXBT_SERVER
Password=$env:PXBT_PASSWORD
KeepPrivate=0
NewsEnable=0

[Experts]
Enabled=1
AllowLiveTrading=0
AllowDllImport=0

[Tester]
Expert=AUREON\$eaBase.ex5
Symbol=$gold
Period=M5
Login=$env:PXBT_LOGIN
Model=4
ExecutionMode=0
Optimization=0
FromDate=$testFrom
ToDate=$testTo
ForwardMode=0
Report=reports\AUREON_V10_PXBT_1Y
ReplaceReport=1
ShutdownTerminal=1
Deposit=10000
Currency=USD
Leverage=1:100
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
"@ | Set-Content -Path $cfgTester -Encoding ASCII

  Write-Info "Starting Strategy Tester: $gold M5, Model=4 real ticks, $testFrom -> $testTo, USD 10,000, 1:100."
  $test = Start-Process -FilePath $terminal.FullName -ArgumentList @("/portable", "/config:`"$cfgTester`"") -PassThru
  if (-not $test.WaitForExit(6600000)) {
    Stop-Process -Id $test.Id -Force -ErrorAction SilentlyContinue
    throw "MT5 one-year backtest exceeded 110 minutes."
  }

  $report = Get-ChildItem -Path $reports -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "AUREON_V10_PXBT_1Y*" -and $_.Extension -in ".htm",".html" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if (-not $report) { throw "MT5 exited without producing the requested Strategy Tester report." }

  Copy-Item $report.FullName (Join-Path $out $report.Name) -Force

  $compileLog = [IO.Path]::ChangeExtension($eaDst, ".log")
  if (Test-Path $compileLog) { Copy-Item $compileLog (Join-Path $out "AUREON_V10_COMPILE.log") -Force }

@"
AUREON OMEGA V10 — MT5 NATIVE BACKTEST
Broker server: configured through encrypted GitHub secret
Gold symbol: $gold
Timeframe: M5
Model: Every tick based on real ticks (Model=4)
Optimization: OFF
Period: $testFrom to $testTo
Deposit: USD 10,000
Leverage: 1:100
Execution: Strategy Tester only
Credential used: investor/read-only password
Report source: MetaTrader 5 Strategy Tester
"@ | Set-Content -Path (Join-Path $out "RUN_MANIFEST.txt") -Encoding UTF8

  Write-Info "Backtest complete; report produced: $($report.Name)"
}
catch {
  $err = Mask-Text $_.Exception.Message
  Write-Error $err
  $err | Set-Content -Path (Join-Path $out "FAILURE.txt") -Encoding UTF8
  throw
}
finally {
  Remove-Item $cfgPreflight -Force -ErrorAction SilentlyContinue
  Remove-Item $cfgTester -Force -ErrorAction SilentlyContinue

  $diag = Join-Path $out "SANITIZED_DIAGNOSTICS.txt"
  "AUREON MT5 RUN DIAGNOSTICS" | Set-Content $diag -Encoding UTF8

  if (Test-Path $root) {
    $logs = Get-ChildItem -Path $root -Filter "*.log" -File -Recurse -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 10

    foreach ($log in $logs) {
      "----- $($log.FullName.Substring($root.Length)) -----" | Add-Content $diag
      Get-Content $log.FullName -ErrorAction SilentlyContinue | Select-Object -Last 300 | ForEach-Object {
        (Mask-Text $_) | Add-Content $diag
      }
    }
  }
}
