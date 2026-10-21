//+------------------------------------------------------------------+
//| AUREON Omega XAUUSD Strategy Research Suite                      |
//| M5 Mean Reversion / H4 Breakout / Session / Daily CRT             |
//| DEMO-only research EA; not certified for live trading.            |
//+------------------------------------------------------------------+
#property strict
#property version   "1.01"
#property description "AUREON XAUUSD strategy comparison EA; demo-only research"

enum ENUM_AUREON_STRATEGY { STRAT_M5_MEAN_REVERSION=0, STRAT_H4_BREAKOUT=1, STRAT_SESSION_BREAKOUT=2, STRAT_DAILY_CRT=3 };
input ENUM_AUREON_STRATEGY InpStrategy=STRAT_M5_MEAN_REVERSION;
input ulong InpMagic=20261021;
input double InpRiskPercent=0.25;
input double InpDailyLossLimitPct=2.0;
input double InpMaxPeakDrawdownPct=6.0;
input int InpMaxSpreadPoints=80;
input int InpDeviationPoints=35;
input int InpMaxTradesPerDay=3;
input int InpCooldownMinutes=30;
input double InpStopATR=1.5;
input double InpRewardRisk=1.5;
input int InpMeanEMA=20;
input int InpRSIPeriod=14;
input double InpRSILow=30.0;
input double InpRSIHigh=70.0;
input double InpMeanDeviationATR=1.25;
input double InpADXMaxForMeanReversion=25.0;
input int InpH4Lookback=20;
input double InpBreakoutBufferATR=0.10;
input int InpAsianStartHour=0;
input int InpAsianEndHour=7;
input int InpSessionTradeStartHour=7;
input int InpSessionTradeEndHour=17;
input bool InpRequireDemoAccount=true;
input bool InpAllowLong=true;
input bool InpAllowShort=true;

int hEMA=INVALID_HANDLE,hRSI=INVALID_HANDLE,hATR=INVALID_HANDLE,hADX=INVALID_HANDLE;
datetime g_lastM5Bar=0,g_lastH4Processed=0,g_lastTradeTime=0;
int g_dayKey=-1,g_tradesToday=0;
double g_dayStartEquity=0.0,g_peakEquity=0.0;
bool g_riskLocked=false;
string g_statePrefix="";

