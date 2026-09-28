//+------------------------------------------------------------------+
//|                    FVG_Scalper_V4_00_ASTRA_ResearchAccelerator_AllInOne.mq5                |
//|   ASTRA Research Accelerator built from V3.00 ASTRA Quant core   |
//|   ASTRA Research Accelerator: EDGE / GROWTH / ROBUST / CUSTOM    |
//|   One EA for optimization, directional research and validation    |
//+------------------------------------------------------------------+
#property strict
#property version   "4.00"
#property description "FVG V4.00 ASTRA Research Accelerator: all-in-one XAUUSD FVG research EA with EDGE/GROWTH/ROBUST/CUSTOM profiles, independent BUY/SELL intelligence, minimum-lot-aware ASTRA gating, historical similarity, contradiction engine, directional exits, optimization telemetry, and custom OnTester fitness."

#include <Trade/Trade.mqh>
CTrade trade;

// External AI is OPTIONAL and disabled by default. Strategy Tester remains fully
// deterministic. For live AI calls, whitelist the endpoint in MT5:
// Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URL.
// Never hard-code a private API key into a distributed source file.

enum ENUM_FVG_TRAIL_MODE
{
   FVG_TRAIL_LEGACY   = 0,
   FVG_TRAIL_ADAPTIVE = 1,
   FVG_TRAIL_HYBRID   = 2,
   FVG_TRAIL_SMART    = 3
};

enum ENUM_ASTRA_AI_VERDICT
{
   ASTRA_AI_BYPASS    = 0,
   ASTRA_AI_ALLOW     = 1,
   ASTRA_AI_DOWNGRADE = 2,
   ASTRA_AI_VETO      = 3,
   ASTRA_AI_ERROR     = 4
};

enum ENUM_ASTRA_RESEARCH_MODE
{
   ASTRA_MODE_EDGE   = 0,
   ASTRA_MODE_GROWTH = 1,
   ASTRA_MODE_ROBUST = 2,
   ASTRA_MODE_CUSTOM = 3
};

//--------------------- ASTRA Research Accelerator --------------------
input group "ASTRA Research Accelerator"
input ENUM_ASTRA_RESEARCH_MODE InpResearchMode = ASTRA_MODE_GROWTH;
input bool InpUseProfileOverrides = true;
input bool InpUseMinLotDecisionGate = true;
input double InpMinLotGateContradiction = 68.0;
input double InpMinLotGateSimilarity = 42.0;
input bool InpCountResearchDecisions = true;

// MT5 optimization / OnTester fitness
input group "Optimization Fitness"
input bool InpUseCustomOnTesterFitness = true;
input int InpFitnessMinTrades = 180;
input double InpFitnessMaxEquityDDPct = 15.0;
input double InpFitnessTargetPF = 2.50;
input double InpFitnessReturnWeight = 1.00;
input double InpFitnessPFWeight = 1.10;
input double InpFitnessDDPenaltyWeight = 1.30;
input double InpFitnessTradeCountWeight = 0.35;
input double InpFitnessRecoveryWeight = 0.35;

//--------------------------- Strategy -------------------------------
input group "Strategy"
input ENUM_TIMEFRAMES InpEntryTF = PERIOD_M1;
input ENUM_TIMEFRAMES InpBiasTF = PERIOD_M1;
input int InpBiasFastEMA = 20;
input int InpBiasSlowEMA = 50;
input bool InpUseBiasFilter = false;
input bool InpAllowLong = true;
input bool InpAllowShort = true;
input bool InpRequireMidpoint = false;
input bool InpRequireRejection = true;
input double InpMinFVG_ATR = 0.15;
input double InpMinBody_ATR = 0.50;
input double InpMinBodyRatio = 0.60;
input int InpMaxFVG_Bars = 1000;
input bool InpReplaceWithNewFVG = true;
input bool InpOneTradePerFVG = false;

//------------------------ Controlled Re-entry -------------------------
input group "Controlled Re-entry / Zone Budget"
input bool InpUseControlledReentry = true;
input int InpMaxAttemptsPerFVG = 3;
input int InpReentryCooldownBars = 3;
input int InpThirdAttemptCooldownBars = 6;
input bool InpRequireClosedBarRejectionOnReentry = true;
input double InpReentryCloseThreshold = 0.60;
input double InpThirdAttemptRejectionThreshold = 0.63;
input bool InpAllowReentryAfterProfit = false;
input double InpQuarantineLossR = 1.50;
input bool InpQuarantineAfterMaxAttempts = true;
input bool InpUseLossStreakPause = true;
input int InpMaxConsecutiveLosses = 3;
input double InpLossCountsBelowR = -0.50;
input int InpLossPauseBars = 15;
input double InpSecondAttemptRiskScale = 0.75;
input double InpThirdAttemptRiskScale = 0.50;
input bool InpUseZoneRiskBudget = true;
input double InpMaxZoneRiskBudgetPct = 2.70;
input bool InpUseQualityScoreForReentry = true;
input double InpMinQualityScoreSecondAttempt = 49.0;
input double InpMinQualityScoreThirdAttempt = 64.0;
input double InpThirdAttemptMinLastR = -1.25;

//------------------------ Regime Intelligence -------------------------
input group "Regime Intelligence"
input bool InpUseRegimeFilter = false;
input ENUM_TIMEFRAMES InpRegimeTF = PERIOD_M15;
input int InpRegimeFastEMA = 20;
input int InpRegimeSlowEMA = 50;
input bool InpRequireRegimeSlope = true;
input bool InpRequirePriceSide = false;
input bool InpUseADXFilter = false;
input int InpADXPeriod = 14;
input double InpMinADX = 18.0;

//------------------------ MTF Context ---------------------------------
input group "M5 / M15 / H1 Context Score"
input bool InpUseMTFScoreFilter = false;
input int InpMTFFastEMA = 20;
input int InpMTFSlowEMA = 50;
input int InpMinMTFScore = 1;

//------------------------ Market Quality ------------------------------
input group "Market Quality"
input bool InpUseVolatilityFilter = false;
input int InpVolatilityLookback = 50;
input double InpMinATRRatio = 0.35;
input double InpMaxATRRatio = 1.80;
input bool InpUseShockGuard = true;
input double InpMaxClosedBarRangeATR = 2.50;
input int InpShockCooldownBars = 2;
input bool InpUseRelativeSpreadGuard = true;
input double InpRelativeSpreadMultiplier = 3.00;
input int InpSpreadEMAWarmupTicks = 200;

//------------------------ Entry Quality -------------------------------
input group "Entry Quality Score"
input bool InpUseEntryQualityScore = false;
input double InpMinEntryQualityScore = 55.0;

//-------------------- Directional Intelligence ------------------------
input group "Directional Intelligence"
input bool InpUseDirectionalIntelligence = true;
input int InpLongMinMTFAlignedVotes = 0;       // allow neutral MTF long context; reject bearish-majority context
input int InpShortMinMTFAlignedVotes = 0;      // reject shorts only when MTF majority is bullish
input double InpLongMinQualityScore = 53.0;
input double InpShortMinQualityScore = 45.0;
input int InpLongMaxAttemptsPerFVG = 3;
input int InpShortMaxAttemptsPerFVG = 3;
input bool InpUseQualityRiskScaling = true;
input double InpQualityFullRiskScore = 70.0;
input double InpQualityMidRiskScore = 57.0;
input double InpQualityMidRiskScale = 0.88;
input double InpQualityLowRiskScale = 0.72;

//---------------------- ASTRA Deterministic Intelligence -------------
input group "ASTRA Deterministic Intelligence"
input bool InpUseASTRARegimeClassifier = true;
input bool InpUseContradictionEngine = true;
input double InpContradictionRiskStart = 55.0;
input double InpContradictionHardVeto = 88.0;
input double InpContradictionMinRiskScale = 0.70;
input bool InpUseHistoricalSimilarity = true;
input int InpSimilarityMemory = 256;
input int InpSimilarityMinSamples = 24;
input int InpSimilarityNeighbors = 12;
input double InpSimilarityLowScore = 45.0;
input double InpSimilarityHighScore = 65.0;
input double InpSimilarityLowRiskScale = 0.78;
input double InpSimilarityMidRiskScale = 0.90;
input bool InpSimilarityHardFilter = false;
input double InpSimilarityMinAllowedScore = 32.0;
input bool InpLoadSimilarityHistoryLive = true;
input string InpSimilarityMemoryFile = "FVG_V4_00_ASTRA_Similarity.csv";
input bool InpASTRAProtectMinimumLot = true;

//------------------------- ASTRA AI Gateway ---------------------------
input group "ASTRA External AI Gateway (LIVE only)"
input bool InpUseExternalAI = false;
input bool InpAIDisableInTester = true;
input string InpAIEndpoint = "https://integrate.api.nvidia.com/v1/chat/completions";
input string InpAIModel = "deepseek-ai/deepseek-v4.1-flash";
input string InpAIApiKey = "";
input int InpAITimeoutMs = 3000;
input double InpAIMinQualityToCall = 58.0;
input bool InpAIOnlyFirstAttempt = true;
input int InpAIMaxCallsDay = 50;
input int InpAIMinSecondsBetweenCalls = 20;
input double InpAIDowngradeRiskScale = 0.60;
input bool InpAIHardVeto = true;
input bool InpAIFailClosed = false;
input bool InpExportASTRAMarketPackets = false;
input string InpASTRAPacketFile = "FVG_V4_00_ASTRA_MarketPackets.jsonl";

//------------------------ Risk Management ----------------------------
input group "Risk Management"
input double InpRiskPercent = 2.0;
input bool InpAutoCompoundLots = true;
input double InpCompoundingBaseBalance = 100.0;
input bool InpUseHardRiskCap = true;
input double InpMaxEffectiveRiskPct = 1.25;
input double InpLongRiskMultiplier = 0.85;
input double InpShortRiskMultiplier = 1.0;
input double InpMaxLots = 0.0;
input double InpRewardRisk = 30.0;
input double InpMaxSL_ATR = 3.0;
input int InpATRPeriod = 14;
input double InpSL_ATR_Buffer = 0.15;
input bool InpUseProfitLock = true;
input double InpLock1TriggerRR = 0.50;
input double InpLock1RR = 0.10;
input double InpLock2TriggerRR = 1.00;
input double InpLock2RR = 0.35;

//------------------------ Exit Research -------------------------------
input group "Exit Research"
input bool InpUseATRTrail = true;
input ENUM_FVG_TRAIL_MODE InpTrailMode = FVG_TRAIL_SMART;
input double InpTrailStartRR = 1.50;
input double InpTrail_ATR = 0.10;
input double InpTrailTightenRR = 4.00;
input double InpTrailTightATR = 0.18;
input double InpAdaptiveTrailFloorRR = 0.50;
input double InpHybridTrailStartRR = 1.75;
input double InpHybridTrailATR = 0.22;
input double InpHybridTightenRR = 4.00;
input double InpHybridTightATR = 0.14;
input double InpHybridTrailFloorRR = 0.50;
input double InpSmartTrailStartRR = 2.00;
input double InpSmartTrailATR = 0.30;
input double InpSmartTightenRR = 5.00;
input double InpSmartTightATR = 0.20;
input double InpSmartTrailFloorRR = 0.50;
input bool InpUsePeakRProtection = true;
input double InpPeakRArm1 = 3.00;
input double InpPeakRGiveback1 = 1.25;
input double InpPeakRArm2 = 6.00;
input double InpPeakRGiveback2 = 1.75;
input bool InpUseTimeStop = false;
input int InpTimeStopBars = 20;
input double InpTimeStopMinMFER = 0.25;

//--------------------- Directional Exit Profiles ---------------------
input group "Directional Exit Profiles"
input bool InpUseDirectionalExitProfiles = true;
input double InpLongTrailStartRR = 1.75;
input double InpLongTrailATR = 0.24;
input double InpLongTightenRR = 4.00;
input double InpLongTightATR = 0.16;
input double InpLongPeakArm1 = 2.50;
input double InpLongPeakGiveback1 = 0.95;
input double InpLongPeakArm2 = 5.00;
input double InpLongPeakGiveback2 = 1.35;
input double InpShortTrailStartRR = 2.25;
input double InpShortTrailATR = 0.34;
input double InpShortTightenRR = 5.50;
input double InpShortTightATR = 0.22;
input double InpShortPeakArm1 = 3.25;
input double InpShortPeakGiveback1 = 1.25;
input double InpShortPeakArm2 = 6.50;
input double InpShortPeakGiveback2 = 1.80;

//--------------------------- Sessions --------------------------------
input group "Sessions"
input bool InpUseSession1 = true;
input int InpSession1Start = 0;
input int InpSession1End = 0;
input bool InpUseSession2 = true;
input int InpSession2Start = 0;
input int InpSession2End = 0;
input int InpMaxSpreadPoints = 80;
input int InpMaxTradesDay = 1000;
input double InpDailyLossPct = 3.0;
input bool InpOnePosition = true;
input bool InpUseSessionQualityFilter = false;
input bool InpAllowAsia = true;
input bool InpAllowLondon = true;
input bool InpAllowLondonNYOverlap = true;
input bool InpAllowNewYork = true;
input bool InpAllowOtherSession = true;

//----------------------- Equity Circuit Breakers ----------------------
input group "Equity Circuit Breakers"
input bool InpUseDailyPeakProtection = false;
input double InpDailyProfitArmPct = 5.0;
input double InpDailyPeakGivebackPct = 2.0;

//--------------------- Equity Drawdown Governor -----------------------
input group "Equity Drawdown Governor"
input bool InpUseEquityDDGovernor = true;
input double InpDDStage1Pct = 5.0;
input double InpDDStage1RiskScale = 0.85;
input double InpDDStage2Pct = 8.0;
input double InpDDStage2RiskScale = 0.60;
input double InpDDStage3Pct = 11.0;
input double InpDDStage3RiskScale = 0.40;
input double InpDDHardStopPct = 15.0;

//----------------------- Execution Safety -----------------------------
input group "Execution Safety"
input bool InpUseMarginGuard = true;
input double InpMinProjectedMarginLevelPct = 150.0;
input double InpMaxSingleTradeMarginPct = 35.0;
input int InpMaxEntrySlippagePoints = 0;
input int InpCooldownSeconds = 0;

//--------------------------- Research ---------------------------------
input group "Research / Telemetry"
input bool InpEnableTelemetry = true;
input string InpTelemetryFile = "FVG_V4_00_ASTRA_Research.csv";
input bool InpPersistState = true;
input int InpResearchSessionOffsetHours = 0;
input bool InpVerboseLog = false;

//--------------------------- Execution --------------------------------
input group "Execution"
input ulong InpMagic = 26081400;
input int InpDeviationPoints = 30;

struct FVGZone
{
   bool valid;
   bool bullish;
   double low;
   double high;
   datetime formed;
   int shift;
   bool traded;
   int attempts;
   datetime lastEntryTime;
   datetime lastExitTime;
   double lastRealizedR;
   bool quarantined;
   double gapATR;
   double bodyATR;
   double bodyRatio;
   double riskSpentPct;
};

struct ASTRAHistorySample
{
   bool bullish;
   double gapATR;
   double bodyATR;
   double bodyRatio;
   double atrRatio;
   double qualityScore;
   int mtfScore;
   int zoneAttempt;
   double realizedR;
};

