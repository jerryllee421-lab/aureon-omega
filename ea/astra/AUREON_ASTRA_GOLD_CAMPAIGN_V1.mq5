//+------------------------------------------------------------------+
//|                    AUREON_ASTRA_GOLD_CAMPAIGN_V1.mq5             |
//| AUREON Ω / ASTRA deterministic XAUUSD campaign research EA       |
//| M5 execution · M15 liquidity · H1/H4 context · E1-E5 scaling     |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "AUREON ASTRA Gold Campaign V1: deterministic liquidity sweep/reclaim, MSS, displacement, FVG retracement, E1-E5 campaign scaling and risk governance."

#include <Trade/Trade.mqh>
CTrade trade;

enum ENUM_ASTRA_SIZING_MODE
{
   ASTRA_FIXED_LOT = 0,
   ASTRA_RISK_PERCENT = 1
};

enum ENUM_ASTRA_CAMPAIGN_STATE
{
   ASTRA_IDLE = 0,
   ASTRA_SWEEP_RECLAIMED,
   ASTRA_WAITING_MSS,
   ASTRA_ENTRY_ZONE_ACTIVE,
   ASTRA_BUILDING,
   ASTRA_PROTECTED,
   ASTRA_PARTIAL_EXIT,
   ASTRA_RUNNER,
   ASTRA_COMPLETED,
   ASTRA_INVALIDATED,
   ASTRA_EXPIRED,
   ASTRA_RISK_REJECTED
};

enum ENUM_ASTRA_ENTRY_STYLE
{
   ASTRA_FVG_NEAR_EDGE = 0,
   ASTRA_FVG_MIDPOINT = 1,
   ASTRA_FVG_FAR_EDGE = 2
};

input group "GENERAL"
input ulong InpMagic = 26092301;
input bool InpLongEnabled = true;
input bool InpShortEnabled = true;
input bool InpClosedCandleAuthority = true;
input bool InpVisualDebug = true;
input bool InpCSVLogging = true;

input group "MARKET DATA"
input ENUM_TIMEFRAMES InpEntryTF = PERIOD_M5;
input ENUM_TIMEFRAMES InpLiquidityTF = PERIOD_M15;
input ENUM_TIMEFRAMES InpH1TF = PERIOD_H1;
input ENUM_TIMEFRAMES InpH4TF = PERIOD_H4;
input int InpATRPeriod = 14;

input group "H4 CONTEXT"
input bool InpRequireH4Bias = true;
input int InpH4FastEMA = 20;
input int InpH4SlowEMA = 50;
input int InpH4SwingBlock = 3;

input group "H1 FILTER"
input bool InpRequireH1Alignment = true;
input int InpH1FastEMA = 20;
input int InpH1SlowEMA = 50;
input int InpADXPeriod = 14;
input double InpMinADX = 18.0;
input bool InpRequireDIDirection = true;

input group "LIQUIDITY"
input int InpLiquidityLookback = 20;
input double InpEqualLevelATR = 0.10;
input bool InpUseRollingLiquidity = true;

input group "SWEEP"
input double InpSweepMinATR = 0.10;
input double InpSweepMaxATR = 0.75;

input group "RECLAIM"
input double InpMinReclaimBody = 0.40;
input bool InpRequireDirectionalReclaim = false;

input group "MSS"
input int InpMSSLookback = 5;
input bool InpRequireClosedMSS = true;

input group "DISPLACEMENT"
input double InpDisplacementATR = 1.20;
input double InpMinBodyEfficiency = 0.65;
input bool InpUseVolumeFilter = true;
input double InpVolumeMultiplier = 1.20;
input int InpVolumeMAPeriod = 20;

input group "FVG"
input double InpMinFVGATR = 0.05;
input double InpMaxFVGATR = 1.00;
input ENUM_ASTRA_ENTRY_STYLE InpEntryStyle = ASTRA_FVG_MIDPOINT;

input group "ENTRY ENGINE"
input int InpEntryExpiryM5Bars = 12;
input int InpSetupExpiryM15Bars = 8;
input int InpCampaignMaxHours = 8;
input double InpOptimalExtensionATR = 0.15;
input double InpMaxEntryExtensionATR = 0.35;
input double InpHardRejectExtensionATR = 0.60;
input double InpMinimumRR = 1.50;

input group "CAMPAIGN E1-E5"
input int InpMaxEntries = 5;
input double InpCampaignLots = 0.10;
input double InpEntryLot = 0.02;
input double InpE2MinMFER = 0.25;
input double InpE3MinMFER = 0.60;
input double InpE4MinMFER = 0.80;
input double InpE5MinMFER = 1.00;
input bool InpRequireProtectedAdds = true;

input group "POSITION SIZING"
input ENUM_ASTRA_SIZING_MODE InpSizingMode = ASTRA_FIXED_LOT;
input double InpRiskPercent = 1.00;
input double InpMaxCampaignRiskPercent = 1.00;

input group "STOP LOSS"
input double InpSLBufferATR = 0.15;
input int InpStructureStopLookback = 5;

input group "TAKE PROFITS"
input bool InpUseStructuralTP1 = true;
input double InpTP1R = 1.50;
input double InpTP2R = 2.50;
input double InpTP3R = 4.00;
input double InpTP1ClosePercent = 30.0;
input double InpTP2ClosePercent = 30.0;
input double InpTP3ClosePercent = 20.0;

input group "BREAKEVEN"
input bool InpUseSmartProtection = true;
input double InpProtectionTriggerR = 1.00;
input double InpProtectionBufferATR = 0.05;

input group "TRAILING"
input bool InpUseRunner = true;
input double InpTrailStartR = 2.50;
input int InpTrailStructureLookback = 3;
input double InpTrailATRBuffer = 0.10;

input group "PYRAMIDING"
input bool InpEnableScaleIns = true;
input bool InpNoAddsAfterTP1 = true;

input group "SESSION"
input bool InpUseLondon = true;
input bool InpUseNewYork = true;
input int InpLondonStartHour = 8;
input int InpLondonEndHour = 12;
input int InpNewYorkStartHour = 13;
input int InpNewYorkEndHour = 17;
input bool InpSessionHoursAreUTC = false;
input int InpBrokerUTCOffsetHours = 0;
input bool InpUseDSTAdjustment = false;

input group "SPREAD & EXECUTION"
input bool InpUseSpreadFilter = true;
input int InpMaxSpreadPoints = 80;
input int InpDeviationPoints = 30;

input group "DAILY LIMITS"
input double InpMaxDailyLossPercent = 3.0;
input int InpMaxDailyCampaigns = 5;
input int InpMaxConsecutiveLosses = 3;

