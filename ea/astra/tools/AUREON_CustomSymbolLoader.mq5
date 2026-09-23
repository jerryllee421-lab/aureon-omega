//+------------------------------------------------------------------+
//|                    AUREON_CustomSymbolLoader.mq5                 |
//| Imports verified external M1 bars into an MT5 custom XAU symbol. |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
#property version "1.00"

input string InpCsvFile="ASTRA_XAUUSD_M1.csv";
input string InpSymbolName="ASTRA_XAUUSD";
input string InpSymbolPath="AUREON";
input int InpDigits=3;
input double InpPoint=0.001;
input double InpContractSize=100.0;
input double InpMinVolume=0.01;
input double InpMaxVolume=100.0;
input double InpVolumeStep=0.01;
input bool InpCloseTerminal=true;

bool ConfigureSymbol()
{
   SymbolSelect(InpSymbolName,false);
   ResetLastError();
   if(!CustomSymbolCreate(InpSymbolName,InpSymbolPath,NULL))
   {
      int err=GetLastError();
      if(err!=5304)
      {
         PrintFormat("ASTRA_IMPORT_FAIL create symbol error=%d",err);
         return false;
      }
   }

   bool ok=true;
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_CHART_MODE,SYMBOL_CHART_MODE_BID);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_DIGITS,InpDigits);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_TRADE_MODE,SYMBOL_TRADE_MODE_FULL);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_TRADE_EXEMODE,SYMBOL_TRADE_EXECUTION_MARKET);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_TRADE_CALC_MODE,SYMBOL_CALC_MODE_CFD);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_TRADE_STOPS_LEVEL,0);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_TRADE_FREEZE_LEVEL,0);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_SPREAD_FLOAT,true);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_ORDER_MODE,SYMBOL_ORDER_MARKET|SYMBOL_ORDER_SL|SYMBOL_ORDER_TP);
   ok &= CustomSymbolSetInteger(InpSymbolName,SYMBOL_FILLING_MODE,SYMBOL_FILLING_IOC);

   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_POINT,InpPoint);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_TRADE_TICK_SIZE,InpPoint);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_TRADE_TICK_VALUE,InpPoint*InpContractSize);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_TRADE_TICK_VALUE_PROFIT,InpPoint*InpContractSize);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_TRADE_TICK_VALUE_LOSS,InpPoint*InpContractSize);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_TRADE_CONTRACT_SIZE,InpContractSize);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_VOLUME_MIN,InpMinVolume);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_VOLUME_MAX,InpMaxVolume);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_VOLUME_STEP,InpVolumeStep);
   ok &= CustomSymbolSetDouble(InpSymbolName,SYMBOL_VOLUME_LIMIT,InpMaxVolume);

   ok &= CustomSymbolSetString(InpSymbolName,SYMBOL_DESCRIPTION,"AUREON ASTRA XAUUSD research symbol");
   ok &= CustomSymbolSetString(InpSymbolName,SYMBOL_CURRENCY_BASE,"XAU");
   ok &= CustomSymbolSetString(InpSymbolName,SYMBOL_CURRENCY_PROFIT,"USD");
   ok &= CustomSymbolSetString(InpSymbolName,SYMBOL_CURRENCY_MARGIN,"USD");

   datetime from=D'1970.01.01 00:00:00';
   datetime to=D'1970.01.01 23:59:59';
   for(int d=MONDAY;d<=FRIDAY;d++)
   {
      ok &= CustomSymbolSetSessionQuote(InpSymbolName,(ENUM_DAY_OF_WEEK)d,0,from,to);
      ok &= CustomSymbolSetSessionTrade(InpSymbolName,(ENUM_DAY_OF_WEEK)d,0,from,to);
   }

   if(!ok)
   {
      PrintFormat("ASTRA_IMPORT_FAIL configure symbol error=%d",GetLastError());
      return false;
   }
   return true;
}

bool FlushRates(MqlRates &rates[],int count,int &total)
{
   if(count<=0) return true;
   ArrayResize(rates,count);
   ResetLastError();
   int updated=CustomRatesUpdate(InpSymbolName,rates,count);
   if(updated<0)
   {
      PrintFormat("ASTRA_IMPORT_FAIL CustomRatesUpdate error=%d",GetLastError());
      return false;
   }
   total+=updated;
   ArrayResize(rates,0);
   return true;
}

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
   if(!ConfigureSymbol())
   {
      Finish(2);
      return;
   }

   ResetLastError();
   CustomRatesDelete(InpSymbolName,0,LONG_MAX);

   int handle=FileOpen(InpCsvFile,FILE_READ|FILE_CSV|FILE_ANSI,',');
   if(handle==INVALID_HANDLE)
   {
      PrintFormat("ASTRA_IMPORT_FAIL FileOpen(%s) error=%d",InpCsvFile,GetLastError());
      Finish(3);
      return;
   }

   // Skip header.
   for(int k=0;k<7;k++) FileReadString(handle);

   const int BATCH=50000;
   MqlRates rates[];
   ArrayResize(rates,BATCH);
   int count=0,total=0;
   datetime first=0,last=0;

   while(!FileIsEnding(handle))
   {
      string ts=FileReadString(handle);
      if(ts=="") break;

      double op=StringToDouble(FileReadString(handle));
      double hi=StringToDouble(FileReadString(handle));
      double lo=StringToDouble(FileReadString(handle));
      double cl=StringToDouble(FileReadString(handle));
      long tv=(long)StringToInteger(FileReadString(handle));
      int spread=(int)StringToInteger(FileReadString(handle));
      datetime t=StringToTime(ts);

      if(t<=0 || op<=0 || hi<MathMax(op,cl) || lo>MathMin(op,cl) || hi<lo)
         continue;

      rates[count].time=t;
      rates[count].open=op;
      rates[count].high=hi;
      rates[count].low=lo;
      rates[count].close=cl;
      rates[count].tick_volume=(ulong)(tv>0 ? tv : 1);
      rates[count].spread=MathMax(1,spread);
      rates[count].real_volume=0;

      if(first==0) first=t;
      last=t;
      count++;

      if(count>=BATCH)
      {
         if(!FlushRates(rates,count,total))
         {
            FileClose(handle);
            Finish(4);
            return;
         }
         ArrayResize(rates,BATCH);
         count=0;
      }
   }

   FileClose(handle);
   if(count>0 && !FlushRates(rates,count,total))
   {
      Finish(5);
      return;
   }

   if(total<=0)
   {
      Print("ASTRA_IMPORT_FAIL zero rows imported");
      Finish(6);
      return;
   }

   SymbolSelect(InpSymbolName,true);
   int bars=Bars(InpSymbolName,PERIOD_M1);
   PrintFormat("ASTRA_IMPORT_OK symbol=%s imported=%d bars=%d first=%s last=%s",
               InpSymbolName,total,bars,TimeToString(first,TIME_DATE|TIME_MINUTES),
               TimeToString(last,TIME_DATE|TIME_MINUTES));
   Finish(0);
}
//+------------------------------------------------------------------+