struct TradeTelemetry
{
   bool active;
   ulong positionTicket;
   long positionType;
   datetime entryTime;
   double requestedEntry;
   double actualEntry;
   double initialSL;
   double originalTP;
   double initialRiskPrice;
   double plannedRiskMoney;
   double effectiveRiskMoney;
   double effectiveRiskPct;
   double requestedRawVolume;
   double volume;
   double maxMFE_R;
   double maxMAE_R;
   double entrySlippagePoints;
   double entrySpreadPoints;
   string sessionTag;
   datetime zoneFormed;
   double zoneLow;
   double zoneHigh;
   bool bullishZone;
   double zoneGapATR;
   double zoneBodyATR;
   double zoneBodyRatio;
   double regimeFastEMA;
   double regimeSlowEMA;
   double regimeADX;
   double regimeSlope;
   double atrRatio;
   double shockRangeATR;
   int zoneAttempt;
   bool reentry;
   int lossStreakAtEntry;
   int mtfScore;
   double qualityScore;
   double spreadRatio;
   double zoneRiskSpentPct;
   double attemptRiskScale;
   double directionRiskScale;
   double qualityRiskScale;
   double ddRiskScale;
   double peakDrawdownPct;
   int alignedMTFVotes;
   string astraRegime;
   double contradictionScore;
   double contradictionRiskScale;
   double similarityScore;
   int similaritySamples;
   double similarityRiskScale;
   string aiVerdict;
   double aiRiskScale;
};

int hATR = INVALID_HANDLE;
int hFastEMA = INVALID_HANDLE;
int hSlowEMA = INVALID_HANDLE;
int hRegimeFastEMA = INVALID_HANDLE;
int hRegimeSlowEMA = INVALID_HANDLE;
int hRegimeADX = INVALID_HANDLE;

int hM5Fast = INVALID_HANDLE;
int hM5Slow = INVALID_HANDLE;
int hM15Fast = INVALID_HANDLE;
int hM15Slow = INVALID_HANDLE;
int hH1Fast = INVALID_HANDLE;
int hH1Slow = INVALID_HANDLE;

datetime g_lastBar = 0;
double g_ctxRegimeFast = 0.0;
double g_ctxRegimeSlow = 0.0;
double g_ctxRegimeADX = 0.0;
double g_ctxRegimeSlope = 0.0;
double g_ctxATRRatio = 0.0;
double g_ctxShockRangeATR = 0.0;
int g_ctxMTFScore = 0;
double g_ctxQualityScore = 0.0;
double g_ctxSpreadRatio = 1.0;

double g_spreadEMA = 0.0;
int g_spreadSamples = 0;

FVGZone g_zone;
TradeTelemetry g_track;
int g_dayKey = -1;
int g_tradesToday = 0;
double g_dayStartEquity = 0.0;
double g_dayPeakEquity = 0.0;
double g_equityPeak = 0.0;
double g_ctxPeakDrawdownPct = 0.0;
double g_ctxDDRiskScale = 1.0;
datetime g_lastEntryTime = 0;
int g_lossStreakLong = 0;
int g_lossStreakShort = 0;
datetime g_pauseUntilLong = 0;
datetime g_pauseUntilShort = 0;

// ASTRA deterministic intelligence context.
string g_ctxASTRARegime = "UNKNOWN";
double g_ctxContradictionScore = 0.0;
double g_ctxContradictionRiskScale = 1.0;
double g_ctxSimilarityScore = 50.0;
int g_ctxSimilaritySamples = 0;
double g_ctxSimilarityRiskScale = 1.0;
string g_ctxAIVerdict = "BYPASS";
double g_ctxAIRiskScale = 1.0;

ASTRAHistorySample g_similarity[];
int g_similarityCount = 0;
int g_similarityHead = 0;

int g_aiCallsToday = 0;
datetime g_lastAICallTime = 0;

// Research decision counters (per run).
long g_researchCandidates = 0;
long g_researchAllowed = 0;
long g_researchDirectionalReject = 0;
long g_researchContradictionVeto = 0;
long g_researchSimilarityVeto = 0;
long g_researchMinLotSkip = 0;
long g_researchReentryReject = 0;
long g_researchOpened = 0;

// Global-variable key prefix for restart-safe state.
string GVPrefix()
{
   return "ASTRA400_" + _Symbol + "_" + IntegerToString((int)InpMagic) + "_";
}

//+------------------------------------------------------------------+
//| Research profile helpers                                          |
//+------------------------------------------------------------------+
string ResearchModeName()
{
   if(InpResearchMode==ASTRA_MODE_EDGE) return "EDGE";
   if(InpResearchMode==ASTRA_MODE_GROWTH) return "GROWTH";
   if(InpResearchMode==ASTRA_MODE_ROBUST) return "ROBUST";
   return "CUSTOM";
}

double EffectiveRiskPercent()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpRiskPercent;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 1.00;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 2.00;
   return 1.00;
}

bool EffectiveAutoCompound()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpAutoCompoundLots;
   return InpResearchMode!=ASTRA_MODE_EDGE;
}

double EffectiveHardRiskCapPct()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpMaxEffectiveRiskPct;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 1.00;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 1.50;
   return 1.00;
}

double EffectiveDirectionRiskMultiplier(bool bullish)
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM)
      return bullish?InpLongRiskMultiplier:InpShortRiskMultiplier;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 1.00;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return bullish?0.90:1.00;
   return bullish?0.75:0.90;
}

double EffectiveMinQuality(bool bullish)
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM)
      return bullish?InpLongMinQualityScore:InpShortMinQualityScore;
   if(InpResearchMode==ASTRA_MODE_EDGE) return bullish?45.0:42.0;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return bullish?50.0:43.0;
   return bullish?58.0:50.0;
}

int EffectiveMinMTFVotes(bool bullish)
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM)
      return bullish?InpLongMinMTFAlignedVotes:InpShortMinMTFAlignedVotes;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 0;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 0;
   return bullish?1:0;
}

int EffectiveMaxAttempts(bool bullish)
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM)
      return bullish?InpLongMaxAttemptsPerFVG:InpShortMaxAttemptsPerFVG;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 3;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 3;
   return bullish?2:3;
}

double EffectiveZoneBudgetPct()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpMaxZoneRiskBudgetPct;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 2.25;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 3.00;
   return 2.00;
}

double EffectiveContradictionVeto()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpContradictionHardVeto;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 94.0;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 82.0;
   return 74.0;
}

bool EffectiveSimilarityHardFilter()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpSimilarityHardFilter;
   return InpResearchMode==ASTRA_MODE_ROBUST;
}

double EffectiveSimilarityMinScore()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpSimilarityMinAllowedScore;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 25.0;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 35.0;
   return 45.0;
}

double EffectiveDDHardStopPct()
{
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM) return InpDDHardStopPct;
   if(InpResearchMode==ASTRA_MODE_EDGE) return 18.0;
   if(InpResearchMode==ASTRA_MODE_GROWTH) return 12.0;
   return 9.0;
}

double EffectiveDDScale()
{
   if(!InpUseEquityDDGovernor) return 1.0;
   double dd=g_ctxPeakDrawdownPct;
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM)
   {
      if(dd>=InpDDHardStopPct) return 0.0;
      if(dd>=InpDDStage3Pct) return InpDDStage3RiskScale;
      if(dd>=InpDDStage2Pct) return InpDDStage2RiskScale;
      if(dd>=InpDDStage1Pct) return InpDDStage1RiskScale;
      return 1.0;
   }
   if(InpResearchMode==ASTRA_MODE_EDGE)
   {
      if(dd>=18.0) return 0.0;
      if(dd>=14.0) return 0.55;
      if(dd>=10.0) return 0.75;
      if(dd>=7.0) return 0.90;
      return 1.0;
   }
   if(InpResearchMode==ASTRA_MODE_GROWTH)
   {
      if(dd>=12.0) return 0.0;
      if(dd>=9.0) return 0.45;
      if(dd>=7.0) return 0.65;
      if(dd>=5.0) return 0.85;
      return 1.0;
   }
   if(dd>=9.0) return 0.0;
   if(dd>=7.0) return 0.40;
   if(dd>=5.0) return 0.60;
   if(dd>=3.5) return 0.80;
   return 1.0;
}