input group "DRAWDOWN"
input double InpMaxEquityDDPercent = 6.0;

input group "BACKTEST"
input bool InpOneCampaignAtATime = true;
input bool InpAllowReplacementBeforeEntry = true;

input group "LOGGING"
input string InpCSVFile = "AUREON_ASTRA_GOLD_CAMPAIGN_V1.csv";

struct AstraCampaign
{
   bool active;
   bool bullish;
   ENUM_ASTRA_CAMPAIGN_STATE state;
   string id;
   datetime created;
   datetime sweepTime;
   datetime confirmTime;
   datetime lastEntryTime;
   double liquidityLevel;
   double sweepExtreme;
   double fvgLow;
   double fvgHigh;
   double idealEntry;
   double stop;
   double tp1;
   double tp2;
   double tp3;
   double initialRiskPrice;
   double bestPrice;
   double peakVolume;
   int entries;
   bool tp1Done;
   bool tp2Done;
   bool tp3Done;
};

AstraCampaign g_campaign;

int hM5ATR=INVALID_HANDLE;
int hM15ATR=INVALID_HANDLE;
int hH4Fast=INVALID_HANDLE;
int hH4Slow=INVALID_HANDLE;
int hH1Fast=INVALID_HANDLE;
int hH1Slow=INVALID_HANDLE;
int hH1ADX=INVALID_HANDLE;
int hM5EMA9=INVALID_HANDLE;
int hM5EMA21=INVALID_HANDLE;

datetime g_lastM5Bar=0;
datetime g_lastM15Bar=0;
int g_dayKey=-1;
int g_campaignsToday=0;
int g_consecutiveLosses=0;
double g_dayStartEquity=0.0;
double g_equityPeak=0.0;
bool g_emergencyHalt=false;
int g_logHandle=INVALID_HANDLE;

int OnInit()
{
   if(InpMaxEntries<1 || InpMaxEntries>5) return INIT_PARAMETERS_INCORRECT;
   if(InpCampaignLots<=0 || InpEntryLot<=0) return INIT_PARAMETERS_INCORRECT;
   if(InpSweepMinATR<0 || InpSweepMaxATR<=InpSweepMinATR) return INIT_PARAMETERS_INCORRECT;
   if(InpTP1R<InpMinimumRR || InpTP2R<=InpTP1R || InpTP3R<=InpTP2R) return INIT_PARAMETERS_INCORRECT;
   if(InpTP1ClosePercent<0 || InpTP2ClosePercent<0 || InpTP3ClosePercent<0) return INIT_PARAMETERS_INCORRECT;
   if(InpTP1ClosePercent+InpTP2ClosePercent+InpTP3ClosePercent>=100.0 && InpUseRunner) return INIT_PARAMETERS_INCORRECT;

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   hM5ATR=iATR(_Symbol,InpEntryTF,InpATRPeriod);
   hM15ATR=iATR(_Symbol,InpLiquidityTF,InpATRPeriod);
   hH4Fast=iMA(_Symbol,InpH4TF,InpH4FastEMA,0,MODE_EMA,PRICE_CLOSE);
   hH4Slow=iMA(_Symbol,InpH4TF,InpH4SlowEMA,0,MODE_EMA,PRICE_CLOSE);
   hH1Fast=iMA(_Symbol,InpH1TF,InpH1FastEMA,0,MODE_EMA,PRICE_CLOSE);
   hH1Slow=iMA(_Symbol,InpH1TF,InpH1SlowEMA,0,MODE_EMA,PRICE_CLOSE);
   hH1ADX=iADX(_Symbol,InpH1TF,InpADXPeriod);
   hM5EMA9=iMA(_Symbol,InpEntryTF,9,0,MODE_EMA,PRICE_CLOSE);
   hM5EMA21=iMA(_Symbol,InpEntryTF,21,0,MODE_EMA,PRICE_CLOSE);

   if(hM5ATR==INVALID_HANDLE || hM15ATR==INVALID_HANDLE ||
      hH4Fast==INVALID_HANDLE || hH4Slow==INVALID_HANDLE ||
      hH1Fast==INVALID_HANDLE || hH1Slow==INVALID_HANDLE ||
      hH1ADX==INVALID_HANDLE || hM5EMA9==INVALID_HANDLE || hM5EMA21==INVALID_HANDLE)
      return INIT_FAILED;

   ResetCampaign();
   ResetDailyStats();
   g_equityPeak=AccountInfoDouble(ACCOUNT_EQUITY);
   OpenLog();
   LogEvent("EA_INIT",0.0,"ASTRA campaign EA initialized");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   LogEvent("EA_DEINIT",0.0,IntegerToString(reason));
   if(g_logHandle!=INVALID_HANDLE) FileClose(g_logHandle);
   if(hM5ATR!=INVALID_HANDLE) IndicatorRelease(hM5ATR);
   if(hM15ATR!=INVALID_HANDLE) IndicatorRelease(hM15ATR);
   if(hH4Fast!=INVALID_HANDLE) IndicatorRelease(hH4Fast);
   if(hH4Slow!=INVALID_HANDLE) IndicatorRelease(hH4Slow);
   if(hH1Fast!=INVALID_HANDLE) IndicatorRelease(hH1Fast);
   if(hH1Slow!=INVALID_HANDLE) IndicatorRelease(hH1Slow);
   if(hH1ADX!=INVALID_HANDLE) IndicatorRelease(hH1ADX);
   if(hM5EMA9!=INVALID_HANDLE) IndicatorRelease(hM5EMA9);
   if(hM5EMA21!=INVALID_HANDLE) IndicatorRelease(hM5EMA21);
   ClearVisuals();
}

void OnTick()
{
   ResetDailyStatsIfNeeded();
   UpdateEquityProtection();
   ManageOpenCampaign();

   bool newM15=IsNewBar(InpLiquidityTF,g_lastM15Bar);
   bool newM5=IsNewBar(InpEntryTF,g_lastM5Bar);

   if(newM15) ProcessM15Setup();
   if(newM5) ProcessM5Campaign();
}

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
{
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol) return;
   if((ulong)HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic) return;

   ENUM_DEAL_ENTRY e=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(e==DEAL_ENTRY_OUT || e==DEAL_ENTRY_OUT_BY)
   {
      double p=HistoryDealGetDouble(trans.deal,DEAL_PROFIT)
              +HistoryDealGetDouble(trans.deal,DEAL_SWAP)
              +HistoryDealGetDouble(trans.deal,DEAL_COMMISSION);
      if(p<0) g_consecutiveLosses++;
      else if(p>0) g_consecutiveLosses=0;
   }
}

