//+------------------------------------------------------------------+
//|                                             FVG_Scalper_V2.mq5   |
//|              FVG scalper - retest + displacement + HTF bias      |
//|              Designed for XAUUSD / M5                           |
//+------------------------------------------------------------------+
#property strict
#property version   "2.11"
#property description "FVG V2.11: persistent zones, intrabar retest, displacement confirmation, HTF bias, rejection confirmation, safer risk and staged management. Fixes: InpOneTradePerFVG now functional, InpAutoCompoundLots/InpCompoundingBaseBalance now functional, added trade-permission checks."

#include <Trade/Trade.mqh>
CTrade trade;

input group "Strategy"
input ENUM_TIMEFRAMES InpEntryTF = PERIOD_M1;
input ENUM_TIMEFRAMES InpBiasTF = PERIOD_M1;
input int InpBiasFastEMA = 20;
input int InpBiasSlowEMA = 50;
input bool InpUseBiasFilter = false;
input bool InpRequireMidpoint = false;
input bool InpRequireRejection = true;
input double InpMinFVG_ATR = 0.15;
input double InpMinBody_ATR = 0.50;
input double InpMinBodyRatio = 0.60;
input int InpMaxFVG_Bars = 1000;
input bool InpReplaceWithNewFVG = true;
input bool InpOneTradePerFVG = true;

input group "Risk Management"
input double InpRiskPercent = 10.0;
input bool InpAutoCompoundLots = true;
input double InpCompoundingBaseBalance = 100.0;
input double InpRewardRisk = 30.0;
input double InpMaxSL_ATR = 3.0;
input int InpATRPeriod = 14;
input double InpSL_ATR_Buffer = 0.15;
input bool InpUseProfitLock = true;
input double InpLock1TriggerRR = 0.50;
input double InpLock1RR = 0.10;
input double InpLock2TriggerRR = 1.00;
input double InpLock2RR = 0.35;
input double InpTrailStartRR = 1.50;
input double InpTrail_ATR = 0.10;

input group "Sessions"
input bool InpUseSession1 = true;
input int InpSession1Start = 0;
input int InpSession1End = 0;
input bool InpUseSession2 = true;
input int InpSession2Start = 0;
input int InpSession2End = 0;
input int InpMaxSpreadPoints = 80;
input int InpMaxTradesDay = 1000;
input double InpDailyLossPct = 0.0;
input bool InpOnePosition = true;

input group "Execution"
input ulong InpMagic = 26081102;
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
};

int hATR = INVALID_HANDLE;
int hFastEMA = INVALID_HANDLE;
int hSlowEMA = INVALID_HANDLE;
datetime g_lastBar = 0;
FVGZone g_zone;
int g_dayKey = -1;
int g_tradesToday = 0;
double g_dayStartEquity = 0.0;

int OnInit()
{
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   hATR = iATR(_Symbol, InpEntryTF, InpATRPeriod);
   hFastEMA = iMA(_Symbol, InpBiasTF, InpBiasFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   hSlowEMA = iMA(_Symbol, InpBiasTF, InpBiasSlowEMA, 0, MODE_EMA, PRICE_CLOSE);

   if(hATR == INVALID_HANDLE || hFastEMA == INVALID_HANDLE || hSlowEMA == INVALID_HANDLE)
      return INIT_FAILED;

   g_zone.valid = false;
   g_zone.traded = false;
   ResetDailyStats();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hATR != INVALID_HANDLE) IndicatorRelease(hATR);
   if(hFastEMA != INVALID_HANDLE) IndicatorRelease(hFastEMA);
   if(hSlowEMA != INVALID_HANDLE) IndicatorRelease(hSlowEMA);
}

void OnTick()
{
   ResetDailyStatsIfNeeded();
   ManageOpenPosition();

   if(IsNewBar())
      UpdateFVG();

   if(!TradingAllowed()) return;
   if(InpOnePosition && HasOurPosition()) return;
   if(g_tradesToday >= InpMaxTradesDay) return;
   if(!g_zone.valid) return;
   if(InpOneTradePerFVG && g_zone.traded) return;
   if(!BiasAllows(g_zone.bullish)) return;
   if(!ZoneStillValid()) { g_zone.valid = false; return; }

   TryFVGEntry();
}

void UpdateFVG()
{
   FVGZone newest;
   if(!FindNewestFVG(newest)) return;

   if(!g_zone.valid || (InpReplaceWithNewFVG && newest.formed > g_zone.formed) || FVGExpired(g_zone))
      g_zone = newest;
}

