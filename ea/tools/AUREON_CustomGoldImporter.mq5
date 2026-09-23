//+------------------------------------------------------------------+
//| AUREON_CustomGoldImporter.mq5                                    |
//| Offline CI helper: import pinned XAUUSD M1 bars into custom MT5  |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string InpCustomSymbol = "AUREON_XAUUSD";
input string InpCsvFile      = "AUREON_XAUUSD_M1.csv";

bool SetIfPossibleInteger(const string symbol, const ENUM_SYMBOL_INFO_INTEGER prop, const long value)
{
   ResetLastError();
   if(CustomSymbolSetInteger(symbol,prop,value))
      return true;
   PrintFormat("WARN CustomSymbolSetInteger %d failed: %d",(int)prop,GetLastError());
   return false;
}

bool SetIfPossibleDouble(const string symbol, const ENUM_SYMBOL_INFO_DOUBLE prop, const double value)
{
   ResetLastError();
   if(CustomSymbolSetDouble(symbol,prop,value))
      return true;
   PrintFormat("WARN CustomSymbolSetDouble %d failed: %d",(int)prop,GetLastError());
   return false;
}

bool SetIfPossibleString(const string symbol, const ENUM_SYMBOL_INFO_STRING prop, const string value)
{
   ResetLastError();
   if(CustomSymbolSetString(symbol,prop,value))
      return true;
   PrintFormat("WARN CustomSymbolSetString %d failed: %d",(int)prop,GetLastError());
   return false;
}

bool ReadCsv(MqlRates &rates[])
{
   ResetLastError();
   int h=FileOpen(InpCsvFile,FILE_READ|FILE_CSV|FILE_ANSI,',');
   if(h==INVALID_HANDLE)
   {
      PrintFormat("AUREON_IMPORT_ERROR FileOpen(%s)=%d",InpCsvFile,GetLastError());
      return false;
   }

   ArrayResize(rates,0);
   int count=0;

   while(!FileIsEnding(h))
   {
      string time_text=FileReadString(h);
      string open_text=FileReadString(h);
      string high_text=FileReadString(h);
      string low_text=FileReadString(h);
      string close_text=FileReadString(h);
      string tick_text=FileReadString(h);
      string spread_text=FileReadString(h);
      string real_text=FileReadString(h);

      if(time_text=="" || time_text=="time")
         continue;

      datetime when=StringToTime(time_text);
      double open=StringToDouble(open_text);
      double high=StringToDouble(high_text);
      double low=StringToDouble(low_text);
      double close=StringToDouble(close_text);
      long tick_volume=(long)StringToInteger(tick_text);
      int spread=(int)StringToInteger(spread_text);
      long real_volume=(long)StringToInteger(real_text);

      if(when<=0 || open<=0.0 || high<open || high<close || low>open || low>close || high<low)
      {
         PrintFormat("AUREON_IMPORT_ERROR invalid row time=%s O=%.5f H=%.5f L=%.5f C=%.5f",
                     time_text,open,high,low,close);
         FileClose(h);
         return false;
      }

      int n=ArraySize(rates);
      if(ArrayResize(rates,n+1,8192)<0)
      {
         Print("AUREON_IMPORT_ERROR ArrayResize failed");
         FileClose(h);
         return false;
      }

      rates[n].time=when;
      rates[n].open=open;
      rates[n].high=high;
      rates[n].low=low;
      rates[n].close=close;
      rates[n].tick_volume=(tick_volume>0 ? tick_volume : 1);
      rates[n].spread=(spread>=0 ? spread : 0);
      rates[n].real_volume=(real_volume>=0 ? real_volume : 0);
      count++;
   }

   FileClose(h);
   PrintFormat("AUREON_IMPORT_READ rows=%d",count);
   return(count>0);
}

void WriteMarker(const string status,const int bars,const int err)
{
   int h=FileOpen("AUREON_CUSTOM_IMPORT_RESULT.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE)
      return;
   FileWrite(h,status);
   FileWrite(h,IntegerToString(bars));
   FileWrite(h,IntegerToString(err));
   FileClose(h);
}

void OnStart()
{
   PrintFormat("AUREON_IMPORT_START origin=%s target=%s file=%s",_Symbol,InpCustomSymbol,InpCsvFile);

   ResetLastError();
   if(!CustomSymbolCreate(InpCustomSymbol,"AUREON",_Symbol))
   {
      int create_error=GetLastError();
      if(create_error!=5304)
      {
         PrintFormat("AUREON_IMPORT_ERROR CustomSymbolCreate=%d",create_error);
         WriteMarker("CREATE_FAILED",0,create_error);
         return;
      }
   }

   // Configure gold-like price precision before loading history.
   SetIfPossibleInteger(InpCustomSymbol,SYMBOL_DIGITS,3);
   SetIfPossibleInteger(InpCustomSymbol,SYMBOL_TRADE_MODE,SYMBOL_TRADE_MODE_FULL);
   SetIfPossibleDouble(InpCustomSymbol,SYMBOL_POINT,0.001);
   SetIfPossibleDouble(InpCustomSymbol,SYMBOL_TRADE_TICK_SIZE,0.001);
   SetIfPossibleDouble(InpCustomSymbol,SYMBOL_TRADE_CONTRACT_SIZE,100.0);
   SetIfPossibleDouble(InpCustomSymbol,SYMBOL_VOLUME_MIN,0.01);
   SetIfPossibleDouble(InpCustomSymbol,SYMBOL_VOLUME_MAX,100.0);
   SetIfPossibleDouble(InpCustomSymbol,SYMBOL_VOLUME_STEP,0.01);
   SetIfPossibleString(InpCustomSymbol,SYMBOL_DESCRIPTION,"AUREON pinned external XAUUSD research proxy");
   SetIfPossibleString(InpCustomSymbol,SYMBOL_CURRENCY_BASE,"XAU");
   SetIfPossibleString(InpCustomSymbol,SYMBOL_CURRENCY_PROFIT,"USD");
   SetIfPossibleString(InpCustomSymbol,SYMBOL_CURRENCY_MARGIN,"USD");

   MqlRates rates[];
   if(!ReadCsv(rates))
   {
      WriteMarker("CSV_FAILED",0,GetLastError());
      return;
   }

   datetime first=rates[0].time;
   datetime last=rates[ArraySize(rates)-1].time;

   ResetLastError();
   int replaced=CustomRatesReplace(InpCustomSymbol,first,last,rates,WHOLE_ARRAY);
   int import_error=GetLastError();
   if(replaced<0)
   {
      PrintFormat("AUREON_IMPORT_ERROR CustomRatesReplace=%d",import_error);
      WriteMarker("IMPORT_FAILED",0,import_error);
      return;
   }

   ResetLastError();
   if(!SymbolSelect(InpCustomSymbol,true))
      PrintFormat("WARN SymbolSelect failed: %d",GetLastError());

   int bars=Bars(InpCustomSymbol,PERIOD_M1,first,last);
   PrintFormat("AUREON_IMPORT_OK replaced=%d bars=%d first=%s last=%s",
               replaced,bars,TimeToString(first,TIME_DATE|TIME_MINUTES),
               TimeToString(last,TIME_DATE|TIME_MINUTES));
   WriteMarker("OK",bars,0);
}
//+------------------------------------------------------------------+