void ProcessM15Setup()
{
   if(g_campaign.active && CampaignHasPosition()) return;

   if(g_campaign.active)
   {
      if(CampaignExpired())
      {
         SetState(ASTRA_EXPIRED,"Candidate expired before entry");
         ResetCampaign();
      }
      else if(!CandidateStillValid())
      {
         SetState(ASTRA_INVALIDATED,"Candidate invalidated before entry");
         ResetCampaign();
      }
   }

   if(g_campaign.active && !InpAllowReplacementBeforeEntry) return;

   bool bullish=false;
   double level=0.0,extreme=0.0;
   datetime sweepTime=0;
   if(!DetectSweepReclaim(bullish,level,extreme,sweepTime)) return;
   if((bullish && !InpLongEnabled) || (!bullish && !InpShortEnabled)) return;
   if(!ContextAllows(bullish)) return;

   if(g_campaign.active && !InpAllowReplacementBeforeEntry) return;

   ResetCampaign();
   g_campaign.active=true;
   g_campaign.bullish=bullish;
   g_campaign.created=TimeCurrent();
   g_campaign.sweepTime=sweepTime;
   g_campaign.liquidityLevel=level;
   g_campaign.sweepExtreme=extreme;
   g_campaign.id=StringFormat("%s-%I64d",bullish?"L":"S",(long)sweepTime);
   SetState(ASTRA_SWEEP_RECLAIMED,"M15 sweep and reclaim");
   SetState(ASTRA_WAITING_MSS,"Waiting for M5 MSS + displacement + FVG");
   DrawCampaignObjects();
}

void ProcessM5Campaign()
{
   if(!g_campaign.active) return;

   if(CampaignExpired())
   {
      if(!CampaignHasPosition())
      {
         SetState(ASTRA_EXPIRED,"Campaign time limit reached");
         ResetCampaign();
      }
      return;
   }

   if(!CampaignHasPosition() && !CandidateStillValid())
   {
      SetState(ASTRA_INVALIDATED,"Closed-candle invalidation");
      ResetCampaign();
      return;
   }

   if(g_campaign.state==ASTRA_WAITING_MSS || g_campaign.state==ASTRA_SWEEP_RECLAIMED)
   {
      if(ConfirmM5Signal())
      {
         SetState(ASTRA_ENTRY_ZONE_ACTIVE,"M5 MSS + DQI + FVG confirmed");
         DrawCampaignObjects();
      }
      return;
   }

   if(g_campaign.state==ASTRA_ENTRY_ZONE_ACTIVE && !CampaignHasPosition())
   {
      EvaluateE1();
      return;
   }

   if(CampaignHasPosition() && InpEnableScaleIns && g_campaign.entries<InpMaxEntries)
      EvaluateScaleIn();
}

bool DetectSweepReclaim(bool &bullish,double &level,double &extreme,datetime &sweepTime)
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   int need=MathMax(InpLiquidityLookback+5,30);
   if(CopyRates(_Symbol,InpLiquidityTF,0,need,r)<InpLiquidityLookback+3) return false;

   double atr=GetBufferValue(hM15ATR,0,1);
   if(atr<=0) return false;

   double priorLow=DBL_MAX,priorHigh=-DBL_MAX;
   for(int i=2;i<2+InpLiquidityLookback && i<ArraySize(r);i++)
   {
      priorLow=MathMin(priorLow,r[i].low);
      priorHigh=MathMax(priorHigh,r[i].high);
   }
   if(priorLow==DBL_MAX || priorHigh==-DBL_MAX) return false;

   double range=r[1].high-r[1].low;
   if(range<=0) return false;
   double body=MathAbs(r[1].close-r[1].open);
   if(body/range<InpMinReclaimBody) return false;

   double bullDepth=priorLow-r[1].low;
   bool bull=bullDepth>=atr*InpSweepMinATR &&
             bullDepth<=atr*InpSweepMaxATR &&
             r[1].close>priorLow;
   if(InpRequireDirectionalReclaim) bull=bull && r[1].close>r[1].open;

   double bearDepth=r[1].high-priorHigh;
   bool bear=bearDepth>=atr*InpSweepMinATR &&
             bearDepth<=atr*InpSweepMaxATR &&
             r[1].close<priorHigh;
   if(InpRequireDirectionalReclaim) bear=bear && r[1].close<r[1].open;

   if(!bull && !bear) return false;

   if(bull && bear)
   {
      if(bullDepth>=bearDepth) bear=false;
      else bull=false;
   }

   bullish=bull;
   level=bull?priorLow:priorHigh;
   extreme=bull?r[1].low:r[1].high;
   sweepTime=r[1].time;
   return true;
}

bool ContextAllows(bool bullish)
{
   if(InpRequireH4Bias)
   {
      int bias=GetH4Bias();
      if(bullish && bias!=1) return false;
      if(!bullish && bias!=-1) return false;
   }

   if(InpRequireH1Alignment)
   {
      double f=GetBufferValue(hH1Fast,0,1);
      double s=GetBufferValue(hH1Slow,0,1);
      double adx=GetBufferValue(hH1ADX,0,1);
      double plusDI=GetBufferValue(hH1ADX,1,1);
      double minusDI=GetBufferValue(hH1ADX,2,1);
      double close=iClose(_Symbol,InpH1TF,1);
      if(f<=0 || s<=0 || adx<InpMinADX || close<=0) return false;
      if(bullish)
      {
         if(!(close>f && f>s)) return false;
         if(InpRequireDIDirection && plusDI<=minusDI) return false;
      }
      else
      {
         if(!(close<f && f<s)) return false;
         if(InpRequireDIDirection && minusDI<=plusDI) return false;
      }
   }
   return true;
}

int GetH4Bias()
{
   double f=GetBufferValue(hH4Fast,0,1);
   double s=GetBufferValue(hH4Slow,0,1);
   double close=iClose(_Symbol,InpH4TF,1);
   if(f<=0 || s<=0 || close<=0) return 0;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   int b=MathMax(InpH4SwingBlock,2);
   if(CopyRates(_Symbol,InpH4TF,0,2*b+3,r)<2*b+2) return 0;

   double recentHigh=-DBL_MAX,recentLow=DBL_MAX,olderHigh=-DBL_MAX,olderLow=DBL_MAX;
   for(int i=1;i<=b;i++)
   {
      recentHigh=MathMax(recentHigh,r[i].high);
      recentLow=MathMin(recentLow,r[i].low);
   }
   for(int i=b+1;i<=2*b;i++)
   {
      olderHigh=MathMax(olderHigh,r[i].high);
      olderLow=MathMin(olderLow,r[i].low);
   }

   bool structureUp=(recentHigh>olderHigh || recentLow>olderLow);
   bool structureDown=(recentHigh<olderHigh || recentLow<olderLow);

   if(close>f && f>s && structureUp) return 1;
   if(close<f && f<s && structureDown) return -1;
   return 0;
}

