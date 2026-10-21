[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$TerminalPath,
  [Parameter(Mandatory=$true)][string]$Mql5ExpertsPath,
  [Parameter(Mandatory=$true)][datetime]$FromDate,
  [Parameter(Mandatory=$true)][datetime]$ToDate,
  [string]$Symbol = "XAUUSD",
  [double]$Deposit = 10000,
  [string]$Currency = "USD",
  [string]$Leverage = "1:100"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $TerminalPath -PathType Leaf)) { throw "TerminalPath does not exist: $TerminalPath" }
if (-not (Test-Path -LiteralPath $Mql5ExpertsPath -PathType Container)) { throw "Mql5ExpertsPath does not exist: $Mql5ExpertsPath" }
if ($ToDate -lt $FromDate) { throw "ToDate must be on or after FromDate." }
if ($Deposit -le 0) { throw "Deposit must be positive." }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$source = Join-Path $repoRoot "ea\challengers\AUREON_XAUUSD_Strategy_Suite_RealTicks_v1.mq5"
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "EA source missing: $source" }

$eaDir = Join-Path $Mql5ExpertsPath "AUREON"
New-Item -ItemType Directory -Force -Path $eaDir | Out-Null
$eaTarget = Join-Path $eaDir (Split-Path $source -Leaf)
Copy-Item -LiteralPath $source -Destination $eaTarget -Force

$metaEditor = Join-Path (Split-Path $TerminalPath -Parent) "MetaEditor64.exe"
if (-not (Test-Path -LiteralPath $metaEditor -PathType Leaf)) { $metaEditor = Join-Path (Split-Path $TerminalPath -Parent) "metaeditor64.exe" }
if (-not (Test-Path -LiteralPath $metaEditor -PathType Leaf)) { throw "MetaEditor64.exe not found beside terminal. Supply a matching MT5 installation." }

$runRoot = Join-Path $repoRoot "research\mt5\strategy-suite-runs"
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$reports = Join-Path $runRoot "reports"
New-Item -ItemType Directory -Force -Path $reports | Out-Null

# Compile the exact source staged into the selected terminal's Experts folder.
$compileLog = Join-Path $runRoot "compile.log"
$compile = Start-Process -FilePath $metaEditor -ArgumentList @("/compile:$eaTarget", "/log") -Wait -PassThru
Start-Sleep -Seconds 2
$nativeLog = [System.IO.Path]::ChangeExtension($eaTarget, ".log")
if (Test-Path -LiteralPath $nativeLog) { Copy-Item -LiteralPath $nativeLog -Destination $compileLog -Force }
$ex5 = [System.IO.Path]::ChangeExtension($eaTarget, ".ex5")
if (-not (Test-Path -LiteralPath $ex5 -PathType Leaf)) { throw "MetaEditor did not create EX5. Inspect $compileLog" }
if ((Test-Path $compileLog) -and ((Get-Content -Raw $compileLog) -notmatch '(?i)0 errors')) { throw "Compile log does not confirm zero errors. Inspect $compileLog" }

$from = $FromDate.ToString("yyyy.MM.dd")
$to = $ToDate.ToString("yyyy.MM.dd")
$tests = @(
  @{Name="M5_MEAN_REVERSION"; Strategy=0; Params=@{InpMeanEMA=20;InpRSILow=30;InpRSIHigh=70;InpMeanDeviationATR=1.25;InpADXMaxForMeanReversion=25}},
  @{Name="H4_BREAKOUT"; Strategy=1; Params=@{InpH4Lookback=20;InpBreakoutBufferATR=0.10}},
  @{Name="SESSION_BREAKOUT"; Strategy=2; Params=@{InpAsianStartHour=0;InpAsianEndHour=7;InpSessionTradeStartHour=7;InpSessionTradeEndHour=17;InpBreakoutBufferATR=0.10}},
  @{Name="DAILY_CRT"; Strategy=3; Params=@{}}
)
$common = [ordered]@{
  InpMagic=20261021
  InpRiskPercent=0.25
  InpDailyLossLimitPct=2.0
  InpMaxPeakDrawdownPct=6.0
  InpMaxSpreadPoints=80
  InpDeviationPoints=35
  InpMaxTradesPerDay=3
  InpCooldownMinutes=30
  InpStopATR=1.5
  InpRewardRisk=1.5
  InpMeanEMA=20
  InpRSIPeriod=14
  InpRSILow=30.0
  InpRSIHigh=70.0
  InpMeanDeviationATR=1.25
  InpADXMaxForMeanReversion=25.0
  InpH4Lookback=20
  InpBreakoutBufferATR=0.10
  InpAsianStartHour=0
  InpAsianEndHour=7
  InpSessionTradeStartHour=7
  InpSessionTradeEndHour=17
  InpRequireDemoAccount=true
  InpAllowLong=true
  InpAllowShort=true
}
$summary = [System.Collections.Generic.List[object]]::new()
foreach ($test in $tests) {
  $params = [ordered]@{}; foreach ($key in $common.Keys) { $params[$key] = $common[$key] }
  $params["InpStrategy"] = $test.Strategy
  foreach ($key in $test.Params.Keys) { $params[$key] = $test.Params[$key] }
  $setPath = Join-Path $runRoot ($test.Name + ".set")
  $setLines = foreach ($key in $params.Keys) { "$key=$($params[$key])" }
  Set-Content -LiteralPath $setPath -Value $setLines -Encoding ASCII

  $reportRel = "reports\$($test.Name).htm"
  $iniPath = Join-Path $runRoot ($test.Name + ".ini")
  $ini = @(
    "[Tester]"
    "Expert=AUREON\AUREON_XAUUSD_Strategy_Suite_RealTicks_v1.ex5"
    "ExpertParameters=$setPath"
    "Symbol=$Symbol"
    "Period=M5"
    "Deposit=$Deposit"
    "Currency=$Currency"
    "Leverage=$Leverage"
    "Model=4"
    "ExecutionMode=0"
    "Optimization=0"
    "FromDate=$from"
    "ToDate=$to"
    "ForwardMode=0"
    "Report=$((Join-Path $reports ($test.Name + ".htm")))"
    "ReplaceReport=1"
    "UseLocal=1"
    "UseRemote=0"
    "UseCloud=0"
    "Visual=0"
    "ShutdownTerminal=1"
  )
  Set-Content -LiteralPath $iniPath -Value $ini -Encoding ASCII
  Write-Host "Running $($test.Name) on $Symbol, $from to $to, Model=4 (Every tick based on real ticks)"
  $proc = Start-Process -FilePath $TerminalPath -ArgumentList @("/config:$iniPath") -Wait -PassThru
  $reportPath = Join-Path $reports ($test.Name + ".htm")
  $exists = Test-Path -LiteralPath $reportPath -PathType Leaf
  $summary.Add([pscustomobject]@{Strategy=$test.Name;ProcessExitCode=$proc.ExitCode;ReportPath=$reportPath;ReportCreated=$exists;Model="Every tick based on real ticks";FromDate=$from;ToDate=$to})
  if (-not $exists) { Write-Warning "No report produced for $($test.Name). This is not a successful backtest." }
}
$summaryPath = Join-Path $runRoot "run-manifest.json"
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
$summary | Format-Table -AutoSize
Write-Host "Manifest: $summaryPath"
Write-Host "IMPORTANT: confirm tick coverage, costs, trade count, and tester report settings before ranking PF."
