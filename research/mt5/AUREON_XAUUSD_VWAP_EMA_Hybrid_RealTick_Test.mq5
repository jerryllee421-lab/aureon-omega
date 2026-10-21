//+------------------------------------------------------------------+
//| AUREON_XAUUSD_VWAP_EMA_Hybrid_RealTick_Test.mq5                  |
//| Research EA: session VWAP + M1 EMA pullback, M5 trend filter.    |
//| DEMO / Strategy Tester only. Not production or live approved.    |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "AUREON Omega XAUUSD VWAP+EMA hybrid research EA"
#property description "Demo/tester only; real-tick validation required."

#include <Trade/Trade.mqh>
CTrade trade;

input bool   InpEnableOrders       = true;     // Tester/demo only
input bool   InpDemoOnly           = true;     // Hard block non-demo accounts
input ulong  InpMagic              = 20261020;
input double InpFixedLots          = 0.01;
input int    InpFastEMA            = 9;
input int    InpSignalEMA          = 21;
input int    InpTrendEMA            = 50;
input int    InpContextEMA          = 200;
input int    InpATRPeriod           = 14;
input double InpSL_ATR_Multiplier   = 1.5;
input double InpTP_R_Multiple       = 1.5;
input int    InpMaxSpreadPoints     = 100;      // Broker points; calibrate per symbol
input int    InpDeviationPoints     = 30;
input int    InpSessionStartHour    = 0;        // Broker-server time
input int    InpSessionStartMinute  = 0;        // VWAP reset boundary
input bool   InpUseEMA200Filter     = false;    // Context filter; test via ablation
input bool   InpRequireM5Trend      = true;

int hFastM1=INVALID_HANDLE, hSignalM1=INVALID_HANDLE;
int hTrendM1=INVALID_HANDLE, hContextM1=INVALID_HANDLE;
int hSignalM5=INVALID_HANDLE, hTrendM5=INVALID_HANDLE;
int hATR=INVALID_HANDLE;
datetime lastM1Bar=0;
string statusText="INITIALIZING";

//--- Fetch a single indicator value at a closed bar shift.
bool BufferValue(const int handle,const int shift,double &value)
{
   double b[];
   ArraySetAsSeries(b,true);
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,b)!=1)
      return false;
   value=b[0];
   return MathIsValidNumber(value) && value!=EMPTY_VALUE;
}

//--- VWAP proxy from broker M1 bars' tick volume since configured session reset.
//--- This is NOT centralized spot-gold traded volume.
bool SessionVWAP(const datetime decisionTime,double &vwap)
{
   MqlDateTime dt;
   TimeToStruct(decisionTime,dt);
   dt.hour=InpSessionStartHour;
   dt.min=InpSessionStartMinute;
   dt.sec=0;
   datetime sessionStart=StructToTime(dt);
   if(decisionTime<sessionStart)
      sessionStart-=86400;

   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   int copied=CopyRates(_Symbol,PERIOD_M1,sessionStart,decisionTime,rates);
   if(copied<2)
      return false;

   double pv=0.0,vol=0.0;
   for(int i=0;i<copied;i++)
   {
      // Exclude the currently forming candle and any candle not closed by decisionTime.
      if(rates[i].time+PeriodSeconds(PERIOD_M1)>decisionTime)
         continue;
      long tv=rates[i].tick_volume;
      if(tv<=0) continue;
      double typical=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      pv+=typical*(double)tv;
      vol+=(double)tv;
   }
   if(vol<=0.0) return false;
   vwap=pv/vol;
   return MathIsValidNumber(vwap);
}

bool HasOurPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return true;
   }
   return false;
}

double NormalizeVolume(double lots)
{
   double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   lots=MathMax(vmin,MathMin(vmax,lots));
   lots=MathFloor(lots/step)*step;
   int digits=2;
   if(step<0.01) digits=3;
   if(step<0.001) digits=4;
   return NormalizeDouble(lots,digits);
}