bool ConfirmM5Signal()
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   int need=MathMax(MathMax(InpMSSLookback+5,InpVolumeMAPeriod+5),30);
   if(CopyRates(_Symbol,InpEntryTF,0,need,r)<need-1) return false;

   double atr=GetBufferValue(hM5ATR,0,1);
   if(atr<=0) return false;

   double breakLevel=g_campaign.bullish?-DBL_MAX:DBL_MAX;
   for(int i=2;i<2+InpMSSLookback && i<ArraySize(r);i++)
   {
      if(g_campaign.bullish) breakLevel=MathMax(breakLevel,r[i].high);
      else breakLevel=MathMin(breakLevel,r[i].low);
   }

   bool mss=g_campaign.bullish ? r[1].close>breakLevel : r[1].close<breakLevel;
   if(!mss) return false;

   double body=MathAbs(r[2].close-r[2].open);
   double range=r[2].high-r[2].low;
   if(range<=0 || body<atr*InpDisplacementATR || body/range<InpMinBodyEfficiency) return false;

   if(InpUseVolumeFilter)
   {
      double avg=0.0;
      int n=0;
      for(int i=3;i<3+InpVolumeMAPeriod && i<ArraySize(r);i++)
      {
         avg+=(double)r[i].tick_volume;
         n++;
      }
      if(n<=0 || avg<=0) return false;
      avg/=n;
      if((double)r[2].tick_volume<avg*InpVolumeMultiplier) return false;
   }

   double gap=0.0;
   if(g_campaign.bullish)
   {
      if(r[1].low<=r[3].high) return false;
      g_campaign.fvgLow=r[3].high;
      g_campaign.fvgHigh=r[1].low;
      gap=g_campaign.fvgHigh-g_campaign.fvgLow;
   }
   else
   {
      if(r[1].high>=r[3].low) return false;
      g_campaign.fvgLow=r[1].high;
      g_campaign.fvgHigh=r[3].low;
      gap=g_campaign.fvgHigh-g_campaign.fvgLow;
   }

   if(gap<atr*InpMinFVGATR || gap>atr*InpMaxFVGATR) return false;

   if(InpEntryStyle==ASTRA_FVG_MIDPOINT)
      g_campaign.idealEntry=(g_campaign.fvgLow+g_campaign.fvgHigh)/2.0;
   else if(InpEntryStyle==ASTRA_FVG_NEAR_EDGE)
      g_campaign.idealEntry=g_campaign.bullish?g_campaign.fvgHigh:g_campaign.fvgLow;
   else
      g_campaign.idealEntry=g_campaign.bullish?g_campaign.fvgLow:g_campaign.fvgHigh;

   g_campaign.stop=DetermineInitialStop();
   if(g_campaign.stop<=0) return false;
   if(g_campaign.bullish && g_campaign.stop>=g_campaign.idealEntry) return false;
   if(!g_campaign.bullish && g_campaign.stop<=g_campaign.idealEntry) return false;

   g_campaign.confirmTime=r[1].time;
   g_campaign.initialRiskPrice=MathAbs(g_campaign.idealEntry-g_campaign.stop);
   BuildTargets(g_campaign.idealEntry);
   return true;
}

double DetermineInitialStop()
{
   double atr=GetBufferValue(hM5ATR,0,1);
   if(atr<=0) return 0.0;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   int need=MathMax(InpStructureStopLookback+3,8);
   if(CopyRates(_Symbol,InpEntryTF,0,need,r)<need-1) return 0.0;

   if(g_campaign.bullish)
   {
      double structure=DBL_MAX;
      for(int i=1;i<=InpStructureStopLookback && i<ArraySize(r);i++)
         structure=MathMin(structure,r[i].low);
      double base=MathMin(g_campaign.sweepExtreme,structure);
      return NormalizePrice(base-atr*InpSLBufferATR);
   }

   double structure=-DBL_MAX;
   for(int i=1;i<=InpStructureStopLookback && i<ArraySize(r);i++)
      structure=MathMax(structure,r[i].high);
   double base=MathMax(g_campaign.sweepExtreme,structure);
   return NormalizePrice(base+atr*InpSLBufferATR);
}

void EvaluateE1()
{
   if(!NewEntryAllowed()) return;
   if(EntryExpired())
   {
      SetState(ASTRA_EXPIRED,"FVG retracement window expired");
      ResetCampaign();
      return;
   }

   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,3,r)<3) return;

   bool touched=g_campaign.idealEntry>=r[1].low && g_campaign.idealEntry<=r[1].high;
   bool reclaimed=g_campaign.bullish ? r[1].close>=g_campaign.idealEntry : r[1].close<=g_campaign.idealEntry;
   if(!touched || !reclaimed) return;

   double atr=GetBufferValue(hM5ATR,0,1);
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double entry=g_campaign.bullish?ask:bid;
   if(atr<=0 || entry<=0) return;

   double extension=MathAbs(entry-g_campaign.idealEntry)/atr;
   if(extension>InpHardRejectExtensionATR)
   {
      SetState(ASTRA_EXPIRED,"ENTRY_MISSED / DO_NOT_CHASE");
      ResetCampaign();
      return;
   }
   if(extension>InpMaxEntryExtensionATR) return;

   double risk=MathAbs(entry-g_campaign.stop);
   if(risk<=0) return;
   BuildTargets(entry);
   double rr=MathAbs(g_campaign.tp1-entry)/risk;
   if(rr<InpMinimumRR) return;

   if(OpenTranche(1))
   {
      g_campaignsToday++;
      SetState(ASTRA_BUILDING,"E1 active");
      DrawCampaignObjects();
   }
}

