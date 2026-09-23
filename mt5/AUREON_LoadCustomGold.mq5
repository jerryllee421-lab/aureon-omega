#property strict
#property script_show_inputs

input string InpCsvFile      = "aureon_gold_m1.csv";
input string InpSymbol       = "AUREON_XAUUSD";
input int    InpDigits       = 3;
input double InpPoint        = 0.001;
input double InpTickSize     = 0.01;
input double InpTickValue    = 1.0;
input double InpContractSize = 100.0;

void WriteResult(const string text)
  {
   int h=FileOpen("aureon_custom_gold_result.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h!=INVALID_HANDLE)
     {
      FileWrite(h,text);
      FileClose(h);
     }
  }

bool SetSymbolProperties()
  {
   bool ok=true;
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_DIGITS,InpDigits);
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_CHART_MODE,SYMBOL_CHART_MODE_BID);
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_SPREAD_FLOAT,true);
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_TRADE_CALC_MODE,SYMBOL_CALC_MODE_CFD);
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_TRADE_MODE,SYMBOL_TRADE_MODE_FULL);
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_TRADE_EXEMODE,SYMBOL_TRADE_EXECUTION_MARKET);
   long order_mode=(long)SYMBOL_ORDER_MARKET|(long)SYMBOL_ORDER_SL|(long)SYMBOL_ORDER_TP;
   ok &= CustomSymbolSetInteger(InpSymbol,SYMBOL_ORDER_MODE,order_mode);

   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_POINT,InpPoint);
   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_TRADE_TICK_SIZE,InpTickSize);
   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_TRADE_TICK_VALUE,InpTickValue);
   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_TRADE_CONTRACT_SIZE,InpContractSize);
   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_VOLUME_MIN,0.01);
   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_VOLUME_MAX,100.0);
   ok &= CustomSymbolSetDouble(InpSymbol,SYMBOL_VOLUME_STEP,0.01);

   ok &= CustomSymbolSetString(InpSymbol,SYMBOL_CURRENCY_BASE,"XAU");
   ok &= CustomSymbolSetString(InpSymbol,SYMBOL_CURRENCY_PROFIT,"USD");
   ok &= CustomSymbolSetString(InpSymbol,SYMBOL_CURRENCY_MARGIN,"USD");
   ok &= CustomSymbolSetString(InpSymbol,SYMBOL_DESCRIPTION,"AUREON pinned external XAUUSD M1 test symbol");
   return(ok);
  }

void Fail(const string reason)
  {
   Print("AUREON_CUSTOM_GOLD_FAIL: ",reason," err=",GetLastError());
   WriteResult("FAIL|"+reason+"|"+IntegerToString(GetLastError()));
  }

void OnStart()
  {
   ResetLastError();
   if(!CustomSymbolCreate(InpSymbol,"AUREON"))
     {
      int err=GetLastError();
      if(err!=5304)
        {
         Fail("CustomSymbolCreate");
         return;
        }
     }

   ResetLastError();
   if(!SetSymbolProperties())
     {
      Fail("SetSymbolProperties");
      return;
     }

   if(!SymbolSelect(InpSymbol,true))
     {
      Fail("SymbolSelect");
      return;
     }

   int h=FileOpen(InpCsvFile,FILE_READ|FILE_CSV|FILE_ANSI,',');
   if(h==INVALID_HANDLE)
     {
      Fail("FileOpen "+InpCsvFile);
      return;
     }

   // Skip header: 10 columns.
   for(int c=0;c<10 && !FileIsEnding(h);c++)
      FileReadString(h);

   MqlRates rates[];
   int count=0;

   while(!FileIsEnding(h))
     {
      string stamp=FileReadString(h);
      if(stamp=="")
         break;

      double bid_open =FileReadNumber(h);
      double bid_high =FileReadNumber(h);
      double bid_low  =FileReadNumber(h);
      double bid_close=FileReadNumber(h);

      // Read ask OHLC for provenance/alignment; MT5 1-minute-OHLC testing
      // uses Bid bars plus the per-minute spread field for Ask.
      double ask_open =FileReadNumber(h);
      double ask_high =FileReadNumber(h);
      double ask_low  =FileReadNumber(h);
      double ask_close=FileReadNumber(h);
      int spread_points=(int)FileReadNumber(h);

      datetime t=StringToTime(stamp);
      if(t<=0 || bid_open<=0 || bid_high<=0 || bid_low<=0 || bid_close<=0)
        {
         FileClose(h);
         Fail("Invalid CSV row at "+stamp);
         return;
        }

      if(bid_high<MathMax(bid_open,bid_close) ||
         bid_low>MathMin(bid_open,bid_close) ||
         bid_low>bid_high)
        {
         FileClose(h);
         Fail("Invalid OHLC at "+stamp);
         return;
        }

      int new_size=ArrayResize(rates,count+1,65536);
      if(new_size<count+1)
        {
         FileClose(h);
         Fail("ArrayResize");
         return;
        }

      rates[count].time=t;
      rates[count].open=bid_open;
      rates[count].high=bid_high;
      rates[count].low=bid_low;
      rates[count].close=bid_close;

      // Source mirror does not provide market tick volume. Value 4 is a
      // modeling count only so MT5's explicit "1 minute OHLC" mode emits
      // O/H/L/C events. It must not be interpreted as market volume.
      rates[count].tick_volume=4;
      rates[count].spread=MathMax(0,spread_points);
      rates[count].real_volume=0;
      count++;
     }

   FileClose(h);

   if(count<500)
     {
      Fail("Insufficient rows "+IntegerToString(count));
      return;
     }

   ResetLastError();
   int updated=CustomRatesUpdate(InpSymbol,rates,count);
   if(updated<0)
     {
      Fail("CustomRatesUpdate");
      return;
     }

   int bars=Bars(InpSymbol,PERIOD_M1);
   if(bars<500)
     {
      Fail("Bars after import "+IntegerToString(bars));
      return;
     }

   string msg=StringFormat("PASS|symbol=%s|rows=%d|updated=%d|bars=%d|first=%s|last=%s",
                           InpSymbol,count,updated,bars,
                           TimeToString(rates[0].time,TIME_DATE|TIME_MINUTES),
                           TimeToString(rates[count-1].time,TIME_DATE|TIME_MINUTES));
   Print("AUREON_CUSTOM_GOLD_PASS: ",msg);
   WriteResult(msg);
  }
