# AUREON FVG V2.171 Closed-Bar Diagnostic Patch
# Creates a separate candidate; never overwrites the V2.17 source.
$ErrorActionPreference = "Stop"
$root = "C:\Users\User\Desktop\AUREON"
$expected = "FVG_Scalper_V2_17_FORWARD_VALIDATION.mq5"
if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "AUREON root not found: $root" }
$found = @(Get-ChildItem -LiteralPath $root -Filter $expected -File -Recurse -ErrorAction SilentlyContinue)
if ($found.Count -ne 1) { throw "Expected exactly one $expected under $root; found $($found.Count). No changes made." }
$srcPath = $found[0].FullName
$src = [IO.File]::ReadAllText($srcPath, [Text.Encoding]::UTF8)
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
if (-not $src.Contains($bullOld) -or -not $src.Contains($bearOld)) { throw "Source does not match expected V2.17 functions. No candidate created." }
$src = $src.Replace($bullOld,$bullNew).Replace($bearOld,$bearNew)
$src = $src.Replace('#property version   "2.17"','#property version   "2.171"')
$src = $src.Replace('#property description "FVG V2.17 Forward Validation: preserves V2.15 aggressive edge; adds live/demo execution telemetry, FVG attribution, benchmark drift monitoring and optional safety block."','#property description "FVG V2.171 Closed-Bar Diagnostic: rejection uses last closed candle; V2.17 preserved as control."')
$src = $src.Replace('input string InpTelemetryFile = "FVG_V2_14_Aggressive.csv";','input string InpTelemetryFile = "FVG_V2_171_Diagnostic.csv";')
$src = $src.Replace('input string InpForwardTelemetryFile = "FVG_V2_17_Forward.csv";','input string InpForwardTelemetryFile = "FVG_V2_171_Forward.csv";')
$src = $src.Replace('Print("FVG V2.17 FORWARD VALIDATION | M1 reaction | repeat FVG entries | 30R anchor | staged lock | 0.10 ATR trail | compounding ON");','Print("FVG V2.171 CLOSED-BAR DIAGNOSTIC | last-closed-candle rejection | other settings retained for controlled A/B test");')
if ($src -match 'double closePos=\(bid-r\[0\]\.low\)/range;' -or $src -match 'double closePos=\(ask-r\[0\]\.low\)/range;' -or -not $src.Contains('r[1].close')) { throw "Post-patch verification failed. No candidate created." }
$outDir = Join-Path $root "research\mt5"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$outPath = Join-Path $outDir "FVG_Scalper_V2_171_ClosedBarDiagnostic.mq5"
if (Test-Path -LiteralPath $outPath) { throw "Candidate already exists; rename/archive it before rerunning: $outPath" }
[IO.File]::WriteAllText($outPath,$src,[Text.UTF8Encoding]::new($false))
$report = "Source preserved: YES" + [Environment]::NewLine + "Candidate: $outPath" + [Environment]::NewLine + "Patch: rejection uses r[1].close; V2.171 telemetry filenames isolated." + [Environment]::NewLine + "Compile/test status: PENDING MT5 terminal. Profitability: NOT VERIFIED." + [Environment]::NewLine + "LIVE TRADING: BLOCKED."
[IO.File]::WriteAllText((Join-Path $outDir "V2_171_PATCH_REPORT.txt"),$report,[Text.UTF8Encoding]::new($false))
Write-Host $report -ForegroundColor Green