void EvaluateScaleIn()
{
   if(InpNoAddsAfterTP1 && g_campaign.tp1Done) return;
   if(!NewEntryAllowed()) return;

   double volume=0.0,avg=0.0;
   long dir=-1;
   if(!GetCampaignPositionStats(volume,avg,dir) || volume<=0 || avg<=0) return;

   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,8,r)<7) return;

   double risk=MathAbs(avg-g_campaign.stop);
   if(risk<=0) return;
   double close=r[1].close;
   double mfe=g_campaign.bullish ? (g_campaign.bestPrice-avg)/risk : (avg-g_campaign.bestPrice)/risk;

   bool directional=g_campaign.bullish ? r[1].close>r[1].open : r[1].close<r[1].open;
   double priorBreak=g_campaign.bullish?-DBL_MAX:DBL_MAX;
   for(int i=2;i<=4;i++)
   {
      if(g_campaign.bullish) priorBreak=MathMax(priorBreak,r[i].high);
      else priorBreak=MathMin(priorBreak,r[i].low);
   }
   bool breakout=g_campaign.bullish?close>priorBreak:close<priorBreak;
   bool protectedNow=AllStopsProtected(avg);

   int next=g_campaign.entries+1;
   bool qualify=false;

   if(next==2)
      qualify=directional && mfe>=InpE2MinMFER;
   else if(next==3)
      qualify=directional && breakout && mfe>=InpE3MinMFER;
   else if(next==4)
   {
      double e9=GetBufferValue(hM5EMA9,0,1);
      double e21=GetBufferValue(hM5EMA21,0,1);
      bool pullback=g_campaign.bullish ? (r[1].low<=e21 && close>=e9) : (r[1].high>=e21 && close<=e9);
      qualify=pullback && mfe>=InpE4MinMFER && (!InpRequireProtectedAdds || protectedNow);
   }
   else if(next==5)
      qualify=directional && breakout && mfe>=InpE5MinMFER && (!InpRequireProtectedAdds || protectedNow);

   if(!qualify) return;
   if(OpenTranche(next))
   {
      SetState(protectedNow?ASTRA_PROTECTED:ASTRA_BUILDING,StringFormat("E%d active",next));
      DrawCampaignObjects();
   }
}

bool OpenTranche(int stage)
{
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double entry=g_campaign.bullish?ask:bid;
   if(entry<=0 || g_campaign.stop<=0) return false;
   if(!StopsValid(entry,g_campaign.stop,g_campaign.bullish)) return false;

   double vol=DetermineEntryVolume(entry,g_campaign.stop);
   if(vol<=0)
   {
      LogEvent("RISK_REJECT",entry,"Volume calculation returned zero");
      return false;
   }

   if(!CanAddRisk(vol,entry,g_campaign.stop))
   {
      LogEvent("RISK_REJECT",entry,StringFormat("E%d rejected by campaign risk cap",stage));
      return false;
   }

   string comment=StringFormat("ASTRA E%d %s",stage,g_campaign.bullish?"BUY":"SELL");
   bool ok=g_campaign.bullish ? trade.Buy(vol,_Symbol,0,g_campaign.stop,0,comment)
                              : trade.Sell(vol,_Symbol,0,g_campaign.stop,0,comment);
   if(!ok)
   {
      LogEvent("ORDER_FAIL",entry,trade.ResultRetcodeDescription());
      return false;
   }

   uint rc=trade.ResultRetcode();
   if(rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL && rc!=TRADE_RETCODE_PLACED)
   {
      LogEvent("ORDER_REJECT",entry,trade.ResultRetcodeDescription());
      return false;
   }

   g_campaign.entries++;
   g_campaign.lastEntryTime=TimeCurrent();

   double total=0.0,avg=0.0;
   long dir=-1;
   if(GetCampaignPositionStats(total,avg,dir))
   {
      g_campaign.peakVolume=MathMax(g_campaign.peakVolume,total);
      g_campaign.initialRiskPrice=MathAbs(avg-g_campaign.stop);
      if(g_campaign.bestPrice<=0) g_campaign.bestPrice=avg;
      BuildTargets(avg);
   }

   LogEvent(StringFormat("E%d_OPEN",stage),entry,StringFormat("volume=%.2f",vol));
   return true;
}

double DetermineEntryVolume(double entry,double sl)
{
   double minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maxLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minLot<=0 || maxLot<=0 || step<=0) return 0.0;

   double current=CampaignCurrentVolume();
   double remaining=InpCampaignLots-current;
   if(remaining<minLot-1e-9) return 0.0;

   double vol=0.0;
   if(InpSizingMode==ASTRA_FIXED_LOT)
      vol=MathMin(InpEntryLot,remaining);
   else
   {
      double equity=AccountInfoDouble(ACCOUNT_EQUITY);
      double riskMoney=equity*(InpRiskPercent/100.0)/MathMax(InpMaxEntries,1);
      double loss1=LossAtStopForVolume(1.0,entry,sl,g_campaign.bullish);
      if(loss1<=0 || riskMoney<=0) return 0.0;
      vol=riskMoney/loss1;
      vol=MathMin(vol,remaining);
   }

   vol=MathFloor(vol/step+1e-9)*step;
   if(vol<minLot) return 0.0;
   if(vol>maxLot) vol=maxLot;
   return NormalizeVolume(vol);
}

bool CanAddRisk(double newVol,double entry,double sl)
{
   if(newVol<=0) return false;
   if(CampaignCurrentVolume()+newVol>InpCampaignLots+1e-9) return false;
   if(InpMaxCampaignRiskPercent<=0) return true;

   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0) return false;
   double allowed=equity*InpMaxCampaignRiskPercent/100.0;

   double risk=0.0;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      long t=PositionGetInteger(POSITION_TYPE);
      double op=PositionGetDouble(POSITION_PRICE_OPEN);
      double pv=PositionGetDouble(POSITION_VOLUME);
      double psl=PositionGetDouble(POSITION_SL);
      if(psl<=0) psl=sl;
      risk+=LossAtStopForVolume(pv,op,psl,t==POSITION_TYPE_BUY);
   }

   risk+=LossAtStopForVolume(newVol,entry,sl,g_campaign.bullish);
   return risk<=allowed+0.01;
}

double LossAtStopForVolume(double vol,double entry,double sl,bool bullish)
{
   if(vol<=0 || entry<=0 || sl<=0) return 0.0;
   double profit=0.0;
   ENUM_ORDER_TYPE type=bullish?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,vol,entry,sl,profit)) return 0.0;
   return MathAbs(profit);
}

