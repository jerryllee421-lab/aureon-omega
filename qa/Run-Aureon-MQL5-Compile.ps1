[CmdletBinding()]
param(
    [string]$SourceDirectory = (Join-Path $PSScriptRoot 'mql5'),
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'artifacts'),
    [switch]$NoInstall
)

$ErrorActionPreference = 'Stop'
$started = Get-Date
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$runId = $started.ToString('yyyyMMdd-HHmmss')
$logDir = Join-Path $OutputDirectory "compile-$runId"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$results = [System.Collections.Generic.List[object]]::new()

function Find-FileRecursive([string[]]$Roots, [string]$Name) {
    foreach ($root in $Roots) {
        if (Test-Path -LiteralPath $root) {
            $match = Get-ChildItem -LiteralPath $root -Filter $Name -File -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($match) { return $match.FullName }
        }
    }
    return $null
}

function Write-Diagnostic([string]$Message) {
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message"
}

try {
    Write-Diagnostic 'AUREON Ω MQL5 compile runner starting.'
    Write-Diagnostic "Computer: $env:COMPUTERNAME | PowerShell: $($PSVersionTable.PSVersion)"
    Write-Diagnostic "Source directory: $SourceDirectory"
    Write-Diagnostic "Output directory: $logDir"

    if (!(Test-Path -LiteralPath $SourceDirectory)) {
        throw "Source directory not found: $SourceDirectory"
    }

    $knownRoots = @(
        'C:\MT5',
        'C:\Program Files\MetaTrader 5',
        'C:\Program Files (x86)\MetaTrader 5',
        "$env:LOCALAPPDATA\Programs\MetaTrader 5",
        "$env:APPDATA\MetaQuotes\Terminal",
        "$env:LOCALAPPDATA\MetaQuotes\Terminal"
    )
    $editor = Find-FileRecursive -Roots $knownRoots -Name 'metaeditor64.exe'
    $terminal = Find-FileRecursive -Roots $knownRoots -Name 'terminal64.exe'

    if ((!$editor -or !$terminal) -and !$NoInstall) {
        Write-Diagnostic 'MetaTrader terminal/editor not both found. Downloading official MetaTrader installer.'
        $installer = Join-Path $env:TEMP "mt5setup-$runId.exe"
        Invoke-WebRequest -Uri 'https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe' -OutFile $installer -TimeoutSec 180
        $installerBytes = (Get-Item -LiteralPath $installer).Length
        if ($installerBytes -lt 100000) { throw "Installer download is unexpectedly small ($installerBytes bytes)." }
        $installProcess = Start-Process -FilePath $installer -ArgumentList @('/auto', '/path:C:\MT5') -PassThru -Wait
        Write-Diagnostic "Installer exit code: $($installProcess.ExitCode); bytes: $installerBytes"
        $knownRoots = @(
            'C:\MT5',
            'C:\Program Files\MetaTrader 5',
            'C:\Program Files (x86)\MetaTrader 5',
            "$env:LOCALAPPDATA\Programs\MetaTrader 5",
            "$env:APPDATA\MetaQuotes\Terminal",
            "$env:LOCALAPPDATA\MetaQuotes\Terminal"
        )
        $editor = Find-FileRecursive -Roots $knownRoots -Name 'metaeditor64.exe'
        $terminal = Find-FileRecursive -Roots $knownRoots -Name 'terminal64.exe'
    }

    if (!$editor) { throw 'MetaEditor executable not found. See diagnostic paths in the report.' }
    if (!$terminal) { throw 'terminal64.exe not found; cannot initialize/check the terminal data directory.' }
    Write-Diagnostic "MetaEditor: $editor"
    Write-Diagnostic "Terminal: $terminal"

    $tradeFile = Find-FileRecursive -Roots $knownRoots -Name 'Trade.mqh'
    if (!$tradeFile) {
        Write-Diagnostic 'Trade.mqh is absent. Launching terminal once to allow first-run initialization/update.'
        $terminalRoot = Split-Path -Parent $terminal
        $bootstrap = Start-Process -FilePath $terminal -ArgumentList '/portable' -WorkingDirectory $terminalRoot -PassThru
        Start-Sleep -Seconds 40
        try {
            $bootstrap.Refresh()
            if (!$bootstrap.HasExited) {
                Stop-Process -Id $bootstrap.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {}
        Start-Sleep -Seconds 3
        $dataRoots = @(
            (Join-Path $terminalRoot 'MQL5'),
            (Join-Path $terminalRoot 'MQL5\Include'),
            "$env:APPDATA\MetaQuotes\Terminal",
            "$env:LOCALAPPDATA\MetaQuotes\Terminal",
            'C:\MT5',
            'C:\Program Files\MetaTrader 5'
        )
        $tradeFile = Find-FileRecursive -Roots $dataRoots -Name 'Trade.mqh'
    }
    if (!$tradeFile) {
        $diagPath = Join-Path $logDir 'installation-diagnostics.txt'
        $lines = [System.Collections.Generic.List[string]]::new()
        $lines.Add("MetaEditor=$editor")
        $lines.Add("Terminal=$terminal")
        foreach ($root in $knownRoots) {
            $lines.Add("ROOT $root exists=$(Test-Path -LiteralPath $root)")
            if (Test-Path -LiteralPath $root) {
                Get-ChildItem -LiteralPath $root -Force -ErrorAction SilentlyContinue |
                    Select-Object -First 80 | ForEach-Object { $lines.Add("  $($_.FullName)") }
            }
        }
        $lines | Set-Content -LiteralPath $diagPath -Encoding UTF8
        throw "Standard Trade.mqh was not found after terminal bootstrap. See $diagPath. No source compilation attempted."
    }

    # Trade.mqh is expected at <MQL5>\Include\Trade\Trade.mqh.
    $includeRoot = Split-Path -Parent (Split-Path -Parent $tradeFile)
    if (!(Test-Path -LiteralPath $includeRoot)) { throw "Include root derived from $tradeFile does not exist: $includeRoot" }
    Write-Diagnostic "Standard library: $tradeFile"
    Write-Diagnostic "Include root: $includeRoot"

    $sources = @(Get-ChildItem -LiteralPath $SourceDirectory -Filter '*.mq5' -File | Sort-Object Name)
    if ($sources.Count -ne 4) {
        throw "Expected exactly four MQL5 source files (V2.17 control + 3 V2.18 challengers); found $($sources.Count)."
    }

    foreach ($source in $sources) {
        $log = Join-Path $logDir ($source.BaseName + '.log')
        $ex5 = [System.IO.Path]::ChangeExtension($source.FullName, '.ex5')
        Remove-Item -LiteralPath $log,$ex5 -Force -ErrorAction SilentlyContinue
        $sourceHash = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash
        Write-Diagnostic "Compiling $($source.Name) | SHA256=$sourceHash"
        $compilerOutput = & $editor "/compile:$($source.FullName)" "/log:$log" "/inc:$includeRoot" 2>&1
        $compilerExit = $LASTEXITCODE
        $deadline = (Get-Date).AddSeconds(120)
        $logText = ''
        while ((Get-Date) -lt $deadline) {
            if (Test-Path -LiteralPath $log) {
                $logText = Get-Content -LiteralPath $log -Raw -ErrorAction SilentlyContinue
                if ($logText -match '\d+\s+errors?,\s*\d+\s+warnings?') { break }
            }
            Start-Sleep -Seconds 2
        }
        if ($compilerOutput) { $compilerOutput | Out-File -LiteralPath (Join-Path $logDir ($source.BaseName + '.stdout.txt')) -Encoding UTF8 }
        if (!(Test-Path -LiteralPath $log)) {
            $results.Add([pscustomobject]@{ Source=$source.Name; Status='FAIL'; ExitCode=$compilerExit; Errors='Compiler log missing'; Warnings='Unknown'; SourceSHA256=$sourceHash; Ex5SHA256=$null })
            throw "Compiler log missing for $($source.Name); native result cannot be verified."
        }
        if (!$logText) { $logText = Get-Content -LiteralPath $log -Raw }
        Write-Host "===== $($source.Name) ====="
        Write-Host $logText
        $zeroErrors = $logText -match '\b0\s+errors?\b'
        $ex5Exists = Test-Path -LiteralPath $ex5
        $status = if ($zeroErrors -and $ex5Exists) { 'PASS' } else { 'FAIL' }
        $ex5Hash = if ($ex5Exists) { (Get-FileHash -LiteralPath $ex5 -Algorithm SHA256).Hash } else { $null }
        $errors = if ($logText -match '(\d+)\s+errors?') { $Matches[1] } else { 'Unknown' }
        $warnings = if ($logText -match '\d+\s+errors?,\s*(\d+)\s+warnings?') { $Matches[1] } else { 'Unknown' }
        $results.Add([pscustomobject]@{ Source=$source.Name; Status=$status; ExitCode=$compilerExit; Errors=$errors; Warnings=$warnings; SourceSHA256=$sourceHash; Ex5SHA256=$ex5Hash })
        if ($status -ne 'PASS') { throw "Compile verification failed for $($source.Name): errors=$errors, ex5Exists=$ex5Exists, compilerExit=$compilerExit" }
    }

    $overall = 'PASS'
} catch {
    $overall = 'FAIL'
    $failure = $_.Exception.Message
    Write-Error $failure
} finally {
    $finished = Get-Date
    $report = [ordered]@{
        project = 'QUANTUM NEXUS AUREON Ω'
        task = 'Native MQL5 compile validation only'
        startedUtc = $started.ToUniversalTime().ToString('o')
        finishedUtc = $finished.ToUniversalTime().ToString('o')
        durationSeconds = [math]::Round(($finished - $started).TotalSeconds, 2)
        computer = $env:COMPUTERNAME
        powershell = $PSVersionTable.PSVersion.ToString()
        sourceDirectory = $SourceDirectory
        outputDirectory = $logDir
        status = $overall
        failure = $failure
        results = @($results)
        safety = 'No broker connection, no order placement, no Strategy Tester run, no live trading.'
    }
    $reportPath = Join-Path $logDir 'compile-report.json'
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    $hashPath = Join-Path $logDir 'SHA256SUMS.txt'
    Get-ChildItem -LiteralPath $logDir -File | Where-Object { $_.FullName -ne $hashPath } |
        Sort-Object Name | ForEach-Object {
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            "$hash  $($_.Name)"
        } | Set-Content -LiteralPath $hashPath -Encoding UTF8
    Write-Host ''
    Write-Host "AUREON MQL5 COMPILE RESULT: $overall"
    Write-Host "Evidence directory: $logDir"
    Write-Host "Report: $reportPath"
}
if ($overall -ne 'PASS') { exit 1 }
exit 0
