//+------------------------------------------------------------------+
//|                    AUREON_CustomSymbolLoader.mq5                 |
//| Imports verified external M1 bars into an MT5 custom XAU symbol. |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
#property version "1.03"

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
   if(CustomSymbolSetInteger(InpSymbolName,prop,value))
      return true;
   PrintFormat("ASTRA_PROP_FAIL %s error=%d value=%I64d",label,GetLastError(),value);
   return false;
}

bool SetDoubleProp(ENUM_SYMBOL_INFO_DOUBLE prop,double value,string label)
{
   ResetLastError();
   if(CustomSymbolSetDouble(InpSymbolName,prop,value))
      return true;
   PrintFormat("ASTRA_PROP_FAIL %s error=%d value=%.10f",label,GetLastError(),value);
   return false;
}

bool SetStringProp(ENUM_SYMBOL_INFO_STRING prop,string value,string label)
{
   ResetLastError();
   if(CustomSymbolSetString(InpSymbolName,prop,value))
      return true;
   PrintFormat("ASTRA_PROP_FAIL %s error=%d value=%s",label,GetLastError(),value);
   return false;
}

bool ConfigureSymbol()
{
   SymbolSelect(InpSymbolName,false);

   // Clone the startup chart symbol so quote/trade sessions and other mandatory
   // specification fields start in a valid state. The test economics below
   // are then overridden explicitly for deterministic XAUUSD research.
   string origin=Symbol();
   ResetLastError();
   if(!CustomSymbolCreate(InpSymbolName,InpSymbolPath,origin))
   {
      int err=GetLastError();
      if(err!=5304)
      {
         PrintFormat("ASTRA_IMPORT_FAIL create symbol origin=%s error=%d",origin,err);
         return false;
      }
   }

   if(!SetIntProp(SYMBOL_CHART_MODE,SYMBOL_CHART_MODE_BID,"SYMBOL_CHART_MODE")) return false;
   if(!SetIntProp(SYMBOL_DIGITS,InpDigits,"SYMBOL_DIGITS")) return false;
   if(!SetDoubleProp(SYMBOL_POINT,InpPoint,"SYMBOL_POINT")) return false;
   if(!SetDoubleProp(SYMBOL_TRADE_TICK_SIZE,InpPoint,"SYMBOL_TRADE_TICK_SIZE")) return false;
   if(!SetDoubleProp(SYMBOL_TRADE_CONTRACT_SIZE,InpContractSize,"SYMBOL_TRADE_CONTRACT_SIZE")) return false;

   // MT5 validates minimum/step against the maximum. Set MAX before MIN.
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
   if(!SetIntProp(SYMBOL_ORDER_MODE,SYMBOL_ORDER_MARKET|SYMBOL_ORDER_LIMIT|SYMBOL_ORDER_SL|SYMBOL_ORDER_TP,"SYMBOL_ORDER_MODE")) return false;
   if(!SetIntProp(SYMBOL_FILLING_MODE,SYMBOL_FILLING_IOC,"SYMBOL_FILLING_MODE")) return false;

   // PROFIT/LOSS tick values are derived/read-only on current MT5 builds.
   double tickValue=InpPoint*InpContractSize;
   if(!SetDoubleProp(SYMBOL_TRADE_TICK_VALUE,tickValue,"SYMBOL_TRADE_TICK_VALUE")) return false;

   if(!SetStringProp(SYMBOL_DESCRIPTION,"AUREON ASTRA XAUUSD research symbol","SYMBOL_DESCRIPTION")) return false;
   if(!SetStringProp(SYMBOL_CURRENCY_BASE,"XAU","SYMBOL_CURRENCY_BASE")) return false;
   if(!SetStringProp(SYMBOL_CURRENCY_PROFIT,"USD","SYMBOL_CURRENCY_PROFIT")) return false;
   if(!SetStringProp(SYMBOL_CURRENCY_MARGIN,"USD","SYMBOL_CURRENCY_MARGIN")) return false;

   PrintFormat("ASTRA_SYMBOL_CONFIG_OK origin=%s digits=%d point=%.6f contract=%.2f",
               origin,InpDigits,InpPoint,InpContractSize);
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
   if(CustomRatesDelete(InpSymbolName,0,LONG_MAX)<0)
      PrintFormat("ASTRA_IMPORT_WARN CustomRatesDelete error=%d",GetLastError());

   int handle=FileOpen(InpCsvFile,FILE_READ|FILE_CSV|FILE_ANSI,',');
   if(handle==INVALID_HANDLE)
   {
      PrintFormat("ASTRA_IMPORT_FAIL FileOpen(%s) error=%d",InpCsvFile,GetLastError());
      Finish(3);
      return;
   }

   // CSV header: time,open,high,low,close,tick_volume,spread
   for(int k=0;k<7;k++) FileReadString(handle);

   const int BATCH=250000;
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
         PrintFormat("ASTRA_IMPORT_PROGRESS imported=%d last=%s",
                     total,TimeToString(last,TIME_DATE|TIME_MINUTES));
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
               InpSymbolName,total,bars,
               TimeToString(first,TIME_DATE|TIME_MINUTES),
               TimeToString(last,TIME_DATE|TIME_MINUTES));
   Finish(0);
}
//+------------------------------------------------------------------+