//+------------------------------------------------------------------+
//| Initialization                                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   if(InpRiskPercent <= 0.0 || InpRewardRisk <= 0.0 || InpATRPeriod < 1)
      return INIT_PARAMETERS_INCORRECT;
   if(InpMinBodyRatio <= 0.0 || InpMinBodyRatio > 1.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpUseHardRiskCap && InpMaxEffectiveRiskPct <= 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpRegimeFastEMA < 1 || InpRegimeSlowEMA < 2 || InpRegimeFastEMA >= InpRegimeSlowEMA)
      return INIT_PARAMETERS_INCORRECT;
   if(InpMTFFastEMA < 1 || InpMTFSlowEMA < 2 || InpMTFFastEMA >= InpMTFSlowEMA)
      return INIT_PARAMETERS_INCORRECT;
   if(InpADXPeriod < 1 || InpMinADX < 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpVolatilityLookback < 5 || InpMinATRRatio < 0.0 || InpMaxATRRatio <= InpMinATRRatio)
      return INIT_PARAMETERS_INCORRECT;
   if(InpMaxClosedBarRangeATR <= 0.0 || InpShockCooldownBars < 1)
      return INIT_PARAMETERS_INCORRECT;
   if(InpRelativeSpreadMultiplier <= 1.0 || InpSpreadEMAWarmupTicks < 10)
      return INIT_PARAMETERS_INCORRECT;
   if(InpUseControlledReentry && (InpMaxAttemptsPerFVG < 1 || InpReentryCooldownBars < 0 || InpThirdAttemptCooldownBars < 0))
      return INIT_PARAMETERS_INCORRECT;
   if(InpReentryCloseThreshold <= 0.50 || InpReentryCloseThreshold >= 1.0 ||
      InpThirdAttemptRejectionThreshold <= 0.50 || InpThirdAttemptRejectionThreshold >= 1.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpSecondAttemptRiskScale <= 0.0 || InpSecondAttemptRiskScale > 1.0 ||
      InpThirdAttemptRiskScale <= 0.0 || InpThirdAttemptRiskScale > InpSecondAttemptRiskScale)
      return INIT_PARAMETERS_INCORRECT;
   if(InpUseZoneRiskBudget && InpMaxZoneRiskBudgetPct <= 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpLongRiskMultiplier <= 0.0 || InpLongRiskMultiplier > 1.0 ||
      InpShortRiskMultiplier <= 0.0 || InpShortRiskMultiplier > 1.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpQuarantineLossR <= 0.0 || InpMaxConsecutiveLosses < 1 || InpLossPauseBars < 0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpTrail_ATR <= 0.0 || InpTrailTightATR <= 0.0 || InpHybridTrailATR <= 0.0 || InpHybridTightATR <= 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpTimeStopBars < 1 || InpTimeStopMinMFER < 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpDailyProfitArmPct < 0.0 || InpDailyPeakGivebackPct < 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpMinMTFScore < 0 || InpMinMTFScore > 3)
      return INIT_PARAMETERS_INCORRECT;
   if(InpMinEntryQualityScore < 0.0 || InpMinEntryQualityScore > 100.0 ||
      InpMinQualityScoreSecondAttempt < 0.0 || InpMinQualityScoreSecondAttempt > 100.0 ||
      InpMinQualityScoreThirdAttempt < 0.0 || InpMinQualityScoreThirdAttempt > 100.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpLongMinMTFAlignedVotes < 0 || InpLongMinMTFAlignedVotes > 3 ||
      InpShortMinMTFAlignedVotes < 0 || InpShortMinMTFAlignedVotes > 3)
      return INIT_PARAMETERS_INCORRECT;
   if(InpLongMinQualityScore < 0.0 || InpLongMinQualityScore > 100.0 ||
      InpShortMinQualityScore < 0.0 || InpShortMinQualityScore > 100.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpLongMaxAttemptsPerFVG < 1 || InpShortMaxAttemptsPerFVG < 1)
      return INIT_PARAMETERS_INCORRECT;
   if(InpQualityFullRiskScore < InpQualityMidRiskScore || InpQualityFullRiskScore > 100.0 ||
      InpQualityMidRiskScore < 0.0 || InpQualityMidRiskScale <= 0.0 || InpQualityMidRiskScale > 1.0 ||
      InpQualityLowRiskScale <= 0.0 || InpQualityLowRiskScale > InpQualityMidRiskScale)
      return INIT_PARAMETERS_INCORRECT;
   if(InpSmartTrailATR <= 0.0 || InpSmartTightATR <= 0.0 || InpSmartTrailStartRR <= 0.0 ||
      InpSmartTightenRR < InpSmartTrailStartRR || InpPeakRArm1 <= 0.0 ||
      InpPeakRArm2 < InpPeakRArm1 || InpPeakRGiveback1 <= 0.0 || InpPeakRGiveback2 <= 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpDDStage1Pct < 0.0 || InpDDStage2Pct <= InpDDStage1Pct ||
      InpDDStage3Pct <= InpDDStage2Pct || InpDDHardStopPct <= InpDDStage3Pct ||
      InpDDStage1RiskScale <= 0.0 || InpDDStage1RiskScale > 1.0 ||
      InpDDStage2RiskScale <= 0.0 || InpDDStage2RiskScale > InpDDStage1RiskScale ||
      InpDDStage3RiskScale <= 0.0 || InpDDStage3RiskScale > InpDDStage2RiskScale)
      return INIT_PARAMETERS_INCORRECT;

   if(InpContradictionRiskStart < 0.0 || InpContradictionRiskStart >= 100.0 ||
      InpContradictionHardVeto <= InpContradictionRiskStart || InpContradictionHardVeto > 100.0 ||
      InpContradictionMinRiskScale <= 0.0 || InpContradictionMinRiskScale > 1.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpSimilarityMemory < 32 || InpSimilarityMemory > 2000 ||
      InpSimilarityMinSamples < 1 || InpSimilarityNeighbors < 1 ||
      InpSimilarityLowScore < 0.0 || InpSimilarityHighScore <= InpSimilarityLowScore ||
      InpSimilarityHighScore > 100.0 || InpSimilarityLowRiskScale <= 0.0 ||
      InpSimilarityMidRiskScale < InpSimilarityLowRiskScale || InpSimilarityMidRiskScale > 1.0 ||
      InpSimilarityMinAllowedScore < 0.0 || InpSimilarityMinAllowedScore > 100.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpAITimeoutMs < 250 || InpAIMaxCallsDay < 1 || InpAIMinSecondsBetweenCalls < 0 ||
      InpAIDowngradeRiskScale <= 0.0 || InpAIDowngradeRiskScale > 1.0 ||
      InpAIMinQualityToCall < 0.0 || InpAIMinQualityToCall > 100.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpFitnessMinTrades < 1 || InpFitnessMaxEquityDDPct <= 0.0 || InpFitnessTargetPF <= 0.0 ||
      InpFitnessReturnWeight < 0.0 || InpFitnessPFWeight < 0.0 || InpFitnessDDPenaltyWeight < 0.0 ||
      InpFitnessTradeCountWeight < 0.0 || InpFitnessRecoveryWeight < 0.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpMinLotGateContradiction < 0.0 || InpMinLotGateContradiction > 100.0 ||
      InpMinLotGateSimilarity < 0.0 || InpMinLotGateSimilarity > 100.0)
      return INIT_PARAMETERS_INCORRECT;
   if(InpLongTrailStartRR <= 0.0 || InpLongTrailATR <= 0.0 || InpLongTightATR <= 0.0 ||
      InpShortTrailStartRR <= 0.0 || InpShortTrailATR <= 0.0 || InpShortTightATR <= 0.0)
      return INIT_PARAMETERS_INCORRECT;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   hATR = iATR(_Symbol, InpEntryTF, InpATRPeriod);
   hFastEMA = iMA(_Symbol, InpBiasTF, InpBiasFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hSlowEMA = iMA(_Symbol, InpBiasTF, InpBiasSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   hRegimeFastEMA = iMA(_Symbol, InpRegimeTF, InpRegimeFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hRegimeSlowEMA = iMA(_Symbol, InpRegimeTF, InpRegimeSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   hRegimeADX = iADX(_Symbol, InpRegimeTF, InpADXPeriod);

   hM5Fast  = iMA(_Symbol, PERIOD_M5,  InpMTFFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hM5Slow  = iMA(_Symbol, PERIOD_M5,  InpMTFSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   hM15Fast = iMA(_Symbol, PERIOD_M15, InpMTFFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hM15Slow = iMA(_Symbol, PERIOD_M15, InpMTFSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   hH1Fast  = iMA(_Symbol, PERIOD_H1,  InpMTFFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hH1Slow  = iMA(_Symbol, PERIOD_H1,  InpMTFSlowEMA, 0, MODE_EMA, PRICE_CLOSE);

   if(hATR == INVALID_HANDLE || hFastEMA == INVALID_HANDLE || hSlowEMA == INVALID_HANDLE ||
      hRegimeFastEMA == INVALID_HANDLE || hRegimeSlowEMA == INVALID_HANDLE || hRegimeADX == INVALID_HANDLE ||
      hM5Fast == INVALID_HANDLE || hM5Slow == INVALID_HANDLE ||
      hM15Fast == INVALID_HANDLE || hM15Slow == INVALID_HANDLE ||
      hH1Fast == INVALID_HANDLE || hH1Slow == INVALID_HANDLE)
      return INIT_FAILED;

   g_zone.valid = false;
   g_zone.traded = false;
   g_zone.attempts = 0;
   g_zone.lastEntryTime = 0;
   g_zone.lastExitTime = 0;
   g_zone.lastRealizedR = 0.0;
   g_zone.quarantined = false;
   g_zone.gapATR = 0.0;
   g_zone.bodyATR = 0.0;
   g_zone.bodyRatio = 0.0;
   g_zone.riskSpentPct = 0.0;

   g_spreadEMA = 0.0;
   g_spreadSamples = 0;
   ArrayResize(g_similarity,InpSimilarityMemory);
   g_similarityCount=0;
   g_similarityHead=0;
   g_aiCallsToday=0;
   g_lastAICallTime=0;
   ResetTelemetry();

   if(InpUseHistoricalSimilarity && InpLoadSimilarityHistoryLive && !IsTesterEnvironment())
      LoadSimilarityHistory();

   if(InpPersistState)
   {
      LoadZoneState();
      LoadLossPauseState();
   }

   ResetDailyStats();
   LoadEquityPeakState();
   UpdateEquityPeak();
   RestoreTelemetryFromPosition();

   if(InpEnableTelemetry)
      EnsureTelemetryHeader();

   g_researchCandidates=0;
   g_researchAllowed=0;
   g_researchDirectionalReject=0;
   g_researchContradictionVeto=0;
   g_researchSimilarityVeto=0;
   g_researchMinLotSkip=0;
   g_researchReentryReject=0;
   g_researchOpened=0;

   if(InpUseExternalAI && InpAIDisableInTester && IsTesterEnvironment() && InpVerboseLog)
      Print("ASTRA400 external AI disabled in Strategy Tester; deterministic ASTRA engine remains active.");

   if(InpVerboseLog)
      Print("ASTRA400 mode=",ResearchModeName()," effectiveRisk=",DoubleToString(EffectiveRiskPercent(),2),
            "% cap=",DoubleToString(EffectiveHardRiskCapPct(),2),"%");

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(InpPersistState)
   {
      SaveZoneState();
      SaveLossPauseState();
      SaveEquityPeakState();
   }

   if(InpCountResearchDecisions && InpVerboseLog)
      Print("ASTRA400 research summary | mode=",ResearchModeName(),
            " candidates=",g_researchCandidates," allowed=",g_researchAllowed,
            " directionalReject=",g_researchDirectionalReject,
            " contradictionVeto=",g_researchContradictionVeto,
            " similarityVeto=",g_researchSimilarityVeto,
            " minLotSkip=",g_researchMinLotSkip,
            " reentryReject=",g_researchReentryReject,
            " opened=",g_researchOpened);

   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hFastEMA != INVALID_HANDLE) IndicatorRelease(hFastEMA);
   if(hSlowEMA != INVALID_HANDLE) IndicatorRelease(hSlowEMA);
   if(hRegimeFastEMA != INVALID_HANDLE) IndicatorRelease(hRegimeFastEMA);
   if(hRegimeSlowEMA != INVALID_HANDLE) IndicatorRelease(hRegimeSlowEMA);
   if(hRegimeADX != INVALID_HANDLE) IndicatorRelease(hRegimeADX);

   if(hM5Fast != INVALID_HANDLE) IndicatorRelease(hM5Fast);
   if(hM5Slow != INVALID_HANDLE) IndicatorRelease(hM5Slow);
   if(hM15Fast != INVALID_HANDLE) IndicatorRelease(hM15Fast);
   if(hM15Slow != INVALID_HANDLE) IndicatorRelease(hM15Slow);
   if(hH1Fast != INVALID_HANDLE) IndicatorRelease(hH1Fast);
   if(hH1Slow != INVALID_HANDLE) IndicatorRelease(hH1Slow);
}

//+------------------------------------------------------------------+
//| Main tick                                                         |
//+------------------------------------------------------------------+
void OnTick()
{
   ResetDailyStatsIfNeeded();
   UpdateSpreadState();
   UpdateDailyPeak();
   UpdateEquityPeak();
   UpdateTelemetryExcursions();
   ManageOpenPosition();

   if(IsNewBar())
      UpdateFVG();

   if(!TradingAllowed()) return;
   if(InpOnePosition && HasOurPosition()) return;
   if(g_tradesToday >= InpMaxTradesDay) return;
   if(!g_zone.valid || g_zone.quarantined) return;
   if(InpOneTradePerFVG && g_zone.traded) return;
   if(g_zone.bullish && !InpAllowLong) return;
   if(!g_zone.bullish && !InpAllowShort) return;
   if(!ZoneStillValid()) { g_zone.valid = false; PersistZoneIfNeeded(); return; }
   if(DirectionPauseActive(g_zone.bullish)) return;
   if(!BiasAllows(g_zone.bullish)) return;
   if(!RegimeAllows(g_zone.bullish)) return;
   if(!MTFScoreAllows(g_zone.bullish)) return;
   if(!MarketQualityAllows()) return;
   if(!SessionQualityAllows(TimeCurrent())) return;

   g_ctxQualityScore=ComputeEntryQualityScore(g_zone.bullish);
   if(InpUseEntryQualityScore && g_ctxQualityScore<InpMinEntryQualityScore) return;
   if(InpCountResearchDecisions) g_researchCandidates++;
   if(!DirectionalIntelligenceAllows(g_zone.bullish))
   {
      if(InpCountResearchDecisions) g_researchDirectionalReject++;
      return;
   }

   UpdateASTRAContext(g_zone.bullish);
   if(InpUseContradictionEngine && g_ctxContradictionScore>=EffectiveContradictionVeto())
   {
      if(InpCountResearchDecisions) g_researchContradictionVeto++;
      return;
   }
   if(InpUseHistoricalSimilarity && EffectiveSimilarityHardFilter() &&
      g_ctxSimilaritySamples>=InpSimilarityMinSamples &&
      g_ctxSimilarityScore<EffectiveSimilarityMinScore())
   {
      if(InpCountResearchDecisions) g_researchSimilarityVeto++;
      return;
   }

   if(g_ctxDDRiskScale<=0.0) return;
   if(!ReentryAllows(g_zone.bullish))
   {
      if(InpCountResearchDecisions) g_researchReentryReject++;
      return;
   }
   if(InpCountResearchDecisions) g_researchAllowed++;

   if(InpCooldownSeconds > 0 && g_lastEntryTime > 0 &&
      (TimeCurrent() - g_lastEntryTime) < InpCooldownSeconds) return;

   TryFVGEntry();
}

//+------------------------------------------------------------------+
//| Trade transaction: capture realised exit                          |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.deal == 0)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;

   string sym = HistoryDealGetString(trans.deal, DEAL_SYMBOL);
   ulong magic = (ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   if(sym != _Symbol || magic != InpMagic)
      return;

   ENUM_DEAL_ENTRY entryType = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entryType != DEAL_ENTRY_OUT && entryType != DEAL_ENTRY_OUT_BY)
      return;

   double profit = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
   double commission = HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   double swap = HistoryDealGetDouble(trans.deal, DEAL_SWAP);
   double fee = HistoryDealGetDouble(trans.deal, DEAL_FEE);
   double net = profit + commission + swap + fee;
   double closePrice = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   datetime closeTime = (datetime)HistoryDealGetInteger(trans.deal, DEAL_TIME);

   if(g_track.active)
   {
      UpdateTelemetryExcursions();
      double realizedR = (g_track.effectiveRiskMoney > 0.0) ? net / g_track.effectiveRiskMoney : 0.0;
      WriteTelemetryRow(closeTime, closePrice, net, realizedR, trans.deal);
      RecordSimilarityOutcome(g_track.positionType==POSITION_TYPE_BUY,realizedR);
      RegisterExitOutcome(g_track.positionType==POSITION_TYPE_BUY, realizedR, closeTime, g_track.zoneFormed);
      if(InpVerboseLog)
         Print("ASTRA400 exit | net=", DoubleToString(net,2), " R=", DoubleToString(realizedR,3),
               " attempt=",g_track.zoneAttempt,
               " MFE_R=", DoubleToString(g_track.maxMFE_R,3), " MAE_R=", DoubleToString(g_track.maxMAE_R,3));
      ResetTelemetry();
   }
}

//+------------------------------------------------------------------+
//| FVG discovery                                                     |
//+------------------------------------------------------------------+
void UpdateFVG()
{
   FVGZone newest;
   if(!FindNewestFVG(newest)) return;

   if(!g_zone.valid || (InpReplaceWithNewFVG && newest.formed > g_zone.formed) || FVGExpired(g_zone))
   {
      g_zone = newest;
      PersistZoneIfNeeded();
   }
}

bool FindNewestFVG(FVGZone &z)
{
   z.valid = false;
   z.traded = false;
   z.shift = -1;
   z.attempts = 0;
   z.lastEntryTime = 0;
   z.lastExitTime = 0;
   z.lastRealizedR = 0.0;
   z.quarantined = false;
   z.gapATR = 0.0;
   z.bodyATR = 0.0;
   z.bodyRatio = 0.0;
   z.riskSpentPct = 0.0;

   MqlRates r[];
   double atr[];
   ArraySetAsSeries(r, true);
   ArraySetAsSeries(atr, true);

   int need=InpMaxFVG_Bars+5;
   if(need<30) need=30;
   if(CopyRates(_Symbol, InpEntryTF, 0, need, r) < 6) return false;
   if(CopyBuffer(hATR, 0, 0, need, atr) < 6) return false;

   for(int s=1; s<=InpMaxFVG_Bars && s+2<ArraySize(r); s++)
   {
      double a = atr[s];
      if(a <= 0) continue;

      double oh = r[s+2].high;
      double ol = r[s+2].low;
      double mo = r[s+1].open;
      double mc = r[s+1].close;
      double mh = r[s+1].high;
      double ml = r[s+1].low;
      double nh = r[s].high;
      double nl = r[s].low;
      double body = MathAbs(mc-mo);
      double range = mh-ml;

      if(body < a*InpMinBody_ATR) continue;
      if(range <= 0 || body/range < InpMinBodyRatio) continue;

      // Bullish FVG: candle s+2 high below candle s low, with bullish displacement candle.
      if(oh < nl)
      {
         double gap = nl-oh;
         if(gap >= a*InpMinFVG_ATR && mc > mo)
         {
            z.valid=true; z.bullish=true; z.low=oh; z.high=nl;
            z.formed=r[s].time; z.shift=s; z.traded=false;
            z.gapATR=gap/a;
            z.bodyATR=body/a;
            z.bodyRatio=body/range;
            z.riskSpentPct=0.0;
            return true;
         }
      }

      // Bearish FVG: candle s+2 low above candle s high, with bearish displacement candle.
      if(ol > nh)
      {
         double gap = ol-nh;
         if(gap >= a*InpMinFVG_ATR && mc < mo)
         {
            z.valid=true; z.bullish=false; z.low=nh; z.high=ol;
            z.formed=r[s].time; z.shift=s; z.traded=false;
            z.gapATR=gap/a;
            z.bodyATR=body/a;
            z.bodyRatio=body/range;
            z.riskSpentPct=0.0;
            return true;
         }
      }
   }
   return false;
}

bool ZoneStillValid()
{
   if(!g_zone.valid || FVGExpired(g_zone)) return false;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol, InpEntryTF, 0, 3, r) < 3) return false;
   double c = r[1].close;

   if(g_zone.bullish && c < g_zone.low) return false;
   if(!g_zone.bullish && c > g_zone.high) return false;
   return true;
}

bool FVGExpired(const FVGZone &z)
{
   if(!z.valid) return true;
   int sh = iBarShift(_Symbol, InpEntryTF, z.formed, false);
   return sh < 0 || sh > InpMaxFVG_Bars;
}

//+------------------------------------------------------------------+
//| Controlled re-entry / streak protection                           |
//+------------------------------------------------------------------+
int BarsSince(datetime t)
{
   if(t<=0) return 1000000;
   int sh=iBarShift(_Symbol,InpEntryTF,t,false);
   if(sh<0) return 0;
   return sh;
}

bool ClosedBarRejectionForReentry(bool bullish,double threshold)
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,3,r)<3) return false;

   // Confirmation candle must be fully closed after the prior exit.
   if(g_zone.lastExitTime>0 && r[1].time<=g_zone.lastExitTime) return false;

   double range=r[1].high-r[1].low;
   if(range<=0.0) return false;

   bool touched=(r[1].low<=g_zone.high && r[1].high>=g_zone.low);
   if(!touched) return false;

   double closePos=(r[1].close-r[1].low)/range;
   if(bullish)
      return r[1].close>r[1].open && closePos>=threshold;
   return r[1].close<r[1].open && closePos<=(1.0-threshold);
}

double AttemptRiskScale(int attempt)
{
   if(attempt<=1) return 1.0;
   if(attempt==2) return InpSecondAttemptRiskScale;
   return InpThirdAttemptRiskScale;
}

int DirectionMaxAttempts(bool bullish)
{
   int m=InpMaxAttemptsPerFVG;
   if(InpUseDirectionalIntelligence)
   {
      int dm=EffectiveMaxAttempts(bullish);
      if(dm<m) m=dm;
   }
   if(m<1) m=1;
   return m;
}

double QualityRiskScale(double score)
{
   if(!InpUseQualityRiskScaling) return 1.0;
   if(score>=InpQualityFullRiskScore) return 1.0;
   if(score>=InpQualityMidRiskScore) return InpQualityMidRiskScale;
   return InpQualityLowRiskScale;
}

bool DirectionalIntelligenceAllows(bool bullish)
{
   if(!InpUseDirectionalIntelligence) return true;
   int aligned=bullish?g_ctxMTFScore:-g_ctxMTFScore;
   int minVotes=EffectiveMinMTFVotes(bullish);
   double minQuality=EffectiveMinQuality(bullish);
   if(aligned<minVotes) return false;
   if(g_ctxQualityScore<minQuality) return false;
   return true;
}

bool ReentryAllows(bool bullish)
{
   if(InpOneTradePerFVG)
      return !g_zone.traded;

   if(!InpUseControlledReentry)
      return true;

   if(g_zone.quarantined) return false;
   int maxAttempts=DirectionMaxAttempts(bullish);
   if(g_zone.attempts>=maxAttempts) return false;
   if(g_zone.attempts<=0) return true;
   if(g_zone.lastExitTime<=0) return false;
   if(!InpAllowReentryAfterProfit && g_zone.lastRealizedR>0.0) return false;

   int nextAttempt=g_zone.attempts+1;
   int cooldown=(nextAttempt>=3)?InpThirdAttemptCooldownBars:InpReentryCooldownBars;
   if(BarsSince(g_zone.lastExitTime)<cooldown) return false;

   if(nextAttempt>=3 && g_zone.lastRealizedR<InpThirdAttemptMinLastR)
      return false;

   if(InpUseQualityScoreForReentry)
   {
      double minScore=(nextAttempt>=3)?InpMinQualityScoreThirdAttempt:InpMinQualityScoreSecondAttempt;
      if(g_ctxQualityScore<minScore) return false;
   }

   if(InpRequireClosedBarRejectionOnReentry)
   {
      double threshold=(nextAttempt>=3)?InpThirdAttemptRejectionThreshold:InpReentryCloseThreshold;
      if(!ClosedBarRejectionForReentry(bullish,threshold)) return false;
   }

   if(InpUseZoneRiskBudget)
   {
      double dirMult=EffectiveDirectionRiskMultiplier(bullish);
      double projectedCap=InpMaxEffectiveRiskPct*AttemptRiskScale(nextAttempt)*dirMult;
      if(g_zone.riskSpentPct>=EffectiveZoneBudgetPct()-1e-8) return false;
      // If the remaining zone budget is too small even for broker minimum risk,
      // CalculateVolume() will reject later. This gate avoids obvious excess.
      if(projectedCap<=0.0) return false;
   }

   return true;
}

bool DirectionPauseActive(bool bullish)
{
   if(!InpUseLossStreakPause) return false;
   datetime now=TimeCurrent();
   datetime until=bullish?g_pauseUntilLong:g_pauseUntilShort;
   if(until<=0) return false;
   if(now>=until)
   {
      if(bullish){ g_pauseUntilLong=0; g_lossStreakLong=0; }
      else       { g_pauseUntilShort=0; g_lossStreakShort=0; }
      SaveLossPauseState();
      return false;
   }
   return true;
}

void RegisterExitOutcome(bool bullish,double realizedR,datetime closeTime,datetime zoneFormed)
{
   // Update only the zone that generated this trade. A newer FVG may have
   // replaced g_zone while the position was open.
   if(g_zone.valid && g_zone.formed==zoneFormed)
   {
      g_zone.lastExitTime=closeTime;
      g_zone.lastRealizedR=realizedR;
      if(realizedR<=-InpQuarantineLossR)
         g_zone.quarantined=true;
      if(InpUseControlledReentry && InpQuarantineAfterMaxAttempts &&
         g_zone.attempts>=DirectionMaxAttempts(bullish))
         g_zone.quarantined=true;
      PersistZoneIfNeeded();
   }

   if(!InpUseLossStreakPause) return;

   int streak=bullish?g_lossStreakLong:g_lossStreakShort;
   if(realizedR<=InpLossCountsBelowR)
      streak++;
   else if(realizedR>0.0)
      streak=0;

   datetime pauseUntil=0;
   if(streak>=InpMaxConsecutiveLosses && InpLossPauseBars>0)
   {
      int secs=PeriodSeconds(InpEntryTF);
      if(secs<=0) secs=60;
      pauseUntil=closeTime+(datetime)(secs*InpLossPauseBars);
   }

   if(bullish)
   {
      g_lossStreakLong=streak;
      if(pauseUntil>0) g_pauseUntilLong=pauseUntil;
   }
   else
   {
      g_lossStreakShort=streak;
      if(pauseUntil>0) g_pauseUntilShort=pauseUntil;
   }
   SaveLossPauseState();
}

void SaveLossPauseState()
{
   if(!InpPersistState) return;
   string p=GVPrefix();
   GlobalVariableSet(p+"LS_LONG",(double)g_lossStreakLong);
   GlobalVariableSet(p+"LS_SHORT",(double)g_lossStreakShort);
   GlobalVariableSet(p+"PAUSE_LONG",(double)g_pauseUntilLong);
   GlobalVariableSet(p+"PAUSE_SHORT",(double)g_pauseUntilShort);
}

void LoadLossPauseState()
{
   if(!InpPersistState) return;
   string p=GVPrefix();
   if(GlobalVariableCheck(p+"LS_LONG")) g_lossStreakLong=(int)GlobalVariableGet(p+"LS_LONG");
   if(GlobalVariableCheck(p+"LS_SHORT")) g_lossStreakShort=(int)GlobalVariableGet(p+"LS_SHORT");
   if(GlobalVariableCheck(p+"PAUSE_LONG")) g_pauseUntilLong=(datetime)GlobalVariableGet(p+"PAUSE_LONG");
   if(GlobalVariableCheck(p+"PAUSE_SHORT")) g_pauseUntilShort=(datetime)GlobalVariableGet(p+"PAUSE_SHORT");
}

//+------------------------------------------------------------------+
//| Entry                                                              |
//+------------------------------------------------------------------+
void TryFVGEntry()
{
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(bid<=0 || ask<=0) return;

   double midpoint=(g_zone.low+g_zone.high)/2.0;

   if(g_zone.bullish)
   {
      if(!InpAllowLong) return;
      if(ask < g_zone.low || ask > g_zone.high) return;
      if(InpRequireMidpoint && ask > midpoint) return;
      if(InpRequireRejection && !BullishRejection()) return;
      if(OpenTrade(true,g_zone))
      {
         g_zone.traded=true;
         PersistZoneIfNeeded();
      }
   }
   else
   {
      if(!InpAllowShort) return;
      if(bid < g_zone.low || bid > g_zone.high) return;
      if(InpRequireMidpoint && bid < midpoint) return;
      if(InpRequireRejection && !BearishRejection()) return;
      if(OpenTrade(false,g_zone))
      {
         g_zone.traded=true;
         PersistZoneIfNeeded();
      }
   }
}

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

bool BiasAllows(bool bullish)
{
   if(!InpUseBiasFilter) return true;
   double f[],s[];
   ArrayResize(f,2); ArrayResize(s,2);
   ArraySetAsSeries(f,true); ArraySetAsSeries(s,true);
   if(CopyBuffer(hFastEMA,0,0,2,f)<2) return false;
   if(CopyBuffer(hSlowEMA,0,0,2,s)<2) return false;
   // Closed-bar bias only: index 1 is the last completed bar.
   return bullish ? f[1]>s[1] : f[1]<s[1];
}

bool RegimeAllows(bool bullish)
{
   g_ctxRegimeFast=0.0;
   g_ctxRegimeSlow=0.0;
   g_ctxRegimeADX=0.0;
   g_ctxRegimeSlope=0.0;

   double f[],s[],a[];
   ArrayResize(f,3); ArrayResize(s,3); ArrayResize(a,2);
   ArraySetAsSeries(f,true); ArraySetAsSeries(s,true); ArraySetAsSeries(a,true);
   if(CopyBuffer(hRegimeFastEMA,0,0,3,f)<3) return false;
   if(CopyBuffer(hRegimeSlowEMA,0,0,3,s)<3) return false;
   if(CopyBuffer(hRegimeADX,0,0,2,a)<2) return false;

   g_ctxRegimeFast=f[1];
   g_ctxRegimeSlow=s[1];
   g_ctxRegimeADX=a[1];
   g_ctxRegimeSlope=f[1]-f[2];

   if(InpUseRegimeFilter)
   {
      bool aligned=bullish ? (f[1]>s[1]) : (f[1]<s[1]);
      if(!aligned) return false;

      if(InpRequireRegimeSlope)
      {
         bool slopeOK=bullish ? (f[1]>f[2]) : (f[1]<f[2]);
         if(!slopeOK) return false;
      }

      if(InpRequirePriceSide)
      {
         double c=iClose(_Symbol,InpRegimeTF,1);
         if(c<=0.0) return false;
         if(bullish && c<=f[1]) return false;
         if(!bullish && c>=f[1]) return false;
      }
   }

   if(InpUseADXFilter && g_ctxRegimeADX < InpMinADX)
      return false;

   return true;
}


int ReadTrendVote(int fastHandle,int slowHandle)
{
   double f[],s[];
   ArrayResize(f,3);
   ArrayResize(s,3);
   ArraySetAsSeries(f,true);
   ArraySetAsSeries(s,true);

   if(CopyBuffer(fastHandle,0,0,3,f)<3) return 0;
   if(CopyBuffer(slowHandle,0,0,3,s)<3) return 0;

   if(f[1]>s[1] && f[1]>f[2]) return 1;
   if(f[1]<s[1] && f[1]<f[2]) return -1;
   return 0;
}

bool MTFScoreAllows(bool bullish)
{
   int m5=ReadTrendVote(hM5Fast,hM5Slow);
   int m15=ReadTrendVote(hM15Fast,hM15Slow);
   int h1=ReadTrendVote(hH1Fast,hH1Slow);
   g_ctxMTFScore=m5+m15+h1;

   if(!InpUseMTFScoreFilter) return true;
   if(InpMinMTFScore<=0) return true;

   if(bullish) return g_ctxMTFScore>=InpMinMTFScore;
   return g_ctxMTFScore<=-InpMinMTFScore;
}

double ComputeEntryQualityScore(bool bullish)
{
   double score=0.0;

   // FVG geometry and displacement: 0-60 points.
   if(g_zone.gapATR>=InpMinFVG_ATR) score+=10.0;
   if(g_zone.gapATR>=0.25) score+=5.0;
   if(g_zone.gapATR>=0.40) score+=5.0;

   if(g_zone.bodyATR>=InpMinBody_ATR) score+=10.0;
   if(g_zone.bodyATR>=0.80) score+=5.0;
   if(g_zone.bodyATR>=1.20) score+=5.0;

   if(g_zone.bodyRatio>=InpMinBodyRatio) score+=10.0;
   if(g_zone.bodyRatio>=0.70) score+=5.0;
   if(g_zone.bodyRatio>=0.80) score+=5.0;

   // MTF alignment: 0-15.
   int alignedVotes=bullish?g_ctxMTFScore:-g_ctxMTFScore;
   if(alignedVotes<0) alignedVotes=0;
   score+=5.0*(double)alignedVotes;

   // Regime state: 0-10.
   bool regimeAligned=bullish?(g_ctxRegimeFast>g_ctxRegimeSlow):(g_ctxRegimeFast<g_ctxRegimeSlow);
   bool slopeAligned=bullish?(g_ctxRegimeSlope>0.0):(g_ctxRegimeSlope<0.0);
   if(regimeAligned) score+=5.0;
   if(slopeAligned) score+=5.0;

   // Trend strength: 0-10.
   if(g_ctxRegimeADX>=18.0) score+=5.0;
   if(g_ctxRegimeADX>=25.0) score+=5.0;

   // Volatility and spread quality: 0-10.
   if(g_ctxATRRatio>=0.60 && g_ctxATRRatio<=1.50) score+=5.0;
   if(g_ctxSpreadRatio<=1.50) score+=5.0;

   if(score>100.0) score=100.0;
   if(score<0.0) score=0.0;
   return score;
}

void UpdateSpreadState()
{
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(bid<=0.0 || ask<=0.0 || p<=0.0) return;

   double spread=(ask-bid)/p;
   if(spread<0.0) return;

   double alpha=2.0/((double)InpSpreadEMAWarmupTicks+1.0);
   if(g_spreadSamples<=0 || g_spreadEMA<=0.0)
      g_spreadEMA=spread;
   else
      g_spreadEMA=g_spreadEMA+alpha*(spread-g_spreadEMA);

   g_spreadSamples++;
   g_ctxSpreadRatio=(g_spreadEMA>0.0)?spread/g_spreadEMA:1.0;
}

bool MarketQualityAllows()
{
   g_ctxATRRatio=0.0;
   g_ctxShockRangeATR=0.0;

   int need=InpVolatilityLookback+2;
   double atr[];
   ArraySetAsSeries(atr,true);
   if(CopyBuffer(hATR,0,0,need,atr)<need) return false;

   double currentATR=atr[1];
   if(currentATR<=0.0) return false;

   double sum=0.0;
   int count=0;
   for(int i=2;i<need;i++)
   {
      if(atr[i]>0.0){ sum+=atr[i]; count++; }
   }
   if(count<=0) return false;

   double meanATR=sum/(double)count;
   if(meanATR<=0.0) return false;
   g_ctxATRRatio=currentATR/meanATR;

   int barsNeed=InpShockCooldownBars+2;
   if(barsNeed<3) barsNeed=3;
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,barsNeed,r)<barsNeed) return false;

   double maxRecentRangeATR=0.0;
   int shockBars=InpShockCooldownBars;
   if(shockBars>barsNeed-1) shockBars=barsNeed-1;
   for(int i=1;i<=shockBars;i++)
   {
      double range=r[i].high-r[i].low;
      if(range<0.0) continue;
      double ratio=range/currentATR;
      if(ratio>maxRecentRangeATR) maxRecentRangeATR=ratio;
   }
   g_ctxShockRangeATR=maxRecentRangeATR;

   if(InpUseVolatilityFilter)
   {
      if(InpMinATRRatio>0.0 && g_ctxATRRatio<InpMinATRRatio) return false;
      if(InpMaxATRRatio>0.0 && g_ctxATRRatio>InpMaxATRRatio) return false;
   }

   if(InpUseShockGuard && g_ctxShockRangeATR>InpMaxClosedBarRangeATR)
      return false;

   return true;
}


