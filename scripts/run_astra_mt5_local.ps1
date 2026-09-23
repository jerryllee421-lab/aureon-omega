param(
    [string]$TerminalPath = '',
    [string]$Symbol = 'XAUUSD',
    [string]$FromDate = '',
    [string]$ToDate = '',
    [double]$Deposit = 10000,
    [string]$Leverage = '1:100',
    [string]$Preset = 'ea/astra/presets/ASTRA_GOLD_V1_BASELINE.set',
    [switch]$ForceCloseTerminal
)

$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$eaSource = Join-Path $repo 'ea/astra/AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5'
if(-not (Test-Path $eaSource)){ throw "EA source not found: $eaSource" }
if(-not (Test-Path $Preset)){ throw "Preset not found: $Preset" }

function Normalize-Path([string]$p) {
    try { return ([IO.Path]::GetFullPath($p)).TrimEnd('\').ToLowerInvariant() }
    catch { return $p.TrimEnd('\').ToLowerInvariant() }
}

function Find-Terminal {
    param([string]$Preferred)

    if($Preferred){
        $resolved=(Resolve-Path $Preferred -ErrorAction Stop).Path
        if((Split-Path $resolved -Leaf).ToLowerInvariant() -ne 'terminal64.exe'){
            throw "TerminalPath must point to terminal64.exe: $resolved"
        }
        return $resolved
    }

    $running=Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object -First 1
    if($running -and $running.Path){ return $running.Path }

    $pf86=[Environment]::GetFolderPath('ProgramFilesX86')
    $common=@(
        (Join-Path $env:ProgramFiles 'MetaTrader 5\terminal64.exe'),
        (Join-Path $pf86 'MetaTrader 5\terminal64.exe')
    )
    foreach($p in $common){ if($p -and (Test-Path $p)){ return $p } }

    $root=Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    if(Test-Path $root){
        foreach($origin in Get-ChildItem $root -Filter origin.txt -Recurse -ErrorAction SilentlyContinue){
            try {
                $install=(Get-Content $origin.FullName -Raw -ErrorAction Stop).Trim()
                $candidate=Join-Path $install 'terminal64.exe'
                if(Test-Path $candidate){ return $candidate }
            } catch {}
        }
    }
    throw 'No MetaTrader 5 terminal64.exe installation was found.'
}

function Find-DataDirectory {
    param([string]$TerminalExe)
    $install=Normalize-Path (Split-Path $TerminalExe -Parent)
    $root=Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    if(-not (Test-Path $root)){ throw "MetaTrader data root not found: $root" }

    foreach($origin in Get-ChildItem $root -Filter origin.txt -Recurse -ErrorAction SilentlyContinue){
        try {
            $recorded=Normalize-Path ((Get-Content $origin.FullName -Raw -ErrorAction Stop).Trim())
            if($recorded -eq $install){ return (Split-Path $origin.FullName -Parent) }
        } catch {}
    }
    throw "Could not map terminal installation '$install' to its MetaTrader data directory."
}

$TerminalPath = Find-Terminal $TerminalPath
$installDir = Split-Path $TerminalPath -Parent
$dataDir = Find-DataDirectory $TerminalPath
$mql5 = Join-Path $dataDir 'MQL5'
$metaEditor = Join-Path $installDir 'metaeditor64.exe'
if(-not (Test-Path $metaEditor)){ throw "MetaEditor not found: $metaEditor" }

$accounts = Join-Path $dataDir 'config\accounts.dat'
if(-not (Test-Path $accounts) -or (Get-Item $accounts).Length -eq 0){
    throw "No saved MT5 trading account was found in $dataDir. Log in to a demo/live MT5 account once, then rerun."
}

if(-not $FromDate){ $FromDate=(Get-Date).AddYears(-5).ToString('yyyy.MM.dd') }
if(-not $ToDate){ $ToDate=(Get-Date).AddDays(-1).ToString('yyyy.MM.dd') }

$artifactDir = Join-Path $repo 'artifacts\mt5-local'
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

$running=Get-Process terminal64 -ErrorAction SilentlyContinue
if($running){
    if(-not $ForceCloseTerminal){
        throw 'MetaTrader 5 is currently running. Close it first or rerun with -ForceCloseTerminal on a dedicated test machine.'
    }
    $running | Stop-Process -Force
    Start-Sleep -Seconds 2
}

$expertDir = Join-Path $mql5 'Experts\AUREON'
New-Item -ItemType Directory -Force -Path $expertDir | Out-Null
$eaDest = Join-Path $expertDir 'AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5'
Copy-Item $eaSource $eaDest -Force

$compileArgs=@("/compile:$eaDest","/include:$mql5",'/log')
$p=Start-Process -FilePath $metaEditor -ArgumentList $compileArgs -PassThru
if(-not $p.WaitForExit(180000)){
    $p.Kill()
    throw 'MetaEditor compilation timed out.'
}
Start-Sleep -Seconds 2
$ex5=[IO.Path]::ChangeExtension($eaDest,'.ex5')
$compileLog=[IO.Path]::ChangeExtension($eaDest,'.log')
if(Test-Path $compileLog){ Copy-Item $compileLog (Join-Path $artifactDir 'compile.log') -Force }
if(-not (Test-Path $ex5)){ throw 'MetaEditor did not produce the EX5 file.' }
$ct=Get-Content $compileLog -Raw -Encoding Unicode
if($ct -notmatch '0 errors'){ throw 'Compilation failed; inspect artifacts\mt5-local\compile.log.' }
Copy-Item $ex5 (Join-Path $artifactDir 'AUREON_ASTRA_GOLD_CAMPAIGN_V1.ex5') -Force

$presetDestDir=Join-Path $mql5 'Profiles\Tester'
New-Item -ItemType Directory -Force -Path $presetDestDir | Out-Null
$presetDest=Join-Path $presetDestDir (Split-Path $Preset -Leaf)
Copy-Item $Preset $presetDest -Force

$reports=Join-Path $installDir 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$reportStem='ASTRA_GOLD_V1_BASELINE'
Get-ChildItem $reports -Filter "$reportStem*" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$config=Join-Path $env:TEMP 'astra-gold-v1-local.ini'
@(
    '[Experts]',
    'Enabled=1',
    'AllowLiveTrading=0',
    'AllowDllImport=0',
    '',
    '[Tester]',
    'Expert=AUREON\AUREON_ASTRA_GOLD_CAMPAIGN_V1',
    "ExpertParameters=$(Split-Path $Preset -Leaf)",
    "Symbol=$Symbol",
    'Period=M5',
    "Deposit=$Deposit",
    'Currency=USD',
    "Leverage=$Leverage",
    'Model=4',
    'ExecutionMode=0',
    'Optimization=0',
    'OptimizationCriterion=6',
    "FromDate=$FromDate",
    "ToDate=$ToDate",
    'ForwardMode=0',
    "Report=reports\$reportStem",
    'ReplaceReport=1',
    'ShutdownTerminal=1',
    'UseLocal=1',
    'UseRemote=0',
    'UseCloud=0',
    'Visual=0'
) | Set-Content -Path $config -Encoding Unicode
Copy-Item $config (Join-Path $artifactDir 'tester.ini') -Force

Write-Host "Launching MT5 native Strategy Tester"
Write-Host "Terminal: $TerminalPath"
Write-Host "DataDir : $dataDir"
Write-Host "Symbol  : $Symbol"
Write-Host "Range   : $FromDate -> $ToDate"

$p=Start-Process -FilePath $TerminalPath -ArgumentList @("/config:$config") -PassThru
if(-not $p.WaitForExit(7200000)){
    $p.Kill()
    throw 'Native MT5 Strategy Tester exceeded the 2-hour safety timeout.'
}
Start-Sleep -Seconds 3

$report=Get-ChildItem $installDir -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "$reportStem*.htm" -or $_.Name -like "$reportStem*.html" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

$logRoots=@((Join-Path $dataDir 'logs'),(Join-Path $dataDir 'Tester\logs'),(Join-Path $mql5 'Logs'))
foreach($lr in $logRoots){
    Get-ChildItem $lr -Filter '*.log' -Recurse -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 3 |
        ForEach-Object {
            $safe=$_.FullName.Replace(':','').Replace('\','_')
            Copy-Item $_.FullName (Join-Path $artifactDir $safe) -Force
        }
}

if($null -eq $report){
    throw 'MT5 test ended without a report. Inspect the copied tester/platform logs.'
}
Copy-Item $report.FullName (Join-Path $artifactDir 'ASTRA_GOLD_V1_BASELINE.htm') -Force

(Get-FileHash $eaSource -Algorithm SHA256).Hash | Set-Content (Join-Path $artifactDir 'source.sha256')
(Get-FileHash $Preset -Algorithm SHA256).Hash | Set-Content (Join-Path $artifactDir 'preset.sha256')
(Get-FileHash $report.FullName -Algorithm SHA256).Hash | Set-Content (Join-Path $artifactDir 'report.sha256')

if(Test-Path 'scripts/analyze_mt5_report.py'){
    python scripts/analyze_mt5_report.py (Join-Path $artifactDir 'ASTRA_GOLD_V1_BASELINE.htm') --out (Join-Path $artifactDir 'analysis')
    if($LASTEXITCODE -ne 0){
        Write-Warning 'Report generated but robustness gate did not pass. This is a research result, not an execution failure.'
    }
}

Write-Host 'ASTRA_NATIVE_MT5_BASELINE_COMPLETE'
Write-Host "Report: $(Join-Path $artifactDir 'ASTRA_GOLD_V1_BASELINE.htm')"