bool FindNewestFVG(FVGZone &z)
{
   z.valid = false;
   z.traded = false;

   MqlRates r[];
   double atr[];
   ArraySetAsSeries(r, true);
   ArraySetAsSeries(atr, true);

   int need = MathMax(InpMaxFVG_Bars + 5, 30);
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

      if(oh < nl)
      {
         double gap = nl-oh;
         if(gap >= a*InpMinFVG_ATR && mc > mo)
         {
            z.valid=true; z.bullish=true; z.low=oh; z.high=nl; z.formed=r[s].time; z.shift=s; z.traded=false;
            return true;
         }
      }

      if(ol > nh)
      {
         double gap = ol-nh;
         if(gap >= a*InpMinFVG_ATR && mc < mo)
         {
            z.valid=true; z.bullish=false; z.low=nh; z.high=ol; z.formed=r[s].time; z.shift=s; z.traded=false;
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

void TryFVGEntry()
{
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(bid<=0 || ask<=0) return;

   double midpoint=(g_zone.low+g_zone.high)/2.0;

   if(g_zone.bullish)
   {
      if(ask < g_zone.low || ask > g_zone.high) return;
      if(InpRequireMidpoint && ask > midpoint) return;
      if(InpRequireRejection && !BullishRejection()) return;
      if(OpenTrade(true,g_zone)) g_zone.traded=true;
   }
   else
   {
      if(bid < g_zone.low || bid > g_zone.high) return;
      if(InpRequireMidpoint && bid < midpoint) return;
      if(InpRequireRejection && !BearishRejection()) return;
      if(OpenTrade(false,g_zone)) g_zone.traded=true;
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
   double f[2],s[2]; ArraySetAsSeries(f,true); ArraySetAsSeries(s,true);
   if(CopyBuffer(hFastEMA,0,0,2,f)<2) return false;
   if(CopyBuffer(hSlowEMA,0,0,2,s)<2) return false;
   return bullish ? f[1]>s[1] : f[1]<s[1];
}

bool OpenTrade(bool bullish,const FVGZone &z)
{
   double atr=GetATR();
   if(atr<=0) return false;
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   double entry=bullish?ask:bid;
   double sl,tp;

   if(bullish)
   {
      sl=z.low-atr*InpSL_ATR_Buffer;
      double risk=entry-sl;
      if(risk<=0 || risk>atr*InpMaxSL_ATR) return false;
      tp=entry+risk*InpRewardRisk;
   }
   else
   {
      sl=z.high+atr*InpSL_ATR_Buffer;
      double risk=sl-entry;
      if(risk<=0 || risk>atr*InpMaxSL_ATR) return false;
      tp=entry-risk*InpRewardRisk;
   }

   sl=NormalizePrice(sl); tp=NormalizePrice(tp);
   if(!StopsAreValid(entry,sl,tp,bullish)) return false;

   double volume=CalculateVolume(entry,sl,bullish);
   if(volume<=0) return false;

   bool ok=bullish ? trade.Buy(volume,_Symbol,0,sl,tp,"FVG V2 Buy")
                   : trade.Sell(volume,_Symbol,0,sl,tp,"FVG V2 Sell");
   if(!ok) { Print("Trade failed: ",trade.ResultRetcodeDescription()); return false; }

   uint rc=trade.ResultRetcode();
   if(rc!=TRADE_RETCODE_DONE && rc!=TRADE_RETCODE_DONE_PARTIAL && rc!=TRADE_RETCODE_PLACED)
   { Print("Trade rejected: ",trade.ResultRetcodeDescription()); return false; }

   g_tradesToday++;
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

double CalculateVolume(double entry,double sl,bool bullish)
{
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0) return 0;

   // Position sizing base:
   // - InpAutoCompoundLots=true  -> risk InpRiskPercent of CURRENT equity,
   //   so lot size compounds up as the account grows (and shrinks in drawdown).
   // - InpAutoCompoundLots=false -> risk InpRiskPercent of the FIXED
   //   InpCompoundingBaseBalance instead, so lot size stays flat regardless
   //   of account growth/drawdown (no compounding).
   double sizingBase = InpAutoCompoundLots ? equity : InpCompoundingBaseBalance;
   if(sizingBase<=0.0) sizingBase=equity;
   double riskMoney=sizingBase*InpRiskPercent/100.0;
   if(riskMoney<=0) return 0;

   double minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maxLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minLot<=0 || maxLot<=0 || step<=0) return 0;

   double lossOneLot=0;
   ENUM_ORDER_TYPE type=bullish?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,lossOneLot)) return 0;
   lossOneLot=MathAbs(lossOneLot);
   if(lossOneLot<=0) return 0;

   double volume=MathFloor((riskMoney/lossOneLot)/step)*step;
   if(volume<minLot) return 0;
   if(volume>maxLot) volume=maxLot;
   return NormalizeVolume(volume);
}

void ManageOpenPosition()
{
   if(!HasOurPosition()) return;
   ulong ticket=GetOurPositionTicket();
   if(ticket==0 || !PositionSelectByTicket(ticket)) return;

   long type=PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   double price=(type==POSITION_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_BID):SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(open<=0 || price<=0 || tp<=0 || InpRewardRisk<=0) return;

   double initialRisk=MathAbs(tp-open)/InpRewardRisk;
   if(initialRisk<=0) return;
   double profitDist=(type==POSITION_TYPE_BUY)?price-open:open-price;
   double rr=profitDist/initialRisk;
   if(rr<=0) return;

   if(InpUseProfitLock)
   {
      double lockRR=-1;
      if(rr>=InpLock2TriggerRR) lockRR=InpLock2RR;
      else if(rr>=InpLock1TriggerRR) lockRR=InpLock1RR;
      if(lockRR>=0)
      {
         double newSL=(type==POSITION_TYPE_BUY)?open+initialRisk*lockRR:open-initialRisk*lockRR;
         newSL=NormalizePrice(newSL);
         if(IsBetterSL(type,sl,newSL) && StopsAreValid(price,newSL,tp,type==POSITION_TYPE_BUY))
            trade.PositionModify(ticket,newSL,tp);
      }
   }

   if(rr>=InpTrailStartRR)
   {
      double atr=GetATR();
      if(atr<=0) return;
      double newSL=(type==POSITION_TYPE_BUY)?price-atr*InpTrail_ATR:price+atr*InpTrail_ATR;
      double floorSL=(type==POSITION_TYPE_BUY)?open+initialRisk*InpLock2RR:open-initialRisk*InpLock2RR;
      if(type==POSITION_TYPE_BUY) newSL=MathMax(newSL,floorSL); else newSL=MathMin(newSL,floorSL);
      newSL=NormalizePrice(newSL);
      if(IsBetterSL(type,sl,newSL) && StopsAreValid(price,newSL,tp,type==POSITION_TYPE_BUY))
         trade.PositionModify(ticket,newSL,tp);
   }
}

bool IsBetterSL(long type,double oldSL,double newSL)
{
   if(type==POSITION_TYPE_BUY) return oldSL==0 || newSL>oldSL;
   return oldSL==0 || newSL<oldSL;
}

bool HasOurPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i); if(t==0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   return false;
}

