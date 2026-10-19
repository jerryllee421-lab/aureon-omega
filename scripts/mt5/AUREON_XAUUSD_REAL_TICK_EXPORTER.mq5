#property strict
#property version "1.00"
#property description "AUREON research-only MT5 real-tick exporter. No trade functions."

input string InpSymbol = "XAUUSD";
input int InpDays = 740; // More than two calendar years.

string OUT_DIR = "AUREON_XAUUSD_Ticks";

string DayKey(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return StringFormat("%04d%02d%02d", dt.year, dt.mon, dt.day);
}

bool WriteDay(datetime from_time, datetime to_time, long &count,
              long &first_msc, long &last_msc, int &copy_error)
{
   count = 0; first_msc = 0; last_msc = 0; copy_error = 0;
   ulong from_msc = (ulong)((long)from_time * 1000);
   ulong to_msc = (ulong)((long)to_time * 1000 - 1);
   MqlTick ticks[];
   ResetLastError();
   int copied = CopyTicksRange(InpSymbol, ticks, COPY_TICKS_ALL, from_msc, to_msc);
   copy_error = GetLastError();
   if(copied <= 0) return true; // Weekends and holidays can be empty.

   string filename = OUT_DIR + "\\ticks_" + DayKey(from_time) + ".csv";
   int handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("AUREON_EXPORT_FATAL output file open failed; error=", GetLastError());
      return false;
   }
   FileWrite(handle, "time_seconds", "time_msc", "bid", "ask", "last", "volume", "volume_real", "flags");
   for(int i=0; i<copied; i++)
   {
      if(ticks[i].time_msc < (long)from_msc || ticks[i].time_msc > (long)to_msc) continue;
      if(count == 0) first_msc = (long)ticks[i].time_msc;
      last_msc = (long)ticks[i].time_msc;
      FileWrite(handle, (long)ticks[i].time, (long)ticks[i].time_msc,
         DoubleToString(ticks[i].bid, _Digits), DoubleToString(ticks[i].ask, _Digits),
         DoubleToString(ticks[i].last, _Digits), (long)ticks[i].volume,
         DoubleToString(ticks[i].volume_real, 8), (long)ticks[i].flags);
      count++;
   }
   FileClose(handle);
   return true;
}

int OnInit()
{
   if(InpDays < 730 || InpDays > 800)
   {
      Print("AUREON_EXPORT_FATAL InpDays must be 730..800.");
      return INIT_FAILED;
   }
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
   {
      Print("AUREON_EXPORT_FATAL DEMO account required; export refused.");
      return INIT_FAILED;
   }
   string server = AccountInfoString(ACCOUNT_SERVER);
   if(server != "PXBTTrading-1")
   {
      Print("AUREON_EXPORT_FATAL unexpected server; export refused. Server=", server);
      return INIT_FAILED;
   }
   int wait_seconds = 0;
   while(!TerminalInfoInteger(TERMINAL_CONNECTED) && wait_seconds < 120)
   {
      Sleep(1000); wait_seconds++;
   }
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      Print("AUREON_EXPORT_FATAL terminal connection timeout.");
      return INIT_FAILED;
   }
   if(!SymbolSelect(InpSymbol, true))
   {
      Print("AUREON_EXPORT_FATAL symbol unavailable: ", InpSymbol);
      return INIT_FAILED;
   }
   FolderCreate(OUT_DIR, FILE_COMMON);

   int manifest = FileOpen(OUT_DIR + "\\manifest.csv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(manifest == INVALID_HANDLE)
   {
      Print("AUREON_EXPORT_FATAL manifest open failed; error=", GetLastError());
      return INIT_FAILED;
   }
   FileWrite(manifest, "utc_day", "tick_count", "first_tick_msc", "last_tick_msc", "copy_error");

   datetime now_utc = TimeGMT();
   datetime end_day = now_utc - (now_utc % 86400);
   datetime start_day = end_day - (InpDays * 86400);
   long total_ticks = 0, earliest_tick = 0, latest_tick = 0;
   int nonempty_days = 0;
   Print("AUREON_EXPORT_START symbol=", InpSymbol, " days=", InpDays,
         " utc_start=", TimeToString(start_day, TIME_DATE),
         " utc_end=", TimeToString(now_utc, TIME_DATE|TIME_MINUTES),
         " source=MT5_CopyTicksRange_COPY_TICKS_ALL");

   for(datetime day=start_day; day<=now_utc; day+=86400)
   {
      datetime range_end = day + 86400;
      if(range_end > now_utc) range_end = now_utc;
      long n, first, last; int copy_error;
      if(!WriteDay(day, range_end, n, first, last, copy_error))
      {
         FileClose(manifest); return INIT_FAILED;
      }
      FileWrite(manifest, DayKey(day), n, first, last, copy_error);
      if(n > 0)
      {
         total_ticks += n; nonempty_days++;
         if(earliest_tick == 0 || first < earliest_tick) earliest_tick = first;
         if(last > latest_tick) latest_tick = last;
      }
      if(((day-start_day)/86400)%30 == 0)
         Print("AUREON_EXPORT_PROGRESS day=", DayKey(day), " daily_ticks=", n, " total_ticks=", total_ticks);
   }
   FileClose(manifest);

   long requested_start = (long)start_day * 1000;
   long requested_end = (long)now_utc * 1000;
   long start_gap = earliest_tick - requested_start;
   long end_gap = requested_end - latest_tick;
   int status = FileOpen(OUT_DIR + "\\status.txt", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(status != INVALID_HANDLE)
   {
      FileWrite(status, "symbol=", InpSymbol);
      FileWrite(status, "server=", server);
      FileWrite(status, "source=MT5 CopyTicksRange COPY_TICKS_ALL");
      FileWrite(status, "requested_days=", InpDays);
      FileWrite(status, "total_ticks=", total_ticks);
      FileWrite(status, "nonempty_days=", nonempty_days);
      FileWrite(status, "first_tick_msc=", earliest_tick);
      FileWrite(status, "last_tick_msc=", latest_tick);
      FileWrite(status, "start_gap_ms=", start_gap);
      FileWrite(status, "end_gap_ms=", end_gap);
      FileClose(status);
   }
   if(total_ticks<=0 || earliest_tick==0 || latest_tick==0 ||
      start_gap > 7*86400*1000 || end_gap > 7*86400*1000)
   {
      Print("AUREON_EXPORT_FATAL coverage validation failed. total_ticks=", total_ticks,
            " start_gap_ms=", start_gap, " end_gap_ms=", end_gap);
      return INIT_FAILED;
   }
   int done = FileOpen(OUT_DIR + "\\DONE.flag", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(done == INVALID_HANDLE)
   {
      Print("AUREON_EXPORT_FATAL completion marker creation failed.");
      return INIT_FAILED;
   }
   FileWrite(done, "validated=1");
   FileWrite(done, "total_ticks=", total_ticks);
   FileClose(done);
   Print("AUREON_EXPORT_DONE symbol=", InpSymbol, " total_ticks=", total_ticks,
         " nonempty_days=", nonempty_days, " earliest_tick_msc=", earliest_tick,
         " latest_tick_msc=", latest_tick, " server=", server, " orders_sent=0");
   ExpertRemove();
   return INIT_SUCCEEDED;
}
void OnTick() {}