//+------------------------------------------------------------------+
//| ASTRA deterministic intelligence                                  |
//+------------------------------------------------------------------+
bool IsTesterEnvironment()
{
   return (bool)MQLInfoInteger(MQL_TESTER);
}

string ClassifyASTRARegime(bool bullish)
{
   if(!InpUseASTRARegimeClassifier) return "DISABLED";

   if(g_ctxShockRangeATR>=2.20) return "SHOCK";
   if(g_ctxATRRatio>0.0 && g_ctxATRRatio<0.65) return "COMPRESSION";
   if(g_ctxATRRatio>=1.35) return "EXPANSION";

   if(g_ctxRegimeADX>=25.0)
   {
      if(g_ctxMTFScore>=2 && g_ctxRegimeFast>g_ctxRegimeSlow) return "TREND_UP";
      if(g_ctxMTFScore<=-2 && g_ctxRegimeFast<g_ctxRegimeSlow) return "TREND_DOWN";
   }

   if(MathAbs((double)g_ctxMTFScore)<=1.0 && g_ctxRegimeADX<20.0) return "RANGE";
   return "TRANSITION";
}

double ComputeContradictionScore(bool bullish)
{
   if(!InpUseContradictionEngine) return 0.0;

   double score=0.0;
   int aligned=bullish?g_ctxMTFScore:-g_ctxMTFScore;
   bool regimeAligned=bullish?(g_ctxRegimeFast>g_ctxRegimeSlow):(g_ctxRegimeFast<g_ctxRegimeSlow);
   bool slopeAligned=bullish?(g_ctxRegimeSlope>0.0):(g_ctxRegimeSlope<0.0);

   if(aligned<0) score+=20.0;
   if(aligned<=-2) score+=10.0;
   if(!regimeAligned) score+=12.0;
   if(!slopeAligned) score+=8.0;

   if(g_ctxRegimeADX>0.0 && g_ctxRegimeADX<15.0) score+=5.0;
   if(g_ctxATRRatio>0.0 && (g_ctxATRRatio<0.45 || g_ctxATRRatio>1.80)) score+=10.0;
   if(g_ctxShockRangeATR>=1.80) score+=12.0;
   if(g_ctxSpreadRatio>=2.00) score+=12.0;

   double minQuality=EffectiveMinQuality(bullish);
   if(g_ctxQualityScore<minQuality+5.0) score+=7.0;

   int nextAttempt=g_zone.attempts+1;
   if(nextAttempt==2) score+=4.0;
   if(nextAttempt>=3) score+=8.0;

   if(g_ctxPeakDrawdownPct>=3.5) score+=5.0;
   if(g_zone.gapATR<0.20) score+=4.0;
   if(g_zone.bodyRatio<0.65) score+=4.0;

   if(score>100.0) score=100.0;
   return score;
}