ulong GetOurPositionTicket()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong t=PositionGetTicket(i); if(t==0 || !PositionSelectByTicket(t)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic) return t;
   }
   return 0;
}

double GetATR()
{
   double v[2]; ArraySetAsSeries(v,true);
   if(CopyBuffer(hATR,0,0,2,v)<2) return 0;
   return v[1];
}

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

   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID),ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK),p=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(bid<=0 || ask<=0 || p<=0) return false;
   if((ask-bid)/p > InpMaxSpreadPoints) return false;

   if(InpDailyLossPct>0 && g_dayStartEquity>0)
   {
      double eq=AccountInfoDouble(ACCOUNT_EQUITY);
      if((g_dayStartEquity-eq)/g_dayStartEquity*100.0 >= InpDailyLossPct) return false;
   }
   return true;
}

bool HourInWindow(int h,int start,int end)
{
   if(start==end) return true;
   if(start<end) return h>=start && h<end;
   return h>=start || h<end;
}

bool IsNewBar()
{
   datetime t=iTime(_Symbol,InpEntryTF,0);
   if(t==0) return false;
   if(t!=g_lastBar){g_lastBar=t;return true;}
   return false;
}

void ResetDailyStats()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   g_dayKey=dt.year*1000+dt.day_of_year;
   g_tradesToday=CountTodayEntries();
   g_dayStartEquity=AccountInfoDouble(ACCOUNT_EQUITY);
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