void BuildTargets(double entry)
{
   double risk=MathAbs(entry-g_campaign.stop);
   if(risk<=0) return;

   double t1=g_campaign.bullish?entry+risk*InpTP1R:entry-risk*InpTP1R;
   if(InpUseStructuralTP1)
   {
      double structural=OpposingLiquidity();
      if(structural>0)
      {
         double rr=g_campaign.bullish?(structural-entry)/risk:(entry-structural)/risk;
         if(rr>=InpMinimumRR && rr<=InpTP2R)
            t1=structural;
      }
   }

   double t2=g_campaign.bullish?entry+risk*InpTP2R:entry-risk*InpTP2R;
   double t3=g_campaign.bullish?entry+risk*InpTP3R:entry-risk*InpTP3R;

   if(g_campaign.bullish)
   {
      t2=MathMax(t2,t1+risk*0.25);
      t3=MathMax(t3,t2+risk*0.25);
   }
   else
   {
      t2=MathMin(t2,t1-risk*0.25);
      t3=MathMin(t3,t2-risk*0.25);
   }

   g_campaign.tp1=NormalizePrice(t1);
   g_campaign.tp2=NormalizePrice(t2);
   g_campaign.tp3=NormalizePrice(t3);
}

double OpposingLiquidity()
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   int n=MathMax(InpLiquidityLookback+2,10);
   if(CopyRates(_Symbol,InpLiquidityTF,0,n,r)<n-1) return 0.0;

   if(g_campaign.bullish)
   {
      double high=-DBL_MAX;
      for(int i=1;i<=InpLiquidityLookback && i<ArraySize(r);i++) high=MathMax(high,r[i].high);
      return high==-DBL_MAX?0.0:high;
   }

   double low=DBL_MAX;
   for(int i=1;i<=InpLiquidityLookback && i<ArraySize(r);i++) low=MathMin(low,r[i].low);
   return low==DBL_MAX?0.0:low;
}

void ManageOpenCampaign()
{
   if(!g_campaign.active) return;

   double total=0.0,avg=0.0;
   long dir=-1;
   bool has=GetCampaignPositionStats(total,avg,dir);

   if(!has)
   {
      if(g_campaign.entries>0)
      {
         SetState(ASTRA_COMPLETED,"Campaign position fully closed");
         ResetCampaign();
      }
      return;
   }

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double price=g_campaign.bullish?bid:ask;
   if(price<=0 || avg<=0) return;

   if(g_campaign.bestPrice<=0) g_campaign.bestPrice=price;
   if(g_campaign.bullish) g_campaign.bestPrice=MathMax(g_campaign.bestPrice,price);
   else g_campaign.bestPrice=MathMin(g_campaign.bestPrice,price);

   double risk=MathAbs(avg-g_campaign.stop);
   if(risk<=0) risk=g_campaign.initialRiskPrice;
   if(risk<=0) return;
   double rr=g_campaign.bullish?(price-avg)/risk:(avg-price)/risk;

   if(!g_campaign.tp1Done && PriceReached(price,g_campaign.tp1))
   {
      CloseCampaignPercent(InpTP1ClosePercent);
      g_campaign.tp1Done=true;
      SetState(ASTRA_PARTIAL_EXIT,"TP1 reached");
      LogEvent("TP1",price,"Partial exit");
   }

   if(!g_campaign.tp2Done && PriceReached(price,g_campaign.tp2))
   {
      CloseCampaignPercent(InpTP2ClosePercent);
      g_campaign.tp2Done=true;
      SetState(ASTRA_PARTIAL_EXIT,"TP2 reached");
      LogEvent("TP2",price,"Partial exit");
   }

   if(!g_campaign.tp3Done && PriceReached(price,g_campaign.tp3))
   {
      CloseCampaignPercent(InpTP3ClosePercent);
      g_campaign.tp3Done=true;
      if(InpUseRunner) SetState(ASTRA_RUNNER,"TP3 reached; runner active");
      else CloseAllCampaignPositions();
      LogEvent("TP3",price,InpUseRunner?"Runner active":"Campaign exit");
   }

   if(InpUseSmartProtection && rr>=InpProtectionTriggerR)
      ApplyStructuralProtection(avg);

   if(InpUseRunner && (g_campaign.tp3Done || rr>=InpTrailStartR))
      ApplyRunnerTrail(avg);
}

bool PriceReached(double price,double target)
{
   if(target<=0) return false;
   return g_campaign.bullish?price>=target:price<=target;
}

void ApplyStructuralProtection(double avg)
{
   double atr=GetBufferValue(hM5ATR,0,1);
   if(atr<=0) return;

   double structure=RecentStructureExtreme(g_campaign.bullish,InpTrailStructureLookback);
   if(structure<=0) return;

   double newSL=g_campaign.bullish?structure-atr*InpProtectionBufferATR
                                  :structure+atr*InpProtectionBufferATR;
   newSL=NormalizePrice(newSL);

   if(g_campaign.bullish && newSL<=g_campaign.stop) return;
   if(!g_campaign.bullish && newSL>=g_campaign.stop) return;

   if(ModifyCampaignStops(newSL))
   {
      if(g_campaign.bullish) g_campaign.stop=MathMax(g_campaign.stop,newSL);
      else g_campaign.stop=MathMin(g_campaign.stop,newSL);
      if(AllStopsProtected(avg)) SetState(ASTRA_PROTECTED,"Structural protection active");
   }
}

void ApplyRunnerTrail(double avg)
{
   double atr=GetBufferValue(hM5ATR,0,1);
   if(atr<=0) return;
   double structure=RecentStructureExtreme(g_campaign.bullish,InpTrailStructureLookback);
   if(structure<=0) return;

   double newSL=g_campaign.bullish?structure-atr*InpTrailATRBuffer
                                  :structure+atr*InpTrailATRBuffer;
   newSL=NormalizePrice(newSL);

   if(g_campaign.bullish && newSL<=g_campaign.stop) return;
   if(!g_campaign.bullish && newSL>=g_campaign.stop) return;

   if(ModifyCampaignStops(newSL))
   {
      if(g_campaign.bullish) g_campaign.stop=MathMax(g_campaign.stop,newSL);
      else g_campaign.stop=MathMin(g_campaign.stop,newSL);
   }
}

double RecentStructureExtreme(bool bullish,int lookback)
{
   MqlRates r[];
   ArraySetAsSeries(r,true);
   int n=MathMax(lookback+2,5);
   if(CopyRates(_Symbol,InpEntryTF,0,n,r)<n-1) return 0.0;

   if(bullish)
   {
      double low=DBL_MAX;
      for(int i=1;i<=lookback && i<ArraySize(r);i++) low=MathMin(low,r[i].low);
      return low==DBL_MAX?0.0:low;
   }

   double high=-DBL_MAX;
   for(int i=1;i<=lookback && i<ArraySize(r);i++) high=MathMax(high,r[i].high);
   return high==-DBL_MAX?0.0:high;
}