double ContradictionRiskScale(double score)
{
   if(!InpUseContradictionEngine) return 1.0;
   if(score<=InpContradictionRiskStart) return 1.0;
   if(score>=InpContradictionHardVeto) return 0.0;

   double span=InpContradictionHardVeto-InpContradictionRiskStart;
   if(span<=0.0) return InpContradictionMinRiskScale;
   double p=(score-InpContradictionRiskStart)/span;
   double scale=1.0-p*(1.0-InpContradictionMinRiskScale);
   if(scale<InpContradictionMinRiskScale) scale=InpContradictionMinRiskScale;
   if(scale>1.0) scale=1.0;
   return scale;
}

double SimilarityDistance(const ASTRAHistorySample &a,bool bullish)
{
   if(a.bullish!=bullish) return 999.0;

   double d=0.0;
   d+=1.6*MathMin(MathAbs(a.gapATR-g_zone.gapATR)/0.50,2.0);
   d+=1.3*MathMin(MathAbs(a.bodyATR-g_zone.bodyATR)/1.20,2.0);
   d+=1.0*MathMin(MathAbs(a.bodyRatio-g_zone.bodyRatio)/0.30,2.0);
   d+=1.2*MathMin(MathAbs(a.atrRatio-g_ctxATRRatio)/0.80,2.0);
   d+=1.0*MathMin(MathAbs(a.qualityScore-g_ctxQualityScore)/35.0,2.0);
   d+=1.2*MathMin(MathAbs((double)(a.mtfScore-g_ctxMTFScore))/3.0,2.0);
   d+=0.5*MathMin(MathAbs((double)(a.zoneAttempt-(g_zone.attempts+1)))/2.0,1.0);
   return d;
}

double ComputeSimilarityScore(bool bullish,int &usedSamples)
{
   usedSamples=0;
   if(!InpUseHistoricalSimilarity || g_similarityCount<InpSimilarityMinSamples)
      return 50.0;

   int k=InpSimilarityNeighbors;
   if(k>g_similarityCount) k=g_similarityCount;
   if(k<1) return 50.0;

   double bestDist[];
   int bestIdx[];
   ArrayResize(bestDist,k);
   ArrayResize(bestIdx,k);
   for(int i=0;i<k;i++){ bestDist[i]=1.0e9; bestIdx[i]=-1; }

   int capacity=ArraySize(g_similarity);
   for(int n=0;n<g_similarityCount && n<capacity;n++)
   {
      double d=SimilarityDistance(g_similarity[n],bullish);
      if(d>=999.0) continue;

      for(int pos=0;pos<k;pos++)
      {
         if(d<bestDist[pos])
         {
            for(int j=k-1;j>pos;j--)
            {
               bestDist[j]=bestDist[j-1];
               bestIdx[j]=bestIdx[j-1];
            }
            bestDist[pos]=d;
            bestIdx[pos]=n;
            break;
         }
      }
   }

   double sumW=0.0,sumR=0.0,wins=0.0;
   for(int i=0;i<k;i++)
   {
      if(bestIdx[i]<0) continue;
      double w=MathExp(-bestDist[i]);
      if(w<=0.0) continue;
      double r=g_similarity[bestIdx[i]].realizedR;
      sumW+=w;
      sumR+=w*r;
      if(r>0.0) wins+=w;
      usedSamples++;
   }

   if(usedSamples<5 || sumW<=0.0)
      return 50.0;

   double avgR=sumR/sumW;
   if(avgR>2.5) avgR=2.5;
   if(avgR<-2.5) avgR=-2.5;
   double winRate=wins/sumW;

   double score=50.0 + 12.0*avgR + 20.0*(winRate-0.50);
   if(score>100.0) score=100.0;
   if(score<0.0) score=0.0;
   return score;
}

double SimilarityRiskScale(double score,int samples)
{
   if(!InpUseHistoricalSimilarity || samples<InpSimilarityMinSamples) return 1.0;
   if(!InpUseProfileOverrides || InpResearchMode==ASTRA_MODE_CUSTOM)
   {
      if(score>=InpSimilarityHighScore) return 1.0;
      if(score>=InpSimilarityLowScore) return InpSimilarityMidRiskScale;
      return InpSimilarityLowRiskScale;
   }
   if(InpResearchMode==ASTRA_MODE_EDGE)
   {
      if(score>=60.0) return 1.0;
      if(score>=40.0) return 0.95;
      return 0.88;
   }
   if(InpResearchMode==ASTRA_MODE_GROWTH)
   {
      if(score>=62.0) return 1.0;
      if(score>=44.0) return 0.94;
      return 0.84;
   }
   if(score>=68.0) return 1.0;
   if(score>=50.0) return 0.88;
   return 0.72;
}

void UpdateASTRAContext(bool bullish)
{
   g_ctxASTRARegime=ClassifyASTRARegime(bullish);
   g_ctxContradictionScore=ComputeContradictionScore(bullish);
   g_ctxContradictionRiskScale=ContradictionRiskScale(g_ctxContradictionScore);
   g_ctxSimilarityScore=ComputeSimilarityScore(bullish,g_ctxSimilaritySamples);
   g_ctxSimilarityRiskScale=SimilarityRiskScale(g_ctxSimilarityScore,g_ctxSimilaritySamples);
   g_ctxAIVerdict="BYPASS";
   g_ctxAIRiskScale=1.0;
}

void RecordSimilarityOutcome(bool bullish,double realizedR)
{
   if(!InpUseHistoricalSimilarity) return;
   int capacity=ArraySize(g_similarity);
   if(capacity<=0) return;

   int idx=g_similarityHead;
   if(idx<0 || idx>=capacity) idx=0;

   g_similarity[idx].bullish=bullish;
   g_similarity[idx].gapATR=g_track.zoneGapATR;
   g_similarity[idx].bodyATR=g_track.zoneBodyATR;
   g_similarity[idx].bodyRatio=g_track.zoneBodyRatio;
   g_similarity[idx].atrRatio=g_track.atrRatio;
   g_similarity[idx].qualityScore=g_track.qualityScore;
   g_similarity[idx].mtfScore=g_track.mtfScore;
   g_similarity[idx].zoneAttempt=g_track.zoneAttempt;
   g_similarity[idx].realizedR=realizedR;

   g_similarityHead=(idx+1)%capacity;
   if(g_similarityCount<capacity) g_similarityCount++;

   if(!IsTesterEnvironment())
      AppendSimilaritySampleToFile(g_similarity[idx]);
}

void AppendSimilaritySampleToFile(const ASTRAHistorySample &x)
{
   if(!InpLoadSimilarityHistoryLive) return;
   int h=FileOpen(InpSimilarityMemoryFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',');
   if(h==INVALID_HANDLE) return;
   FileSeek(h,0,SEEK_END);
   FileWrite(h,(x.bullish?"BUY":"SELL"),
             DoubleToString(x.gapATR,5),DoubleToString(x.bodyATR,5),
             DoubleToString(x.bodyRatio,5),DoubleToString(x.atrRatio,5),
             DoubleToString(x.qualityScore,2),x.mtfScore,x.zoneAttempt,
             DoubleToString(x.realizedR,5));
   FileClose(h);
}

void LoadSimilarityHistory()
{
   int h=FileOpen(InpSimilarityMemoryFile,FILE_READ|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',');
   if(h==INVALID_HANDLE) return;

   int capacity=ArraySize(g_similarity);
   while(!FileIsEnding(h) && capacity>0)
   {
      string dir=FileReadString(h);
      if(dir=="") break;

      ASTRAHistorySample x;
      x.bullish=(dir=="BUY");
      x.gapATR=StringToDouble(FileReadString(h));
      x.bodyATR=StringToDouble(FileReadString(h));
      x.bodyRatio=StringToDouble(FileReadString(h));
      x.atrRatio=StringToDouble(FileReadString(h));
      x.qualityScore=StringToDouble(FileReadString(h));
      x.mtfScore=(int)StringToInteger(FileReadString(h));
      x.zoneAttempt=(int)StringToInteger(FileReadString(h));
      x.realizedR=StringToDouble(FileReadString(h));

      g_similarity[g_similarityHead]=x;
      g_similarityHead=(g_similarityHead+1)%capacity;
      if(g_similarityCount<capacity) g_similarityCount++;
   }
   FileClose(h);
}

double ProtectMinimumLotSoftScaling(double entry,double sl,bool bullish,double coreScale,double astraScale)
{
   if(!InpASTRAProtectMinimumLot || astraScale>=0.999 || coreScale<=0.0) return astraScale;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double sizingBase=EffectiveAutoCompound()?equity:InpCompoundingBaseBalance;
   double minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(equity<=0.0 || sizingBase<=0.0 || minLot<=0.0) return astraScale;

   double lossOneLot=0.0;
   ENUM_ORDER_TYPE type=bullish?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,lossOneLot)) return astraScale;
   lossOneLot=MathAbs(lossOneLot);
   if(lossOneLot<=0.0) return astraScale;

   double coreMoney=sizingBase*EffectiveRiskPercent()/100.0*coreScale;
   double rawCore=coreMoney/lossOneLot;
   double rawASTRA=coreMoney*astraScale/lossOneLot;

   if(rawCore>=minLot && rawASTRA<minLot)
   {
      bool materiallyWeak=(g_ctxContradictionScore>=InpMinLotGateContradiction);
      if(g_ctxSimilaritySamples>=InpSimilarityMinSamples && g_ctxSimilarityScore<InpMinLotGateSimilarity)
         materiallyWeak=true;
      if(InpUseMinLotDecisionGate && materiallyWeak)
      {
         if(InpCountResearchDecisions) g_researchMinLotSkip++;
         return 0.0;
      }
      return 1.0;
   }
   return astraScale;
}

string JsonEscape(string v)
{
   StringReplace(v,"\\","\\\\");
   StringReplace(v,"\"","\\\"");
   StringReplace(v,"\r"," ");
   StringReplace(v,"\n"," ");
   return v;
}

string BuildASTRAMarketPacket(bool bullish,double entry,double sl,double tp,int attempt)
{
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double o1=iOpen(_Symbol,InpEntryTF,1);
   double h1=iHigh(_Symbol,InpEntryTF,1);
   double l1=iLow(_Symbol,InpEntryTF,1);
   double c1=iClose(_Symbol,InpEntryTF,1);

   string packet="{";
   packet+="\"schema\":\"ASTRA_MARKET_PACKET_V1\",";
   packet+="\"symbol\":\""+JsonEscape(_Symbol)+"\",";
   packet+="\"time\":\""+TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS)+"\",";
   packet+="\"direction\":\""+(bullish?"BUY":"SELL")+"\",";
   packet+="\"bid\":"+DoubleToString(bid,_Digits)+",";
   packet+="\"ask\":"+DoubleToString(ask,_Digits)+",";
   packet+="\"last_closed_bar\":{\"open\":"+DoubleToString(o1,_Digits)+
           ",\"high\":"+DoubleToString(h1,_Digits)+
           ",\"low\":"+DoubleToString(l1,_Digits)+
           ",\"close\":"+DoubleToString(c1,_Digits)+"},";
   packet+="\"entry\":"+DoubleToString(entry,_Digits)+",";
   packet+="\"sl\":"+DoubleToString(sl,_Digits)+",";
   packet+="\"tp\":"+DoubleToString(tp,_Digits)+",";
   packet+="\"attempt\":"+IntegerToString(attempt)+",";
   packet+="\"session\":\""+ResearchSessionTag(TimeCurrent())+"\",";
   packet+="\"regime\":\""+g_ctxASTRARegime+"\",";
   packet+="\"quality\":"+DoubleToString(g_ctxQualityScore,2)+",";
   packet+="\"contradiction\":"+DoubleToString(g_ctxContradictionScore,2)+",";
   packet+="\"similarity\":"+DoubleToString(g_ctxSimilarityScore,2)+",";
   packet+="\"similarity_samples\":"+IntegerToString(g_ctxSimilaritySamples)+",";
   packet+="\"mtf_score\":"+IntegerToString(g_ctxMTFScore)+",";
   packet+="\"regime_adx\":"+DoubleToString(g_ctxRegimeADX,2)+",";
   packet+="\"atr_ratio\":"+DoubleToString(g_ctxATRRatio,4)+",";
   packet+="\"shock_range_atr\":"+DoubleToString(g_ctxShockRangeATR,4)+",";
   packet+="\"spread_ratio\":"+DoubleToString(g_ctxSpreadRatio,4)+",";
   packet+="\"peak_drawdown_pct\":"+DoubleToString(g_ctxPeakDrawdownPct,3)+",";
   packet+="\"fvg\":{\"low\":"+DoubleToString(g_zone.low,_Digits)+
           ",\"high\":"+DoubleToString(g_zone.high,_Digits)+
           ",\"gap_atr\":"+DoubleToString(g_zone.gapATR,4)+
           ",\"body_atr\":"+DoubleToString(g_zone.bodyATR,4)+
           ",\"body_ratio\":"+DoubleToString(g_zone.bodyRatio,4)+"}";
   packet+="}";
   return packet;
}

void ExportASTRAPacket(string packet)
{
   if(!InpExportASTRAMarketPackets) return;
   int h=FileOpen(InpASTRAPacketFile,FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h==INVALID_HANDLE) return;
   FileSeek(h,0,SEEK_END);
   FileWriteString(h,packet+"\r\n");
   FileClose(h);
}

bool ExternalAIAllows(bool bullish,double entry,double sl,double tp,int attempt,double &riskScale,string &verdict)
{
   riskScale=1.0;
   verdict="BYPASS";

   string packet=BuildASTRAMarketPacket(bullish,entry,sl,tp,attempt);
   ExportASTRAPacket(packet);

   if(!InpUseExternalAI) return true;
   if(InpAIDisableInTester && IsTesterEnvironment()) return true;
   if(InpAIOnlyFirstAttempt && attempt>1) return true;
   if(g_ctxQualityScore<InpAIMinQualityToCall) return true;
   if(InpAIApiKey=="" || InpAIModel=="" || InpAIEndpoint=="")
   {
      verdict="NO_CONFIG";
      return !InpAIFailClosed;
   }
   if(g_aiCallsToday>=InpAIMaxCallsDay)
   {
      verdict="CALL_LIMIT";
      return true;
   }
   if(InpAIMinSecondsBetweenCalls>0 && g_lastAICallTime>0 &&
      (TimeCurrent()-g_lastAICallTime)<InpAIMinSecondsBetweenCalls)
   {
      verdict="THROTTLED";
      return true;
   }

   string systemText=
      "You are ASTRA Critic. Evaluate only the supplied deterministic market packet. "
      "Return exactly one leading verdict token: ALLOW, DOWNGRADE, or VETO. "
      "ALLOW means no material contradiction. DOWNGRADE means setup remains valid but context is weaker. "
      "VETO means a concrete contradiction makes this setup unsafe. Do not invent prices or indicators.";

   string userText="Market packet: "+packet;
   string body="{\"model\":\""+JsonEscape(InpAIModel)+"\",\"temperature\":0.1,\"max_tokens\":80,"
               "\"messages\":[{\"role\":\"system\",\"content\":\""+JsonEscape(systemText)+"\"},"
               "{\"role\":\"user\",\"content\":\""+JsonEscape(userText)+"\"}]}";

   string headers="Content-Type: application/json\r\nAuthorization: Bearer "+InpAIApiKey+"\r\n";
   char data[];
   char result[];
   string resultHeaders="";
   int copied=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
   if(copied>0)
      ArrayResize(data,copied-1); // remove terminal null from HTTP body

   ResetLastError();
   int code=WebRequest("POST",InpAIEndpoint,headers,InpAITimeoutMs,data,result,resultHeaders);
   g_lastAICallTime=TimeCurrent();
   g_aiCallsToday++;

   if(code<200 || code>=300)
   {
      verdict="ERROR";
      if(InpVerboseLog)
         Print("ASTRA400 AI request failed HTTP=",code," err=",GetLastError());
      return !InpAIFailClosed;
   }

   string response=CharArrayToString(result,0,-1,CP_UTF8);
   if(StringFind(response,"VETO")>=0)
   {
      verdict="VETO";
      return !InpAIHardVeto;
   }
   if(StringFind(response,"DOWNGRADE")>=0)
   {
      verdict="DOWNGRADE";
      riskScale=InpAIDowngradeRiskScale;
      return true;
   }
   if(StringFind(response,"ALLOW")>=0)
   {
      verdict="ALLOW";
      return true;
   }

   verdict="UNPARSED";
   return !InpAIFailClosed;
}

