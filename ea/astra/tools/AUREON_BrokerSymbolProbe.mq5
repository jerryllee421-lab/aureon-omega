//+------------------------------------------------------------------+
//| AUREON_BrokerSymbolProbe.mq5                                    |
//| Prints broker-native symbol specifications and history coverage.  |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
#property version "1.00"

input string InpSymbol="XAUUSD.ecn";
input bool InpCloseTerminal=true;

void Finish(int code)
{
   if(InpCloseTerminal && MQLInfoInteger(MQL_STARTED_FROM_CONFIG))
   {
      Sleep(500);
      TerminalClose(code);
   }
}

void OnStart()
{
   if(!SymbolSelect(InpSymbol,true))
   {
      PrintFormat("ASTRA_BROKER_PROBE_FAIL select symbol=%s error=%d",InpSymbol,GetLastError());
      Finish(2);
      return;
   }

   long digits=SymbolInfoInteger(InpSymbol,SYMBOL_DIGITS);
   double point=SymbolInfoDouble(InpSymbol,SYMBOL_POINT);
   double tickSize=SymbolInfoDouble(InpSymbol,SYMBOL_TRADE_TICK_SIZE);
   double tickValue=SymbolInfoDouble(InpSymbol,SYMBOL_TRADE_TICK_VALUE);
   double contract=SymbolInfoDouble(InpSymbol,SYMBOL_TRADE_CONTRACT_SIZE);
   double minVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MIN);
   double maxVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_MAX);
   double stepVol=SymbolInfoDouble(InpSymbol,SYMBOL_VOLUME_STEP);
   long tradeMode=SymbolInfoInteger(InpSymbol,SYMBOL_TRADE_MODE);
   long stops=SymbolInfoInteger(InpSymbol,SYMBOL_TRADE_STOPS_LEVEL);
   long freeze=SymbolInfoInteger(InpSymbol,SYMBOL_TRADE_FREEZE_LEVEL);

   MqlTick tick;
   bool gotTick=SymbolInfoTick(InpSymbol,tick);
   double spreadPoints=0.0;
   if(gotTick && point>0.0) spreadPoints=(tick.ask-tick.bid)/point;

   int barsM1=Bars(InpSymbol,PERIOD_M1);
   int barsM5=Bars(InpSymbol,PERIOD_M5);
   int barsH1=Bars(InpSymbol,PERIOD_H1);
   datetime firstM1=0,lastM1=0;
   if(barsM1>0)
   {
      firstM1=(datetime)SeriesInfoInteger(InpSymbol,PERIOD_M1,SERIES_FIRSTDATE);
      lastM1=iTime(InpSymbol,PERIOD_M1,0);
   }

   PrintFormat("ASTRA_BROKER_PROBE_OK symbol=%s digits=%d point=%.10f tick_size=%.10f tick_value=%.6f contract=%.2f vol_min=%.2f vol_max=%.2f vol_step=%.2f trade_mode=%d stops=%d freeze=%d spread_points=%.1f bars_m1=%d bars_m5=%d bars_h1=%d first_m1=%s last_m1=%s",
      InpSymbol,(int)digits,point,tickSize,tickValue,contract,minVol,maxVol,stepVol,(int)tradeMode,(int)stops,(int)freeze,
      spreadPoints,barsM1,barsM5,barsH1,
      TimeToString(firstM1,TIME_DATE|TIME_MINUTES),
      TimeToString(lastM1,TIME_DATE|TIME_MINUTES));
   Finish(0);
}
//+------------------------------------------------------------------+