bool ModifyCampaignStops(double newSL)
{
   bool any=false;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;

      long type=PositionGetInteger(POSITION_TYPE);
      double oldSL=PositionGetDouble(POSITION_SL);
      double price=type==POSITION_TYPE_BUY?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      bool better=type==POSITION_TYPE_BUY ? (oldSL==0 || newSL>oldSL) : (oldSL==0 || newSL<oldSL);
      if(!better || !StopsValid(price,newSL,type==POSITION_TYPE_BUY)) continue;

      if(trade.PositionModify(ticket,newSL,0)) any=true;
   }
   return any;
}

bool AllStopsProtected(double avg)
{
   bool found=false;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      found=true;
      double sl=PositionGetDouble(POSITION_SL);
      if(sl<=0) return false;
      if(g_campaign.bullish && sl<avg) return false;
      if(!g_campaign.bullish && sl>avg) return false;
   }
   return found;
}

bool ReduceNettingPosition(double closeVol,long positionType)
{
   if(closeVol<=0) return false;
   bool ok=(positionType==POSITION_TYPE_BUY)
           ? trade.Sell(closeVol,_Symbol,0,0,0,"ASTRA partial close")
           : trade.Buy(closeVol,_Symbol,0,0,0,"ASTRA partial close");
   if(!ok) return false;
   uint rc=trade.ResultRetcode();
   return rc==TRADE_RETCODE_DONE || rc==TRADE_RETCODE_DONE_PARTIAL || rc==TRADE_RETCODE_PLACED;
}

void CloseCampaignPercent(double pct)
{
   if(pct<=0) return;
   double total=CampaignCurrentVolume();
   if(total<=0) return;

   double target=g_campaign.peakVolume*pct/100.0;
   target=MathMin(target,total);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(step<=0 || minLot<=0) return;
   target=MathFloor(target/step+1e-9)*step;
   if(target<minLot) return;

   ENUM_ACCOUNT_MARGIN_MODE marginMode=(ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   bool hedging=(marginMode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);

   double remaining=target;
   for(int i=PositionsTotal()-1;i>=0 && remaining>=minLot-1e-9;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;

      double pv=PositionGetDouble(POSITION_VOLUME);
      long positionType=PositionGetInteger(POSITION_TYPE);
      double closeVol=MathMin(pv,remaining);
      closeVol=MathFloor(closeVol/step+1e-9)*step;
      if(closeVol<minLot) continue;

      bool ok=false;
      if(closeVol>=pv-step/2.0)
         ok=trade.PositionClose(ticket);
      else if(hedging)
         ok=trade.PositionClosePartial(ticket,closeVol);
      else
         ok=ReduceNettingPosition(closeVol,positionType);

      if(ok) remaining-=closeVol;
   }
}

void CloseAllCampaignPositions()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         trade.PositionClose(ticket);
   }
}

bool GetCampaignPositionStats(double &volume,double &avg,long &dir)
{
   volume=0.0;
   avg=0.0;
   dir=-1;
   double weighted=0.0;

   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || (ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      long t=PositionGetInteger(POSITION_TYPE);
      double v=PositionGetDouble(POSITION_VOLUME);
      double p=PositionGetDouble(POSITION_PRICE_OPEN);
      if(v<=0 || p<=0) continue;
      if(dir==-1) dir=t;
      if(t!=dir) return false;
      volume+=v;
      weighted+=v*p;
   }

   if(volume<=0) return false;
   avg=weighted/volume;
   return true;
}

double CampaignCurrentVolume()
{
   double v=0.0,a=0.0;
   long d=-1;
   if(!GetCampaignPositionStats(v,a,d)) return 0.0;
   return v;
}

bool CampaignHasPosition()
{
   return CampaignCurrentVolume()>0.0;
}

bool CandidateStillValid()
{
   if(!g_campaign.active) return false;
   MqlRates r[];
   ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,InpEntryTF,0,3,r)<3) return true;
   if(g_campaign.bullish && r[1].close<g_campaign.sweepExtreme) return false;
   if(!g_campaign.bullish && r[1].close>g_campaign.sweepExtreme) return false;
   return true;
}

bool CampaignExpired()
{
   if(!g_campaign.active) return false;
   if(InpCampaignMaxHours>0 && TimeCurrent()-g_campaign.created>InpCampaignMaxHours*3600) return true;
   if(g_campaign.entries==0 && g_campaign.sweepTime>0)
   {
      int s=iBarShift(_Symbol,InpLiquidityTF,g_campaign.sweepTime,false);
      if(s>InpSetupExpiryM15Bars) return true;
   }
   return false;
}

bool EntryExpired()
{
   if(g_campaign.confirmTime<=0) return false;
   int s=iBarShift(_Symbol,InpEntryTF,g_campaign.confirmTime,false);
   return s>InpEntryExpiryM5Bars;
}

bool NewEntryAllowed()
{
   if(g_emergencyHalt) return false;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return false;
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)) return false;
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;
   if(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_MODE)!=SYMBOL_TRADE_MODE_FULL) return false;
   if(!SessionAllowed()) return false;
   if(InpUseSpreadFilter && CurrentSpreadPoints()>InpMaxSpreadPoints) return false;
   if(g_campaignsToday>=InpMaxDailyCampaigns && g_campaign.entries==0) return false;
   if(g_consecutiveLosses>=InpMaxConsecutiveLosses) return false;

   if(InpMaxDailyLossPercent>0 && g_dayStartEquity>0)
   {
      double eq=AccountInfoDouble(ACCOUNT_EQUITY);
      double loss=(g_dayStartEquity-eq)/g_dayStartEquity*100.0;
      if(loss>=InpMaxDailyLossPercent) return false;
   }
   return true;
}

bool SessionAllowed()
{
   if(!InpUseLondon && !InpUseNewYork) return true;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(),dt);
   int h=dt.hour;
   if(InpSessionHoursAreUTC)
   {
      h-=InpBrokerUTCOffsetHours;
      if(InpUseDSTAdjustment) h-=1;
      while(h<0) h+=24;
      while(h>=24) h-=24;
   }
   bool london=InpUseLondon && HourInWindow(h,InpLondonStartHour,InpLondonEndHour);
   bool ny=InpUseNewYork && HourInWindow(h,InpNewYorkStartHour,InpNewYorkEndHour);
   return london || ny;
}

bool HourInWindow(int h,int start,int end)
{
   if(start==end) return true;
   if(start<end) return h>=start && h<end;
   return h>=start || h<end;
}

double CurrentSpreadPoints()
{
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(bid<=0 || ask<=0 || point<=0) return DBL_MAX;
   return (ask-bid)/point;
}

bool StopsValid(double price,double sl,bool bullish)
{
   if(price<=0 || sl<=0) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   long stops=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   long freeze=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist=MathMax(stops,freeze)*point;
   if(bullish) return sl<price && price-sl>=minDist;
   return sl>price && sl-price>=minDist;
}

