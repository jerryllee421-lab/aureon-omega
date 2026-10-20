# AUREON FVG V2.171 Closed-Bar Diagnostic Patch
# Creates a separate candidate; never overwrites the V2.17 source.
$ErrorActionPreference = "Stop"
$root = "C:\Users\User\Desktop\AUREON"
$expected = "FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5"
$lf = [string][char]10

if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw "AUREON root not found: $root"
}
$found = @(Get-ChildItem -LiteralPath $root -Filter $expected -File -Recurse -ErrorAction SilentlyContinue)
if ($found.Count -ne 1) {
    throw "Expected exactly one $expected under $root; found $($found.Count). No changes made."
}
$srcPath = $found[0].FullName
$src = [System.IO.File]::ReadAllText($srcPath, [System.Text.Encoding]::UTF8)
$src = [regex]::Replace($src, '\r\n?', $lf)

$bullOld = @'
bool BullishRejection()
{
   MqlRates r[]; ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,2,r)<2) return false;
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double range=r[0].high-r[0].low;
   if(range<=0) return false;
   double closePos=(bid-r[0].low)/range;
   return closePos >= 0.55;
}
'@
$bearOld = @'
bool BearishRejection()
{
   MqlRates r[]; ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,2,r)<2) return false;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double range=r[0].high-r[0].low;
   if(range<=0) return false;
   double closePos=(ask-r[0].low)/range;
   return closePos <= 0.45;
}
'@
$bullNew = @'
bool BullishRejection()
{
   // V2.171 diagnostic: rejection is confirmed from the last CLOSED candle.
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,2,r)<2) return false;
   const double range=r[1].high-r[1].low;
   if(range<=0.0) return false;
   const double closePos=(r[1].close-r[1].low)/range;
   return (closePos >= 0.55);
}
'@
$bearNew = @'
bool BearishRejection()
{
   // V2.171 diagnostic: rejection is confirmed from the last CLOSED candle.
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,2,r)<2) return false;
   const double range=r[1].high-r[1].low;
   if(range<=0.0) return false;
   const double closePos=(r[1].close-r[1].low)/range;
   return (closePos <= 0.45);
}
'@

$bullOld = [regex]::Replace($bullOld, '\r\n?', $lf)
$bearOld = [regex]::Replace($bearOld, '\r\n?', $lf)
$bullNew = [regex]::Replace($bullNew, '\r\n?', $lf)
$bearNew = [regex]::Replace($bearNew, '\r\n?', $lf)
if (-not $src.Contains($bullOld) -or -not $src.Contains($bearOld)) {
    throw "Source does not match expected V2.17 functions. No candidate created."
}

$src = $src.Replace($bullOld, $bullNew).Replace($bearOld, $bearNew)
$src = $src.Replace('#property version   "2.17"', '#property version   "2.171"')
$src = $src.Replace(
    '#property description "FVG V2.17 Forward Validation: preserves V2.15 aggressive edge; adds live/demo execution telemetry, FVG attribution, benchmark drift monitoring and optional safety block."',
    '#property description "FVG V2.171 Closed-Bar Diagnostic: rejection uses last closed candle; V2.17 preserved as control."'
)
$src = $src.Replace('input string InpTelemetryFile = "FVG_V2_14_Aggressive.csv";', 'input string InpTelemetryFile = "FVG_V2_171_Diagnostic.csv";')
$src = $src.Replace('input string InpForwardTelemetryFile = "FVG_V2_17_Forward.csv";', 'input string InpForwardTelemetryFile = "FVG_V2_171_Forward.csv";')
$src = $src.Replace(
    'Print("FVG V2.17 FORWARD VALIDATION | M1 reaction | repeat FVG entries | 30R anchor | staged lock | 0.10 ATR trail | compounding ON");',
    'Print("FVG V2.171 CLOSED-BAR DIAGNOSTIC | last-closed-candle rejection | other settings retained for controlled A/B test");'
)

if ($src -match 'double closePos=\(bid-r\[0\]\.low\)/range;' -or
    $src -match 'double closePos=\(ask-r\[0\]\.low\)/range;' -or
    -not $src.Contains('const double closePos=(r[1].close-r[1].low)/range;')) {
    throw "Post-patch verification failed. No candidate created."
}

$outDir = Join-Path $root "research\mt5"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$outPath = Join-Path $outDir "FVG_Scalper_V2_171_ClosedBarDiagnostic.mq5"
if (Test-Path -LiteralPath $outPath) {
    throw "Candidate already exists; rename/archive it before rerunning: $outPath"
}
[System.IO.File]::WriteAllText($outPath, $src, [System.Text.UTF8Encoding]::new($false))
$report = @"
Source preserved: YES
Candidate: $outPath
Patch: rejection uses r[1].close; V2.171 telemetry filenames isolated.
Compile/test status: PENDING MT5 terminal. Profitability: NOT VERIFIED.
LIVE TRADING: BLOCKED.
"@
[System.IO.File]::WriteAllText((Join-Path $outDir "V2_171_PATCH_REPORT.txt"), $report, [System.Text.UTF8Encoding]::new($false))
Write-Host $report -ForegroundColor Green