bool SessionQualityAllows(datetime t)
{
   if(!InpUseSessionQualityFilter) return true;
   string tag=ResearchSessionTag(t);
   if(tag=="ASIA") return InpAllowAsia;
   if(tag=="LONDON") return InpAllowLondon;
   if(tag=="LONDON_NY_OVERLAP") return InpAllowLondonNYOverlap;
   if(tag=="NEW_YORK") return InpAllowNewYork;
   return InpAllowOtherSession;
}

bool OpenTrade(bool bullish,const FVGZone &z)
{
   double atr=GetATR();
   if(atr<=0.0) return false;

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(point<=0.0 || bid<=0.0 || ask<=0.0) return false;

   double requestedEntry=bullish?ask:bid;
   double sl=0.0,tp=0.0;
   if(bullish)
   {
      sl=z.low-atr*InpSL_ATR_Buffer;
      double risk=requestedEntry-sl;
      if(risk<=0.0 || risk>atr*InpMaxSL_ATR) return false;
      tp=requestedEntry+risk*InpRewardRisk;
   }
   else
   {
      sl=z.high+atr*InpSL_ATR_Buffer;
      double risk=sl-requestedEntry;
      if(risk<=0.0 || risk>atr*InpMaxSL_ATR) return false;
      tp=requestedEntry-risk*InpRewardRisk;
   }

   sl=NormalizePrice(sl);
   tp=NormalizePrice(tp);
   if(!StopsAreValid(requestedEntry,sl,tp,bullish)) return false;

   int nextAttempt=g_zone.attempts+1;
   double attemptScale=AttemptRiskScale(nextAttempt);
   double directionScale=EffectiveDirectionRiskMultiplier(bullish);
   double qualityScale=QualityRiskScale(g_ctxQualityScore);
   double ddScale=g_ctxDDRiskScale;

   // ASTRA deterministic overlays are soft by default: risk scaling, not blind rejection.
   double astraDeterministicScale=g_ctxContradictionRiskScale*g_ctxSimilarityRiskScale;

   // Optional external AI is LIVE-only by default and never required for Strategy Tester.
   double aiScale=1.0;
   string aiVerdict="BYPASS";
   if(!ExternalAIAllows(bullish,requestedEntry,sl,tp,nextAttempt,aiScale,aiVerdict))
      return false;
   g_ctxAIRiskScale=aiScale;
   g_ctxAIVerdict=aiVerdict;

   double coreScale=attemptScale*directionScale*qualityScale*ddScale;
   double astraScale=astraDeterministicScale*aiScale;
   astraScale=ProtectMinimumLotSoftScaling(requestedEntry,sl,bullish,coreScale,astraScale);
   double combinedScale=coreScale*astraScale;
   if(combinedScale<=0.0) return false;

   double maxRiskCapPct=EffectiveHardRiskCapPct()*combinedScale;
   if(InpUseZoneRiskBudget)
   {
      double remaining=EffectiveZoneBudgetPct()-g_zone.riskSpentPct;
      if(remaining<=0.0) return false;
      maxRiskCapPct=MathMin(maxRiskCapPct,remaining);
   }
   if(maxRiskCapPct<=0.0) return false;

   double rawVolume=0.0, plannedRisk=0.0, effectiveRisk=0.0, effectiveRiskPct=0.0;
   double volume=CalculateVolume(requestedEntry,sl,bullish,combinedScale,maxRiskCapPct,
                                 rawVolume,plannedRisk,effectiveRisk,effectiveRiskPct);
   if(volume<=0.0) return false;

   if(!MarginPreflight(bullish,volume,requestedEntry))
   {
      if(InpVerboseLog) Print("ASTRA400 margin guard rejected entry");
      return false;
   }

   double spreadPoints=(ask-bid)/point;
   bool ok=bullish ? trade.Buy(volume,_Symbol,0,sl,tp,"ASTRA V4 Buy")
                   : trade.Sell(volume,_Symbol,0,sl,tp,"ASTRA V4 Sell");
   if(!ok)
   {
      Print("ASTRA400 trade failed: ",trade.ResultRetcodeDescription());
      return false;
   }

   uint rc=trade.ResultRetcode();
   if(rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL && rc!=TRADE_RETCODE_PLACED)
   {
      Print("ASTRA400 trade rejected: ",trade.ResultRetcodeDescription());
      return false;
   }

   g_tradesToday++;
   g_lastEntryTime=TimeCurrent();

   // Build telemetry from actual position fill where possible.
   ulong ticket=GetOurPositionTicket();
   double actualEntry=requestedEntry;
   double actualVolume=volume;
   if(ticket>0 && PositionSelectByTicket(ticket))
   {
      actualEntry=PositionGetDouble(POSITION_PRICE_OPEN);
      actualVolume=PositionGetDouble(POSITION_VOLUME);
   }

   double actualRiskMoney=0.0;
   ENUM_ORDER_TYPE orderType=bullish?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(orderType,_Symbol,actualVolume,actualEntry,sl,actualRiskMoney))
      actualRiskMoney=-effectiveRisk;
   actualRiskMoney=MathAbs(actualRiskMoney);

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double actualRiskPct=(equity>0.0)?actualRiskMoney/equity*100.0:0.0;
   double slipPts=bullish?(actualEntry-requestedEntry)/point:(requestedEntry-actualEntry)/point;

   g_zone.attempts++;
   g_zone.lastEntryTime=g_lastEntryTime;
   g_zone.traded=true;
   g_zone.riskSpentPct+=actualRiskPct;
   PersistZoneIfNeeded();

   g_track.active=true;
   g_track.positionTicket=ticket;
   g_track.positionType=bullish?POSITION_TYPE_BUY:POSITION_TYPE_SELL;
   g_track.entryTime=TimeCurrent();
   g_track.requestedEntry=requestedEntry;
   g_track.actualEntry=actualEntry;
   g_track.initialSL=sl;
   g_track.originalTP=tp;
   g_track.initialRiskPrice=MathAbs(actualEntry-sl);
   g_track.plannedRiskMoney=plannedRisk;
   g_track.effectiveRiskMoney=actualRiskMoney;
   g_track.effectiveRiskPct=actualRiskPct;
   g_track.requestedRawVolume=rawVolume;
   g_track.volume=actualVolume;
   g_track.maxMFE_R=0.0;
   g_track.maxMAE_R=0.0;
   g_track.entrySlippagePoints=slipPts;
   g_track.entrySpreadPoints=spreadPoints;
   g_track.sessionTag=ResearchSessionTag(TimeCurrent());
   g_track.zoneFormed=z.formed;
   g_track.zoneLow=z.low;
   g_track.zoneHigh=z.high;
   g_track.bullishZone=z.bullish;
   g_track.zoneGapATR=z.gapATR;
   g_track.zoneBodyATR=z.bodyATR;
   g_track.zoneBodyRatio=z.bodyRatio;
   g_track.regimeFastEMA=g_ctxRegimeFast;
   g_track.regimeSlowEMA=g_ctxRegimeSlow;
   g_track.regimeADX=g_ctxRegimeADX;
   g_track.regimeSlope=g_ctxRegimeSlope;
   g_track.atrRatio=g_ctxATRRatio;
   g_track.shockRangeATR=g_ctxShockRangeATR;
   g_track.zoneAttempt=g_zone.attempts;
   g_track.reentry=(g_zone.attempts>1);
   g_track.lossStreakAtEntry=bullish?g_lossStreakLong:g_lossStreakShort;
   g_track.mtfScore=g_ctxMTFScore;
   g_track.qualityScore=g_ctxQualityScore;
   g_track.spreadRatio=g_ctxSpreadRatio;
   g_track.zoneRiskSpentPct=g_zone.riskSpentPct;
   g_track.attemptRiskScale=combinedScale;
   g_track.directionRiskScale=directionScale;
   g_track.qualityRiskScale=qualityScale;
   g_track.ddRiskScale=ddScale;
   g_track.peakDrawdownPct=g_ctxPeakDrawdownPct;
   g_track.alignedMTFVotes=bullish?g_ctxMTFScore:-g_ctxMTFScore;
   g_track.astraRegime=g_ctxASTRARegime;
   g_track.contradictionScore=g_ctxContradictionScore;
   g_track.contradictionRiskScale=g_ctxContradictionRiskScale;
   g_track.similarityScore=g_ctxSimilarityScore;
   g_track.similaritySamples=g_ctxSimilaritySamples;
   g_track.similarityRiskScale=g_ctxSimilarityRiskScale;
   g_track.aiVerdict=g_ctxAIVerdict;
   g_track.aiRiskScale=g_ctxAIRiskScale;

   if(InpMaxEntrySlippagePoints>0 && slipPts>(double)InpMaxEntrySlippagePoints)
      Print("ASTRA400 WARNING: entry slippage exceeded research threshold: ",DoubleToString(slipPts,1)," pts");

   if(InpCountResearchDecisions) g_researchOpened++;

   if(InpVerboseLog)
      Print("ASTRA400 entry | mode=",ResearchModeName()," attempt=",g_zone.attempts,
            " quality=",DoubleToString(g_ctxQualityScore,1),
            " mtf=",g_ctxMTFScore,
            " scale=",DoubleToString(combinedScale,2),
            " vol=",DoubleToString(actualVolume,2),
            " risk%=",DoubleToString(actualRiskPct,3),
            " zoneRisk%=",DoubleToString(g_zone.riskSpentPct,3),
            " spreadRatio=",DoubleToString(g_ctxSpreadRatio,2),
            " regime=",g_ctxASTRARegime,
            " contradiction=",DoubleToString(g_ctxContradictionScore,1),
            " similarity=",DoubleToString(g_ctxSimilarityScore,1),
            " ai=",g_ctxAIVerdict);

   return true;
}

//+------------------------------------------------------------------+
//| Position sizing                                                   |
//+------------------------------------------------------------------+
double CalculateVolume(double entry,double sl,bool bullish,
                       double riskScale,double maxRiskCapPct,
                       double &rawVolume,double &plannedRiskMoney,
                       double &effectiveRiskMoney,double &effectiveRiskPct)
{
   rawVolume=0.0;
   plannedRiskMoney=0.0;
   effectiveRiskMoney=0.0;
   effectiveRiskPct=0.0;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0 || riskScale<=0.0 || maxRiskCapPct<=0.0) return 0.0;

   double sizingBase=EffectiveAutoCompound()?equity:InpCompoundingBaseBalance;
   if(sizingBase<=0.0) sizingBase=equity;

   plannedRiskMoney=sizingBase*EffectiveRiskPercent()/100.0*riskScale;
   if(plannedRiskMoney<=0.0) return 0.0;

   double minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double brokerMaxLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minLot<=0.0 || brokerMaxLot<=0.0 || step<=0.0) return 0.0;

   double userMaxLot=(InpMaxLots>0.0)?MathMin(InpMaxLots,brokerMaxLot):brokerMaxLot;

   double lossOneLot=0.0;
   ENUM_ORDER_TYPE type=bullish?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,lossOneLot)) return 0.0;
   lossOneLot=MathAbs(lossOneLot);
   if(lossOneLot<=0.0) return 0.0;

   rawVolume=plannedRiskMoney/lossOneLot;
   double volume=MathFloor(rawVolume/step)*step;
   if(volume>userMaxLot) volume=userMaxLot;
   volume=NormalizeVolume(volume);
   if(volume<minLot) return 0.0;

   double calcLoss=0.0;
   if(!OrderCalcProfit(type,_Symbol,volume,entry,sl,calcLoss)) return 0.0;
   effectiveRiskMoney=MathAbs(calcLoss);
   effectiveRiskPct=(equity>0.0)?effectiveRiskMoney/equity*100.0:0.0;

   // Hard cap and zone-budget cap are expressed as one effective percentage ceiling.
   bool capRequired=InpUseHardRiskCap || InpUseZoneRiskBudget;
   if(capRequired && effectiveRiskPct>maxRiskCapPct+1e-8)
   {
      double capMoney=equity*maxRiskCapPct/100.0;
      double cappedVolume=MathFloor((capMoney/lossOneLot)/step)*step;
      if(cappedVolume>userMaxLot) cappedVolume=userMaxLot;
      cappedVolume=NormalizeVolume(cappedVolume);
      if(cappedVolume<minLot) return 0.0;

      volume=cappedVolume;
      if(!OrderCalcProfit(type,_Symbol,volume,entry,sl,calcLoss)) return 0.0;
      effectiveRiskMoney=MathAbs(calcLoss);
      effectiveRiskPct=effectiveRiskMoney/equity*100.0;

      if(effectiveRiskPct>maxRiskCapPct+1e-6) return 0.0;
   }

   return volume;
}