void UpdateEquityProtection()
{
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq<=0) return;
   if(g_equityPeak<=0 || eq>g_equityPeak) g_equityPeak=eq;
   if(InpMaxEquityDDPercent>0 && g_equityPeak>0)
   {
      double dd=(g_equityPeak-eq)/g_equityPeak*100.0;
      if(dd>=InpMaxEquityDDPercent && !g_emergencyHalt)
      {
         g_emergencyHalt=true;
         LogEvent("EMERGENCY_HALT",eq,StringFormat("Equity drawdown %.2f%%",dd));
      }
   }
}

void ResetDailyStats()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(),dt);
   g_dayKey=dt.year*1000+dt.day_of_year;
   g_dayStartEquity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_campaignsToday=0;
}

void ResetDailyStatsIfNeeded()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(),dt);
   int key=dt.year*1000+dt.day_of_year;
   if(key!=g_dayKey) ResetDailyStats();
}

bool IsNewBar(ENUM_TIMEFRAMES tf,datetime &last)
{
   datetime t=iTime(_Symbol,tf,0);
   if(t<=0) return false;
   if(t!=last)
   {
      last=t;
      return true;
   }
   return false;
}

double GetBufferValue(int handle,int buffer,int shift)
{
   double v[1];
   if(handle==INVALID_HANDLE) return 0.0;
   if(CopyBuffer(handle,buffer,shift,1,v)!=1) return 0.0;
   return v[0];
}

void SetState(ENUM_ASTRA_CAMPAIGN_STATE state,string reason)
{
   g_campaign.state=state;
   LogEvent("STATE",0.0,EnumToString(state)+" | "+reason);
}

void ResetCampaign()
{
   g_campaign.active=false;
   g_campaign.bullish=true;
   g_campaign.state=ASTRA_IDLE;
   g_campaign.id="";
   g_campaign.created=0;
   g_campaign.sweepTime=0;
   g_campaign.confirmTime=0;
   g_campaign.lastEntryTime=0;
   g_campaign.liquidityLevel=0.0;
   g_campaign.sweepExtreme=0.0;
   g_campaign.fvgLow=0.0;
   g_campaign.fvgHigh=0.0;
   g_campaign.idealEntry=0.0;
   g_campaign.stop=0.0;
   g_campaign.tp1=0.0;
   g_campaign.tp2=0.0;
   g_campaign.tp3=0.0;
   g_campaign.initialRiskPrice=0.0;
   g_campaign.bestPrice=0.0;
   g_campaign.peakVolume=0.0;
   g_campaign.entries=0;
   g_campaign.tp1Done=false;
   g_campaign.tp2Done=false;
   g_campaign.tp3Done=false;
   ClearVisuals();
}

double NormalizePrice(double p)
{
   return NormalizeDouble(p,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(double v)
{
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0) return 0.0;
   int digits=0;
   double x=step;
   while(x<1.0 && digits<8)
   {
      x*=10.0;
      digits++;
   }
   return NormalizeDouble(v,digits);
}

void OpenLog()
{
   if(!InpCSVLogging) return;
   g_logHandle=FileOpen(InpCSVFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI);
   if(g_logHandle==INVALID_HANDLE)
   {
      Print("ASTRA CSV open failed: ",GetLastError());
      return;
   }
   if(FileSize(g_logHandle)==0)
   {
      FileWrite(g_logHandle,
         "time","campaign_id","event","state","direction","price","liquidity",
         "sweep_extreme","fvg_low","fvg_high","ideal_entry","stop","tp1","tp2","tp3",
         "entries","volume","spread_points","equity","note");
   }
   FileSeek(g_logHandle,0,SEEK_END);
}

void LogEvent(string event,double price,string note)
{
   if(g_logHandle==INVALID_HANDLE) return;
   double vol=CampaignCurrentVolume();
   FileWrite(g_logHandle,
      TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
      g_campaign.id,event,EnumToString(g_campaign.state),
      g_campaign.bullish?"BUY":"SELL",
      DoubleToString(price,_Digits),
      DoubleToString(g_campaign.liquidityLevel,_Digits),
      DoubleToString(g_campaign.sweepExtreme,_Digits),
      DoubleToString(g_campaign.fvgLow,_Digits),
      DoubleToString(g_campaign.fvgHigh,_Digits),
      DoubleToString(g_campaign.idealEntry,_Digits),
      DoubleToString(g_campaign.stop,_Digits),
      DoubleToString(g_campaign.tp1,_Digits),
      DoubleToString(g_campaign.tp2,_Digits),
      DoubleToString(g_campaign.tp3,_Digits),
      g_campaign.entries,
      DoubleToString(vol,2),
      DoubleToString(CurrentSpreadPoints(),1),
      DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),
      note);
   FileFlush(g_logHandle);
}

void DrawCampaignObjects()
{
   if(!InpVisualDebug || !g_campaign.active) return;
   DrawHLine("ASTRA_LIQ",g_campaign.liquidityLevel);
   DrawHLine("ASTRA_ENTRY",g_campaign.idealEntry);
   DrawHLine("ASTRA_SL",g_campaign.stop);
   DrawHLine("ASTRA_TP1",g_campaign.tp1);
   DrawHLine("ASTRA_TP2",g_campaign.tp2);
   DrawHLine("ASTRA_TP3",g_campaign.tp3);
}

void DrawHLine(string name,double price)
{
   if(price<=0) return;
   if(ObjectFind(0,name)<0)
      ObjectCreate(0,name,OBJ_HLINE,0,0,price);
   else
      ObjectSetDouble(0,name,OBJPROP_PRICE,price);
}

void ClearVisuals()
{
   string names[6]={"ASTRA_LIQ","ASTRA_ENTRY","ASTRA_SL","ASTRA_TP1","ASTRA_TP2","ASTRA_TP3"};
   for(int i=0;i<6;i++) ObjectDelete(0,names[i]);
}

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double payoff=TesterStatistics(STAT_EXPECTED_PAYOFF);

   // Custom robustness criterion for later controlled optimization.
   // It intentionally penalizes tiny samples and drawdown instead of
   // maximizing headline balance or win rate.
   if(trades<30.0 || pf<=0.0) return -1000000.0+trades;
   double samplePenalty=MathMin(1.0,trades/100.0);
   double drawdownPenalty=MathMax(0.05,1.0-dd/100.0);
   return pf*samplePenalty*drawdownPenalty*MathMax(0.01,payoff);
}
//+------------------------------------------------------------------+
