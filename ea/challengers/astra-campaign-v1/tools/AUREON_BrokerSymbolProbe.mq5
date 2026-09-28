//+------------------------------------------------------------------+
//| AUREON_BrokerSymbolProbe.mq5                                    |
//| Discovers broker-native Gold symbols and prints execution truth.  |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
#property version "1.10"

input string InpPreferredSymbol="";
input bool InpCloseTerminal=true;

void Finish(int code)
{
   if(InpCloseTerminal && MQLInfoInteger(MQL_STARTED_FROM_CONFIG))
   {
      Sleep(500);
      TerminalClose(code);
   }
}

int GoldScore(string symbol)
{
   string s=symbol;
   StringToUpper(s);
   int score=-1;
   if(s=="XAUUSD") score=1000;
   else if(StringFind(s,"XAUUSD")==0) score=950;
   else if(StringFind(s,"XAUUSD")>=0) score=900;
   else if(StringFind(s,"XAU")>=0 && StringFind(s,"USD")>=0) score=850;
   else if(StringFind(s,"GOLD")>=0 && StringFind(s,"USD")>=0) score=800;
   else if(StringFind(s,"XAU")>=0) score=700;
   else if(StringFind(s,"GOLD")>=0) score=650;
   return score;
}

void PrintCandidate(string symbol,int score)
{
   if(!SymbolSelect(symbol,true))
   {
      PrintFormat("ASTRA_BROKER_CANDIDATE symbol=%s score=%d selectable=0 error=%d",symbol,score,GetLastError());
      ResetLastError();
      return;
   }
   long tradeMode=SymbolInfoInteger(symbol,SYMBOL_TRADE_MODE);
   long digits=SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   double point=SymbolInfoDouble(symbol,SYMBOL_POINT);
   double tickSize=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   double contract=SymbolInfoDouble(symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   double minVol=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double stepVol=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   MqlTick tick;
   bool gotTick=SymbolInfoTick(symbol,tick);
   double spreadPoints=0.0;
   if(gotTick && point>0.0) spreadPoints=(tick.ask-tick.bid)/point;
   PrintFormat("ASTRA_BROKER_CANDIDATE symbol=%s score=%d selectable=1 trade_mode=%d digits=%d point=%.10f tick_size=%.10f contract=%.2f vol_min=%.4f vol_step=%.4f tick=%d spread_points=%.1f",
      symbol,score,(int)tradeMode,(int)digits,point,tickSize,contract,minVol,stepVol,gotTick?1:0,spreadPoints);
}

void OnStart()
{
   string chosen="";
   int best=-1;

   if(StringLen(InpPreferredSymbol)>0)
   {
      if(SymbolSelect(InpPreferredSymbol,true))
      {
         chosen=InpPreferredSymbol;
         best=GoldScore(chosen);
         PrintFormat("ASTRA_BROKER_PREFERRED_OK symbol=%s score=%d",chosen,best);
      }
      else
         PrintFormat("ASTRA_BROKER_PREFERRED_FAIL symbol=%s error=%d",InpPreferredSymbol,GetLastError());
      ResetLastError();
   }

   int total=SymbolsTotal(false);
   PrintFormat("ASTRA_BROKER_SYMBOL_ENUM total=%d",total);
   for(int i=0;i<total;i++)
   {
      string s=SymbolName(i,false);
      int score=GoldScore(s);
      if(score<0) continue;
      PrintCandidate(s,score);
      if(score>best && SymbolSelect(s,true))
      {
         long tm=SymbolInfoInteger(s,SYMBOL_TRADE_MODE);
         if(tm!=SYMBOL_TRADE_MODE_DISABLED)
         {
            chosen=s;
            best=score;
         }
      }
   }

   if(StringLen(chosen)==0)
   {
      Print("ASTRA_BROKER_PROBE_FAIL no selectable XAU/GOLD symbol discovered");
      Finish(2);
      return;
   }

   if(!SymbolSelect(chosen,true))
   {
      PrintFormat("ASTRA_BROKER_PROBE_FAIL select symbol=%s error=%d",chosen,GetLastError());
      Finish(2);
      return;
   }

   long digits=SymbolInfoInteger(chosen,SYMBOL_DIGITS);
   double point=SymbolInfoDouble(chosen,SYMBOL_POINT);
   double tickSize=SymbolInfoDouble(chosen,SYMBOL_TRADE_TICK_SIZE);
   double tickValue=SymbolInfoDouble(chosen,SYMBOL_TRADE_TICK_VALUE);
   double tickValueProfit=SymbolInfoDouble(chosen,SYMBOL_TRADE_TICK_VALUE_PROFIT);
   double tickValueLoss=SymbolInfoDouble(chosen,SYMBOL_TRADE_TICK_VALUE_LOSS);
   double contract=SymbolInfoDouble(chosen,SYMBOL_TRADE_CONTRACT_SIZE);
   double minVol=SymbolInfoDouble(chosen,SYMBOL_VOLUME_MIN);
   double maxVol=SymbolInfoDouble(chosen,SYMBOL_VOLUME_MAX);
   double stepVol=SymbolInfoDouble(chosen,SYMBOL_VOLUME_STEP);
   long tradeMode=SymbolInfoInteger(chosen,SYMBOL_TRADE_MODE);
   long calcMode=SymbolInfoInteger(chosen,SYMBOL_TRADE_CALC_MODE);
   long stops=SymbolInfoInteger(chosen,SYMBOL_TRADE_STOPS_LEVEL);
   long freeze=SymbolInfoInteger(chosen,SYMBOL_TRADE_FREEZE_LEVEL);
   long filling=SymbolInfoInteger(chosen,SYMBOL_FILLING_MODE);
   long orderMode=SymbolInfoInteger(chosen,SYMBOL_ORDER_MODE);
   long expirationMode=SymbolInfoInteger(chosen,SYMBOL_EXPIRATION_MODE);
   long gtcMode=SymbolInfoInteger(chosen,SYMBOL_ORDER_GTC_MODE);

   MqlTick tick;
   bool gotTick=SymbolInfoTick(chosen,tick);
   double spreadPoints=0.0;
   if(gotTick && point>0.0) spreadPoints=(tick.ask-tick.bid)/point;

   int barsM1=Bars(chosen,PERIOD_M1);
   int barsM5=Bars(chosen,PERIOD_M5);
   int barsM15=Bars(chosen,PERIOD_M15);
   int barsH1=Bars(chosen,PERIOD_H1);
   int barsH4=Bars(chosen,PERIOD_H4);
   datetime firstM1=0,lastM1=0;
   if(barsM1>0)
   {
      firstM1=(datetime)SeriesInfoInteger(chosen,PERIOD_M1,SERIES_FIRSTDATE);
      lastM1=iTime(chosen,PERIOD_M1,0);
   }

   PrintFormat("ASTRA_BROKER_SELECTED symbol=%s score=%d",chosen,best);
   PrintFormat("ASTRA_BROKER_PROBE_OK symbol=%s digits=%d point=%.10f tick_size=%.10f tick_value=%.6f tick_value_profit=%.6f tick_value_loss=%.6f contract=%.2f vol_min=%.4f vol_max=%.4f vol_step=%.4f trade_mode=%d calc_mode=%d stops=%d freeze=%d filling=%d order_mode=%d expiration_mode=%d gtc_mode=%d spread_points=%.1f bars_m1=%d bars_m5=%d bars_m15=%d bars_h1=%d bars_h4=%d first_m1=%s last_m1=%s",
      chosen,(int)digits,point,tickSize,tickValue,tickValueProfit,tickValueLoss,contract,minVol,maxVol,stepVol,
      (int)tradeMode,(int)calcMode,(int)stops,(int)freeze,(int)filling,(int)orderMode,(int)expirationMode,(int)gtcMode,
      spreadPoints,barsM1,barsM5,barsM15,barsH1,barsH4,
      TimeToString(firstM1,TIME_DATE|TIME_MINUTES),
      TimeToString(lastM1,TIME_DATE|TIME_MINUTES));
   Finish(0);
}
//+------------------------------------------------------------------+