bool MarginPreflight(bool bullish,double volume,double entry)
{
   if(!InpUseMarginGuard) return true;

   ENUM_ORDER_TYPE type=bullish?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   double required=0.0;
   if(!OrderCalcMargin(type,_Symbol,volume,entry,required))
      return false;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   double currentMargin=AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin=AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   if(equity<=0.0 || freeMargin<=0.0) return false;
   if(required>freeMargin) return false;

   if(InpMaxSingleTradeMarginPct>0.0 && required/equity*100.0 > InpMaxSingleTradeMarginPct)
      return false;

   double projectedMargin=currentMargin+required;
   if(projectedMargin>0.0 && InpMinProjectedMarginLevelPct>0.0)
   {
      double projectedLevel=equity/projectedMargin*100.0;
      if(projectedLevel < InpMinProjectedMarginLevelPct)
         return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Position management                                               |
//+------------------------------------------------------------------+
void ManageOpenPosition()
{
   if(!HasOurPosition()) return;
   ulong ticket=GetOurPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket)) return;

   long type=PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   datetime positionTime=(datetime)PositionGetInteger(POSITION_TIME);
   double price=(type==POSITION_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(open<=0.0 || price<=0.0 || tp<=0.0 || InpRewardRisk<=0.0) return;

   double initialRisk=MathAbs(tp-open)/InpRewardRisk;
   if(initialRisk<=0.0) return;

   double profitDist=(type==POSITION_TYPE_BUY)?price-open:open-price;
   double rr=profitDist/initialRisk;

   // Optional stagnation exit for research. It only activates after enough
   // completed entry-TF bars and when the trade has failed to produce MFE.
   if(InpUseTimeStop && positionTime>0)
   {
      int barsHeld=BarsSince(positionTime);
      double observedMFE=g_track.active?g_track.maxMFE_R:0.0;
      if(barsHeld>=InpTimeStopBars && observedMFE<InpTimeStopMinMFER)
      {
         SafeClosePosition(ticket,"TIME_STOP");
         return;
      }
   }

   if(rr<=0.0) return;

   if(InpUseProfitLock)
   {
      double lockRR=-1.0;
      if(rr>=InpLock2TriggerRR) lockRR=InpLock2RR;
      else if(rr>=InpLock1TriggerRR) lockRR=InpLock1RR;

      if(lockRR>=0.0)
      {
         double newSL=(type==POSITION_TYPE_BUY)?open+initialRisk*lockRR:open-initialRisk*lockRR;
         newSL=NormalizePrice(newSL);
         if(IsBetterSL(type,sl,newSL) && StopsAreValid(price,newSL,tp,type==POSITION_TYPE_BUY))
            SafeModifyPosition(ticket,newSL,tp,"LOCK");
      }
   }

   if(!InpUseATRTrail) return;

   double trailStart=InpTrailStartRR;
   double trailATR=InpTrail_ATR;
   double tightenRR=InpTrailTightenRR;
   double tightATR=InpTrailTightATR;
   double floorRR=InpLock2RR;

   if(InpTrailMode==FVG_TRAIL_ADAPTIVE)
   {
      floorRR=MathMax(floorRR,InpAdaptiveTrailFloorRR);
   }
   else if(InpTrailMode==FVG_TRAIL_HYBRID)
   {
      trailStart=InpHybridTrailStartRR;
      trailATR=InpHybridTrailATR;
      tightenRR=InpHybridTightenRR;
      tightATR=InpHybridTightATR;
      floorRR=MathMax(floorRR,InpHybridTrailFloorRR);
   }
   else if(InpTrailMode==FVG_TRAIL_SMART)
   {
      double peakArm1=InpPeakRArm1, peakGive1=InpPeakRGiveback1;
      double peakArm2=InpPeakRArm2, peakGive2=InpPeakRGiveback2;
      trailStart=InpSmartTrailStartRR;
      trailATR=InpSmartTrailATR;
      tightenRR=InpSmartTightenRR;
      tightATR=InpSmartTightATR;
      floorRR=MathMax(floorRR,InpSmartTrailFloorRR);

      if(InpUseDirectionalExitProfiles)
      {
         bool isBuy=(type==POSITION_TYPE_BUY);
         if(isBuy)
         {
            trailStart=InpLongTrailStartRR; trailATR=InpLongTrailATR;
            tightenRR=InpLongTightenRR; tightATR=InpLongTightATR;
            peakArm1=InpLongPeakArm1; peakGive1=InpLongPeakGiveback1;
            peakArm2=InpLongPeakArm2; peakGive2=InpLongPeakGiveback2;
         }
         else
         {
            trailStart=InpShortTrailStartRR; trailATR=InpShortTrailATR;
            tightenRR=InpShortTightenRR; tightATR=InpShortTightATR;
            peakArm1=InpShortPeakArm1; peakGive1=InpShortPeakGiveback1;
            peakArm2=InpShortPeakArm2; peakGive2=InpShortPeakGiveback2;
         }
      }

      if(InpUsePeakRProtection && g_track.active)
      {
         double peakR=g_track.maxMFE_R;
         double peakFloor=-1.0;
         if(peakR>=peakArm2) peakFloor=peakR-peakGive2;
         else if(peakR>=peakArm1) peakFloor=peakR-peakGive1;
         if(peakFloor>floorRR) floorRR=peakFloor;
      }
   }

   if(rr<trailStart) return;

   double atr=GetATR();
   if(atr<=0.0) return;

   if(rr>=tightenRR)
      trailATR=tightATR;

   double newSL=(type==POSITION_TYPE_BUY)?price-atr*trailATR:price+atr*trailATR;
   double floorSL=(type==POSITION_TYPE_BUY)?open+initialRisk*floorRR:open-initialRisk*floorRR;

   if(type==POSITION_TYPE_BUY) newSL=MathMax(newSL,floorSL);
   else newSL=MathMin(newSL,floorSL);

   newSL=NormalizePrice(newSL);
   if(IsBetterSL(type,sl,newSL) && StopsAreValid(price,newSL,tp,type==POSITION_TYPE_BUY))
   {
      string reason="TRAIL";
      if(InpTrailMode==FVG_TRAIL_ADAPTIVE) reason="ADAPTIVE_TRAIL";
      if(InpTrailMode==FVG_TRAIL_HYBRID) reason="HYBRID_TRAIL";
      if(InpTrailMode==FVG_TRAIL_SMART) reason="SMART_TRAIL";
      SafeModifyPosition(ticket,newSL,tp,reason);
   }
}

bool SafeClosePosition(ulong ticket,string reason)
{
   ResetLastError();
   bool ok=trade.PositionClose(ticket,(ulong)InpDeviationPoints);
   uint rc=trade.ResultRetcode();
   if(!ok || (rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL && rc!=TRADE_RETCODE_PLACED))
   {
      Print("ASTRA400 close failed [",reason,"] ticket=",ticket,
            " rc=",rc," ",trade.ResultRetcodeDescription()," err=",GetLastError());
      return false;
   }
   if(InpVerboseLog)
      Print("ASTRA400 position close requested [",reason,"] ticket=",ticket);
   return true;
}

bool SafeModifyPosition(ulong ticket,double newSL,double tp,string reason)
{
   ResetLastError();
   bool ok=trade.PositionModify(ticket,newSL,tp);
   uint rc=trade.ResultRetcode();
   if(!ok || (rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_NO_CHANGES && rc!=TRADE_RETCODE_PLACED))
   {
      Print("ASTRA400 SL modify failed [",reason,"] ticket=",ticket,
            " sl=",DoubleToString(newSL,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS)),
            " rc=",rc," ",trade.ResultRetcodeDescription()," err=",GetLastError());
      return false;
   }
   return true;
}

bool StopsAreValid(double price,double sl,double tp,bool bullish)
{
   double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(p<=0) return false;
   long st=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   long fr=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist=MathMax(st,fr)*p;
   if(bullish)
      return sl<price && tp>price && price-sl>=minDist && tp-price>=minDist;
   return sl>price && tp<price && sl-price>=minDist && price-tp>=minDist;
}

bool IsBetterSL(long type,double oldSL,double newSL)
{
   if(type==POSITION_TYPE_BUY) return oldSL==0 || newSL>oldSL;
   return oldSL==0 || newSL<oldSL;
}

//+------------------------------------------------------------------+
//| Telemetry                                                         |
//+------------------------------------------------------------------+
void ResetTelemetry()
{
   g_track.active=false;
   g_track.positionTicket=0;
   g_track.positionType=-1;
   g_track.entryTime=0;
   g_track.requestedEntry=0.0;
   g_track.actualEntry=0.0;
   g_track.initialSL=0.0;
   g_track.originalTP=0.0;
   g_track.initialRiskPrice=0.0;
   g_track.plannedRiskMoney=0.0;
   g_track.effectiveRiskMoney=0.0;
   g_track.effectiveRiskPct=0.0;
   g_track.requestedRawVolume=0.0;
   g_track.volume=0.0;
   g_track.maxMFE_R=0.0;
   g_track.maxMAE_R=0.0;
   g_track.entrySlippagePoints=0.0;
   g_track.entrySpreadPoints=0.0;
   g_track.sessionTag="";
   g_track.zoneFormed=0;
   g_track.zoneLow=0.0;
   g_track.zoneHigh=0.0;
   g_track.bullishZone=false;
   g_track.zoneGapATR=0.0;
   g_track.zoneBodyATR=0.0;
   g_track.zoneBodyRatio=0.0;
   g_track.regimeFastEMA=0.0;
   g_track.regimeSlowEMA=0.0;
   g_track.regimeADX=0.0;
   g_track.regimeSlope=0.0;
   g_track.atrRatio=0.0;
   g_track.shockRangeATR=0.0;
   g_track.zoneAttempt=0;
   g_track.reentry=false;
   g_track.lossStreakAtEntry=0;
   g_track.mtfScore=0;
   g_track.qualityScore=0.0;
   g_track.spreadRatio=1.0;
   g_track.zoneRiskSpentPct=0.0;
   g_track.attemptRiskScale=1.0;
   g_track.directionRiskScale=1.0;
   g_track.qualityRiskScale=1.0;
   g_track.ddRiskScale=1.0;
   g_track.peakDrawdownPct=0.0;
   g_track.alignedMTFVotes=0;
   g_track.astraRegime="";
   g_track.contradictionScore=0.0;
   g_track.contradictionRiskScale=1.0;
   g_track.similarityScore=50.0;
   g_track.similaritySamples=0;
   g_track.similarityRiskScale=1.0;
   g_track.aiVerdict="BYPASS";
   g_track.aiRiskScale=1.0;
}

void UpdateTelemetryExcursions()
{
   if(!g_track.active || g_track.initialRiskPrice<=0.0) return;
   if(!HasOurPosition()) return;

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(bid<=0 || ask<=0) return;

   double price=(g_track.positionType==POSITION_TYPE_BUY)?bid:ask;
   double move=(g_track.positionType==POSITION_TYPE_BUY)?price-g_track.actualEntry:g_track.actualEntry-price;
   double r=move/g_track.initialRiskPrice;
   if(r>g_track.maxMFE_R) g_track.maxMFE_R=r;
   if(r<0.0 && -r>g_track.maxMAE_R) g_track.maxMAE_R=-r;
}

void RestoreTelemetryFromPosition()
{
   if(!HasOurPosition()) return;
   ulong ticket=GetOurPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket)) return;

   long type=PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double tp=PositionGetDouble(POSITION_TP);
   double currentSL=PositionGetDouble(POSITION_SL);
   double volume=PositionGetDouble(POSITION_VOLUME);
   datetime t=(datetime)PositionGetInteger(POSITION_TIME);
   if(open<=0.0 || tp<=0.0 || InpRewardRisk<=0.0) return;

   double initialRisk=MathAbs(tp-open)/InpRewardRisk;
   if(initialRisk<=0.0) return;
   double reconstructedSL=(type==POSITION_TYPE_BUY)?open-initialRisk:open+initialRisk;

   double riskMoney=0.0;
   ENUM_ORDER_TYPE ot=(type==POSITION_TYPE_BUY)?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(ot,_Symbol,volume,open,reconstructedSL,riskMoney)) return;
   riskMoney=MathAbs(riskMoney);

   bool bullish=(type==POSITION_TYPE_BUY);
   RegimeAllows(bullish);
   MTFScoreAllows(bullish);
   MarketQualityAllows();
   g_ctxQualityScore=ComputeEntryQualityScore(bullish);
   UpdateASTRAContext(bullish);
   g_ctxAIVerdict="RESTORED";
   g_ctxAIRiskScale=1.0;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_track.active=true;
   g_track.positionTicket=ticket;
   g_track.positionType=type;
   g_track.entryTime=t;
   g_track.requestedEntry=open;
   g_track.actualEntry=open;
   g_track.initialSL=reconstructedSL;
   g_track.originalTP=tp;
   g_track.initialRiskPrice=initialRisk;
   g_track.plannedRiskMoney=riskMoney;
   g_track.effectiveRiskMoney=riskMoney;
   g_track.effectiveRiskPct=(equity>0.0)?riskMoney/equity*100.0:0.0;
   g_track.requestedRawVolume=volume;
   g_track.volume=volume;
   g_track.maxMFE_R=0.0;
   g_track.maxMAE_R=0.0;
   g_track.entrySlippagePoints=0.0;
   g_track.entrySpreadPoints=0.0;
   g_track.sessionTag=ResearchSessionTag(t);
   g_track.zoneFormed=g_zone.formed;
   g_track.zoneLow=g_zone.low;
   g_track.zoneHigh=g_zone.high;
   g_track.bullishZone=g_zone.bullish;
   g_track.zoneGapATR=g_zone.gapATR;
   g_track.zoneBodyATR=g_zone.bodyATR;
   g_track.zoneBodyRatio=g_zone.bodyRatio;
   g_track.regimeFastEMA=g_ctxRegimeFast;
   g_track.regimeSlowEMA=g_ctxRegimeSlow;
   g_track.regimeADX=g_ctxRegimeADX;
   g_track.regimeSlope=g_ctxRegimeSlope;
   g_track.atrRatio=g_ctxATRRatio;
   g_track.shockRangeATR=g_ctxShockRangeATR;
   g_track.zoneAttempt=(g_zone.attempts>0)?g_zone.attempts:1;
   g_track.reentry=(g_track.zoneAttempt>1);
   g_track.lossStreakAtEntry=bullish?g_lossStreakLong:g_lossStreakShort;
   g_track.mtfScore=g_ctxMTFScore;
   g_track.qualityScore=g_ctxQualityScore;
   g_track.spreadRatio=g_ctxSpreadRatio;
   g_track.zoneRiskSpentPct=g_zone.riskSpentPct;
   g_track.directionRiskScale=bullish?InpLongRiskMultiplier:InpShortRiskMultiplier;
   g_track.qualityRiskScale=QualityRiskScale(g_ctxQualityScore);
   g_track.ddRiskScale=g_ctxDDRiskScale;
   g_track.peakDrawdownPct=g_ctxPeakDrawdownPct;
   g_track.alignedMTFVotes=bullish?g_ctxMTFScore:-g_ctxMTFScore;
   g_track.astraRegime=g_ctxASTRARegime;
   g_track.contradictionScore=g_ctxContradictionScore;
   g_track.contradictionRiskScale=g_ctxContradictionRiskScale;
   g_track.similarityScore=g_ctxSimilarityScore;
   g_track.similaritySamples=g_ctxSimilaritySamples;
   g_track.similarityRiskScale=g_ctxSimilarityRiskScale;
   g_track.aiVerdict=g_ctxAIVerdict;
   g_track.aiRiskScale=g_ctxAIRiskScale;
   g_track.attemptRiskScale=AttemptRiskScale(g_track.zoneAttempt)*g_track.directionRiskScale*
                            g_track.qualityRiskScale*g_track.ddRiskScale*
                            g_track.contradictionRiskScale*g_track.similarityRiskScale;

   if(InpVerboseLog)
      Print("ASTRA400 telemetry restored for open position ticket=",ticket," currentSL=",currentSL);
}

void EnsureTelemetryHeader()
{
   int h=FileOpen(InpTelemetryFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',');
   if(h==INVALID_HANDLE)
   {
      Print("ASTRA400 telemetry open failed: ",GetLastError());
      return;
   }

   if(FileSize(h)==0)
   {
      FileWrite(h,
         "symbol","magic","research_mode","entry_time","exit_time","direction","session",
         "zone_formed","zone_low","zone_high","gap_atr","body_atr","body_ratio",
         "requested_entry","actual_entry","initial_sl","original_tp","initial_risk_price",
         "requested_raw_volume","volume","planned_risk_money","effective_risk_money","effective_risk_pct",
         "entry_spread_points","entry_slippage_points","spread_ratio","mfe_r","mae_r",
         "regime_fast_ema","regime_slow_ema","regime_adx","regime_slope",
         "mtf_score","quality_score","atr_ratio","shock_range_atr",
         "zone_attempt","reentry","attempt_risk_scale","direction_risk_scale","quality_risk_scale",
         "dd_risk_scale","peak_drawdown_pct","aligned_mtf_votes","zone_risk_spent_pct","loss_streak_at_entry",
         "astra_regime","contradiction_score","contradiction_risk_scale",
         "similarity_score","similarity_samples","similarity_risk_scale",
         "ai_verdict","ai_risk_scale",
         "exit_price","net_profit","realized_r","exit_deal");
   }
   FileClose(h);
}

