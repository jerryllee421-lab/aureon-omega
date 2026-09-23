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

bool SetIntProp(ENUM_SYMBOL_INFO_INTEGER prop,long value,string label)
{
   ResetLastError();
   if(CustomSymbolSetInteger(InpSymbolName,prop,value)) return true;
   PrintFormat("ASTRA_IMPORT_FAIL property=%s value=%I64d error=%d",label,value,GetLastError());
   return false;
}

bool SetDoubleProp(ENUM_SYMBOL_INFO_DOUBLE prop,double value,string label)
{
   ResetLastError();
   if(CustomSymbolSetDouble(InpSymbolName,prop,value)) return true;
   PrintFormat("ASTRA_IMPORT_FAIL property=%s value=%.10f error=%d",label,value,GetLastError());
   return false;
}

bool SetStringProp(ENUM_SYMBOL_INFO_STRING prop,string value,string label)
{
   ResetLastError();
   if(CustomSymbolSetString(InpSymbolName,prop,value)) return true;
   PrintFormat("ASTRA_IMPORT_FAIL property=%s value=%s error=%d",label,value,GetLastError());
   return false;
}

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

   // Apply specification in dependency-safe order. In particular, MT5
   // validates VOLUME_MIN against VOLUME_MAX, so MAX must be set first.
   if(!SetIntProp(SYMBOL_CHART_MODE,SYMBOL_CHART_MODE_BID,"SYMBOL_CHART_MODE")) return false;
   if(!SetIntProp(SYMBOL_DIGITS,InpDigits,"SYMBOL_DIGITS")) return false;
   if(!SetDoubleProp(SYMBOL_POINT,InpPoint,"SYMBOL_POINT")) return false;
   if(!SetDoubleProp(SYMBOL_TRADE_TICK_SIZE,InpPoint,"SYMBOL_TRADE_TICK_SIZE")) return false;
   if(!SetDoubleProp(SYMBOL_TRADE_CONTRACT_SIZE,InpContractSize,"SYMBOL_TRADE_CONTRACT_SIZE")) return false;

   if(!SetDoubleProp(SYMBOL_VOLUME_MAX,InpMaxVolume,"SYMBOL_VOLUME_MAX")) return false;
   if(!SetDoubleProp(SYMBOL_VOLUME_STEP,InpVolumeStep,"SYMBOL_VOLUME_STEP")) return false;
   if(!SetDoubleProp(SYMBOL_VOLUME_MIN,InpMinVolume,"SYMBOL_VOLUME_MIN")) return false;
   if(!SetDoubleProp(SYMBOL_VOLUME_LIMIT,InpMaxVolume,"SYMBOL_VOLUME_LIMIT")) return false;

   if(!SetIntProp(SYMBOL_TRADE_CALC_MODE,SYMBOL_CALC_MODE_CFD,"SYMBOL_TRADE_CALC_MODE")) return false;
   if(!SetIntProp(SYMBOL_TRADE_MODE,SYMBOL_TRADE_MODE_FULL,"SYMBOL_TRADE_MODE")) return false;
   if(!SetIntProp(SYMBOL_TRADE_EXEMODE,SYMBOL_TRADE_EXECUTION_MARKET,"SYMBOL_TRADE_EXEMODE")) return false;
   if(!SetIntProp(SYMBOL_TRADE_STOPS_LEVEL,0,"SYMBOL_TRADE_STOPS_LEVEL")) return false;
   if(!SetIntProp(SYMBOL_TRADE_FREEZE_LEVEL,0,"SYMBOL_TRADE_FREEZE_LEVEL")) return false;
   if(!SetIntProp(SYMBOL_SPREAD_FLOAT,true,"SYMBOL_SPREAD_FLOAT")) return false;
   if(!SetIntProp(SYMBOL_ORDER_MODE,SYMBOL_ORDER_MARKET|SYMBOL_ORDER_SL|SYMBOL_ORDER_TP,"SYMBOL_ORDER_MODE")) return false;
   if(!SetIntProp(SYMBOL_FILLING_MODE,SYMBOL_FILLING_IOC,"SYMBOL_FILLING_MODE")) return false;

   // Tick value is 1 point * contract size for this CFD-style research symbol.
   double tickValue=InpPoint*InpContractSize;
   if(!SetDoubleProp(SYMBOL_TRADE_TICK_VALUE,tickValue,"SYMBOL_TRADE_TICK_VALUE")) return false;
   if(!SetDoubleProp(SYMBOL_TRADE_TICK_VALUE_PROFIT,tickValue,"SYMBOL_TRADE_TICK_VALUE_PROFIT")) return false;
   if(!SetDoubleProp(SYMBOL_TRADE_TICK_VALUE_LOSS,tickValue,"SYMBOL_TRADE_TICK_VALUE_LOSS")) return false;

   if(!SetStringProp(SYMBOL_DESCRIPTION,"AUREON ASTRA XAUUSD research symbol","SYMBOL_DESCRIPTION")) return false;
   if(!SetStringProp(SYMBOL_CURRENCY_BASE,"XAU","SYMBOL_CURRENCY_BASE")) return false;
   if(!SetStringProp(SYMBOL_CURRENCY_PROFIT,"USD","SYMBOL_CURRENCY_PROFIT")) return false;
   if(!SetStringProp(SYMBOL_CURRENCY_MARGIN,"USD","SYMBOL_CURRENCY_MARGIN")) return false;

   datetime from=D'1970.01.01 00:00:00';
   datetime to=D'1970.01.01 23:59:59';
   for(int d=MONDAY;d<=FRIDAY;d++)
   {
      ResetLastError();
      if(!CustomSymbolSetSessionQuote(InpSymbolName,(ENUM_DAY_OF_WEEK)d,0,from,to))
      {
         PrintFormat("ASTRA_IMPORT_FAIL property=QUOTE_SESSION day=%d error=%d",d,GetLastError());
         return false;
      }
      ResetLastError();
      if(!CustomSymbolSetSessionTrade(InpSymbolName,(ENUM_DAY_OF_WEEK)d,0,from,to))
      {
         PrintFormat("ASTRA_IMPORT_FAIL property=TRADE_SESSION day=%d error=%d",d,GetLastError());
         return false;
      }
   }

   Print("ASTRA_IMPORT_SPEC_OK");
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
      rates[count].tick_volume=(tv>0 ? tv : 1);
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