bool EnvironmentAllowed()
{
   if(!InpEnableOrders)
   {
      statusText="ORDERS_DISABLED";
      return false;
   }
   if(InpDemoOnly)
   {
      ENUM_ACCOUNT_TRADE_MODE mode=(ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
      if(mode!=ACCOUNT_TRADE_MODE_DEMO)
      {
         statusText="BLOCKED_NON_DEMO_ACCOUNT";
         return false;
      }
   }
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      statusText="BLOCKED_TERMINAL_DISCONNECTED";
      return false;
   }
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED) || !TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      statusText="BLOCKED_TRADING_NOT_ALLOWED";
      return false;
   }
   return true;
}

int OnInit()
{
   if(_Period!=PERIOD_M1)
      Print("NOTICE: attach/run on M1; EA uses M1 entries and M5 confirmation.");
   if(InpFastEMA<=0 || InpSignalEMA<=0 || InpTrendEMA<=0 ||
      InpATRPeriod<=0 || InpFixedLots<=0 || InpSL_ATR_Multiplier<=0 ||
      InpTP_R_Multiple<=0 || InpSessionStartHour<0 || InpSessionStartHour>23 ||
      InpSessionStartMinute<0 || InpSessionStartMinute>59)
      return INIT_PARAMETERS_INCORRECT;

   hFastM1=iMA(_Symbol,PERIOD_M1,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   hSignalM1=iMA(_Symbol,PERIOD_M1,InpSignalEMA,0,MODE_EMA,PRICE_CLOSE);
   hTrendM1=iMA(_Symbol,PERIOD_M1,InpTrendEMA,0,MODE_EMA,PRICE_CLOSE);
   hContextM1=iMA(_Symbol,PERIOD_M1,InpContextEMA,0,MODE_EMA,PRICE_CLOSE);
   hSignalM5=iMA(_Symbol,PERIOD_M5,InpSignalEMA,0,MODE_EMA,PRICE_CLOSE);
   hTrendM5=iMA(_Symbol,PERIOD_M5,InpTrendEMA,0,MODE_EMA,PRICE_CLOSE);
   hATR=iATR(_Symbol,PERIOD_M1,InpATRPeriod);

   if(hFastM1==INVALID_HANDLE || hSignalM1==INVALID_HANDLE ||
      hTrendM1==INVALID_HANDLE || hContextM1==INVALID_HANDLE ||
      hSignalM5==INVALID_HANDLE || hTrendM5==INVALID_HANDLE || hATR==INVALID_HANDLE)
   {
      Print("INIT_FAILED: indicator handle creation failed.");
      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   statusText="READY_RESEARCH_ONLY";
   Print("AUREON VWAP+EMA research EA initialized. Symbol=",_Symbol,
         " server=",AccountInfoString(ACCOUNT_SERVER),
         " account_mode=",AccountInfoInteger(ACCOUNT_TRADE_MODE),
         " session_reset=",InpSessionStartHour,":",InpSessionStartMinute,
         ". Real-tick tester validation required; live deployment not approved.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(hFastM1!=INVALID_HANDLE) IndicatorRelease(hFastM1);
   if(hSignalM1!=INVALID_HANDLE) IndicatorRelease(hSignalM1);
   if(hTrendM1!=INVALID_HANDLE) IndicatorRelease(hTrendM1);
   if(hContextM1!=INVALID_HANDLE) IndicatorRelease(hContextM1);
   if(hSignalM5!=INVALID_HANDLE) IndicatorRelease(hSignalM5);
   if(hTrendM5!=INVALID_HANDLE) IndicatorRelease(hTrendM5);
   if(hATR!=INVALID_HANDLE) IndicatorRelease(hATR);
}

void OnTick()
{
   datetime barTime=iTime(_Symbol,PERIOD_M1,0);
   if(barTime<=0 || barTime==lastM1Bar) return;
   lastM1Bar=barTime; // one decision per new M1 bar; all signals use shift 1/2 closed bars

   if(!EnvironmentAllowed())
   {
      Print("ENTRY_BLOCKED: ",statusText);
      return;
   }
   if(HasOurPosition())
   {
      statusText="POSITION_ALREADY_OPEN";
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0 || tick.bid<=0 || tick.ask<tick.bid)
   {
      statusText="BLOCKED_INVALID_QUOTE";
      return;
   }
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(point<=0) return;
   double spreadPoints=(tick.ask-tick.bid)/point;
   if(spreadPoints>InpMaxSpreadPoints)
   {
      statusText="BLOCKED_SPREAD";
      Print(statusText, " spread_points=",DoubleToString(spreadPoints,1));
      return;
   }

   double fast1,fast2,signal1,signal2,trend1,context1,m5signal,m5trend,atr,vwap;
   if(!BufferValue(hFastM1,1,fast1) || !BufferValue(hFastM1,2,fast2) ||
      !BufferValue(hSignalM1,1,signal1) || !BufferValue(hSignalM1,2,signal2) ||
      !BufferValue(hTrendM1,1,trend1) || !BufferValue(hContextM1,1,context1) ||
      !BufferValue(hSignalM5,1,m5signal) || !BufferValue(hTrendM5,1,m5trend) ||
      !BufferValue(hATR,1,atr) || atr<=0 ||
      !SessionVWAP(iTime(_Symbol,PERIOD_M1,1)+PeriodSeconds(PERIOD_M1),vwap))
   {
      statusText="BLOCKED_INDICATOR_OR_VWAP_WARMUP";
      Print(statusText);
      return;
   }

   double c1=iClose(_Symbol,PERIOD_M1,1);
   double c2=iClose(_Symbol,PERIOD_M1,2);
   if(c1<=0 || c2<=0) return;

   bool m5Bull=(c1>vwap && m5signal>m5trend);
   bool m5Bear=(c1<vwap && m5signal<m5trend);
   bool longContext=(!InpRequireM5Trend || m5Bull);
   bool shortContext=(!InpRequireM5Trend || m5Bear);
   if(InpUseEMA200Filter)
   {
      longContext=longContext && c1>context1;
      shortContext=shortContext && c1<context1;
   }

   // Hybrid trigger: pullback/reclaim of EMA21 or session VWAP, confirmed by closed candle.
   bool bullishReclaim=(c2<=signal2 && c1>signal1) ||
                       (c2<=vwap && c1>vwap && c1>signal1);
   bool bearishReject=(c2>=signal2 && c1<signal1) ||
                      (c2>=vwap && c1<vwap && c1<signal1);
   bool longSignal=longContext && fast1>signal1 && signal1>=trend1 && bullishReclaim;
   bool shortSignal=shortContext && fast1<signal1 && signal1<=trend1 && bearishReject;

   if(longSignal==shortSignal)
   {
      statusText="NO_VALID_SIGNAL";
      return;
   }

   double volume=NormalizeVolume(InpFixedLots);
   if(volume<=0)
   {
      statusText="BLOCKED_INVALID_VOLUME";
      return;
   }
   double minStop=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   double slDistance=MathMax(atr*InpSL_ATR_Multiplier,minStop+2*point);
   double tpDistance=slDistance*InpTP_R_Multiple;
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   bool sent=false;

   if(longSignal)
   {
      double sl=NormalizeDouble(tick.ask-slDistance,digits);
      double tp=NormalizeDouble(tick.ask+tpDistance,digits);
      sent=trade.Buy(volume,_Symbol,0.0,sl,tp,"AUREON VWAP EMA BUY");
   }
   else if(shortSignal)
   {
      double sl=NormalizeDouble(tick.bid+slDistance,digits);
      double tp=NormalizeDouble(tick.bid-tpDistance,digits);
      sent=trade.Sell(volume,_Symbol,0.0,sl,tp,"AUREON VWAP EMA SELL");
   }

   statusText=sent ? "ORDER_REQUEST_ACCEPTED_CHECK_FILL" : "ORDER_REQUEST_FAILED";
   Print("SIGNAL_RESULT=",statusText,
         " side=",(longSignal?"BUY":"SELL"),
         " lots=",DoubleToString(volume,3),
         " spread_points=",DoubleToString(spreadPoints,1),
         " ATR=",DoubleToString(atr,digits),
         " VWAP=",DoubleToString(vwap,digits),
         " retcode=",trade.ResultRetcode(),
         " description=",trade.ResultRetcodeDescription());
}