void WriteTelemetryRow(datetime closeTime,double closePrice,double net,double realizedR,ulong deal)
{
   if(!InpEnableTelemetry) return;

   int h=FileOpen(InpTelemetryFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',');
   if(h==INVALID_HANDLE)
   {
      Print("ASTRA400 telemetry write failed: ",GetLastError());
      return;
   }
   FileSeek(h,0,SEEK_END);

   string direction=(g_track.positionType==POSITION_TYPE_BUY)?"BUY":"SELL";
   FileWrite(h,
      _Symbol,(long)InpMagic,ResearchModeName(),
      TimeToString(g_track.entryTime,TIME_DATE|TIME_SECONDS),
      TimeToString(closeTime,TIME_DATE|TIME_SECONDS),
      direction,g_track.sessionTag,
      TimeToString(g_track.zoneFormed,TIME_DATE|TIME_SECONDS),
      DoubleToString(g_track.zoneLow,_Digits),DoubleToString(g_track.zoneHigh,_Digits),
      DoubleToString(g_track.zoneGapATR,4),DoubleToString(g_track.zoneBodyATR,4),DoubleToString(g_track.zoneBodyRatio,4),
      DoubleToString(g_track.requestedEntry,_Digits),DoubleToString(g_track.actualEntry,_Digits),
      DoubleToString(g_track.initialSL,_Digits),DoubleToString(g_track.originalTP,_Digits),
      DoubleToString(g_track.initialRiskPrice,_Digits),
      DoubleToString(g_track.requestedRawVolume,4),DoubleToString(g_track.volume,4),
      DoubleToString(g_track.plannedRiskMoney,2),DoubleToString(g_track.effectiveRiskMoney,2),
      DoubleToString(g_track.effectiveRiskPct,4),
      DoubleToString(g_track.entrySpreadPoints,1),DoubleToString(g_track.entrySlippagePoints,1),
      DoubleToString(g_track.spreadRatio,4),
      DoubleToString(g_track.maxMFE_R,4),DoubleToString(g_track.maxMAE_R,4),
      DoubleToString(g_track.regimeFastEMA,_Digits),DoubleToString(g_track.regimeSlowEMA,_Digits),
      DoubleToString(g_track.regimeADX,2),DoubleToString(g_track.regimeSlope,_Digits),
      g_track.mtfScore,DoubleToString(g_track.qualityScore,2),
      DoubleToString(g_track.atrRatio,4),DoubleToString(g_track.shockRangeATR,4),
      g_track.zoneAttempt,(g_track.reentry?"TRUE":"FALSE"),
      DoubleToString(g_track.attemptRiskScale,3),DoubleToString(g_track.directionRiskScale,3),
      DoubleToString(g_track.qualityRiskScale,3),DoubleToString(g_track.ddRiskScale,3),
      DoubleToString(g_track.peakDrawdownPct,3),g_track.alignedMTFVotes,
      DoubleToString(g_track.zoneRiskSpentPct,4),g_track.lossStreakAtEntry,
      g_track.astraRegime,DoubleToString(g_track.contradictionScore,2),
      DoubleToString(g_track.contradictionRiskScale,3),
      DoubleToString(g_track.similarityScore,2),g_track.similaritySamples,
      DoubleToString(g_track.similarityRiskScale,3),
      g_track.aiVerdict,DoubleToString(g_track.aiRiskScale,3),
      DoubleToString(closePrice,_Digits),DoubleToString(net,2),DoubleToString(realizedR,4),(long)deal);

   FileClose(h);
}

string ResearchSessionTag(datetime t)
{
   MqlDateTime dt; TimeToStruct(t,dt);
   int h=dt.hour+InpResearchSessionOffsetHours;
   while(h<0) h+=24;
   while(h>=24) h-=24;

   if(h>=0 && h<7) return "ASIA";
   if(h>=7 && h<12) return "LONDON";
   if(h>=12 && h<16) return "LONDON_NY_OVERLAP";
   if(h>=16 && h<21) return "NEW_YORK";
   return "OTHER";
}

//+------------------------------------------------------------------+
//| Trading permissions / daily controls                              |
//+------------------------------------------------------------------+
bool TradingAllowed()
{
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return false;
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)) return false;
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;
   if(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_MODE)!=SYMBOL_TRADE_MODE_FULL) return false;

   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   bool s1=InpUseSession1 && HourInWindow(dt.hour,InpSession1Start,InpSession1End);
   bool s2=InpUseSession2 && HourInWindow(dt.hour,InpSession2Start,InpSession2End);
   if(!s1 && !s2) return false;

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(bid<=0.0 || ask<=0.0 || p<=0.0) return false;

   double spread=(ask-bid)/p;
   if(spread>InpMaxSpreadPoints) return false;

   if(InpUseRelativeSpreadGuard && g_spreadSamples>=InpSpreadEMAWarmupTicks &&
      g_spreadEMA>0.0 && spread>g_spreadEMA*InpRelativeSpreadMultiplier)
      return false;

   double eq=AccountInfoDouble(ACCOUNT_EQUITY);

   if(InpDailyLossPct>0.0 && g_dayStartEquity>0.0)
   {
      if((g_dayStartEquity-eq)/g_dayStartEquity*100.0 >= InpDailyLossPct)
         return false;
   }

   if(InpUseDailyPeakProtection && g_dayStartEquity>0.0 && g_dayPeakEquity>0.0)
   {
      double profitPct=(g_dayPeakEquity-g_dayStartEquity)/g_dayStartEquity*100.0;
      double givebackPct=(g_dayPeakEquity-eq)/g_dayPeakEquity*100.0;
      if(profitPct>=InpDailyProfitArmPct && givebackPct>=InpDailyPeakGivebackPct)
         return false;
   }

   if(InpUseEquityDDGovernor && g_ctxDDRiskScale<=0.0)
      return false;

   return true;
}

bool HourInWindow(int h,int start,int end)
{
   if(start==end) return true; // preserves V2.11 semantics: 0->0 means all day
   if(start<end) return h>=start && h<end;
   return h>=start || h<end;
}

double EquityDDRiskScale()
{
   return EffectiveDDScale();
}

void UpdateEquityPeak()
{
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq<=0.0) return;
   if(g_equityPeak<=0.0 || eq>g_equityPeak)
   {
      g_equityPeak=eq;
      SaveEquityPeakState();
   }
   g_ctxPeakDrawdownPct=(g_equityPeak>0.0)?(g_equityPeak-eq)/g_equityPeak*100.0:0.0;
   if(g_ctxPeakDrawdownPct<0.0) g_ctxPeakDrawdownPct=0.0;
   g_ctxDDRiskScale=EquityDDRiskScale();
}

void SaveEquityPeakState()
{
   if(!InpPersistState) return;
   GlobalVariableSet(GVPrefix()+"EQ_PEAK",g_equityPeak);
}

void LoadEquityPeakState()
{
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   g_equityPeak=eq;
   if(InpPersistState && GlobalVariableCheck(GVPrefix()+"EQ_PEAK"))
      g_equityPeak=MathMax(eq,GlobalVariableGet(GVPrefix()+"EQ_PEAK"));
   g_ctxPeakDrawdownPct=0.0;
   g_ctxDDRiskScale=1.0;
}

void ResetDailyStats()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   g_dayKey=dt.year*1000+dt.day_of_year;
   g_tradesToday=CountTodayEntries();
   g_aiCallsToday=0;

   string keyDay=GVPrefix()+"DAYKEY";
   string keyEq=GVPrefix()+"DAYEQ";
   string keyPeak=GVPrefix()+"DAYPEAK";

   if(InpPersistState && GlobalVariableCheck(keyDay) && GlobalVariableCheck(keyEq) &&
      (int)GlobalVariableGet(keyDay)==g_dayKey)
   {
      g_dayStartEquity=GlobalVariableGet(keyEq);
      g_dayPeakEquity=GlobalVariableCheck(keyPeak)?GlobalVariableGet(keyPeak):AccountInfoDouble(ACCOUNT_EQUITY);
   }
   else
   {
      g_dayStartEquity=AccountInfoDouble(ACCOUNT_EQUITY);
      g_dayPeakEquity=g_dayStartEquity;

      if(InpPersistState)
      {
         GlobalVariableSet(keyDay,(double)g_dayKey);
         GlobalVariableSet(keyEq,g_dayStartEquity);
         GlobalVariableSet(keyPeak,g_dayPeakEquity);
      }
   }
}

void UpdateDailyPeak()
{
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq<=0.0) return;
   if(g_dayPeakEquity<=0.0 || eq>g_dayPeakEquity)
   {
      g_dayPeakEquity=eq;
      if(InpPersistState)
         GlobalVariableSet(GVPrefix()+"DAYPEAK",g_dayPeakEquity);
   }
}

void ResetDailyStatsIfNeeded()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   int key=dt.year*1000+dt.day_of_year;
   if(key!=g_dayKey) ResetDailyStats();
}

int CountTodayEntries()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   dt.hour=0;dt.min=0;dt.sec=0;
   datetime from=StructToTime(dt),to=TimeCurrent();
   if(!HistorySelect(from,to)) return 0;

   int count=0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong d=HistoryDealGetTicket(i); if(d==0) continue;
      if(HistoryDealGetString(d,DEAL_SYMBOL)!=_Symbol) continue;
      if((ulong)HistoryDealGetInteger(d,DEAL_MAGIC)!=InpMagic) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(d,DEAL_ENTRY)==DEAL_ENTRY_IN) count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Persistent zone state                                             |
//+------------------------------------------------------------------+
void PersistZoneIfNeeded()
{
   if(InpPersistState) SaveZoneState();
}

void SaveZoneState()
{
   string p=GVPrefix();
   GlobalVariableSet(p+"Z_VALID",g_zone.valid?1.0:0.0);
   GlobalVariableSet(p+"Z_BULL",g_zone.bullish?1.0:0.0);
   GlobalVariableSet(p+"Z_LOW",g_zone.low);
   GlobalVariableSet(p+"Z_HIGH",g_zone.high);
   GlobalVariableSet(p+"Z_FORMED",(double)g_zone.formed);
   GlobalVariableSet(p+"Z_TRADED",g_zone.traded?1.0:0.0);
   GlobalVariableSet(p+"Z_ATTEMPTS",(double)g_zone.attempts);
   GlobalVariableSet(p+"Z_LAST_ENTRY",(double)g_zone.lastEntryTime);
   GlobalVariableSet(p+"Z_LAST_EXIT",(double)g_zone.lastExitTime);
   GlobalVariableSet(p+"Z_LAST_R",g_zone.lastRealizedR);
   GlobalVariableSet(p+"Z_QUAR",g_zone.quarantined?1.0:0.0);
   GlobalVariableSet(p+"Z_GAP_ATR",g_zone.gapATR);
   GlobalVariableSet(p+"Z_BODY_ATR",g_zone.bodyATR);
   GlobalVariableSet(p+"Z_BODY_RATIO",g_zone.bodyRatio);
   GlobalVariableSet(p+"Z_RISK_SPENT",g_zone.riskSpentPct);
}

void LoadZoneState()
{
   string p=GVPrefix();
   if(!GlobalVariableCheck(p+"Z_VALID")) return;

   g_zone.valid=GlobalVariableGet(p+"Z_VALID")>0.5;
   g_zone.bullish=GlobalVariableCheck(p+"Z_BULL") && GlobalVariableGet(p+"Z_BULL")>0.5;
   g_zone.low=GlobalVariableCheck(p+"Z_LOW")?GlobalVariableGet(p+"Z_LOW"):0.0;
   g_zone.high=GlobalVariableCheck(p+"Z_HIGH")?GlobalVariableGet(p+"Z_HIGH"):0.0;
   g_zone.formed=GlobalVariableCheck(p+"Z_FORMED")?(datetime)GlobalVariableGet(p+"Z_FORMED"):0;
   g_zone.traded=GlobalVariableCheck(p+"Z_TRADED") && GlobalVariableGet(p+"Z_TRADED")>0.5;
   g_zone.attempts=GlobalVariableCheck(p+"Z_ATTEMPTS")?(int)GlobalVariableGet(p+"Z_ATTEMPTS"):0;
   g_zone.lastEntryTime=GlobalVariableCheck(p+"Z_LAST_ENTRY")?(datetime)GlobalVariableGet(p+"Z_LAST_ENTRY"):0;
   g_zone.lastExitTime=GlobalVariableCheck(p+"Z_LAST_EXIT")?(datetime)GlobalVariableGet(p+"Z_LAST_EXIT"):0;
   g_zone.lastRealizedR=GlobalVariableCheck(p+"Z_LAST_R")?GlobalVariableGet(p+"Z_LAST_R"):0.0;
   g_zone.quarantined=GlobalVariableCheck(p+"Z_QUAR") && GlobalVariableGet(p+"Z_QUAR")>0.5;
   g_zone.gapATR=GlobalVariableCheck(p+"Z_GAP_ATR")?GlobalVariableGet(p+"Z_GAP_ATR"):0.0;
   g_zone.bodyATR=GlobalVariableCheck(p+"Z_BODY_ATR")?GlobalVariableGet(p+"Z_BODY_ATR"):0.0;
   g_zone.bodyRatio=GlobalVariableCheck(p+"Z_BODY_RATIO")?GlobalVariableGet(p+"Z_BODY_RATIO"):0.0;
   g_zone.riskSpentPct=GlobalVariableCheck(p+"Z_RISK_SPENT")?GlobalVariableGet(p+"Z_RISK_SPENT"):0.0;
   g_zone.shift=(g_zone.formed>0)?iBarShift(_Symbol,InpEntryTF,g_zone.formed,false):-1;

   if(g_zone.valid && FVGExpired(g_zone))
      g_zone.valid=false;
}

//+------------------------------------------------------------------+
//| Position helpers                                                  |
//+------------------------------------------------------------------+
bool HasOurPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i);
      if(t==0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   return false;
}

ulong GetOurPositionTicket()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i);
      if(t==0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic) return t;
   }
   return 0;
}

double GetATR()
{
   double v[];
   ArrayResize(v,2);
   ArraySetAsSeries(v,true);
   if(CopyBuffer(hATR,0,0,2,v)<2) return 0;
   // Use the last completed candle ATR, never the still-forming bar.
   return v[1];
}

bool IsNewBar()
{
   datetime t=iTime(_Symbol,InpEntryTF,0);
   if(t==0) return false;
   if(t!=g_lastBar){g_lastBar=t;return true;}
   return false;
}

double NormalizePrice(double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(double volume)
{
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0) return 0;
   int digits=0; double x=step;
   while(x<1.0 && digits<8){x*=10.0;digits++;}
   return NormalizeDouble(volume,digits);
}
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| MT5 optimization fitness                                         |
//+------------------------------------------------------------------+
double OnTester()
{
   if(!InpUseCustomOnTesterFitness)
      return TesterStatistics(STAT_PROFIT);

   double deposit=TesterStatistics(STAT_INITIAL_DEPOSIT);
   double profit=TesterStatistics(STAT_PROFIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double recovery=TesterStatistics(STAT_RECOVERY_FACTOR);
   double trades=TesterStatistics(STAT_TRADES);

   if(deposit<=0.0) deposit=1.0;
   if(trades<=0.0 || profit<=0.0)
      return -1000000.0 + profit;

   double returnPct=profit/deposit*100.0;
   if(pf<0.0) pf=0.0;
   if(pf>5.0) pf=5.0;
   if(dd<0.10) dd=0.10;
   if(recovery<0.0) recovery=0.0;

   double tradeFactor=MathSqrt(MathMax(0.05,trades/(double)InpFitnessMinTrades));
   if(tradeFactor>2.0) tradeFactor=2.0;

   double pfFactor=MathPow(MathMax(0.20,pf/InpFitnessTargetPF),InpFitnessPFWeight);
   if(pfFactor>2.0) pfFactor=2.0;

   double ddPenalty=MathPow(1.0+dd/MathMax(1.0,InpFitnessMaxEquityDDPct),InpFitnessDDPenaltyWeight);
   if(dd>InpFitnessMaxEquityDDPct)
      ddPenalty*=1.0+(dd-InpFitnessMaxEquityDDPct)/InpFitnessMaxEquityDDPct*3.0;

   double recoveryFactor=MathPow(MathMax(0.10,recovery),InpFitnessRecoveryWeight);
   double countFactor=MathPow(MathMax(0.10,tradeFactor),InpFitnessTradeCountWeight);
   double returnFactor=MathPow(MathMax(0.01,returnPct),InpFitnessReturnWeight);

   double score=returnFactor*pfFactor*recoveryFactor*countFactor/ddPenalty;

   // Strong penalty for statistically thin results even if headline profit is large.
   if(trades<(double)InpFitnessMinTrades)
      score*=MathMax(0.10,trades/(double)InpFitnessMinTrades);

   return score;
}