int DayKey(datetime t){ MqlDateTime d; TimeToStruct(t,d); return d.year*10000+d.mon*100+d.day; }
bool IsDemoAccount()
{
   if((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO) return true;
   string server=AccountInfoString(ACCOUNT_SERVER); StringToLower(server);
   return StringFind(server,"demo")>=0;
}
bool IsNewBar(ENUM_TIMEFRAMES tf,datetime &last)
{
   datetime t=iTime(_Symbol,tf,0); if(t<=0 || t==last) return false; last=t; return true;
}
bool ReadValue(int handle,int buffer,int shift,double &value)
{
   double v[1]; if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,shift,1,v)!=1) return false;
   value=v[0]; return MathIsValidNumber(value);
}
bool GetClosedM5(MqlRates &bar){ MqlRates r[1]; if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1) return false; bar=r[0]; return true; }
void UpdateRiskState()
{
   int key=DayKey(TimeCurrent()); double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   // Persist locks and peak equity across EA/terminal restarts for this account, symbol and magic.
   string peakKey=g_statePrefix+"PEAK";
   string peakLockKey=g_statePrefix+"PEAKLOCK";
   string dayKeyName=g_statePrefix+"DAY";
   string dayEqName=g_statePrefix+"DAYEQ";
   string dayLockName=g_statePrefix+"DAYLOCK";
   if(GlobalVariableCheck(peakKey)) g_peakEquity=MathMax(g_peakEquity,GlobalVariableGet(peakKey));
   if(g_peakEquity<=0.0) g_peakEquity=equity;
   if(equity>g_peakEquity) g_peakEquity=equity;
   GlobalVariableSet(peakKey,g_peakEquity);
   bool peakLocked=(GlobalVariableCheck(peakLockKey) && GlobalVariableGet(peakLockKey)>0.5);
   if(key!=g_dayKey)
   {
      g_dayKey=key; g_tradesToday=0;
      if(GlobalVariableCheck(dayKeyName) && (int)GlobalVariableGet(dayKeyName)==key && GlobalVariableCheck(dayEqName))
      {
         g_dayStartEquity=GlobalVariableGet(dayEqName);
         string tradesKey=g_statePrefix+"TRADES";
         if(GlobalVariableCheck(tradesKey)) g_tradesToday=(int)GlobalVariableGet(tradesKey);
      }
      else
      {
         g_dayStartEquity=equity;
         g_tradesToday=0;
         GlobalVariableSet(dayKeyName,(double)key);
         GlobalVariableSet(dayEqName,equity);
         GlobalVariableSet(dayLockName,0.0);
         GlobalVariableSet(g_statePrefix+"TRADES",0.0);
      }
   }
   bool dailyLocked=(GlobalVariableCheck(dayLockName) && GlobalVariableGet(dayLockName)>0.5);
   if(g_dayStartEquity>0 && equity<=g_dayStartEquity*(1.0-InpDailyLossLimitPct/100.0))
   {
      dailyLocked=true;
      GlobalVariableSet(dayLockName,1.0);
   }
   if(g_peakEquity>0 && equity<=g_peakEquity*(1.0-InpMaxPeakDrawdownPct/100.0))
   {
      peakLocked=true;
      GlobalVariableSet(peakLockKey,1.0);
   }
   g_riskLocked=(dailyLocked || peakLocked);
}
bool CanTrade()
{
   UpdateRiskState();
   if(InpRequireDemoAccount && !IsDemoAccount()) return false;
   if(g_riskLocked || g_tradesToday>=InpMaxTradesPerDay || PositionSelect(_Symbol)) return false;
   if(g_lastTradeTime>0 && TimeCurrent()-g_lastTradeTime<InpCooldownMinutes*60) return false;
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0 || tick.bid<=0) return false;
   if((tick.ask-tick.bid)/_Point>InpMaxSpreadPoints) return false;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;
   return true;
}
double NormalizeVolume(double lots)
{
   double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0 || vmin<=0) return 0.0;
   lots=MathFloor(lots/step)*step; lots=MathMax(vmin,MathMin(vmax,lots));
   int digits=(step>=1.0?0:(step>=0.1?1:(step>=0.01?2:3)));
   return NormalizeDouble(lots,digits);
}
double LotsForRisk(double entry,double stop)
{
   double riskMoney=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double tickSize=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double tickValue=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickValue<=0) tickValue=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   double distance=MathAbs(entry-stop);
   if(riskMoney<=0 || tickSize<=0 || tickValue<=0 || distance<=0) return 0.0;
   double lossPerLot=(distance/tickSize)*tickValue; if(lossPerLot<=0) return 0.0;
   double rawLots=riskMoney/lossPerLot;
   double minLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(rawLots<minLot) return 0.0;
   double lots=NormalizeVolume(rawLots);
   if(lots<minLot || lossPerLot*lots>riskMoney*1.001) return 0.0;
   return lots;
}
bool PlaceTrade(int direction,double atr,string tag)
{
   if(!CanTrade() || atr<=0) return false;
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0?tick.ask:tick.bid);
   double stop=(direction>0?entry-atr*InpStopATR:entry+atr*InpStopATR);
   double target=(direction>0?entry+(entry-stop)*InpRewardRisk:entry-(stop-entry)*InpRewardRisk);
   int stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(MathAbs(entry-stop)<stops*_Point || MathAbs(target-entry)<stops*_Point) return false;
   double lots=LotsForRisk(entry,stop); if(lots<=0) return false;
   if((direction>0 && !InpAllowLong)||(direction<0 && !InpAllowShort)) return false;
   MqlTradeRequest request={};
   MqlTradeResult result={};
   request.action=TRADE_ACTION_DEAL;
   request.symbol=_Symbol;
   request.magic=InpMagic;
   request.volume=lots;
   request.type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   request.price=NormalizeDouble(entry,_Digits);
   request.sl=NormalizeDouble(stop,_Digits);
   request.tp=NormalizeDouble(target,_Digits);
   request.deviation=(ulong)InpDeviationPoints;
   request.comment=StringSubstr(tag,0,31);
   long filling=SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC) request.type_filling=ORDER_FILLING_IOC;
   else if((filling & SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK) request.type_filling=ORDER_FILLING_FOK;
   else request.type_filling=ORDER_FILLING_RETURN;
   if(!OrderSend(request,result))
   {
      Print("AUREON_ORDER_SEND_FAILED error=",GetLastError()," retcode=",result.retcode);
      return false;
   }
   bool ok=(result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL || result.retcode==TRADE_RETCODE_PLACED);
   if(ok)
   {
      g_tradesToday++;
      g_lastTradeTime=TimeCurrent();
      GlobalVariableSet(g_statePrefix+"TRADES",(double)g_tradesToday);
      GlobalVariableSet(g_statePrefix+"LASTTRADE",(double)g_lastTradeTime);
      Print("AUREON_ENTRY strategy=",EnumToString(InpStrategy)," side=",direction," lots=",lots," tag=",tag," order=",result.order," deal=",result.deal);
   }
   else Print("AUREON_ORDER_REJECT retcode=",result.retcode," comment=",result.comment);
   return ok;
}
bool MeanReversionSignal(int &side,double &atr)
{
   side=0; double ema,rsi,adx;
   if(!ReadValue(hEMA,0,1,ema)||!ReadValue(hRSI,0,1,rsi)||!ReadValue(hATR,0,1,atr)||!ReadValue(hADX,0,1,adx)) return false;
   if(adx>InpADXMaxForMeanReversion) return true;
   MqlRates b; if(!GetClosedM5(b)) return false;
   double dev=(b.close-ema)/atr;
   if(dev<=-InpMeanDeviationATR && rsi<=InpRSILow && b.close>b.open) side=1;
   if(dev>=InpMeanDeviationATR && rsi>=InpRSIHigh && b.close<b.open) side=-1;
   return true;
}
bool H4BreakoutSignal(int &side,double &atr)
{
   side=0; if(!ReadValue(hATR,0,1,atr)) return false;
   MqlRates h4[]; ArraySetAsSeries(h4,true);
   if(CopyRates(_Symbol,PERIOD_H4,1,InpH4Lookback+1,h4)<InpH4Lookback+1) return false;
   if(h4[0].time==g_lastH4Processed) return true;
   g_lastH4Processed=h4[0].time;
   double hi=-DBL_MAX,lo=DBL_MAX;
   for(int i=1;i<=InpH4Lookback;i++){ if(h4[i].high>hi) hi=h4[i].high; if(h4[i].low<lo) lo=h4[i].low; }
   double buffer=atr*InpBreakoutBufferATR;
   if(h4[0].close>hi+buffer) side=1; else if(h4[0].close<lo-buffer) side=-1;
   return true;
}
bool BuildSessionRange(datetime now,double &hi,double &lo)
{
   hi=-DBL_MAX; lo=DBL_MAX; MqlDateTime d; TimeToStruct(now,d);
   MqlDateTime a=d,z=d; a.hour=InpAsianStartHour; a.min=0; a.sec=0; z.hour=InpAsianEndHour; z.min=0; z.sec=0;
   datetime start=StructToTime(a),end=StructToTime(z); if(end<=start) end+=86400;
   MqlRates r[]; ArraySetAsSeries(r,false); int n=CopyRates(_Symbol,PERIOD_M5,start,end,r); if(n<=0) return false;
   for(int i=0;i<n;i++)
   {
      MqlDateTime bt; TimeToStruct(r[i].time,bt);
      if(DayKey(r[i].time)!=DayKey(now)||bt.hour<InpAsianStartHour||bt.hour>=InpAsianEndHour) continue;
      if(r[i].high>hi) hi=r[i].high; if(r[i].low<lo) lo=r[i].low;
   }
   return hi>-DBL_MAX && lo<DBL_MAX && hi>lo;
}
bool SessionBreakoutSignal(int &side,double &atr)
{
   side=0; if(!ReadValue(hATR,0,1,atr)) return false;
   MqlDateTime t; TimeToStruct(TimeCurrent(),t);
   if(t.hour<InpSessionTradeStartHour||t.hour>=InpSessionTradeEndHour) return true;
   double hi,lo; if(!BuildSessionRange(TimeCurrent(),hi,lo)) return true;
   MqlRates b; if(!GetClosedM5(b)) return false; double buffer=atr*InpBreakoutBufferATR;
   if(b.close>hi+buffer) side=1; else if(b.close<lo-buffer) side=-1;
   return true;
}
bool DailyCRTSignal(int &side,double &atr)
{
   side=0; if(!ReadValue(hATR,0,1,atr)) return false;
   MqlRates d[1],b; if(CopyRates(_Symbol,PERIOD_D1,1,1,d)!=1||!GetClosedM5(b)) return false;
   if(b.low<d[0].low&&b.close>d[0].low&&b.close<d[0].high&&b.close>b.open) side=1;
   else if(b.high>d[0].high&&b.close<d[0].high&&b.close>d[0].low&&b.close<b.open) side=-1;
   return true;
}
int OnInit()
{
   if(InpRiskPercent<=0||InpRiskPercent>1.0||InpDailyLossLimitPct<=0||InpMaxPeakDrawdownPct<=0||InpMaxTradesPerDay<1||InpH4Lookback<2||InpAsianStartHour<0||InpAsianStartHour>23||InpAsianEndHour<0||InpAsianEndHour>23||InpSessionTradeStartHour<0||InpSessionTradeStartHour>23||InpSessionTradeEndHour<0||InpSessionTradeEndHour>23)
   { Print("Invalid risk or strategy inputs."); return INIT_PARAMETERS_INCORRECT; }
   if(InpRequireDemoAccount&&!IsDemoAccount()){ Print("LIVE BLOCKED: AUREON research EA requires a DEMO account."); return INIT_FAILED; }
   hEMA=iMA(_Symbol,PERIOD_M5,InpMeanEMA,0,MODE_EMA,PRICE_CLOSE); hRSI=iRSI(_Symbol,PERIOD_M5,InpRSIPeriod,PRICE_CLOSE);
   hATR=iATR(_Symbol,PERIOD_M5,14); hADX=iADX(_Symbol,PERIOD_M5,14);
   if(hEMA==INVALID_HANDLE||hRSI==INVALID_HANDLE||hATR==INVALID_HANDLE||hADX==INVALID_HANDLE){ Print("Indicator initialization failed."); return INIT_FAILED; }
   g_statePrefix=StringFormat("AUR_%I64d_%s_%I64u_",AccountInfoInteger(ACCOUNT_LOGIN),_Symbol,InpMagic);
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   g_dayKey=-1;
   if(GlobalVariableCheck(g_statePrefix+"PEAK")) g_peakEquity=GlobalVariableGet(g_statePrefix+"PEAK");
   if(GlobalVariableCheck(g_statePrefix+"LASTTRADE")) g_lastTradeTime=(datetime)GlobalVariableGet(g_statePrefix+"LASTTRADE");
   if(g_peakEquity<=0.0) g_peakEquity=equity;
   if(GlobalVariableCheck(g_statePrefix+"PEAKLOCK") && GlobalVariableGet(g_statePrefix+"PEAKLOCK")>0.5) g_riskLocked=true;
   UpdateRiskState();
   Print("AUREON Strategy Suite v1.01 ready. Strategy=",EnumToString(InpStrategy)," symbol=",_Symbol," execution=M5 DEMO ONLY; live blocked; persistent drawdown lock enabled.");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ if(hEMA!=INVALID_HANDLE)IndicatorRelease(hEMA); if(hRSI!=INVALID_HANDLE)IndicatorRelease(hRSI); if(hATR!=INVALID_HANDLE)IndicatorRelease(hATR); if(hADX!=INVALID_HANDLE)IndicatorRelease(hADX); }
void OnTick()
{
   if(!IsNewBar(PERIOD_M5,g_lastM5Bar)||!CanTrade()) return;
   int side=0; double atr=0; bool valid=false;
   switch(InpStrategy)
   {
      case STRAT_M5_MEAN_REVERSION: valid=MeanReversionSignal(side,atr); break;
      case STRAT_H4_BREAKOUT: valid=H4BreakoutSignal(side,atr); break;
      case STRAT_SESSION_BREAKOUT: valid=SessionBreakoutSignal(side,atr); break;
      case STRAT_DAILY_CRT: valid=DailyCRTSignal(side,atr); break;
   }
   if(valid&&side!=0) PlaceTrade(side,atr,EnumToString(InpStrategy));
}
