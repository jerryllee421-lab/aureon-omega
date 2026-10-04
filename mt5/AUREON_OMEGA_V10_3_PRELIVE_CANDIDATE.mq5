//+------------------------------------------------------------------+
//| AUREON_OMEGA_V10_3_PRELIVE_CANDIDATE.mq5              |
//| Research-grade XAUUSD market-relationship / sequence engine      |
//|                                                                  |
//| PURPOSE                                                          |
//|  Upgrade V9.2 from static confluence checks into a forensic lab  |
//|  that measures location, ordered M1 event sequences, execution   |
//|  realism, event expectancy and portfolio expectancy separately.  |
//|                                                                  |
//| FROZEN CONTROL                                                   |
//|  - XAUUSD M5                                                     |
//|  - 20-bar liquidity sweep/reclaim                                |
//|  - RSI(14) <=30 long / >=70 short                               |
//|  - ADX Wilder(14) <=30                                           |
//|  - >=2 ATR extension from EMA21                                  |
//|  - ATR14 / median ATR14(50) in [0.80,1.80)                      |
//|  - London research session 07:00-12:00 UTC                       |
//|  - next M5 bar first-tick virtual entry                          |
//|                                                                  |
//| V9.3 CORRECTIONS                                                 |
//|  - configurable historical DST-aware broker clock                |
//|  - previous TRADING day, not simply calendar yesterday           |
//|  - S/R penetration classes + maximum penetration veto            |
//|  - M1 ordered sequence: raid -> reclaim -> MSS -> displacement   |
//|    -> FVG -> retracement                                         |
//|  - stricter ATR-normalized fresh FVG definition                  |
//|  - validated trendlines with slope/separation/break checks        |
//|  - gap-aware stop fills                                          |
//|  - independent event probes (12/36 M5 bars)                      |
//|  - portfolio simulation kept separate from event expectancy      |
//|  - DEV / VALIDATION / HOLDOUT and half-year reporting            |
//|                                                                  |
//| V10 AUTONOMOUS HYPER SCALPER INTELLIGENCE                             |
//|  - Super Scalper readiness: BLOCKED/WATCH/ARMED/TRIGGERED        |
//|  - daily/London VWAP + anchored VWAP + deviation bands           |
//|  - POC / VAH / VAL volume-profile intelligence                   |
//|  - volume-ablation variants + hybrid structural targets          |
//|  - native MT5 Strategy Tester execution for standard reports     |
//|  - automatic safe DEMO execution                      |
//|  - LIVE order execution hard-blocked in code                     |
//|  - risk-sized volume, spread/slippage/margin/risk governors      |
//|  - staged TP1/TP2 protection + TP3 runner                        |
//|                                                                  |
//| V10 AUTONOMOUS HYPER SCALPER                                      |
//|  - zero manual inputs: all parameters compiled into this EA         |
//|  - EMA100 H1/M5 regime + M1 EMA21 precision timing                  |
//|  - 5s/15s/30s tick-aggregated microstructure engine                 |
//|  - 1,000/day execution capacity; no forced-trade quota              |
//|  - structural SL + hybrid VWAP/POC/liquidity targets                |
//|  - Strategy Tester + DEMO auto execution; REAL hard blocked         |
//|                                                                  |
//| IMPORTANT                                                        |
//|  - Completed bars only; no future bars in signal features.       |
//|  - Strategy Tester and DEMO only for broker orders.              |
//|  - LIVE accounts can never receive orders from this EA.          |
//|  - No DXY fusion in this build: isolate Gold structure first.    |
//+------------------------------------------------------------------+
#property copyright "AUREON OMEGA"
#property version   "10.30"
#property strict

//-------------------------- Enumerations -----------------------------
enum ENUM_BROKER_DST_RULE
  {
   DST_NONE = 0,
   DST_EU_LAST_SUNDAY = 1,
   DST_US_SUNDAY_RULE = 2
  };

enum ENUM_PENETRATION_CLASS
  {
   PEN_NONE  = 0,
   PEN_TOUCH = 1,
   PEN_SWEEP = 2,
   PEN_DEEP  = 3,
   PEN_FAIL  = 4
  };

enum ENUM_EXECUTION_MODE
  {
   EXEC_VIRTUAL_ONLY    = 0,
   EXEC_STRATEGY_TESTER = 1,
   EXEC_DEMO_ARMED      = 2,
   EXEC_AUTO_SAFE       = 3   // tester=>TESTER, chart=>VIRTUAL unless DEMO_ARMED+explicit arm
  };

enum ENUM_VOLUME_MODE
  {
   VOLUME_RISK_PERCENT = 0,
   VOLUME_FIXED_LOT    = 1
  };

enum ENUM_SCALPER_STATE
  {
   SCALPER_BLOCKED   = 0,
   SCALPER_WATCH     = 1,
   SCALPER_ARMED     = 2,
   SCALPER_TRIGGERED = 3
  };

enum ENUM_VARIANT
  {
   VAR_CONTROL             = 0,
   VAR_PDH_PDL             = 1,
   VAR_ASIA_RANGE          = 2,
   VAR_SWING_SR            = 3,
   VAR_FIB                 = 4,
   VAR_M5_STRUCTURE_BREAK  = 5,
   VAR_SEQ_M1_MSS          = 6,
   VAR_SEQ_DISPLACEMENT    = 7,
   VAR_SEQ_FVG             = 8,
   VAR_SEQ_RETRACE         = 9,
   VAR_TRENDLINE           = 10,
   VAR_LOCATION_COMPOSITE  = 11,
   VAR_SNIPER_COMPOSITE    = 12,
   VAR_VWAP_CONTEXT        = 13,
   VAR_VOLUME_PROFILE      = 14,
   VAR_VOLUME_COMPOSITE    = 15,
   VAR_SUPER_SCALPER       = 16,
   VAR_SUPER_SCALPER_VOLUME= 17,
   VARIANT_COUNT           = 18
  };

enum ENUM_TARGET_MODE
  {
   TARGET_FIXED_R    = 0,
   TARGET_HYBRID     = 1,
   TARGET_STRUCTURE  = 2
  };

enum ENUM_EMA100_STATE
  {
   EMA100_NEUTRAL=0,
   EMA100_STRONG_BULL=1,
   EMA100_BULL_PULLBACK=2,
   EMA100_RECLAIM=3,
   EMA100_SUPPORT=4,
   EMA100_COMPRESSION=5,
   EMA100_RESISTANCE=6,
   EMA100_REJECTION=7,
   EMA100_BEAR_PULLBACK=8,
   EMA100_STRONG_BEAR=9,
   EMA100_EXTENDED_ABOVE=10,
   EMA100_EXTENDED_BELOW=11
  };

//--------------------------- Inputs ---------------------------------
ulong  InpResearchId                    = 2610041030;
bool   InpEnforceGoldSymbol             = true;

// Frozen Gold control signal -- do not tune in the first parity run.
int    InpGoldRSIPeriod                 = 14;
double InpGoldRSILongMax                = 30.0;
double InpGoldRSIShortMin               = 70.0;
int    InpGoldADXPeriod                 = 14;
double InpGoldADXMax                    = 30.0;
int    InpGoldATRPeriod                 = 14;
int    InpGoldEMAPeriod                 = 21;
int    InpGoldSweepLookback             = 20;
double InpGoldExtensionATR              = 2.0;
int    InpGoldVolMedianBars             = 50;
double InpGoldVolRatioMin               = 0.80;
double InpGoldVolRatioMaxExclusive      = 1.80;
int    InpSessionStartUTC               = 7;
int    InpSessionEndUTCExclusive        = 12;
int    InpHyperSessionStartUTC          = 6;
int    InpHyperSessionEndUTCExclusive   = 21;

// Historical broker clock reconstruction.
int                  InpBrokerBaseUTCOffsetHours = 2;
int                  InpBrokerDSTAddHours        = 1;
ENUM_BROKER_DST_RULE InpBrokerDSTRule            = DST_EU_LAST_SUNDAY;

// Chronological research folds. Values are interpreted as UTC.
datetime InpDevelopmentEndUTC            = D'2023.12.31 23:59';
datetime InpValidationEndUTC             = D'2024.12.31 23:59';

// Frozen virtual exit geometry (V7 EDGE_MAX control).
double InpVirtualSL_ATR                  = 2.5;
double InpVirtualRR                      = 4.0;
int    InpVirtualMaxHoldM5Bars           = 96;

// Virtual execution-cost stress.
double InpVirtualEntrySlippagePoints     = 0.0;
double InpVirtualExitSlippagePoints      = 0.0;
double InpVirtualCommissionPointsRT      = 0.0;
double InpMaxObservedSpreadPoints        = 0.0; // 0 = no veto

// Location / structure definitions.
double InpLevelToleranceATR              = 0.25;
double InpTouchPenetrationATR            = 0.15;
double InpSweepPenetrationATR            = 0.50;
double InpMaxLevelPenetrationATR         = 1.00;
int    InpSwingLookbackBars              = 120;
int    InpPivotSpanBars                  = 2;
int    InpM5StructureLookbackBars        = 3;
double InpMinFibImpulseATR               = 2.0;
int    InpLocationCompositeMinFeatures   = 2;

// M1 ordered-sequence definitions.
int    InpM1MSSLookbackBars              = 5;
double InpM1DisplacementBodyATR          = 0.60;
double InpM1DisplacementBodyRatio        = 0.60;
double InpM1MinFVG_ATR                   = 0.10;
double InpM1FVGRetraceFraction           = 0.50;
bool   InpRequireFreshFVG                 = true;

// Trendline quality controls.
int    InpTrendlineMinPivotSeparationBars= 5;
int    InpTrendlineMinAgeBars            = 10;
double InpTrendlineMaxPenetrationATR     = 0.50;
bool   InpTrendlineRequireDirectionalSlope = true;

// Previous-session data quality.
int    InpPreviousTradingDaySearchDays   = 7;
int    InpMinTradingDayM5Bars            = 100;

// Independent event probes. Portfolio execution remains frozen 4R.
int    InpEventHorizonFastM5Bars         = 12;
int    InpEventHorizonSlowM5Bars         = 36;

// Research reference target ladder (logged only).
double InpReferenceTP1_R                 = 1.0;
double InpReferenceTP2_R                 = 2.0;
double InpReferenceTP3_R                 = 4.0;

// V9.5 VWAP / volume-profile intelligence.
bool   InpEnableVolumeIntelligence              = true;
bool   InpPreferRealVolume                      = true;
int    InpVolumeProfileBins                     = 64;
double InpValueAreaFraction                     = 0.70;
int    InpMinVolumeM1Bars                       = 30;
int    InpVWAPSlopeLookbackMinutes              = 15;
double InpVolumeLevelToleranceATR               = 0.20;
double InpVWAPBandSigma1                        = 1.0;
double InpVWAPBandSigma2                        = 2.0;
bool   InpRequireVolumeConfirmationForExecution = false;
int    InpMinVolumeScoreForExecution            = 7;
ENUM_TARGET_MODE InpTargetMode                  = TARGET_HYBRID;
double InpStructuralTP1MinR                     = 0.50;
double InpStructuralTP2MinR                     = 1.25;
double InpStructuralTP3MinR                     = 2.00;

// V9.5 Super Scalper / production-test execution.
ENUM_EXECUTION_MODE InpExecutionMode             = EXEC_AUTO_SAFE;
bool   InpArmDemoExecution                       = true; // autonomous DEMO; LIVE still blocked
ulong  InpMagic                                  = 10300261004;
ENUM_VOLUME_MODE InpVolumeMode                   = VOLUME_RISK_PERCENT;
double InpRiskPercent                            = 0.05;
double InpMaxRiskPercent                         = 0.10;
double InpFixedLot                               = 0.10;
int    InpMaxTradesPerDay                        = 200; // above observed V2.17 max day (165), below runaway territory
int    InpMinimumPostExitSeconds                 = 6;   // <=5s re-entry bucket was negative in V2.12 + V2.17
bool   InpUseDirectionalRisk                     = true;
double InpLongRiskMultiplier                    = 0.85;
double InpShortRiskMultiplier                   = 1.00;
bool   InpUseLossStreakQuarantine                = true;
int    InpQualifyingLossStreak                    = 3;
double InpQualifyingLossR                         = -0.50;
int    InpLossStreakPauseMinutes                  = 15;
double InpDailyLossLimitPct                      = 3.0;
double InpEquityDrawdownLimitPct                 = 6.0;
bool   InpApplyRiskGovernorInTester              = true;
bool   InpEmergencyCloseOnGovernor               = true;
double InpMaxProductionSpreadPoints              = 80.0;
double InpMaxExpectedSlippagePoints              = 35.0;
double InpMaxTickAgeSeconds                       = 3.0;
double InpExpectedSlippagePointsRT               = 20.0;
int    InpOrderDeviationPoints                   = 35;
double InpAssumedGrossEdgeR                      = 0.212;
double InpMinNetEdgeR                            = 0.05;
int    InpArmedReadiness                         = 65;
int    InpTriggeredReadiness                     = 82;
double InpProductionSL_ATR                       = 2.5;
double InpProductionTP1_R                        = 1.0;
double InpProductionTP2_R                        = 2.0;
double InpProductionTP3_R                        = 4.0;
int    InpProductionMaxHoldM5Bars                = 12;
int    InpProductionMaxHoldSeconds               = 600;
int    InpAdverseExitMinSeconds                   = 90;
double InpMicroMinRangeATR                        = 0.05;
double InpMicroEMATouchATR                        = 0.20;
int    InpMicroBarSecondsFast                     = 5;
int    InpMicroBarSecondsMedium                   = 15;
int    InpMicroBarSecondsSlow                     = 30;
double InpTP1CloseFraction                       = 0.35;
double InpTP2CloseFraction                       = 0.35;
bool   InpMoveSLToBEAtTP1                       = true;
bool   InpLock1RAtTP2                            = true;
bool   InpShowDashboard                          = true;
bool   InpWriteExecutionEvidence                 = true;
string InpExecutionEvidenceFile                  = "AUREON_V10_3_EXECUTION.csv";

// Evidence outputs.
bool   InpWriteSignalEvidence            = true;
bool   InpWriteTradeEvidence             = true;
bool   InpWriteEventEvidence             = true;
bool   InpWriteSummary                   = true;
string InpSignalEvidenceFile             = "AUREON_V10_FORENSICS_SIGNALS.csv";
string InpTradeEvidenceFile              = "AUREON_V10_FORENSICS_TRADES.csv";
string InpEventEvidenceFile              = "AUREON_V10_FORENSICS_EVENTS.csv";
string InpSummaryFile                    = "AUREON_V10_FORENSICS_SUMMARY.csv";
string InpPeriodSummaryFile              = "AUREON_V10_PERIOD_SUMMARY.csv";
bool   InpVerbose                        = true;

//-------------------------- Structures -------------------------------
struct GoldContext
  {
   datetime signal_time;
   int      direction;
   double   atr;
   double   rsi;
   double   adx;
   double   ema21;
   double   ema55;
   double   ema100_m5;
   double   ema200;
   double   ema100_h1;
   double   ema100_slope_atr;
   double   ema21_100_sep_atr;
   int      ema100_state;
   bool     ema_stack_aligned;
   double   vol_ratio;
   double   prior_low;
   double   prior_high;
   double   signal_open;
   double   signal_low;
   double   signal_high;
   double   signal_close;
   double   extension;
   double   spread_points;
   int      historical_utc_offset;
   string   fold;
   string   halfyear;
  };

struct VolumeContext
  {
   bool     valid;
   int      bars;
   int      source_quality;       // 0=tick volume, 1=mixed, 2=real volume
   double   real_volume_fraction;

   double   daily_vwap;
   double   daily_sigma;
   double   london_vwap;
   double   london_sigma;
   double   anchored_vwap;
   datetime anchored_vwap_time;

   double   vwap_upper1;
   double   vwap_lower1;
   double   vwap_upper2;
   double   vwap_lower2;

   double   poc;
   double   vah;
   double   val;

   double   daily_vwap_distance_atr;
   double   london_vwap_distance_atr;
   double   anchored_vwap_distance_atr;
   double   poc_distance_atr;
   double   vwap_slope_atr_per_15m;

   int      value_area_state;     // -1 below, 0 inside, +1 above
   bool     vwap_reclaim;
   bool     value_area_reclaim;
   bool     mean_reversion_path;
   bool     volume_location_ok;
   int      score;
  };

struct FeatureContext
  {
   bool     valid;

   double   prev_day_high;
   double   prev_day_low;
   bool     prev_day_ok;
   double   prev_day_distance_atr;
   double   prev_day_penetration_atr;
   int      prev_day_pen_class;

   double   asia_high;
   double   asia_low;
   bool     asia_ok;
   double   asia_distance_atr;
   double   asia_penetration_atr;
   int      asia_pen_class;

   double   swing_level;
   int      swing_shift;
   bool     swing_ok;
   double   swing_distance_atr;
   double   swing_penetration_atr;
   int      swing_pen_class;

   double   fib_level;
   double   fib_ratio;
   bool     fib_ok;
   double   fib_distance_atr;

   bool     m5_structure_break;

   bool     seq_raid;
   bool     seq_reclaim;
   bool     seq_mss;
   bool     seq_displacement;
   bool     seq_fvg;
   bool     seq_retrace;
   datetime raid_time;
   datetime reclaim_time;
   datetime mss_time;
   datetime displacement_time;
   datetime fvg_time;
   datetime retrace_time;
   double   fvg_low;
   double   fvg_high;
   double   fvg_gap_atr;
   double   fvg_retrace_depth;

   double   trendline_level;
   bool     trendline_ok;
   double   trendline_distance_atr;
   double   trendline_slope_atr_per_bar;
   int      trendline_age_bars;
   int      trendline_pivot_separation_bars;

   VolumeContext volume;

   int      location_count;
   int      feature_count;
   int      feature_mask;
  };

struct ScalperDecision
  {
   ENUM_SCALPER_STATE state;
   int      readiness;
   int      context_score;
   int      micro_score;
   int      timing_score;
   int      execution_score;
   int      volume_score;
   double   net_edge_r;
   double   spread_cost_r;
   double   slippage_cost_r;
   string   reason;
  };

struct ProductionState
  {
   bool     active;
   ulong    ticket;
   ulong    position_id;
   long     signal_id;
   int      direction;
   datetime signal_time;
   datetime open_time;
   double   entry;
   double   risk_distance;
   double   initial_volume;
   double   tp1;
   double   tp2;
   double   tp3;
   bool     tp1_done;
   bool     tp2_done;
  };

struct MicroBar
  {
   bool     initialized;
   datetime bucket_time;
   double   open;
   double   high;
   double   low;
   double   close;
   long     ticks;
   double   spread_sum_points;
  };

struct VirtualTrade
  {
   bool     active;
   long     signal_id;
   int      direction;
   datetime signal_time;
   datetime open_time;
   double   entry;
   double   sl;
   double   tp;
   double   risk_distance;

   double   gold_rsi;
   double   gold_adx;
   double   gold_vol_ratio;
   double   gold_extension;
   int      feature_count;
   int      feature_mask;
   string   fold;
   string   halfyear;
  };

struct VariantStats
  {
   string       name;
   long         eligible_signals;
   long         trades;
   long         wins;
   long         losses;
   long         time_exits;
   double       net_r;
   double       gross_win_r;
   double       gross_loss_r;
   double       peak_r;
   double       max_dd_r;
   long         event_fast_n;
   long         event_slow_n;
   double       event_fast_sum_r;
   double       event_slow_sum_r;
   VirtualTrade pos;
  };

struct EventProbe
  {
   bool     active;
   long     signal_id;
   int      variant;
   int      direction;
   datetime signal_time;
   datetime open_time;
   double   entry;
   double   risk_distance;
   bool     fast_done;
   bool     slow_done;
   string   fold;
   string   halfyear;
  };

struct PeriodVariantStats
  {
   string label;
   int    variant;
   long   trades;
   long   wins;
   long   losses;
   double net_r;
   double gross_win_r;
   double gross_loss_r;
   double peak_r;
   double max_dd_r;
   long   event_fast_n;
   long   event_slow_n;
   double event_fast_sum_r;
   double event_slow_sum_r;
  };

//--------------------------- Globals ---------------------------------
int hGoldATR   = INVALID_HANDLE;
int hGoldRSI   = INVALID_HANDLE;
int hGoldADX   = INVALID_HANDLE;
int hGoldEMA21 = INVALID_HANDLE;
int hGoldM1ATR = INVALID_HANDLE;
int hGoldEMA55M5 = INVALID_HANDLE;
int hGoldEMA100M5 = INVALID_HANDLE;
int hGoldEMA200M5 = INVALID_HANDLE;
int hGoldEMA100H1 = INVALID_HANDLE;
int hGoldEMA21M1 = INVALID_HANDLE;
int hGoldEMA100M1 = INVALID_HANDLE;

datetime           g_last_m5_bar = 0;
long               g_signal_id = 0;
VariantStats       g_stats[VARIANT_COUNT];
EventProbe         g_probes[];
PeriodVariantStats g_period_stats[];

ProductionState g_prod;
ScalperDecision g_last_scalper;
VolumeContext   g_last_volume;
bool             g_is_tester=false;
ENUM_EXECUTION_MODE g_effective_execution_mode=EXEC_VIRTUAL_ONLY;
bool             g_risk_halted=false;
int              g_risk_day_key=0;
double           g_day_start_equity=0.0;
double           g_peak_equity=0.0;
int              g_trades_today=0;
datetime         g_last_production_exit=0;
int              g_long_loss_streak=0;
int              g_short_loss_streak=0;
datetime         g_long_pause_until=0;
datetime         g_short_pause_until=0;
long             g_last_production_signal=0;
MicroBar         g_micro5;
MicroBar         g_micro15;
MicroBar         g_micro30;
long             g_shadow_evaluations_today=0;
long             g_shadow_setups_today=0;
int              g_micro_day_key=0;
bool             g_anchor_valid=false;
long             g_anchor_signal_id=0;
GoldContext      g_anchor_gold;
FeatureContext   g_anchor_features;
datetime         g_last_m1_bar=0;
datetime         g_control_anchor_priority_until=0;

//----------------------------- Logging -------------------------------
void Log(const string msg)
  {
   if(InpVerbose)
      Print("[AUREON V10.3] ",msg);
  }

//----------------------------- Helpers -------------------------------
bool GetBufferValue(const int handle,const int buffer,const int shift,double &value)
  {
   if(handle==INVALID_HANDLE || shift<0)
      return false;

   double x[1];
   if(CopyBuffer(handle,buffer,shift,1,x)!=1)
      return false;

   value=x[0];
   return MathIsValidNumber(value);
  }

double Median(double &values[])
  {
   int n=ArraySize(values);
   if(n<=0)
      return 0.0;

   double tmp[];
   ArrayResize(tmp,n);
   for(int i=0;i<n;i++)
      tmp[i]=values[i];

   ArraySort(tmp);
   if((n%2)==1)
      return tmp[n/2];
   return 0.5*(tmp[n/2-1]+tmp[n/2]);
  }

bool GetGoldATRMedian(const int signal_shift,const int bars,double &median_value)
  {
   if(bars<=0)
      return false;

   double values[];
   ArrayResize(values,bars);

   for(int i=0;i<bars;i++)
     {
      double v=0.0;
      if(!GetBufferValue(hGoldATR,0,signal_shift+i,v) || v<=0.0)
         return false;
      values[i]=v;
     }

   median_value=Median(values);
   return (median_value>0.0 && MathIsValidNumber(median_value));
  }

int DaysInMonth(const int year,const int mon)
  {
   if(mon==2)
     {
      bool leap=((year%400)==0 || ((year%4)==0 && (year%100)!=0));
      return (leap ? 29 : 28);
     }
   if(mon==4 || mon==6 || mon==9 || mon==11)
      return 30;
   return 31;
  }

datetime MakeDate(const int year,const int mon,const int day,const int hour=0,const int minute=0,const int sec=0)
  {
   MqlDateTime d={};
   d.year=year; d.mon=mon; d.day=day;
   d.hour=hour; d.min=minute; d.sec=sec;
   return StructToTime(d);
  }

int NthSundayDay(const int year,const int mon,const int nth)
  {
   if(nth<1) return 1;
   MqlDateTime d={};
   TimeToStruct(MakeDate(year,mon,1),d);
   int first=1+((7-d.day_of_week)%7);
   return first+7*(nth-1);
  }

int LastSundayDay(const int year,const int mon)
  {
   int last=DaysInMonth(year,mon);
   MqlDateTime d={};
   TimeToStruct(MakeDate(year,mon,last),d);
   return last-d.day_of_week;
  }

int DateKey(const datetime t)
  {
   MqlDateTime d={};
   TimeToStruct(t,d);
   return d.year*10000+d.mon*100+d.day;
  }

bool IsDSTCalendarDate(const datetime calendar_time)
  {
   if(InpBrokerDSTRule==DST_NONE || InpBrokerDSTAddHours==0)
      return false;

   MqlDateTime d={};
   TimeToStruct(calendar_time,d);
   int start_day=0,end_day=0;
   int start_mon=3,end_mon=10;

   if(InpBrokerDSTRule==DST_EU_LAST_SUNDAY)
     {
      start_day=LastSundayDay(d.year,3);
      end_day=LastSundayDay(d.year,10);
     }
   else if(InpBrokerDSTRule==DST_US_SUNDAY_RULE)
     {
      start_day=NthSundayDay(d.year,3,2);
      end_day=NthSundayDay(d.year,11,1);
      end_mon=11;
     }
   else
      return false;

   int key=DateKey(calendar_time);
   int start_key=d.year*10000+start_mon*100+start_day;
   int end_key=d.year*10000+end_mon*100+end_day;
   return (key>=start_key && key<end_key);
  }

int HistoricalOffsetHours(const datetime server_or_calendar_time)
  {
   int offset=InpBrokerBaseUTCOffsetHours;
   if(IsDSTCalendarDate(server_or_calendar_time))
      offset+=InpBrokerDSTAddHours;
   return offset;
  }

datetime ServerToUTC(const datetime server_time)
  {
   return server_time-(HistoricalOffsetHours(server_time)*3600);
  }

datetime UTCToServer(const datetime utc_time)
  {
   // Calendar-date rule is sufficient because Gold is normally closed over
   // the actual Sunday DST transition; this avoids a circular conversion.
   return utc_time+(HistoricalOffsetHours(utc_time)*3600);
  }

datetime UTCMidnight(const datetime server_time)
  {
   datetime utc=ServerToUTC(server_time);
   MqlDateTime dt={};
   TimeToStruct(utc,dt);
   dt.hour=0; dt.min=0; dt.sec=0;
   return StructToTime(dt);
  }

string FoldLabel(const datetime server_time)
  {
   datetime utc=ServerToUTC(server_time);
   if(utc<=InpDevelopmentEndUTC) return "DEV";
   if(utc<=InpValidationEndUTC)  return "VALIDATION";
   return "HOLDOUT";
  }

string HalfYearLabel(const datetime server_time)
  {
   MqlDateTime d={};
   TimeToStruct(ServerToUTC(server_time),d);
   return StringFormat("%04d-H%d",d.year,(d.mon<=6 ? 1 : 2));
  }

bool InResearchSession(const datetime server_time)
  {
   MqlDateTime dt={};
   TimeToStruct(ServerToUTC(server_time),dt);
   return (dt.hour>=InpSessionStartUTC && dt.hour<InpSessionEndUTCExclusive);
  }

bool IsNewM5Bar()
  {
   datetime t=iTime(_Symbol,PERIOD_M5,0);
   if(t<=0)
      return false;

   if(g_last_m5_bar==0)
     {
      g_last_m5_bar=t;
      return false;
     }

   if(t!=g_last_m5_bar)
     {
      g_last_m5_bar=t;
      return true;
     }

   return false;
  }

bool PreviousExtremes(const string symbol,
                      const ENUM_TIMEFRAMES tf,
                      const int signal_shift,
                      const int lookback,
                      double &prior_low,
                      double &prior_high)
  {
   if(lookback<=0 || signal_shift<0)
      return false;

   prior_low=DBL_MAX;
   prior_high=-DBL_MAX;

   for(int k=1;k<=lookback;k++)
     {
      int sh=signal_shift+k;
      double lo=iLow(symbol,tf,sh);
      double hi=iHigh(symbol,tf,sh);
      if(lo<=0.0 || hi<=0.0)
         return false;
      if(lo<prior_low)   prior_low=lo;
      if(hi>prior_high) prior_high=hi;
     }

   return (prior_low<DBL_MAX && prior_high>-DBL_MAX);
  }

double CurrentSpreadPoints()
  {
   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0 || tick.ask<tick.bid)
      return -1.0;
   return (tick.ask-tick.bid)/_Point;
  }

double AbsDistanceATR(const double price,const double level,const double atr)
  {
   if(price<=0.0 || level<=0.0 || atr<=0.0)
      return DBL_MAX;
   return MathAbs(price-level)/atr;
  }

bool M1ATRAtTime(const datetime bar_time,double &atr)
  {
   int sh=iBarShift(_Symbol,PERIOD_M1,bar_time,false);
   if(sh<0) return false;
   return (GetBufferValue(hGoldM1ATR,0,sh,atr) && atr>0.0);
  }

int GetPeriodStatIndex(const string label,const int variant,const bool create_if_missing=true)
  {
   for(int i=0;i<ArraySize(g_period_stats);i++)
      if(g_period_stats[i].label==label && g_period_stats[i].variant==variant)
         return i;

   if(!create_if_missing)
      return -1;

   int n=ArraySize(g_period_stats);
   ArrayResize(g_period_stats,n+1);
   ZeroMemory(g_period_stats[n]);
   g_period_stats[n].label=label;
   g_period_stats[n].variant=variant;
   return n;
  }

//---------------------- EMA100 Intelligence -------------------------
string EMA100StateName(const int state)
  {
   if(state==EMA100_STRONG_BULL)      return "STRONG_BULL";
   if(state==EMA100_BULL_PULLBACK)    return "BULL_PULLBACK";
   if(state==EMA100_RECLAIM)          return "RECLAIM";
   if(state==EMA100_SUPPORT)          return "SUPPORT";
   if(state==EMA100_COMPRESSION)      return "COMPRESSION";
   if(state==EMA100_RESISTANCE)       return "RESISTANCE";
   if(state==EMA100_REJECTION)        return "REJECTION";
   if(state==EMA100_BEAR_PULLBACK)    return "BEAR_PULLBACK";
   if(state==EMA100_STRONG_BEAR)      return "STRONG_BEAR";
   if(state==EMA100_EXTENDED_ABOVE)   return "EXTENDED_ABOVE";
   if(state==EMA100_EXTENDED_BELOW)   return "EXTENDED_BELOW";
   return "NEUTRAL";
  }

bool EvaluateEMA100Context(GoldContext &ctx)
  {
   double e55=0.0,e100=0.0,e100_old=0.0,e200=0.0,h1e100=0.0;
   if(!GetBufferValue(hGoldEMA55M5,0,1,e55)) return false;
   if(!GetBufferValue(hGoldEMA100M5,0,1,e100)) return false;
   if(!GetBufferValue(hGoldEMA100M5,0,4,e100_old)) return false;
   if(!GetBufferValue(hGoldEMA200M5,0,1,e200)) return false;
   if(!GetBufferValue(hGoldEMA100H1,0,1,h1e100)) return false;
   if(ctx.atr<=0.0 || e100<=0.0) return false;

   ctx.ema55=e55;
   ctx.ema100_m5=e100;
   ctx.ema200=e200;
   ctx.ema100_h1=h1e100;
   ctx.ema100_slope_atr=(e100-e100_old)/(3.0*ctx.atr);
   ctx.ema21_100_sep_atr=(ctx.ema21-e100)/ctx.atr;
   bool bull_stack=(e55>e100 && e100>e200);
   bool bear_stack=(e55<e100 && e100<e200);
   ctx.ema_stack_aligned=(ctx.direction>0 ? bull_stack : bear_stack);

   double dist=(ctx.signal_close-e100)/ctx.atr;
   double sep=MathAbs(ctx.ema21_100_sep_atr);
   if(dist>=2.0) ctx.ema100_state=EMA100_EXTENDED_ABOVE;
   else if(dist<=-2.0) ctx.ema100_state=EMA100_EXTENDED_BELOW;
   else if(sep<=0.12) ctx.ema100_state=EMA100_COMPRESSION;
   else if(bull_stack && dist>0.0 && ctx.ema100_slope_atr>0.0) ctx.ema100_state=EMA100_STRONG_BULL;
   else if(bear_stack && dist<0.0 && ctx.ema100_slope_atr<0.0) ctx.ema100_state=EMA100_STRONG_BEAR;
   else if(dist>0.0 && ctx.ema100_slope_atr>=0.0) ctx.ema100_state=EMA100_BULL_PULLBACK;
   else if(dist<0.0 && ctx.ema100_slope_atr<=0.0) ctx.ema100_state=EMA100_BEAR_PULLBACK;
   else ctx.ema100_state=EMA100_NEUTRAL;
   return true;
  }

bool InHyperSession(const datetime server_time)
  {
   datetime utc=ServerToUTC(server_time);
   MqlDateTime dt={}; TimeToStruct(utc,dt);
   return (dt.hour>=InpHyperSessionStartUTC && dt.hour<InpHyperSessionEndUTCExclusive);
  }

bool BuildAutonomousTrendAnchor(GoldContext &gold,FeatureContext &f)
  {
   ZeroMemory(gold);
   const int s=1;
   datetime signal_time=iTime(_Symbol,PERIOD_M5,s);
   if(signal_time<=0 || !InHyperSession(TimeCurrent())) return false;

   double atr=0.0,rsi=0.0,adx=0.0,ema21=0.0,e100=0.0,e100old=0.0,h1e100=0.0,h1e100old=0.0;
   if(!GetBufferValue(hGoldATR,0,s,atr) || atr<=0.0) return false;
   if(!GetBufferValue(hGoldRSI,0,s,rsi)) return false;
   if(!GetBufferValue(hGoldADX,0,s,adx)) return false;
   if(!GetBufferValue(hGoldEMA21,0,s,ema21)) return false;
   if(!GetBufferValue(hGoldEMA100M5,0,s,e100)) return false;
   if(!GetBufferValue(hGoldEMA100M5,0,4,e100old)) return false;
   if(!GetBufferValue(hGoldEMA100H1,0,1,h1e100)) return false;
   if(!GetBufferValue(hGoldEMA100H1,0,3,h1e100old)) return false;

   double cl=iClose(_Symbol,PERIOD_M5,s);
   double h1cl=iClose(_Symbol,PERIOD_H1,1);
   if(cl<=0.0 || h1cl<=0.0) return false;
   double m5slope=(e100-e100old)/(3.0*atr);
   int direction=0;
   if(cl>e100 && h1cl>h1e100 && e100>e100old && h1e100>h1e100old) direction=1;
   if(cl<e100 && h1cl<h1e100 && e100<e100old && h1e100<h1e100old) direction=-1;
   if(direction==0) return false;

   double atr_median=0.0;
   if(!GetGoldATRMedian(s,InpGoldVolMedianBars,atr_median) || atr_median<=0.0) return false;
   double vol_ratio=atr/atr_median;
   if(vol_ratio<0.60 || vol_ratio>=2.20) return false;
   double pullback=MathAbs(cl-ema21)/atr;
   if(pullback>1.25) return false;

   double prior_low=0.0,prior_high=0.0;
   if(!PreviousExtremes(_Symbol,PERIOD_M5,s,InpGoldSweepLookback,prior_low,prior_high)) return false;
   gold.signal_time=signal_time;
   gold.direction=direction;
   gold.atr=atr;
   gold.rsi=rsi;
   gold.adx=adx;
   gold.ema21=ema21;
   gold.vol_ratio=vol_ratio;
   gold.prior_low=prior_low;
   gold.prior_high=prior_high;
   gold.signal_open=iOpen(_Symbol,PERIOD_M5,s);
   gold.signal_low=iLow(_Symbol,PERIOD_M5,s);
   gold.signal_high=iHigh(_Symbol,PERIOD_M5,s);
   gold.signal_close=cl;
   gold.extension=pullback;
   gold.spread_points=CurrentSpreadPoints();
   gold.historical_utc_offset=HistoricalOffsetHours(signal_time);
   gold.fold=FoldLabel(signal_time);
   gold.halfyear=HalfYearLabel(signal_time);
   if(!EvaluateEMA100Context(gold)) return false;
   BuildFeatureContext(gold,f);
   return true;
  }

ScalperDecision BuildHyperTrendDecision(const GoldContext &gold,const FeatureContext &f,const MqlTick &tick,const bool micro_trigger)
  {
   ScalperDecision d; ZeroMemory(d);
   d.state=SCALPER_BLOCKED; d.reason="HYPER_UNSET";
   double risk=MathMax(0.75*gold.atr,10.0*_Point);
   double spread_price=tick.ask-tick.bid;
   d.spread_cost_r=(risk>0.0 ? spread_price/risk : 999.0);
   d.slippage_cost_r=(risk>0.0 ? InpExpectedSlippagePointsRT*_Point/risk : 999.0);
   d.net_edge_r=InpAssumedGrossEdgeR-d.spread_cost_r-d.slippage_cost_r;

   bool side=(gold.direction>0 ? gold.signal_close>=gold.ema100_m5 : gold.signal_close<=gold.ema100_m5);
   bool slope=(gold.direction>0 ? gold.ema100_slope_atr>0.0 : gold.ema100_slope_atr<0.0);
   int context=0;
   if(side) context+=12;
   if(slope) context+=10;
   if(gold.ema_stack_aligned) context+=8;
   if(gold.vol_ratio>=0.70 && gold.vol_ratio<2.0) context+=5;
   d.context_score=ClampInt(context,0,35);

   int micro=0;
   if(micro_trigger) micro+=18;
   if(f.m5_structure_break) micro+=4;
   if(f.seq_mss) micro+=3;
   if(f.seq_displacement) micro+=3;
   if(f.seq_fvg) micro+=2;
   d.micro_score=ClampInt(micro,0,30);

   int location=0;
   if(f.location_count>=1) location+=4;
   if(f.volume.valid && f.volume.volume_location_ok) location+=4;
   if(f.volume.valid && f.volume.score>=5) location+=2;
   d.volume_score=ClampInt(location,0,10);
   d.timing_score=10;
   double total_cost=d.spread_cost_r+d.slippage_cost_r;
   d.execution_score=ClampInt((int)MathRound(15.0*ClampDouble(1.0-total_cost/0.20,0.0,1.0)),0,15);
   d.readiness=ClampInt(d.context_score+d.micro_score+d.volume_score+d.timing_score+d.execution_score,0,100);

   double spread_points=(tick.ask-tick.bid)/_Point;
   double tick_age=MathMax(0.0,(double)(TimeCurrent()-tick.time));
   if(tick_age>InpMaxTickAgeSeconds) d.reason="STALE_TICK";
   else if(spread_points>InpMaxProductionSpreadPoints) d.reason="SPREAD";
   else if(d.net_edge_r<InpMinNetEdgeR) d.reason="NET_EDGE";
   else if(g_risk_halted && RiskGovernorApplies()) d.reason="RISK_GOVERNOR";
   else if(g_trades_today>=InpMaxTradesPerDay) d.reason="TRADE_LIMIT";
   else if(g_last_production_exit>0 && (TimeCurrent()-g_last_production_exit)<InpMinimumPostExitSeconds) d.reason="COOLDOWN";
   else if(DirectionLossPauseActive(gold.direction)) d.reason="LOSS_STREAK_PAUSE";
   else if(!micro_trigger) {d.state=SCALPER_ARMED; d.reason="WAIT_MICRO"; return d;}
   else if(d.readiness>=72) {d.state=SCALPER_TRIGGERED; d.reason="HYPER_TREND_TRIGGER"; return d;}
   else {d.state=SCALPER_WATCH; d.reason="HYPER_LOW_SCORE"; return d;}
   d.state=SCALPER_BLOCKED;
   return d;
  }

void RefreshAutonomousTrendAnchor()
  {
   datetime current_m1=iTime(_Symbol,PERIOD_M1,0);
   if(current_m1<=0 || current_m1==g_last_m1_bar) return;
   g_last_m1_bar=current_m1;
   if(TimeCurrent()<g_control_anchor_priority_until) return;
   GoldContext gold; FeatureContext f;
   if(!BuildAutonomousTrendAnchor(gold,f)) return;
   g_signal_id++;
   g_anchor_valid=true;
   g_anchor_signal_id=g_signal_id;
   g_anchor_gold=gold;
   g_anchor_features=f;
  }

//-------------------------- Gold Control -----------------------------
bool EvaluateGoldControl(GoldContext &ctx)
  {
   ZeroMemory(ctx);
   const int s=1;

   datetime signal_time=iTime(_Symbol,PERIOD_M5,s);
   if(signal_time<=0 || !InResearchSession(signal_time))
      return false;

   double atr=0.0,rsi=0.0,adx=0.0,ema21=0.0;
   if(!GetBufferValue(hGoldATR,0,s,atr))      return false;
   if(!GetBufferValue(hGoldRSI,0,s,rsi))      return false;
   if(!GetBufferValue(hGoldADX,0,s,adx))      return false;
   if(!GetBufferValue(hGoldEMA21,0,s,ema21))  return false;

   if(atr<=0.0 || adx>InpGoldADXMax)
      return false;

   double atr_median=0.0;
   if(!GetGoldATRMedian(s,InpGoldVolMedianBars,atr_median) || atr_median<=0.0)
      return false;

   double vol_ratio=atr/atr_median;
   if(vol_ratio<InpGoldVolRatioMin || vol_ratio>=InpGoldVolRatioMaxExclusive)
      return false;

   double prior_low=0.0,prior_high=0.0;
   if(!PreviousExtremes(_Symbol,PERIOD_M5,s,InpGoldSweepLookback,prior_low,prior_high))
      return false;

   double op=iOpen(_Symbol,PERIOD_M5,s);
   double lo=iLow(_Symbol,PERIOD_M5,s);
   double hi=iHigh(_Symbol,PERIOD_M5,s);
   double cl=iClose(_Symbol,PERIOD_M5,s);
   if(op<=0.0 || lo<=0.0 || hi<=0.0 || cl<=0.0)
      return false;

   bool sweep_low =(lo<prior_low  && cl>prior_low);
   bool sweep_high=(hi>prior_high && cl<prior_high);

   double long_ext =(ema21-cl)/atr;
   double short_ext=(cl-ema21)/atr;

   bool long_signal = sweep_low  && rsi<=InpGoldRSILongMax  && long_ext>=InpGoldExtensionATR;
   bool short_signal= sweep_high && rsi>=InpGoldRSIShortMin && short_ext>=InpGoldExtensionATR;

   if(long_signal==short_signal)
      return false;

   double spread_points=CurrentSpreadPoints();
   if(InpMaxObservedSpreadPoints>0.0 &&
      spread_points>=0.0 && spread_points>InpMaxObservedSpreadPoints)
      return false;

   ctx.signal_time=signal_time;
   ctx.direction=(long_signal ? 1 : -1);
   ctx.atr=atr;
   ctx.rsi=rsi;
   ctx.adx=adx;
   ctx.ema21=ema21;
   ctx.vol_ratio=vol_ratio;
   ctx.prior_low=prior_low;
   ctx.prior_high=prior_high;
   ctx.signal_open=op;
   ctx.signal_low=lo;
   ctx.signal_high=hi;
   ctx.signal_close=cl;
   ctx.extension=(long_signal ? long_ext : short_ext);
   ctx.spread_points=spread_points;
   ctx.historical_utc_offset=HistoricalOffsetHours(signal_time);
   ctx.fold=FoldLabel(signal_time);
   ctx.halfyear=HalfYearLabel(signal_time);
   EvaluateEMA100Context(ctx);
   return true;
  }

//--------------------- UTC Session / Daily Levels -------------------
bool RangeHLCount(const datetime start_server,
                  const datetime end_server,
                  double &range_high,
                  double &range_low,
                  int &bar_count)
  {
   range_high=-DBL_MAX;
   range_low=DBL_MAX;
   bar_count=0;
   if(start_server<=0 || end_server<=start_server)
      return false;

   MqlRates rates[];
   int n=CopyRates(_Symbol,PERIOD_M5,start_server,end_server,rates);
   if(n<=0)
      return false;

   for(int i=0;i<n;i++)
     {
      if(rates[i].high<=0.0 || rates[i].low<=0.0)
         continue;
      if(rates[i].high>range_high) range_high=rates[i].high;
      if(rates[i].low<range_low)   range_low=rates[i].low;
      bar_count++;
     }

   return (bar_count>0 && range_high>-DBL_MAX && range_low<DBL_MAX && range_high>range_low);
  }

bool RangeHL(const datetime start_server,
             const datetime end_server,
             double &range_high,
             double &range_low)
  {
   int count=0;
   return RangeHLCount(start_server,end_server,range_high,range_low,count);
  }

bool PreviousUTCTradingDayHL(const datetime signal_server_time,double &pdh,double &pdl)
  {
   datetime today_utc=UTCMidnight(signal_server_time);
   int max_days=(InpPreviousTradingDaySearchDays>1 ? InpPreviousTradingDaySearchDays : 1);

   for(int back=1;back<=max_days;back++)
     {
      datetime start_utc=today_utc-back*86400;
      datetime end_utc=start_utc+86400-1;
      double hi=0.0,lo=0.0;
      int bars=0;
      if(!RangeHLCount(UTCToServer(start_utc),UTCToServer(end_utc),hi,lo,bars))
         continue;
      if(bars<InpMinTradingDayM5Bars)
         continue;
      pdh=hi; pdl=lo;
      return true;
     }
   return false;
  }

bool CurrentAsiaHL(const datetime signal_server_time,double &ah,double &al)
  {
   datetime today_utc=UTCMidnight(signal_server_time);
   datetime start_utc=today_utc;
   datetime end_utc=today_utc+7*3600-1;
   int bars=0;
   return RangeHLCount(UTCToServer(start_utc),UTCToServer(end_utc),ah,al,bars) && bars>=24;
  }

int PenetrationClass(const double penetration_atr)
  {
   if(!MathIsValidNumber(penetration_atr) || penetration_atr<0.0)
      return PEN_NONE;
   if(penetration_atr<=InpTouchPenetrationATR)
      return PEN_TOUCH;
   if(penetration_atr<=InpSweepPenetrationATR)
      return PEN_SWEEP;
   if(penetration_atr<=InpMaxLevelPenetrationATR)
      return PEN_DEEP;
   return PEN_FAIL;
  }

bool LevelConfluenceEx(const GoldContext &gold,
                       const double support_level,
                       const double resistance_level,
                       double &distance_atr,
                       double &penetration_atr,
                       int &pen_class)
  {
   distance_atr=DBL_MAX;
   penetration_atr=DBL_MAX;
   pen_class=PEN_NONE;
   if(gold.atr<=0.0)
      return false;

   double tol=InpLevelToleranceATR*gold.atr;

   if(gold.direction>0 && support_level>0.0)
     {
      distance_atr=AbsDistanceATR(gold.signal_close,support_level,gold.atr);
      bool touched=(gold.signal_low<=support_level+tol);
      bool reclaimed=(gold.signal_close>=support_level);
      penetration_atr=MathMax(0.0,(support_level-gold.signal_low)/gold.atr);
      pen_class=PenetrationClass(penetration_atr);
      return (touched && reclaimed && pen_class!=PEN_FAIL);
     }

   if(gold.direction<0 && resistance_level>0.0)
     {
      distance_atr=AbsDistanceATR(gold.signal_close,resistance_level,gold.atr);
      bool touched=(gold.signal_high>=resistance_level-tol);
      bool reclaimed=(gold.signal_close<=resistance_level);
      penetration_atr=MathMax(0.0,(gold.signal_high-resistance_level)/gold.atr);
      pen_class=PenetrationClass(penetration_atr);
      return (touched && reclaimed && pen_class!=PEN_FAIL);
     }

   return false;
  }

//----------------------- Confirmed Pivots ----------------------------
bool IsPivotLow(const int shift,const int span)
  {
   if(shift<=span || span<1)
      return false;

   double p=iLow(_Symbol,PERIOD_M5,shift);
   if(p<=0.0)
      return false;

   for(int j=1;j<=span;j++)
     {
      double newer=iLow(_Symbol,PERIOD_M5,shift-j);
      double older=iLow(_Symbol,PERIOD_M5,shift+j);
      if(newer<=0.0 || older<=0.0)
         return false;
      if(p>newer || p>older)
         return false;
     }
   return true;
  }

bool IsPivotHigh(const int shift,const int span)
  {
   if(shift<=span || span<1)
      return false;

   double p=iHigh(_Symbol,PERIOD_M5,shift);
   if(p<=0.0)
      return false;

   for(int j=1;j<=span;j++)
     {
      double newer=iHigh(_Symbol,PERIOD_M5,shift-j);
      double older=iHigh(_Symbol,PERIOD_M5,shift+j);
      if(newer<=0.0 || older<=0.0)
         return false;
      if(p<newer || p<older)
         return false;
     }
   return true;
  }

bool FindRecentPivot(const bool want_low,
                     const int start_shift,
                     const int lookback,
                     const int span,
                     double &price,
                     int &pivot_shift,
                     datetime &pivot_time)
  {
   price=0.0; pivot_shift=-1; pivot_time=0;
   int first=((start_shift+span)>(span+1) ? (start_shift+span) : (span+1));
   int last=start_shift+lookback-span;

   for(int s=first;s<=last;s++)
     {
      bool ok=(want_low ? IsPivotLow(s,span) : IsPivotHigh(s,span));
      if(!ok)
         continue;
      price=(want_low ? iLow(_Symbol,PERIOD_M5,s) : iHigh(_Symbol,PERIOD_M5,s));
      pivot_shift=s;
      pivot_time=iTime(_Symbol,PERIOD_M5,s);
      return (price>0.0 && pivot_time>0);
     }
   return false;
  }

bool FindTwoRecentPivots(const bool want_low,
                         const int start_shift,
                         const int lookback,
                         const int span,
                         double &new_price,
                         datetime &new_time,
                         double &old_price,
                         datetime &old_time)
  {
   new_price=0.0; old_price=0.0; new_time=0; old_time=0;
   int found=0;
   int first=((start_shift+span)>(span+1) ? (start_shift+span) : (span+1));
   int last=start_shift+lookback-span;

   for(int s=first;s<=last;s++)
     {
      bool ok=(want_low ? IsPivotLow(s,span) : IsPivotHigh(s,span));
      if(!ok)
         continue;

      double p=(want_low ? iLow(_Symbol,PERIOD_M5,s) : iHigh(_Symbol,PERIOD_M5,s));
      datetime t=iTime(_Symbol,PERIOD_M5,s);
      if(p<=0.0 || t<=0)
         continue;

      if(found==0)
        {
         new_price=p; new_time=t; found=1;
        }
      else
        {
         old_price=p; old_time=t; return true;
        }
     }
   return false;
  }

//----------------------- Fibonacci Context ---------------------------
bool FibConfluence(const GoldContext &gold,
                   double &fib_level,
                   double &fib_ratio,
                   double &distance_atr)
  {
   fib_level=0.0; fib_ratio=0.0; distance_atr=DBL_MAX;

   double low_p=0.0,high_p=0.0;
   int low_s=-1,high_s=-1;
   datetime low_t=0,high_t=0;
   if(!FindRecentPivot(true,1,InpSwingLookbackBars,InpPivotSpanBars,low_p,low_s,low_t))
      return false;
   if(!FindRecentPivot(false,1,InpSwingLookbackBars,InpPivotSpanBars,high_p,high_s,high_t))
      return false;

   double range=high_p-low_p;
   if(range<=0.0 || gold.atr<=0.0 || range/gold.atr<InpMinFibImpulseATR)
      return false;

   double ratios[5]={0.382,0.500,0.618,0.705,0.786};
   double best=DBL_MAX;
   double best_level=0.0;
   double best_ratio=0.0;

   if(gold.direction>0)
     {
      // Prior upswing: older low -> newer high. Shift is smaller when newer.
      if(!(high_s<low_s))
         return false;
      for(int i=0;i<5;i++)
        {
         double level=high_p-ratios[i]*range;
         double d=MathMin(MathAbs(gold.signal_low-level),MathAbs(gold.signal_close-level))/gold.atr;
         if(d<best){best=d;best_level=level;best_ratio=ratios[i];}
        }
     }
   else
     {
      // Prior downswing: older high -> newer low.
      if(!(low_s<high_s))
         return false;
      for(int i=0;i<5;i++)
        {
         double level=low_p+ratios[i]*range;
         double d=MathMin(MathAbs(gold.signal_high-level),MathAbs(gold.signal_close-level))/gold.atr;
         if(d<best){best=d;best_level=level;best_ratio=ratios[i];}
        }
     }

   fib_level=best_level;
   fib_ratio=best_ratio;
   distance_atr=best;
   return (best<=InpLevelToleranceATR);
  }

//------------------- Structure / Ordered M1 Sequence -----------------
bool M5StructureBreak(const GoldContext &gold)
  {
   double hi=-DBL_MAX,lo=DBL_MAX;
   for(int s=2;s<2+InpM5StructureLookbackBars;s++)
     {
      double h=iHigh(_Symbol,PERIOD_M5,s);
      double l=iLow(_Symbol,PERIOD_M5,s);
      if(h<=0.0 || l<=0.0) return false;
      if(h>hi) hi=h;
      if(l<lo) lo=l;
     }
   if(gold.direction>0) return (gold.signal_close>hi);
   return (gold.signal_close<lo);
  }

bool M1StructureBreakAt(const datetime bar_time,const int direction)
  {
   int s=iBarShift(_Symbol,PERIOD_M1,bar_time,true);
   if(s<0) return false;
   double cl=iClose(_Symbol,PERIOD_M1,s);
   if(cl<=0.0) return false;

   double hi=-DBL_MAX,lo=DBL_MAX;
   for(int k=1;k<=InpM1MSSLookbackBars;k++)
     {
      double h=iHigh(_Symbol,PERIOD_M1,s+k);
      double l=iLow(_Symbol,PERIOD_M1,s+k);
      if(h<=0.0 || l<=0.0) return false;
      if(h>hi) hi=h;
      if(l<lo) lo=l;
     }
   if(direction>0) return (cl>hi);
   return (cl<lo);
  }

bool DirectionalDisplacement(const MqlRates &r,const int direction,const double atr)
  {
   if(atr<=0.0 || r.high<=r.low)
      return false;
   double body=MathAbs(r.close-r.open);
   double range=r.high-r.low;
   double body_atr=body/atr;
   double body_ratio=(range>0.0 ? body/range : 0.0);
   bool directional=(direction>0 ? r.close>r.open : r.close<r.open);
   return (directional && body_atr>=InpM1DisplacementBodyATR && body_ratio>=InpM1DisplacementBodyRatio);
  }

bool ReconstructM1Sequence(const GoldContext &gold,FeatureContext &f)
  {
   datetime signal_end=gold.signal_time+PeriodSeconds(PERIOD_M5);
   MqlRates r[];
   int n=CopyRates(_Symbol,PERIOD_M1,gold.signal_time,signal_end-1,r);
   if(n<=0)
      return false;

   int raid=-1,reclaim=-1,mss=-1,disp=-1,fvg=-1;
   double level=(gold.direction>0 ? gold.prior_low : gold.prior_high);

   // 1) Liquidity raid and reclaim must occur in chronological order.
   for(int i=0;i<n;i++)
     {
      bool breached=(gold.direction>0 ? r[i].low<level : r[i].high>level);
      if(raid<0 && breached)
        {
         raid=i;
         f.seq_raid=true;
         f.raid_time=r[i].time;
        }

      if(raid>=0 && reclaim<0)
        {
         bool reclaimed=(gold.direction>0 ? r[i].close>level : r[i].close<level);
         if(reclaimed)
           {
            reclaim=i;
            f.seq_reclaim=true;
            f.reclaim_time=r[i].time;
           }
        }
     }

   if(reclaim<0)
      return true;

   // 2) First M1 structure break after the reclaim.
   for(int i=reclaim;i<n;i++)
     {
      if(M1StructureBreakAt(r[i].time,gold.direction))
        {
         mss=i;
         f.seq_mss=true;
         f.mss_time=r[i].time;
         break;
        }
     }

   if(mss<0)
      return true;

   // 3) Directional displacement at or after MSS.
   for(int i=mss;i<n;i++)
     {
      double atr=0.0;
      if(!M1ATRAtTime(r[i].time,atr))
         continue;
      if(DirectionalDisplacement(r[i],gold.direction,atr))
        {
         disp=i;
         f.seq_displacement=true;
         f.displacement_time=r[i].time;
         break;
        }
     }

   if(disp<0)
      return true;

   // 4) Fresh direction-aligned FVG formed after MSS/displacement.
   //    The middle candle must itself be a valid displacement candle.
   int fvg_start=disp+1;
   if(fvg_start<2) fvg_start=2;
   for(int i=fvg_start;i<n;i++)
     {
      int oldest=i-2;
      int middle=i-1;
      double atr_mid=0.0;
      if(!M1ATRAtTime(r[middle].time,atr_mid) || atr_mid<=0.0)
         continue;
      if(!DirectionalDisplacement(r[middle],gold.direction,atr_mid))
         continue;

      double gap=0.0,zlo=0.0,zhi=0.0;
      if(gold.direction>0)
        {
         gap=r[i].low-r[oldest].high;
         zlo=r[oldest].high;
         zhi=r[i].low;
        }
      else
        {
         gap=r[oldest].low-r[i].high;
         zlo=r[i].high;
         zhi=r[oldest].low;
        }

      if(gap<=0.0 || gap/atr_mid<InpM1MinFVG_ATR)
         continue;

      fvg=i;
      f.seq_fvg=true;
      f.fvg_time=r[i].time;
      f.fvg_low=zlo;
      f.fvg_high=zhi;
      f.fvg_gap_atr=gap/atr_mid;
      break;
     }

   if(fvg<0)
      return true;

   // 5) Optional retracement into the FVG after formation while it remains fresh.
   double width=f.fvg_high-f.fvg_low;
   if(width<=0.0)
      return true;

   double target=(gold.direction>0
                  ? f.fvg_high-InpM1FVGRetraceFraction*width
                  : f.fvg_low+InpM1FVGRetraceFraction*width);
   double max_depth=0.0;

   for(int i=fvg+1;i<n;i++)
     {
      if(gold.direction>0)
        {
         double depth=(f.fvg_high-r[i].low)/width;
         if(depth>max_depth) max_depth=depth;
         bool invalid=(r[i].low<=f.fvg_low);
         if(InpRequireFreshFVG && invalid)
            break;
         if(r[i].low<=target && (!InpRequireFreshFVG || r[i].close>f.fvg_low))
           {
            f.seq_retrace=true;
            f.retrace_time=r[i].time;
            break;
           }
        }
      else
        {
         double depth=(r[i].high-f.fvg_low)/width;
         if(depth>max_depth) max_depth=depth;
         bool invalid=(r[i].high>=f.fvg_high);
         if(InpRequireFreshFVG && invalid)
            break;
         if(r[i].high>=target && (!InpRequireFreshFVG || r[i].close<f.fvg_high))
           {
            f.seq_retrace=true;
            f.retrace_time=r[i].time;
            break;
           }
        }
     }

   f.fvg_retrace_depth=MathMax(0.0,MathMin(max_depth,2.0));
   return true;
  }

//----------------------- Trendline Context ---------------------------
bool TrendlineInteractionValidated(const GoldContext &gold,
                                   double &line_level,
                                   double &distance_atr,
                                   double &slope_atr_per_bar,
                                   int &age_bars,
                                   int &pivot_separation_bars)
  {
   line_level=0.0;
   distance_atr=DBL_MAX;
   slope_atr_per_bar=0.0;
   age_bars=0;
   pivot_separation_bars=0;
   bool want_low=(gold.direction>0);

   double np=0.0,op=0.0;
   datetime nt=0,ot=0;
   if(!FindTwoRecentPivots(want_low,1,InpSwingLookbackBars,InpPivotSpanBars,np,nt,op,ot))
      return false;
   if(nt<=ot || gold.signal_time<=nt || gold.atr<=0.0)
      return false;

   int ns=iBarShift(_Symbol,PERIOD_M5,nt,true);
   int os=iBarShift(_Symbol,PERIOD_M5,ot,true);
   if(ns<0 || os<0 || os<=ns)
      return false;

   pivot_separation_bars=os-ns;
   age_bars=ns-1; // signal bar is shift 1
   if(pivot_separation_bars<InpTrendlineMinPivotSeparationBars || age_bars<InpTrendlineMinAgeBars)
      return false;

   if(InpTrendlineRequireDirectionalSlope)
     {
      if(gold.direction>0 && np<=op) return false;
      if(gold.direction<0 && np>=op) return false;
     }

   double seconds=(double)(nt-ot);
   if(seconds<=0.0)
      return false;
   double slope=(np-op)/seconds;
   slope_atr_per_bar=(slope*PeriodSeconds(PERIOD_M5))/gold.atr;

   // A line that was materially broken before the current signal is invalid.
   for(int s=ns-1;s>=2;s--)
     {
      datetime bt=iTime(_Symbol,PERIOD_M5,s);
      double cl=iClose(_Symbol,PERIOD_M5,s);
      if(bt<=0 || cl<=0.0) continue;
      double line=np+slope*(double)(bt-nt);
      if(gold.direction>0 && cl<line-InpTrendlineMaxPenetrationATR*gold.atr)
         return false;
      if(gold.direction<0 && cl>line+InpTrendlineMaxPenetrationATR*gold.atr)
         return false;
     }

   datetime projection_time=gold.signal_time+PeriodSeconds(PERIOD_M5)-1;
   double projected=np+slope*(double)(projection_time-nt);
   if(projected<=0.0 || !MathIsValidNumber(projected))
      return false;

   line_level=projected;
   distance_atr=AbsDistanceATR(gold.signal_close,projected,gold.atr);
   double tol=InpLevelToleranceATR*gold.atr;

   if(gold.direction>0)
     {
      double pen=MathMax(0.0,(projected-gold.signal_low)/gold.atr);
      return (gold.signal_low<=projected+tol && gold.signal_close>=projected && pen<=InpTrendlineMaxPenetrationATR);
     }
   double pen=MathMax(0.0,(gold.signal_high-projected)/gold.atr);
   return (gold.signal_high>=projected-tol && gold.signal_close<=projected && pen<=InpTrendlineMaxPenetrationATR);
  }

//------------------- V9.5 Volume Intelligence -----------------------
double VolumeForBar(const MqlRates &bar,bool &used_real)
  {
   used_real=false;
   if(InpPreferRealVolume && bar.real_volume>0)
     {
      used_real=true;
      return (double)bar.real_volume;
     }
   return (double)bar.tick_volume;
  }

bool CopyClosedM1Window(const datetime start_server,const datetime end_server,MqlRates &rates[])
  {
   ArrayResize(rates,0);
   if(start_server<=0 || end_server<start_server)
      return false;
   int copied=CopyRates(_Symbol,PERIOD_M1,start_server,end_server,rates);
   if(copied<=0)
      return false;
   ArraySetAsSeries(rates,false);
   return true;
  }

bool VWAPFromRates(MqlRates &rates[],double &vwap,double &sigma,double &real_fraction)
  {
   vwap=0.0;
   sigma=0.0;
   real_fraction=0.0;
   int n=ArraySize(rates);
   if(n<=0) return false;

   double total_v=0.0,total_pv=0.0,total_p2v=0.0;
   int real_bars=0,valid_bars=0;
   for(int i=0;i<n;i++)
     {
      if(rates[i].high<=0.0 || rates[i].low<=0.0 || rates[i].close<=0.0)
         continue;
      bool used_real=false;
      double vol=VolumeForBar(rates[i],used_real);
      if(vol<=0.0) continue;
      double price=(rates[i].high+rates[i].low+rates[i].close)/3.0;
      total_v+=vol;
      total_pv+=price*vol;
      total_p2v+=price*price*vol;
      valid_bars++;
      if(used_real) real_bars++;
     }
   if(total_v<=0.0 || valid_bars<=0)
      return false;

   vwap=total_pv/total_v;
   double variance=MathMax(0.0,total_p2v/total_v-vwap*vwap);
   sigma=MathSqrt(variance);
   real_fraction=(double)real_bars/(double)valid_bars;
   return (vwap>0.0 && MathIsValidNumber(vwap) && MathIsValidNumber(sigma));
  }

bool VWAPWindow(const datetime start_server,const datetime end_server,
                double &vwap,double &sigma,int &bars,double &real_fraction)
  {
   MqlRates rates[];
   if(!CopyClosedM1Window(start_server,end_server,rates))
      return false;
   bars=ArraySize(rates);
   return VWAPFromRates(rates,vwap,sigma,real_fraction);
  }

bool VolumeProfileFromRates(MqlRates &rates[],double &poc,double &val,double &vah)
  {
   poc=0.0; val=0.0; vah=0.0;
   int n=ArraySize(rates);
   int bins=InpVolumeProfileBins;
   if(n<=0 || bins<8)
      return false;

   double profile_low=DBL_MAX,profile_high=-DBL_MAX;
   for(int i=0;i<n;i++)
     {
      if(rates[i].low>0.0 && rates[i].low<profile_low) profile_low=rates[i].low;
      if(rates[i].high>0.0 && rates[i].high>profile_high) profile_high=rates[i].high;
     }
   if(profile_low>=DBL_MAX || profile_high<=profile_low)
      return false;

   double width=(profile_high-profile_low)/(double)bins;
   if(width<=0.0) return false;

   double binvol[];
   ArrayResize(binvol,bins);
   ArrayInitialize(binvol,0.0);
   double total=0.0;

   for(int i=0;i<n;i++)
     {
      if(rates[i].high<=0.0 || rates[i].low<=0.0) continue;
      bool used_real=false;
      double vol=VolumeForBar(rates[i],used_real);
      if(vol<=0.0) continue;

      int first=(int)MathFloor((rates[i].low-profile_low)/width);
      int last=(int)MathFloor((rates[i].high-profile_low)/width);
      first=(int)MathMax(0,MathMin(bins-1,first));
      last=(int)MathMax(0,MathMin(bins-1,last));
      if(last<first) {int t=first;first=last;last=t;}
      int count=last-first+1;
      double share=vol/(double)count;
      for(int b=first;b<=last;b++)
         binvol[b]+=share;
      total+=vol;
     }
   if(total<=0.0)
      return false;

   int poc_idx=0;
   for(int b=1;b<bins;b++)
      if(binvol[b]>binvol[poc_idx]) poc_idx=b;

   int lo=poc_idx,hi=poc_idx;
   double accumulated=binvol[poc_idx];
   double target=total*InpValueAreaFraction;
   while(accumulated<target && (lo>0 || hi<bins-1))
     {
      double left=(lo>0 ? binvol[lo-1] : -1.0);
      double right=(hi<bins-1 ? binvol[hi+1] : -1.0);
      if(right>left)
        {
         hi++;
         accumulated+=binvol[hi];
        }
      else if(lo>0)
        {
         lo--;
         accumulated+=binvol[lo];
        }
      else
        {
         hi++;
         accumulated+=binvol[hi];
        }
     }

   poc=profile_low+((double)poc_idx+0.5)*width;
   val=profile_low+((double)lo+0.5)*width;
   vah=profile_low+((double)hi+0.5)*width;
   return (poc>0.0 && val>0.0 && vah>=val);
  }

bool BuildVolumeContext(const GoldContext &gold,FeatureContext &f)
  {
   ZeroMemory(f.volume);
   if(!InpEnableVolumeIntelligence || gold.atr<=0.0)
      return false;

   datetime signal_end=gold.signal_time+PeriodSeconds(PERIOD_M5)-1;
   datetime day_start_utc=UTCMidnight(gold.signal_time);
   datetime day_start_server=UTCToServer(day_start_utc);
   datetime london_start_server=UTCToServer(day_start_utc+InpSessionStartUTC*3600);
   if(signal_end<london_start_server)
      return false;

   MqlRates daily[];
   if(!CopyClosedM1Window(day_start_server,signal_end,daily))
      return false;
   int daily_bars=ArraySize(daily);
   if(daily_bars<InpMinVolumeM1Bars)
      return false;

   double real_fraction=0.0;
   if(!VWAPFromRates(daily,f.volume.daily_vwap,f.volume.daily_sigma,real_fraction))
      return false;
   f.volume.real_volume_fraction=real_fraction;
   f.volume.source_quality=(real_fraction>=0.95 ? 2 : (real_fraction>0.0 ? 1 : 0));
   f.volume.bars=daily_bars;

   int london_bars=0;
   double london_real=0.0;
   if(!VWAPWindow(london_start_server,signal_end,f.volume.london_vwap,f.volume.london_sigma,london_bars,london_real))
      return false;

   datetime anchor=(f.raid_time>0 ? f.raid_time : gold.signal_time);
   if(anchor<day_start_server) anchor=day_start_server;
   int avwap_bars=0;
   double avwap_sigma=0.0,avwap_real=0.0;
   if(!VWAPWindow(anchor,signal_end,f.volume.anchored_vwap,avwap_sigma,avwap_bars,avwap_real))
      f.volume.anchored_vwap=f.volume.london_vwap;
   f.volume.anchored_vwap_time=anchor;

   if(!VolumeProfileFromRates(daily,f.volume.poc,f.volume.val,f.volume.vah))
      return false;

   f.volume.vwap_upper1=f.volume.london_vwap+InpVWAPBandSigma1*f.volume.london_sigma;
   f.volume.vwap_lower1=f.volume.london_vwap-InpVWAPBandSigma1*f.volume.london_sigma;
   f.volume.vwap_upper2=f.volume.london_vwap+InpVWAPBandSigma2*f.volume.london_sigma;
   f.volume.vwap_lower2=f.volume.london_vwap-InpVWAPBandSigma2*f.volume.london_sigma;

   f.volume.daily_vwap_distance_atr=(gold.signal_close-f.volume.daily_vwap)/gold.atr;
   f.volume.london_vwap_distance_atr=(gold.signal_close-f.volume.london_vwap)/gold.atr;
   f.volume.anchored_vwap_distance_atr=(gold.signal_close-f.volume.anchored_vwap)/gold.atr;
   f.volume.poc_distance_atr=(gold.signal_close-f.volume.poc)/gold.atr;

   f.volume.vwap_slope_atr_per_15m=0.0;
   datetime prior_end=signal_end-InpVWAPSlopeLookbackMinutes*60;
   if(prior_end>london_start_server)
     {
      double prior_vwap=0.0,prior_sigma=0.0,prior_real=0.0;
      int prior_bars=0;
      if(VWAPWindow(london_start_server,prior_end,prior_vwap,prior_sigma,prior_bars,prior_real) && prior_vwap>0.0)
         f.volume.vwap_slope_atr_per_15m=(f.volume.london_vwap-prior_vwap)/gold.atr;
     }

   if(gold.signal_close<f.volume.val) f.volume.value_area_state=-1;
   else if(gold.signal_close>f.volume.vah) f.volume.value_area_state=1;
   else f.volume.value_area_state=0;

   double tol=InpVolumeLevelToleranceATR*gold.atr;
   if(gold.direction>0)
     {
      f.volume.vwap_reclaim=(gold.signal_low<=f.volume.london_vwap+tol && gold.signal_close>=f.volume.london_vwap);
      f.volume.value_area_reclaim=(gold.signal_low<=f.volume.val+tol && gold.signal_close>=f.volume.val);
      f.volume.mean_reversion_path=(gold.signal_close<f.volume.london_vwap && f.volume.poc>gold.signal_close);
     }
   else
     {
      f.volume.vwap_reclaim=(gold.signal_high>=f.volume.london_vwap-tol && gold.signal_close<=f.volume.london_vwap);
      f.volume.value_area_reclaim=(gold.signal_high>=f.volume.vah-tol && gold.signal_close<=f.volume.vah);
      f.volume.mean_reversion_path=(gold.signal_close>f.volume.london_vwap && f.volume.poc<gold.signal_close);
     }

   bool avwap_support=(gold.direction>0 ? gold.signal_close>=f.volume.anchored_vwap : gold.signal_close<=f.volume.anchored_vwap);
   bool slope_ok=(gold.direction>0 ? f.volume.vwap_slope_atr_per_15m>=-0.10 : f.volume.vwap_slope_atr_per_15m<=0.10);

   int score=0;
   if(f.volume.vwap_reclaim) score+=4;
   if(f.volume.value_area_reclaim) score+=4;
   if(f.volume.mean_reversion_path) score+=3;
   if(avwap_support) score+=2;
   if(slope_ok) score+=2;
   f.volume.score=ClampInt(score,0,15);
   f.volume.volume_location_ok=(f.volume.vwap_reclaim || f.volume.value_area_reclaim || f.volume.mean_reversion_path);
   f.volume.valid=true;
   return true;
  }

// Hybrid structural targets. They are only execution geometry; they never alter
// the frozen entry signal or any research gate unless explicitly selected.
void AddDirectionalTargetCandidate(const int direction,const double entry,const double risk,
                                   const double level,double &r_values[],double &levels[],int &count)
  {
   if(level<=0.0 || risk<=0.0 || count>=ArraySize(levels)) return;
   double r=((level-entry)*direction)/risk;
   if(r<=0.0 || !MathIsValidNumber(r)) return;
   r_values[count]=r;
   levels[count]=level;
   count++;
  }

void SortTargetCandidates(double &r_values[],double &levels[],const int count)
  {
   for(int i=0;i<count-1;i++)
      for(int j=i+1;j<count;j++)
         if(r_values[j]<r_values[i])
           {
            double tr=r_values[i]; r_values[i]=r_values[j]; r_values[j]=tr;
            double tl=levels[i]; levels[i]=levels[j]; levels[j]=tl;
           }
  }

double PickStructuralTarget(const int direction,const double entry,const double risk,
                            double &r_values[],double &levels[],const int count,
                            const double min_r,const double fallback_r,const double previous_distance)
  {
   for(int i=0;i<count;i++)
     {
      double distance=(levels[i]-entry)*direction;
      if(r_values[i]>=min_r && distance>previous_distance+_Point)
        {
         if(InpTargetMode==TARGET_HYBRID && r_values[i]>fallback_r*1.25)
            break;
         return levels[i];
        }
     }
   return entry+direction*fallback_r*risk;
  }

void ResolveProductionTargets(const GoldContext &gold,const FeatureContext &f,
                              const double entry,const double risk,
                              double &tp1,double &tp2,double &tp3)
  {
   tp1=entry+gold.direction*InpProductionTP1_R*risk;
   tp2=entry+gold.direction*InpProductionTP2_R*risk;
   tp3=entry+gold.direction*InpProductionTP3_R*risk;
   if(InpTargetMode==TARGET_FIXED_R || risk<=0.0)
      return;

   double levels[];
   double r_values[];
   ArrayResize(levels,12);
   ArrayResize(r_values,12);
   ArrayInitialize(levels,0.0);
   ArrayInitialize(r_values,0.0);
   int count=0;

   if(f.volume.valid)
     {
      AddDirectionalTargetCandidate(gold.direction,entry,risk,f.volume.london_vwap,r_values,levels,count);
      AddDirectionalTargetCandidate(gold.direction,entry,risk,f.volume.daily_vwap,r_values,levels,count);
      AddDirectionalTargetCandidate(gold.direction,entry,risk,f.volume.poc,r_values,levels,count);
      AddDirectionalTargetCandidate(gold.direction,entry,risk,(gold.direction>0 ? f.volume.vah : f.volume.val),r_values,levels,count);
     }
   AddDirectionalTargetCandidate(gold.direction,entry,risk,(gold.direction>0 ? f.prev_day_high : f.prev_day_low),r_values,levels,count);
   AddDirectionalTargetCandidate(gold.direction,entry,risk,(gold.direction>0 ? f.asia_high : f.asia_low),r_values,levels,count);
   AddDirectionalTargetCandidate(gold.direction,entry,risk,f.swing_level,r_values,levels,count);
   AddDirectionalTargetCandidate(gold.direction,entry,risk,f.trendline_level,r_values,levels,count);
   SortTargetCandidates(r_values,levels,count);

   tp1=PickStructuralTarget(gold.direction,entry,risk,r_values,levels,count,InpStructuralTP1MinR,InpProductionTP1_R,0.0);
   double d1=(tp1-entry)*gold.direction;
   tp2=PickStructuralTarget(gold.direction,entry,risk,r_values,levels,count,InpStructuralTP2MinR,InpProductionTP2_R,d1);
   double d2=(tp2-entry)*gold.direction;
   tp3=PickStructuralTarget(gold.direction,entry,risk,r_values,levels,count,InpStructuralTP3MinR,InpProductionTP3_R,d2);

   // Final monotonic safety fallback.
   if((tp2-entry)*gold.direction<=d1)
      tp2=entry+gold.direction*InpProductionTP2_R*risk;
   if((tp3-entry)*gold.direction<=(tp2-entry)*gold.direction)
      tp3=entry+gold.direction*InpProductionTP3_R*risk;
  }

//------------------------ Build Features -----------------------------
bool BuildFeatureContext(const GoldContext &gold,FeatureContext &f)
  {
   ZeroMemory(f);
   f.valid=true;
   f.prev_day_distance_atr=DBL_MAX;
   f.prev_day_penetration_atr=DBL_MAX;
   f.asia_distance_atr=DBL_MAX;
   f.asia_penetration_atr=DBL_MAX;
   f.swing_distance_atr=DBL_MAX;
   f.swing_penetration_atr=DBL_MAX;
   f.fib_distance_atr=DBL_MAX;
   f.trendline_distance_atr=DBL_MAX;

   if(PreviousUTCTradingDayHL(gold.signal_time,f.prev_day_high,f.prev_day_low))
      f.prev_day_ok=LevelConfluenceEx(gold,f.prev_day_low,f.prev_day_high,
                                      f.prev_day_distance_atr,f.prev_day_penetration_atr,f.prev_day_pen_class);

   if(CurrentAsiaHL(gold.signal_time,f.asia_high,f.asia_low))
      f.asia_ok=LevelConfluenceEx(gold,f.asia_low,f.asia_high,
                                  f.asia_distance_atr,f.asia_penetration_atr,f.asia_pen_class);

   double sp=0.0; int ss=-1; datetime st=0;
   bool want_low=(gold.direction>0);
   if(FindRecentPivot(want_low,1,InpSwingLookbackBars,InpPivotSpanBars,sp,ss,st))
     {
      f.swing_level=sp;
      f.swing_shift=ss;
      double support=(gold.direction>0 ? sp : 0.0);
      double resist=(gold.direction<0 ? sp : 0.0);
      f.swing_ok=LevelConfluenceEx(gold,support,resist,
                                   f.swing_distance_atr,f.swing_penetration_atr,f.swing_pen_class);
     }

   f.fib_ok=FibConfluence(gold,f.fib_level,f.fib_ratio,f.fib_distance_atr);
   f.m5_structure_break=M5StructureBreak(gold);
   ReconstructM1Sequence(gold,f);
   f.trendline_ok=TrendlineInteractionValidated(gold,f.trendline_level,f.trendline_distance_atr,
                                                f.trendline_slope_atr_per_bar,f.trendline_age_bars,
                                                f.trendline_pivot_separation_bars);
   BuildVolumeContext(gold,f);

   int locations=0;
   int count=0;
   int mask=0;
   if(f.prev_day_ok)          {locations++; count++; mask|=1;}
   if(f.asia_ok)              {locations++; count++; mask|=2;}
   if(f.swing_ok)             {locations++; count++; mask|=4;}
   if(f.fib_ok)               {locations++; count++; mask|=8;}
   if(f.m5_structure_break)   {count++; mask|=16;}
   if(f.seq_mss)              {count++; mask|=32;}
   if(f.seq_displacement)     {count++; mask|=64;}
   if(f.seq_fvg)              {count++; mask|=128;}
   if(f.seq_retrace)          {count++; mask|=256;}
   if(f.trendline_ok)         {locations++; count++; mask|=512;}
   if(f.volume.vwap_reclaim)      {count++; mask|=1024;}
   if(f.volume.value_area_reclaim){count++; mask|=2048;}
   if(f.volume.mean_reversion_path){count++; mask|=4096;}

   f.location_count=locations;
   f.feature_count=count;
   f.feature_mask=mask;
   return true;
  }

//--------------------- V9.5 Super Scalper --------------------------
string ScalperStateName(const ENUM_SCALPER_STATE state)
  {
   if(state==SCALPER_TRIGGERED) return "TRIGGERED";
   if(state==SCALPER_ARMED)     return "ARMED";
   if(state==SCALPER_WATCH)     return "WATCH";
   return "BLOCKED";
  }

int ClampInt(const int value,const int lo,const int hi)
  {
   return (value<lo ? lo : (value>hi ? hi : value));
  }

double ClampDouble(const double value,const double lo,const double hi)
  {
   return (value<lo ? lo : (value>hi ? hi : value));
  }

bool RiskGovernorApplies()
  {
   return (!g_is_tester || InpApplyRiskGovernorInTester);
  }

void UpdateRiskGovernor()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity<=0.0) return;

   int day=DateKey(ServerToUTC(TimeCurrent()));
   if(g_risk_day_key!=day)
     {
      g_risk_day_key=day;
      g_day_start_equity=equity;
      g_trades_today=CountTodayManagedEntries();
      // Daily-loss halt clears with a new UTC trading day. Overall drawdown
      // remains governed by the current peak and can immediately re-halt.
      g_risk_halted=false;
     }

   if(g_day_start_equity<=0.0) g_day_start_equity=equity;
   if(g_peak_equity<=0.0 || equity>g_peak_equity) g_peak_equity=equity;

   if(!RiskGovernorApplies()) return;

   double daily_loss=(g_day_start_equity>0.0 ? 100.0*(g_day_start_equity-equity)/g_day_start_equity : 0.0);
   double drawdown=(g_peak_equity>0.0 ? 100.0*(g_peak_equity-equity)/g_peak_equity : 0.0);
   if(daily_loss>=InpDailyLossLimitPct || drawdown>=InpEquityDrawdownLimitPct)
      g_risk_halted=true;

   SaveRiskGovernorState();
  }

bool DirectionLossPauseActive(const int direction)
  {
   if(!InpUseLossStreakQuarantine) return false;
   datetime until=(direction>0 ? g_long_pause_until : g_short_pause_until);
   return (until>TimeCurrent());
  }

bool ClosedProductionResultR(const ProductionState &p,double &result_r)
  {
   result_r=0.0;
   if(p.open_time<=0 || p.initial_volume<=0.0 || p.risk_distance<=0.0) return false;
   if(!HistorySelect(p.open_time-60,TimeCurrent()+60)) return false;

   double pnl=0.0;
   bool saw_exit=false;
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      if((ulong)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      if(p.position_id>0 && (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID)!=p.position_id) continue;
      datetime dt=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      if(dt<p.open_time-5) continue;
      ENUM_DEAL_ENTRY de=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(de==DEAL_ENTRY_OUT || de==DEAL_ENTRY_OUT_BY) saw_exit=true;
      pnl+=HistoryDealGetDouble(deal,DEAL_PROFIT);
      pnl+=HistoryDealGetDouble(deal,DEAL_COMMISSION);
      pnl+=HistoryDealGetDouble(deal,DEAL_SWAP);
      pnl+=HistoryDealGetDouble(deal,DEAL_FEE);
     }
   if(!saw_exit) return false;

   double stop_price=p.entry-p.direction*p.risk_distance;
   double one_r=0.0;
   ENUM_ORDER_TYPE type=(p.direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,p.initial_volume,p.entry,stop_price,one_r)) return false;
   one_r=MathAbs(one_r);
   if(one_r<=0.0) return false;
   result_r=pnl/one_r;
   return true;
  }

void UpdateLossStreakQuarantine(const ProductionState &p)
  {
   if(!InpUseLossStreakQuarantine) return;
   double r=0.0;
   if(!ClosedProductionResultR(p,r)) return;

   int streak=(p.direction>0 ? g_long_loss_streak : g_short_loss_streak);
   if(r<=InpQualifyingLossR) streak++;
   else streak=0;

   datetime pause_until=0;
   if(streak>=InpQualifyingLossStreak)
     {
      pause_until=TimeCurrent()+InpLossStreakPauseMinutes*60;
      streak=0;
      WriteExecutionEvidence("LOSS_STREAK_PAUSE",g_last_scalper,p.signal_id,p.direction,p.ticket,0.0,p.entry,0.0,
                             p.tp1,p.tp2,p.tp3,"DIRECTION_QUARANTINE");
     }

   if(p.direction>0)
     {
      g_long_loss_streak=streak;
      if(pause_until>0) g_long_pause_until=pause_until;
     }
   else
     {
      g_short_loss_streak=streak;
      if(pause_until>0) g_short_pause_until=pause_until;
     }
   SaveRiskGovernorState();
  }

ScalperDecision BuildScalperDecision(const GoldContext &gold,const FeatureContext &f,const MqlTick &tick,const bool use_volume)
  {
   ScalperDecision d;
   ZeroMemory(d);
   d.state=SCALPER_BLOCKED;
   d.reason="UNSET";

   // Context is based only on information already required by the frozen
   // control. The score measures readiness, not probability of winning.
   int context=8+6+4;
   bool ema_side=(gold.direction>0 ? gold.signal_close>=gold.ema100_m5 : gold.signal_close<=gold.ema100_m5);
   bool ema_slope=(gold.direction>0 ? gold.ema100_slope_atr>0.0 : gold.ema100_slope_atr<0.0);
   if(ema_side) context+=4;
   if(ema_slope) context+=3;
   if(gold.ema_stack_aligned) context+=3;
   context+= (int)MathRound(6.0*ClampDouble((gold.extension-1.5)/1.5,0.0,1.0));
   context+= (int)MathRound(4.0*ClampDouble((30.0-gold.adx)/12.0,0.0,1.0));
   if(gold.vol_ratio>=0.80 && gold.vol_ratio<1.80) context+=2;
   d.context_score=ClampInt(context,0,35);

   int micro=0;
   if(f.seq_mss)          micro+=9;
   if(f.seq_displacement) micro+=8;
   if(f.seq_fvg)          micro+=6;
   if(f.m5_structure_break) micro+=4;
   if(f.seq_retrace)      micro+=3;
   d.micro_score=ClampInt(micro,0,30);

   double age_minutes=(double)(TimeCurrent()-gold.signal_time)/60.0;
   if(age_minutes<0.0) d.timing_score=0;
   else if(age_minutes<=10.0) d.timing_score=15;
   else if(age_minutes<=20.0) d.timing_score=13;
   else if(age_minutes<=30.0) d.timing_score=10;
   else if(age_minutes<=45.0) d.timing_score=6;
   else if(age_minutes<=60.0) d.timing_score=3;
   else d.timing_score=0;

   double risk=InpProductionSL_ATR*gold.atr;
   double spread_price=tick.ask-tick.bid;
   d.spread_cost_r=(risk>0.0 ? spread_price/risk : 999.0);
   d.slippage_cost_r=(risk>0.0 ? InpExpectedSlippagePointsRT*_Point/risk : 999.0);
   double commission_cost_r=(risk>0.0 ? InpVirtualCommissionPointsRT*_Point/risk : 0.0);
   d.net_edge_r=InpAssumedGrossEdgeR-d.spread_cost_r-d.slippage_cost_r-commission_cost_r;

   double total_cost_r=d.spread_cost_r+d.slippage_cost_r+commission_cost_r;
   int cost_points=(int)MathRound(12.0*ClampDouble(1.0-total_cost_r/0.20,0.0,1.0));
   int freshness=4; // current M5 first tick; stale tick veto handled below
   int latency=(InpExpectedSlippagePointsRT<=InpMaxExpectedSlippagePoints ? 4 : 0);
   d.execution_score=ClampInt(cost_points+freshness+latency,0,20);
   d.volume_score=(use_volume && f.volume.valid ? f.volume.score : 0);
   d.readiness=ClampInt(d.context_score+d.micro_score+d.timing_score+d.execution_score+d.volume_score,0,100);

   double spread_points=(tick.ask-tick.bid)/_Point;
   double tick_age=MathMax(0.0,(double)(TimeCurrent()-tick.time));
   bool hard_block=false;
   string why="";
   if(tick_age>InpMaxTickAgeSeconds) {hard_block=true;why="STALE_TICK";}
   else if(spread_points>InpMaxProductionSpreadPoints) {hard_block=true;why="SPREAD";}
   else if(InpExpectedSlippagePointsRT>InpMaxExpectedSlippagePoints) {hard_block=true;why="SLIPPAGE";}
   else if(d.net_edge_r<InpMinNetEdgeR) {hard_block=true;why="NET_EDGE";}
   else if(age_minutes>60.0) {hard_block=true;why="ANCHOR_EXPIRED";}
   else if(g_risk_halted && RiskGovernorApplies()) {hard_block=true;why="RISK_GOVERNOR";}
   else if(g_trades_today>=InpMaxTradesPerDay) {hard_block=true;why="TRADE_LIMIT";}
   else if(g_last_production_exit>0 && (TimeCurrent()-g_last_production_exit)<InpMinimumPostExitSeconds) {hard_block=true;why="COOLDOWN";}
   else if(DirectionLossPauseActive(gold.direction)) {hard_block=true;why="LOSS_STREAK_PAUSE";}
   else if(use_volume && !f.volume.valid) {hard_block=true;why="VOLUME_DATA";}
   else if(use_volume && !f.volume.volume_location_ok) {hard_block=true;why="VOLUME_LOCATION";}
   else if(use_volume && f.volume.score<InpMinVolumeScoreForExecution) {hard_block=true;why="VOLUME_SCORE";}

   if(hard_block)
     {
      d.state=SCALPER_BLOCKED;
      d.reason=why;
      return d;
     }

   bool final_trigger=(f.location_count>=1 && f.seq_mss && f.seq_displacement && f.seq_fvg);
   if(use_volume)
      final_trigger=(final_trigger && f.volume.valid && f.volume.volume_location_ok && f.volume.score>=InpMinVolumeScoreForExecution);
   if(d.readiness>=InpTriggeredReadiness && final_trigger)
     {
      d.state=SCALPER_TRIGGERED;
      d.reason="FULL_TRIGGER";
     }
   else if(d.readiness>=InpArmedReadiness)
     {
      d.state=SCALPER_ARMED;
      d.reason="AWAIT_MICRO_TRIGGER";
     }
   else
     {
      d.state=SCALPER_WATCH;
      d.reason="NOT_READY";
     }
   return d;
  }

//---------------- Production-test execution ------------------------
bool IsLiveAccount()
  {
   if(g_is_tester) return false;
   return ((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL);
  }

string ExecutionModeName(const ENUM_EXECUTION_MODE mode)
  {
   if(mode==EXEC_VIRTUAL_ONLY)    return "VIRTUAL";
   if(mode==EXEC_STRATEGY_TESTER) return "TESTER";
   if(mode==EXEC_DEMO_ARMED)      return "DEMO_ARMED";
   if(mode==EXEC_AUTO_SAFE)       return "AUTO_SAFE";
   return "UNKNOWN";
  }

ENUM_EXECUTION_MODE ResolveEffectiveExecutionMode()
  {
   // Strategy Tester is isolated from the account. AUTO_SAFE becomes TESTER there.
   if(g_is_tester)
     {
      if(InpExecutionMode==EXEC_VIRTUAL_ONLY)
         return EXEC_VIRTUAL_ONLY;
      return EXEC_STRATEGY_TESTER;
     }

   // REAL accounts are always monitor/virtual only in this release.
   if(IsLiveAccount())
      return EXEC_VIRTUAL_ONLY;

   ENUM_ACCOUNT_TRADE_MODE account_mode=(ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(account_mode==ACCOUNT_TRADE_MODE_DEMO && InpArmDemoExecution &&
      (InpExecutionMode==EXEC_DEMO_ARMED || InpExecutionMode==EXEC_AUTO_SAFE))
      return EXEC_DEMO_ARMED;

   // Normal chart attachment, AUTO_SAFE, TESTER requested outside tester, or unarmed DEMO
   // all degrade safely to monitor/virtual mode instead of failing OnInit.
   return EXEC_VIRTUAL_ONLY;
  }

bool OrdersEnabledByMode()
  {
   if(g_effective_execution_mode==EXEC_VIRTUAL_ONLY) return false;
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)) return false;
   if(!g_is_tester && (!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))) return false;
   if(g_is_tester) return (g_effective_execution_mode==EXEC_STRATEGY_TESTER);
   if(IsLiveAccount()) return false;
   if(g_effective_execution_mode!=EXEC_DEMO_ARMED || !InpArmDemoExecution) return false;
   return ((ENUM_ACCOUNT_TRADE_MODE)AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO);
  }

ENUM_ORDER_TYPE_FILLING GetFillingMode()
  {
   long mode=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_FILLING_MODE,mode))
      return ORDER_FILLING_FOK;
   if((mode & SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK) return ORDER_FILLING_FOK;
   if((mode & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

double NormalizePriceToTick(const double price)
  {
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0) tick_size=_Point;
   return NormalizeDouble(MathRound(price/tick_size)*tick_size,_Digits);
  }

int VolumeDigits(const double step)
  {
   int digits=0;
   double x=step;
   while(digits<8 && MathAbs(x-MathRound(x))>1e-8)
     {
      x*=10.0;
      digits++;
     }
   return digits;
  }

double NormalizeVolumeDown(const double volume)
  {
   double minv=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maxv=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || minv<=0.0 || maxv<=0.0 || volume<minv) return 0.0;
   double steps=MathFloor((volume-minv+1e-12)/step);
   double v=minv+MathMax(0.0,steps)*step;
   if(v<minv) return 0.0;
   if(v>maxv)
     {
      double max_steps=MathFloor((maxv-minv+1e-12)/step);
      v=minv+MathMax(0.0,max_steps)*step;
     }
   return NormalizeDouble(v,VolumeDigits(step));
  }

bool HasAnySymbolPosition()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol) return true;
     }
   return false;
  }

bool HasAnySymbolOrder()
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==_Symbol) return true;
     }
   return false;
  }

bool SymbolTradeModeAllows(const int direction)
  {
   long raw=0;
   if(!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_MODE,raw))
      return false;
   ENUM_SYMBOL_TRADE_MODE mode=(ENUM_SYMBOL_TRADE_MODE)raw;
   if(mode==SYMBOL_TRADE_MODE_DISABLED || mode==SYMBOL_TRADE_MODE_CLOSEONLY)
      return false;
   if(direction>0 && mode==SYMBOL_TRADE_MODE_SHORTONLY)
      return false;
   if(direction<0 && mode==SYMBOL_TRADE_MODE_LONGONLY)
      return false;
   return true;
  }

ulong FindManagedPositionTicket()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      return ticket;
     }
   return 0;
  }

bool SelectManagedPosition(ulong &ticket)
  {
   ticket=FindManagedPositionTicket();
   if(ticket==0) return false;
   return PositionSelectByTicket(ticket);
  }

string GVKey(const string suffix)
  {
   return StringFormat("AUREON10.%I64u.%s.%s",InpMagic,_Symbol,suffix);
  }

int CountTodayManagedEntries()
  {
   datetime now=TimeCurrent();
   datetime start_server=UTCToServer(UTCMidnight(now));
   if(!HistorySelect(start_server,now))
      return 0;

   int count=0;
   int total=HistoryDealsTotal();
   for(int i=0;i<total;i++)
     {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      if((ulong)HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      ENUM_DEAL_ENTRY entry=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN) continue;
      ENUM_DEAL_TYPE type=(ENUM_DEAL_TYPE)HistoryDealGetInteger(deal,DEAL_TYPE);
      if(type==DEAL_TYPE_BUY || type==DEAL_TYPE_SELL)
         count++;
     }
   return count;
  }

void SaveRiskGovernorState()
  {
   if(g_is_tester)
      return;
   GlobalVariableSet(GVKey("riskday"),(double)g_risk_day_key);
   GlobalVariableSet(GVKey("dayeq"),g_day_start_equity);
   GlobalVariableSet(GVKey("peakeq"),g_peak_equity);
   GlobalVariableSet(GVKey("tradesday"),(double)g_trades_today);
   GlobalVariableSet(GVKey("lastexit"),(double)g_last_production_exit);
   GlobalVariableSet(GVKey("longloss"),(double)g_long_loss_streak);
   GlobalVariableSet(GVKey("shortloss"),(double)g_short_loss_streak);
   GlobalVariableSet(GVKey("longpause"),(double)g_long_pause_until);
   GlobalVariableSet(GVKey("shortpause"),(double)g_short_pause_until);
  }

void RecoverRiskGovernorState()
  {
   double equity=AccountInfoDouble(ACCOUNT_EQUITY);
   int today=DateKey(ServerToUTC(TimeCurrent()));
   g_risk_day_key=today;
   g_day_start_equity=equity;
   g_peak_equity=equity;
   g_trades_today=CountTodayManagedEntries();
   g_last_production_exit=0;

   if(g_is_tester)
      return;

   int saved_day=(GlobalVariableCheck(GVKey("riskday")) ? (int)GlobalVariableGet(GVKey("riskday")) : 0);
   if(saved_day==today && GlobalVariableCheck(GVKey("dayeq")))
     {
      double saved=GlobalVariableGet(GVKey("dayeq"));
      if(saved>0.0) g_day_start_equity=saved;
     }
   if(GlobalVariableCheck(GVKey("peakeq")))
     {
      double saved=GlobalVariableGet(GVKey("peakeq"));
      if(saved>g_peak_equity) g_peak_equity=saved;
     }
   if(GlobalVariableCheck(GVKey("tradesday")))
     {
      int saved_trades=(int)GlobalVariableGet(GVKey("tradesday"));
      if(saved_trades>g_trades_today)
         g_trades_today=saved_trades;
     }
   if(GlobalVariableCheck(GVKey("lastexit")))
      g_last_production_exit=(datetime)GlobalVariableGet(GVKey("lastexit"));
   if(GlobalVariableCheck(GVKey("longloss"))) g_long_loss_streak=(int)GlobalVariableGet(GVKey("longloss"));
   if(GlobalVariableCheck(GVKey("shortloss"))) g_short_loss_streak=(int)GlobalVariableGet(GVKey("shortloss"));
   if(GlobalVariableCheck(GVKey("longpause"))) g_long_pause_until=(datetime)GlobalVariableGet(GVKey("longpause"));
   if(GlobalVariableCheck(GVKey("shortpause"))) g_short_pause_until=(datetime)GlobalVariableGet(GVKey("shortpause"));

   SaveRiskGovernorState();
  }

void SaveProductionState()
  {
   if(!g_prod.active) return;
   GlobalVariableSet(GVKey("risk"),g_prod.risk_distance);
   GlobalVariableSet(GVKey("initvol"),g_prod.initial_volume);
   GlobalVariableSet(GVKey("tp1done"),(g_prod.tp1_done?1.0:0.0));
   GlobalVariableSet(GVKey("tp2done"),(g_prod.tp2_done?1.0:0.0));
   GlobalVariableSet(GVKey("tp1"),g_prod.tp1);
   GlobalVariableSet(GVKey("tp2"),g_prod.tp2);
   GlobalVariableSet(GVKey("tp3"),g_prod.tp3);
   GlobalVariableSet(GVKey("signal"),(double)g_prod.signal_id);
   GlobalVariableSet(GVKey("positionid"),(double)g_prod.position_id);
   GlobalVariableSet(GVKey("ticket"),(double)g_prod.ticket);
   GlobalVariableSet(GVKey("direction"),(double)g_prod.direction);
   GlobalVariableSet(GVKey("opentime"),(double)g_prod.open_time);
   GlobalVariableSet(GVKey("entry"),g_prod.entry);
  }

void ClearProductionState()
  {
   GlobalVariableDel(GVKey("risk"));
   GlobalVariableDel(GVKey("initvol"));
   GlobalVariableDel(GVKey("tp1done"));
   GlobalVariableDel(GVKey("tp2done"));
   GlobalVariableDel(GVKey("tp1"));
   GlobalVariableDel(GVKey("tp2"));
   GlobalVariableDel(GVKey("tp3"));
   GlobalVariableDel(GVKey("signal"));
   GlobalVariableDel(GVKey("positionid"));
   GlobalVariableDel(GVKey("ticket"));
   GlobalVariableDel(GVKey("direction"));
   GlobalVariableDel(GVKey("opentime"));
   GlobalVariableDel(GVKey("entry"));
   ZeroMemory(g_prod);
  }

bool LoadPersistedProductionSnapshot(ProductionState &p)
  {
   ZeroMemory(p);
   if(!GlobalVariableCheck(GVKey("positionid")) ||
      !GlobalVariableCheck(GVKey("direction")) ||
      !GlobalVariableCheck(GVKey("opentime")) ||
      !GlobalVariableCheck(GVKey("entry")) ||
      !GlobalVariableCheck(GVKey("risk")) ||
      !GlobalVariableCheck(GVKey("initvol")))
      return false;

   p.active=true;
   p.position_id=(ulong)GlobalVariableGet(GVKey("positionid"));
   p.ticket=(ulong)(GlobalVariableCheck(GVKey("ticket")) ? GlobalVariableGet(GVKey("ticket")) : 0.0);
   p.direction=(int)GlobalVariableGet(GVKey("direction"));
   p.open_time=(datetime)GlobalVariableGet(GVKey("opentime"));
   p.signal_time=p.open_time;
   p.entry=GlobalVariableGet(GVKey("entry"));
   p.risk_distance=GlobalVariableGet(GVKey("risk"));
   p.initial_volume=GlobalVariableGet(GVKey("initvol"));
   p.signal_id=(long)(GlobalVariableCheck(GVKey("signal")) ? GlobalVariableGet(GVKey("signal")) : 0.0);
   p.tp1_done=(GlobalVariableCheck(GVKey("tp1done")) && GlobalVariableGet(GVKey("tp1done"))>0.5);
   p.tp2_done=(GlobalVariableCheck(GVKey("tp2done")) && GlobalVariableGet(GVKey("tp2done"))>0.5);
   p.tp1=(GlobalVariableCheck(GVKey("tp1")) ? GlobalVariableGet(GVKey("tp1")) : 0.0);
   p.tp2=(GlobalVariableCheck(GVKey("tp2")) ? GlobalVariableGet(GVKey("tp2")) : 0.0);
   p.tp3=(GlobalVariableCheck(GVKey("tp3")) ? GlobalVariableGet(GVKey("tp3")) : 0.0);
   return (p.position_id>0 && p.direction!=0 && p.open_time>0 && p.entry>0.0 && p.risk_distance>0.0 && p.initial_volume>0.0);
  }

bool RecoverProductionState()
  {
   ulong ticket=0;
   if(!SelectManagedPosition(ticket))
     {
      ProductionState persisted;
      if(LoadPersistedProductionSnapshot(persisted))
        {
         UpdateLossStreakQuarantine(persisted);
         g_last_production_exit=TimeCurrent();
         SaveRiskGovernorState();
         WriteExecutionEvidence("RECOVERED_CLOSED",g_last_scalper,persisted.signal_id,persisted.direction,persisted.ticket,0.0,persisted.entry,0.0,
                                persisted.tp1,persisted.tp2,persisted.tp3,"RESTART_RECONCILIATION");
        }
      ClearProductionState();
      return false;
     }

   ZeroMemory(g_prod);
   g_prod.active=true;
   g_prod.ticket=ticket;
   g_prod.position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   g_prod.direction=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1);
   g_prod.entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double sl=PositionGetDouble(POSITION_SL);
   double tp=PositionGetDouble(POSITION_TP);
   g_prod.open_time=(datetime)PositionGetInteger(POSITION_TIME);
   g_prod.signal_time=g_prod.open_time;
   g_prod.risk_distance=(GlobalVariableCheck(GVKey("risk")) ? GlobalVariableGet(GVKey("risk")) : MathAbs(g_prod.entry-sl));
   g_prod.initial_volume=(GlobalVariableCheck(GVKey("initvol")) ? GlobalVariableGet(GVKey("initvol")) : PositionGetDouble(POSITION_VOLUME));
   g_prod.signal_id=(long)(GlobalVariableCheck(GVKey("signal")) ? GlobalVariableGet(GVKey("signal")) : 0.0);
   g_prod.tp1_done=(GlobalVariableCheck(GVKey("tp1done")) && GlobalVariableGet(GVKey("tp1done"))>0.5);
   g_prod.tp2_done=(GlobalVariableCheck(GVKey("tp2done")) && GlobalVariableGet(GVKey("tp2done"))>0.5);
   if(g_prod.risk_distance<=0.0) return false;
   g_prod.tp1=(GlobalVariableCheck(GVKey("tp1")) ? GlobalVariableGet(GVKey("tp1")) : g_prod.entry+g_prod.direction*InpProductionTP1_R*g_prod.risk_distance);
   g_prod.tp2=(GlobalVariableCheck(GVKey("tp2")) ? GlobalVariableGet(GVKey("tp2")) : g_prod.entry+g_prod.direction*InpProductionTP2_R*g_prod.risk_distance);
   g_prod.tp3=(GlobalVariableCheck(GVKey("tp3")) ? GlobalVariableGet(GVKey("tp3")) : (tp>0.0 ? tp : g_prod.entry+g_prod.direction*InpProductionTP3_R*g_prod.risk_distance));
   return true;
  }

void WriteExecutionEvidence(const string event_name,const ScalperDecision &d,const long signal_id,const int direction,
                            const ulong ticket,const double volume,const double entry,const double sl,
                            const double tp1,const double tp2,const double tp3,const string detail)
  {
   if(!InpWriteExecutionEvidence) return;
   int h=FileOpen(InpExecutionEvidenceFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,';');
   if(h==INVALID_HANDLE) return;
   if(FileSize(h)==0)
      FileWrite(h,"time","event","signal_id","direction","state","readiness","net_edge_r","context","micro","timing","execution","volume_score",
                  "ticket","volume","entry","sl","tp1","tp2","tp3","equity","detail");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),event_name,signal_id,direction,ScalperStateName(d.state),d.readiness,
             DoubleToString(d.net_edge_r,6),d.context_score,d.micro_score,d.timing_score,d.execution_score,d.volume_score,(long)ticket,
             DoubleToString(volume,4),DoubleToString(entry,_Digits),DoubleToString(sl,_Digits),DoubleToString(tp1,_Digits),
             DoubleToString(tp2,_Digits),DoubleToString(tp3,_Digits),DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),2),detail);
   FileClose(h);
  }

bool SendDeal(const int direction,const double volume,const double sl,const double tp,const string comment,ulong &deal_out)
  {
   deal_out=0;
   if(!OrdersEnabledByMode() || IsLiveAccount()) return false;
   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;

   MqlTradeRequest req={};
   MqlTradeResult res={};
   req.action=TRADE_ACTION_DEAL;
   req.magic=InpMagic;
   req.symbol=_Symbol;
   req.volume=volume;
   req.type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   req.price=(direction>0 ? tick.ask : tick.bid);
   req.sl=NormalizePriceToTick(sl);
   req.tp=NormalizePriceToTick(tp);
   req.deviation=(ulong)InpOrderDeviationPoints;
   req.type_filling=GetFillingMode();
   req.type_time=ORDER_TIME_GTC;
   req.comment=comment;

   MqlTradeCheckResult check={};
   ResetLastError();
   if(!OrderCheck(req,check))
     {
      PrintFormat("[AUREON V10.3] ORDER CHECK failed err=%d ret=%u %s",GetLastError(),check.retcode,check.comment);
      return false;
     }
   ResetLastError();
   if(!OrderSend(req,res))
     {
      PrintFormat("[AUREON V10.3] ORDER SEND failed err=%d ret=%u %s",GetLastError(),res.retcode,res.comment);
      return false;
     }
   if(res.retcode!=TRADE_RETCODE_DONE && res.retcode!=TRADE_RETCODE_DONE_PARTIAL && res.retcode!=TRADE_RETCODE_PLACED)
     {
      PrintFormat("[AUREON V10.3] ORDER rejected ret=%u %s",res.retcode,res.comment);
      return false;
     }
   deal_out=res.deal;
   return true;
  }

bool ModifyManagedStops(const ulong ticket,const double sl,const double tp)
  {
   if(!OrdersEnabledByMode() || IsLiveAccount() || !PositionSelectByTicket(ticket)) return false;
   MqlTradeRequest req={};
   MqlTradeResult res={};
   req.action=TRADE_ACTION_SLTP;
   req.magic=InpMagic;
   req.symbol=_Symbol;
   req.position=ticket;
   req.sl=(sl>0.0 ? NormalizePriceToTick(sl) : 0.0);
   req.tp=(tp>0.0 ? NormalizePriceToTick(tp) : 0.0);
   MqlTradeCheckResult check={};
   ResetLastError();
   if(!OrderCheck(req,check))
     {
      PrintFormat("[AUREON V10.3] SLTP check failed err=%d ret=%u %s",GetLastError(),check.retcode,check.comment);
      return false;
     }
   ResetLastError();
   if(!OrderSend(req,res))
     {
      PrintFormat("[AUREON V10.3] SLTP send failed err=%d ret=%u %s",GetLastError(),res.retcode,res.comment);
      return false;
     }
   return (res.retcode==TRADE_RETCODE_DONE || res.retcode==TRADE_RETCODE_NO_CHANGES);
  }

bool CloseManagedVolume(const ulong ticket,double volume,const string comment)
  {
   if(!OrdersEnabledByMode() || IsLiveAccount() || !PositionSelectByTicket(ticket)) return false;
   double current=PositionGetDouble(POSITION_VOLUME);
   int direction=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1);
   if(current<=0.0) return false;
   if(volume>current) volume=current;
   volume=NormalizeVolumeDown(volume);
   if(volume<=0.0) return false;

   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   MqlTradeRequest req={};
   MqlTradeResult res={};
   req.action=TRADE_ACTION_DEAL;
   req.magic=InpMagic;
   req.symbol=_Symbol;
   req.position=ticket;
   req.volume=volume;
   req.type=(direction>0 ? ORDER_TYPE_SELL : ORDER_TYPE_BUY);
   req.price=(direction>0 ? tick.bid : tick.ask);
   req.deviation=(ulong)InpOrderDeviationPoints;
   req.type_filling=GetFillingMode();
   req.type_time=ORDER_TIME_GTC;
   req.comment=comment;
   MqlTradeCheckResult check={};
   ResetLastError();
   if(!OrderCheck(req,check))
     {
      PrintFormat("[AUREON V10.3] CLOSE check failed err=%d ret=%u %s",GetLastError(),check.retcode,check.comment);
      return false;
     }
   ResetLastError();
   if(!OrderSend(req,res))
     {
      PrintFormat("[AUREON V10.3] CLOSE send failed err=%d ret=%u %s",GetLastError(),res.retcode,res.comment);
      return false;
     }
   return (res.retcode==TRADE_RETCODE_DONE || res.retcode==TRADE_RETCODE_DONE_PARTIAL || res.retcode==TRADE_RETCODE_PLACED);
  }

double RiskSizedVolume(const int direction,const double entry,const double sl)
  {
   if(InpVolumeMode==VOLUME_FIXED_LOT) return NormalizeVolumeDown(InpFixedLot);
   double risk_pct=MathMin(InpRiskPercent,InpMaxRiskPercent);
   if(InpUseDirectionalRisk)
     {
      double side_mult=(direction>0 ? InpLongRiskMultiplier : InpShortRiskMultiplier);
      risk_pct*=ClampDouble(side_mult,0.0,1.0);
     }
   if(risk_pct<=0.0) return 0.0;
   double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*risk_pct/100.0;
   if(risk_money<=0.0) return 0.0;
   double one_lot_profit=0.0;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,sl,one_lot_profit)) return 0.0;
   double loss_per_lot=MathAbs(one_lot_profit);
   if(loss_per_lot<=0.0) return 0.0;
   return NormalizeVolumeDown(risk_money/loss_per_lot);
  }

bool MarginAvailable(const int direction,const double volume,const double price)
  {
   double margin=0.0;
   if(!OrderCalcMargin((direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),_Symbol,volume,price,margin)) return false;
   return (margin>0.0 && AccountInfoDouble(ACCOUNT_MARGIN_FREE)>=margin*1.10);
  }

double ResolveProductionStop(const GoldContext &gold,const FeatureContext &f,const double entry)
  {
   double min_stop=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   double buffer=MathMax(0.10*gold.atr,2.0*_Point);
   double max_risk=MathMax(InpProductionSL_ATR*gold.atr,min_stop+2.0*_Point);
   double best=entry-gold.direction*max_risk;
   double best_dist=max_risk;
   double levels[8];
   ArrayInitialize(levels,0.0);
   int n=0;
   levels[n++]=(gold.direction>0 ? gold.prior_low : gold.prior_high);
   if(f.swing_level>0.0) levels[n++]=f.swing_level;
   if(f.seq_fvg) levels[n++]=(gold.direction>0 ? f.fvg_low : f.fvg_high);
   if(gold.ema100_m5>0.0) levels[n++]=gold.ema100_m5;
   if(f.volume.valid)
     {
      if(f.volume.poc>0.0) levels[n++]=f.volume.poc;
      double va=(gold.direction>0 ? f.volume.val : f.volume.vah);
      if(va>0.0) levels[n++]=va;
     }
   for(int i=0;i<n;i++)
     {
      double level=levels[i];
      if(level<=0.0) continue;
      double candidate=(gold.direction>0 ? level-buffer : level+buffer);
      double dist=MathAbs(entry-candidate);
      bool correct_side=(gold.direction>0 ? candidate<entry : candidate>entry);
      if(!correct_side || dist<min_stop+2.0*_Point || dist>max_risk) continue;
      if(dist<best_dist)
        {
         best=candidate;
         best_dist=dist;
        }
     }
   return NormalizePriceToTick(best);
  }

bool OpenProductionTrade(const long signal_id,const GoldContext &gold,const FeatureContext &f,const ScalperDecision &d,const MqlTick &tick)
  {
   if(d.state!=SCALPER_TRIGGERED || !OrdersEnabledByMode() || IsLiveAccount()) return false;
   if(!SymbolTradeModeAllows(gold.direction))
     {
      WriteExecutionEvidence("BLOCKED",d,signal_id,gold.direction,0,0.0,0.0,0.0,0.0,0.0,0.0,"SYMBOL_TRADE_MODE");
      return false;
     }
   if(HasAnySymbolPosition() || HasAnySymbolOrder())
     {
      WriteExecutionEvidence("BLOCKED",d,signal_id,gold.direction,0,0.0,0.0,0.0,0.0,0.0,0.0,"EXISTING_GOLD_EXPOSURE");
      return false;
     }
   if(g_last_production_signal==signal_id) return false;

   double entry=(gold.direction>0 ? tick.ask : tick.bid);
   double sl=ResolveProductionStop(gold,f,entry);
   double risk=MathAbs(entry-sl);
   if(risk<=0.0) return false;
   double tp1=0.0,tp2=0.0,tp3=0.0;
   ResolveProductionTargets(gold,f,entry,risk,tp1,tp2,tp3);
   double volume=RiskSizedVolume(gold.direction,entry,sl);
   if(volume<=0.0 || !MarginAvailable(gold.direction,volume,entry))
     {
      WriteExecutionEvidence("BLOCKED",d,signal_id,gold.direction,0,volume,entry,sl,tp1,tp2,tp3,"VOLUME_OR_MARGIN");
      return false;
     }

   ulong deal=0;
   if(!SendDeal(gold.direction,volume,sl,tp3,"AUREON10_HYPER",deal))
     {
      WriteExecutionEvidence("ORDER_REJECT",d,signal_id,gold.direction,0,volume,entry,sl,tp1,tp2,tp3,"SEND_FAILED");
      return false;
     }

   ulong ticket=0;
   if(!SelectManagedPosition(ticket))
     {
      Print("[AUREON V10.3] order accepted but managed position not found yet.");
      return true;
     }

   ZeroMemory(g_prod);
   g_prod.active=true;
   g_prod.ticket=ticket;
   g_prod.position_id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   g_prod.signal_id=signal_id;
   g_prod.direction=gold.direction;
   g_prod.signal_time=gold.signal_time;
   g_prod.open_time=(datetime)PositionGetInteger(POSITION_TIME);
   g_prod.entry=PositionGetDouble(POSITION_PRICE_OPEN);
   g_prod.risk_distance=MathAbs(g_prod.entry-PositionGetDouble(POSITION_SL));
   if(g_prod.risk_distance<=0.0) g_prod.risk_distance=risk;
   g_prod.initial_volume=PositionGetDouble(POSITION_VOLUME);
   ResolveProductionTargets(gold,f,g_prod.entry,g_prod.risk_distance,g_prod.tp1,g_prod.tp2,g_prod.tp3);
   double current_sl=PositionGetDouble(POSITION_SL);
   double current_tp=PositionGetDouble(POSITION_TP);
   if(g_prod.tp3>0.0 && MathAbs(current_tp-g_prod.tp3)>_Point)
      ModifyManagedStops(ticket,current_sl,g_prod.tp3);
   g_prod.tp1_done=false;
   g_prod.tp2_done=false;
   SaveProductionState();
   g_trades_today++;
   g_last_production_signal=signal_id;
   SaveRiskGovernorState();
   WriteExecutionEvidence("OPEN",d,signal_id,gold.direction,ticket,g_prod.initial_volume,g_prod.entry,
                          PositionGetDouble(POSITION_SL),g_prod.tp1,g_prod.tp2,g_prod.tp3,"OK");
   return true;
  }

double PartialVolumeForFraction(const double current,const double initial,const double fraction)
  {
   double minv=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double desired=NormalizeVolumeDown(initial*fraction);
   if(desired<=0.0 || desired>=current) return 0.0;
   double remain=current-desired;
   if(remain>0.0 && remain<minv)
      desired=NormalizeVolumeDown(current-minv);
   return desired;
  }

void StartMicroBar(MicroBar &bar,const datetime bucket,const double price,const double spread_points)
  {
   bar.initialized=true;
   bar.bucket_time=bucket;
   bar.open=price;
   bar.high=price;
   bar.low=price;
   bar.close=price;
   bar.ticks=1;
   bar.spread_sum_points=spread_points;
  }

bool UpdateOneMicroBar(MicroBar &bar,const int seconds,const MqlTick &tick,MicroBar &closed_bar)
  {
   if(seconds<=0 || tick.time<=0 || tick.ask<=0.0 || tick.bid<=0.0) return false;
   datetime bucket=(datetime)(((long)tick.time/(long)seconds)*(long)seconds);
   double price=0.5*(tick.ask+tick.bid);
   double spread_points=(tick.ask-tick.bid)/_Point;
   if(!bar.initialized)
     {
      StartMicroBar(bar,bucket,price,spread_points);
      return false;
     }
   if(bucket==bar.bucket_time)
     {
      if(price>bar.high) bar.high=price;
      if(price<bar.low) bar.low=price;
      bar.close=price;
      bar.ticks++;
      bar.spread_sum_points+=spread_points;
      return false;
     }
   closed_bar=bar;
   StartMicroBar(bar,bucket,price,spread_points);
   return true;
  }

bool MicroEntryTrigger(const MicroBar &bar,const GoldContext &gold)
  {
   double ema21=0.0,ema100=0.0,atr1=0.0;
   if(!GetBufferValue(hGoldEMA21M1,0,1,ema21)) return false;
   if(!GetBufferValue(hGoldEMA100M1,0,1,ema100)) return false;
   if(!GetBufferValue(hGoldM1ATR,0,1,atr1) || atr1<=0.0) return false;
   double range=bar.high-bar.low;
   if(range<InpMicroMinRangeATR*atr1) return false;
   double touch=InpMicroEMATouchATR*atr1;
   if(gold.direction>0)
      return (bar.close>bar.open && bar.close>ema21 && bar.low<=ema21+touch && bar.close>=ema100-touch);
   return (bar.close<bar.open && bar.close<ema21 && bar.high>=ema21-touch && bar.close<=ema100+touch);
  }

void ResetMicroDayIfNeeded()
  {
   int day=DateKey(ServerToUTC(TimeCurrent()));
   if(g_micro_day_key==day) return;
   g_micro_day_key=day;
   g_shadow_evaluations_today=0;
   g_shadow_setups_today=0;
  }

void UpdateMicroEngine()
  {
   ResetMicroDayIfNeeded();
   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick)) return;
   MicroBar closed5,closed15,closed30;
   bool c5=UpdateOneMicroBar(g_micro5,InpMicroBarSecondsFast,tick,closed5);
   UpdateOneMicroBar(g_micro15,InpMicroBarSecondsMedium,tick,closed15);
   UpdateOneMicroBar(g_micro30,InpMicroBarSecondsSlow,tick,closed30);
   if(!c5) return;

   g_shadow_evaluations_today++;
   double avg_spread=(closed5.ticks>0 ? closed5.spread_sum_points/(double)closed5.ticks : 9999.0);
   if(avg_spread>InpMaxProductionSpreadPoints || closed5.high<=closed5.low) return;

   if(!g_anchor_valid) return;
   double age_minutes=(double)(TimeCurrent()-g_anchor_gold.signal_time)/60.0;
   if(age_minutes<0.0 || age_minutes>60.0)
     {
      g_anchor_valid=false;
      return;
     }
   if(!MicroEntryTrigger(closed5,g_anchor_gold)) return;
   g_shadow_setups_today++;

   bool frozen_like=(g_anchor_gold.extension>=InpGoldExtensionATR &&
                     ((g_anchor_gold.direction>0 && g_anchor_gold.rsi<=InpGoldRSILongMax) ||
                      (g_anchor_gold.direction<0 && g_anchor_gold.rsi>=InpGoldRSIShortMin)));
   ScalperDecision d;
   if(frozen_like) d=BuildScalperDecision(g_anchor_gold,g_anchor_features,tick,InpRequireVolumeConfirmationForExecution);
   else d=BuildHyperTrendDecision(g_anchor_gold,g_anchor_features,tick,true);
   if(frozen_like && d.state==SCALPER_ARMED && d.net_edge_r>=InpMinNetEdgeR)
     {
      d.state=SCALPER_TRIGGERED;
      d.reason="MICRO_5S_TRIGGER";
      d.micro_score=ClampInt(d.micro_score+5,0,30);
      d.readiness=ClampInt(d.readiness+5,0,100);
     }
   if(d.state!=SCALPER_TRIGGERED) return;
   long micro_intent=g_anchor_signal_id*(long)1000000+(long)(g_shadow_evaluations_today%(long)1000000);
   g_last_scalper=d;
   OpenProductionTrade(micro_intent,g_anchor_gold,g_anchor_features,d,tick);
  }

void ManageProductionPosition()
  {
   ulong ticket=0;
   bool exists=SelectManagedPosition(ticket);
   if(!exists)
     {
      if(g_prod.active)
        {
         UpdateLossStreakQuarantine(g_prod);
         g_last_production_exit=TimeCurrent();
         SaveRiskGovernorState();
         WriteExecutionEvidence("CLOSED",g_last_scalper,g_prod.signal_id,g_prod.direction,g_prod.ticket,0.0,g_prod.entry,0.0,
                                g_prod.tp1,g_prod.tp2,g_prod.tp3,"POSITION_GONE");
        }
      ClearProductionState();
      return;
     }

   if(!g_prod.active || g_prod.ticket!=ticket)
      RecoverProductionState();
   if(!g_prod.active || g_prod.risk_distance<=0.0) return;

   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double px=(g_prod.direction>0 ? tick.bid : tick.ask);
   double current=PositionGetDouble(POSITION_VOLUME);

   if(g_risk_halted && RiskGovernorApplies() && InpEmergencyCloseOnGovernor)
     {
      if(CloseManagedVolume(ticket,current,"AUREON_RISK_HALT"))
         WriteExecutionEvidence("EMERGENCY_CLOSE",g_last_scalper,g_prod.signal_id,g_prod.direction,ticket,current,g_prod.entry,
                                PositionGetDouble(POSITION_SL),g_prod.tp1,g_prod.tp2,g_prod.tp3,"RISK_GOVERNOR");
      return;
     }

   if(!g_prod.tp1_done && ((g_prod.direction>0 && px>=g_prod.tp1) || (g_prod.direction<0 && px<=g_prod.tp1)))
     {
      double part=PartialVolumeForFraction(current,g_prod.initial_volume,InpTP1CloseFraction);
      bool partial_ok=(part<=0.0 ? true : CloseManagedVolume(ticket,part,"AUREON_TP1"));
      if(partial_ok)
        {
         if(PositionSelectByTicket(ticket) && InpMoveSLToBEAtTP1)
            ModifyManagedStops(ticket,g_prod.entry,g_prod.tp3);
         g_prod.tp1_done=true;
         SaveProductionState();
         WriteExecutionEvidence("TP1",g_last_scalper,g_prod.signal_id,g_prod.direction,ticket,part,g_prod.entry,g_prod.entry,
                                g_prod.tp1,g_prod.tp2,g_prod.tp3,"PARTIAL_OR_PROTECT");
        }
     }

   if(PositionSelectByTicket(ticket)) current=PositionGetDouble(POSITION_VOLUME); else return;
   if(!g_prod.tp2_done && ((g_prod.direction>0 && px>=g_prod.tp2) || (g_prod.direction<0 && px<=g_prod.tp2)))
     {
      double part=PartialVolumeForFraction(current,g_prod.initial_volume,InpTP2CloseFraction);
      bool partial_ok=(part<=0.0 ? true : CloseManagedVolume(ticket,part,"AUREON_TP2"));
      if(partial_ok)
        {
         double lock_sl=g_prod.entry+g_prod.direction*g_prod.risk_distance;
         if(PositionSelectByTicket(ticket) && InpLock1RAtTP2)
            ModifyManagedStops(ticket,lock_sl,g_prod.tp3);
         g_prod.tp2_done=true;
         SaveProductionState();
         WriteExecutionEvidence("TP2",g_last_scalper,g_prod.signal_id,g_prod.direction,ticket,part,g_prod.entry,lock_sl,
                                g_prod.tp1,g_prod.tp2,g_prod.tp3,"PARTIAL_OR_LOCK");
        }
     }

   if(PositionSelectByTicket(ticket))
     {
      int held_seconds=(int)(TimeCurrent()-g_prod.open_time);
      if(held_seconds>=InpProductionMaxHoldSeconds)
        {
         current=PositionGetDouble(POSITION_VOLUME);
         if(current>0.0 && CloseManagedVolume(ticket,current,"AUREON_HYPER_TIME"))
            WriteExecutionEvidence("TIME_EXIT",g_last_scalper,g_prod.signal_id,g_prod.direction,ticket,current,g_prod.entry,
                                   PositionGetDouble(POSITION_SL),g_prod.tp1,g_prod.tp2,g_prod.tp3,"MAX_SECONDS");
         return;
        }
      if(held_seconds>=InpAdverseExitMinSeconds)
        {
         double ema21_now=0.0;
         if(GetBufferValue(hGoldEMA21M1,0,0,ema21_now) && ema21_now>0.0)
           {
            bool adverse=(g_prod.direction>0 ? px<ema21_now : px>ema21_now);
            if(adverse)
              {
               current=PositionGetDouble(POSITION_VOLUME);
               if(current>0.0 && CloseManagedVolume(ticket,current,"AUREON_ADVERSE_EMA21"))
                  WriteExecutionEvidence("ADVERSE_EXIT",g_last_scalper,g_prod.signal_id,g_prod.direction,ticket,current,g_prod.entry,
                                         PositionGetDouble(POSITION_SL),g_prod.tp1,g_prod.tp2,g_prod.tp3,"EMA21_FLIP");
               return;
              }
           }
        }
      int bars_since=iBarShift(_Symbol,PERIOD_M5,g_prod.open_time,false);
      if(bars_since>=InpProductionMaxHoldM5Bars)
        {
         current=PositionGetDouble(POSITION_VOLUME);
         if(current>0.0 && CloseManagedVolume(ticket,current,"AUREON_TIME"))
            WriteExecutionEvidence("TIME_EXIT",g_last_scalper,g_prod.signal_id,g_prod.direction,ticket,current,g_prod.entry,
                                   PositionGetDouble(POSITION_SL),g_prod.tp1,g_prod.tp2,g_prod.tp3,"MAX_HOLD");
        }
     }
  }

void UpdateDashboard()
  {
   if(!InpShowDashboard) {Comment(""); return;}
   string mode=ExecutionModeName(g_effective_execution_mode);
   string requested=ExecutionModeName(InpExecutionMode);
   ulong ticket=FindManagedPositionTicket();
   string pos=(ticket>0 ? StringFormat("OPEN #%I64u",ticket) : "FLAT");
   Comment("AUREON OMEGA V10.3 PRE-LIVE CANDIDATE\n",
           "Mode: ",mode," (requested ",requested,") | LIVE: HARD BLOCKED\n",
           "State: ",ScalperStateName(g_last_scalper.state)," | Readiness: ",IntegerToString(g_last_scalper.readiness),"/100\n",
           "Net edge: ",DoubleToString(g_last_scalper.net_edge_r,3),"R | C/M/T/E/V: ",
           IntegerToString(g_last_scalper.context_score),"/",IntegerToString(g_last_scalper.micro_score),"/",
           IntegerToString(g_last_scalper.timing_score),"/",IntegerToString(g_last_scalper.execution_score),"/",IntegerToString(g_last_scalper.volume_score),"\n",
           "VWAP: ",DoubleToString(g_last_volume.london_vwap,_Digits)," | POC: ",DoubleToString(g_last_volume.poc,_Digits),
           " | VAL/VAH: ",DoubleToString(g_last_volume.val,_Digits),"/",DoubleToString(g_last_volume.vah,_Digits),"\n",
           "EMA100: ",EMA100StateName(g_anchor_gold.ema100_state)," | M5=",DoubleToString(g_anchor_gold.ema100_m5,_Digits),
           " | H1=",DoubleToString(g_anchor_gold.ema100_h1,_Digits),"\n",
           "Position: ",pos," | Trades: ",IntegerToString(g_trades_today),"/",IntegerToString(InpMaxTradesPerDay),
           " | Shadow 5s: ",StringFormat("%I64d",g_shadow_evaluations_today)," | Qualified: ",StringFormat("%I64d",g_shadow_setups_today),"\n",
           "Risk halt: ",(g_risk_halted?"YES":"NO")," | Reason: ",g_last_scalper.reason);
  }

//------------------------- Evidence Writers --------------------------

// MQL5 FileWrite has a finite variadic argument count. The V9.5 signal
// evidence schema intentionally exceeds that limit, so the wide evidence row
// is streamed with FileWriteString instead of truncating or splitting a CSV row.
string CsvEscapeField(const string value)
  {
   string s=value;
   bool quote=(StringFind(s,";")>=0 || StringFind(s,"\r")>=0 || StringFind(s,"\n")>=0 || StringFind(s,"\"")>=0);
   if(StringFind(s,"\"")>=0)
      StringReplace(s,"\"","\"\"");
   return (quote ? "\""+s+"\"" : s);
  }

void CsvAppend(string &row,const string value)
  {
   if(StringLen(row)>0) row+=";";
   row+=CsvEscapeField(value);
  }

void CsvAppend(string &row,const int value)
  {
   CsvAppend(row,IntegerToString(value));
  }

void CsvAppend(string &row,const long value)
  {
   CsvAppend(row,StringFormat("%I64d",value));
  }

void CsvAppend(string &row,const ulong value)
  {
   CsvAppend(row,StringFormat("%I64u",value));
  }

void CsvAppend(string &row,const double value)
  {
   CsvAppend(row,DoubleToString(value,8));
  }

void CsvWriteLine(const int handle,const string row)
  {
   FileWriteString(handle,row+"\r\n");
  }

void WriteSignalEvidence(const long signal_id,
                         const GoldContext &gold,
                         const FeatureContext &f,
                         const bool &gates[],
                         const ScalperDecision &scalper,
                         const ScalperDecision &volume_scalper)
  {
   if(!InpWriteSignalEvidence)
      return;

   int h=FileOpen(InpSignalEvidenceFile,
                  FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,
                  ';');
   if(h==INVALID_HANDLE)
      return;

   if(FileSize(h)==0)
     {
            string header="";
      CsvAppend(header,"research_id");
      CsvAppend(header,"signal_id");
      CsvAppend(header,"signal_time");
      CsvAppend(header,"fold");
      CsvAppend(header,"halfyear");
      CsvAppend(header,"utc_offset");
      CsvAppend(header,"direction");
      CsvAppend(header,"gold_close");
      CsvAppend(header,"gold_atr");
      CsvAppend(header,"gold_rsi");
      CsvAppend(header,"gold_adx");
      CsvAppend(header,"vol_ratio");
      CsvAppend(header,"extension_atr");
      CsvAppend(header,"spread_points");
      CsvAppend(header,"pdh");
      CsvAppend(header,"pdl");
      CsvAppend(header,"prev_day_ok");
      CsvAppend(header,"prev_day_dist_atr");
      CsvAppend(header,"prev_day_pen_atr");
      CsvAppend(header,"prev_day_pen_class");
      CsvAppend(header,"asia_high");
      CsvAppend(header,"asia_low");
      CsvAppend(header,"asia_ok");
      CsvAppend(header,"asia_dist_atr");
      CsvAppend(header,"asia_pen_atr");
      CsvAppend(header,"asia_pen_class");
      CsvAppend(header,"swing_level");
      CsvAppend(header,"swing_shift");
      CsvAppend(header,"swing_ok");
      CsvAppend(header,"swing_dist_atr");
      CsvAppend(header,"swing_pen_atr");
      CsvAppend(header,"swing_pen_class");
      CsvAppend(header,"fib_level");
      CsvAppend(header,"fib_ratio");
      CsvAppend(header,"fib_ok");
      CsvAppend(header,"fib_dist_atr");
      CsvAppend(header,"m5_structure_break");
      CsvAppend(header,"seq_raid");
      CsvAppend(header,"raid_time");
      CsvAppend(header,"seq_reclaim");
      CsvAppend(header,"reclaim_time");
      CsvAppend(header,"seq_mss");
      CsvAppend(header,"mss_time");
      CsvAppend(header,"seq_displacement");
      CsvAppend(header,"displacement_time");
      CsvAppend(header,"seq_fvg");
      CsvAppend(header,"fvg_time");
      CsvAppend(header,"fvg_low");
      CsvAppend(header,"fvg_high");
      CsvAppend(header,"fvg_gap_atr");
      CsvAppend(header,"seq_retrace");
      CsvAppend(header,"retrace_time");
      CsvAppend(header,"fvg_retrace_depth");
      CsvAppend(header,"trendline_level");
      CsvAppend(header,"trendline_ok");
      CsvAppend(header,"trendline_dist_atr");
      CsvAppend(header,"trendline_slope_atr_bar");
      CsvAppend(header,"trendline_age_bars");
      CsvAppend(header,"trendline_pivot_sep_bars");
      CsvAppend(header,"daily_vwap");
      CsvAppend(header,"london_vwap");
      CsvAppend(header,"anchored_vwap");
      CsvAppend(header,"anchored_vwap_time");
      CsvAppend(header,"london_sigma");
      CsvAppend(header,"vwap_upper1");
      CsvAppend(header,"vwap_lower1");
      CsvAppend(header,"vwap_upper2");
      CsvAppend(header,"vwap_lower2");
      CsvAppend(header,"poc");
      CsvAppend(header,"val");
      CsvAppend(header,"vah");
      CsvAppend(header,"daily_vwap_dist_atr");
      CsvAppend(header,"london_vwap_dist_atr");
      CsvAppend(header,"anchored_vwap_dist_atr");
      CsvAppend(header,"poc_dist_atr");
      CsvAppend(header,"vwap_slope_atr_15m");
      CsvAppend(header,"value_area_state");
      CsvAppend(header,"volume_source_quality");
      CsvAppend(header,"real_volume_fraction");
      CsvAppend(header,"vwap_reclaim");
      CsvAppend(header,"value_area_reclaim");
      CsvAppend(header,"mean_reversion_path");
      CsvAppend(header,"volume_location_ok");
      CsvAppend(header,"volume_score");
      CsvAppend(header,"location_count");
      CsvAppend(header,"feature_count");
      CsvAppend(header,"feature_mask");
      CsvAppend(header,"reference_sl");
      CsvAppend(header,"reference_tp1");
      CsvAppend(header,"reference_tp2");
      CsvAppend(header,"reference_tp3");
      CsvAppend(header,"target_mode");
      CsvAppend(header,"structural_tp1");
      CsvAppend(header,"structural_tp2");
      CsvAppend(header,"structural_tp3");
      CsvAppend(header,"gate_control");
      CsvAppend(header,"gate_pdh_pdl");
      CsvAppend(header,"gate_asia");
      CsvAppend(header,"gate_swing");
      CsvAppend(header,"gate_fib");
      CsvAppend(header,"gate_m5_break");
      CsvAppend(header,"gate_seq_mss");
      CsvAppend(header,"gate_seq_disp");
      CsvAppend(header,"gate_seq_fvg");
      CsvAppend(header,"gate_seq_retrace");
      CsvAppend(header,"gate_trendline");
      CsvAppend(header,"gate_location_composite");
      CsvAppend(header,"gate_sniper_composite");
      CsvAppend(header,"gate_vwap_context");
      CsvAppend(header,"gate_volume_profile");
      CsvAppend(header,"gate_volume_composite");
      CsvAppend(header,"gate_super_scalper");
      CsvAppend(header,"gate_super_scalper_volume");
      CsvAppend(header,"scalper_state");
      CsvAppend(header,"readiness");
      CsvAppend(header,"net_edge_r");
      CsvAppend(header,"score_context");
      CsvAppend(header,"score_micro");
      CsvAppend(header,"score_timing");
      CsvAppend(header,"score_execution");
      CsvAppend(header,"scalper_reason");
      CsvAppend(header,"volume_scalper_state");
      CsvAppend(header,"volume_readiness");
      CsvAppend(header,"volume_net_edge_r");
      CsvAppend(header,"volume_score_component");
      CsvAppend(header,"volume_scalper_reason");
      CsvWriteLine(h,header);
     }

   double ref_entry=gold.signal_close;
   double risk=InpVirtualSL_ATR*gold.atr;
   double ref_sl=(gold.direction>0 ? ref_entry-risk : ref_entry+risk);
   double tp1=(gold.direction>0 ? ref_entry+InpReferenceTP1_R*risk : ref_entry-InpReferenceTP1_R*risk);
   double tp2=(gold.direction>0 ? ref_entry+InpReferenceTP2_R*risk : ref_entry-InpReferenceTP2_R*risk);
   double tp3=(gold.direction>0 ? ref_entry+InpReferenceTP3_R*risk : ref_entry-InpReferenceTP3_R*risk);
   double stp1=0.0,stp2=0.0,stp3=0.0;
   ResolveProductionTargets(gold,f,ref_entry,risk,stp1,stp2,stp3);

   FileSeek(h,0,SEEK_END);
      string row="";
   CsvAppend(row,(long)InpResearchId);
   CsvAppend(row,signal_id);
   CsvAppend(row,TimeToString(gold.signal_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,gold.fold);
   CsvAppend(row,gold.halfyear);
   CsvAppend(row,gold.historical_utc_offset);
   CsvAppend(row,gold.direction);
   CsvAppend(row,DoubleToString(gold.signal_close,_Digits));
   CsvAppend(row,DoubleToString(gold.atr,_Digits));
   CsvAppend(row,DoubleToString(gold.rsi,4));
   CsvAppend(row,DoubleToString(gold.adx,4));
   CsvAppend(row,DoubleToString(gold.vol_ratio,5));
   CsvAppend(row,DoubleToString(gold.extension,5));
   CsvAppend(row,DoubleToString(gold.spread_points,2));
   CsvAppend(row,DoubleToString(f.prev_day_high,_Digits));
   CsvAppend(row,DoubleToString(f.prev_day_low,_Digits));
   CsvAppend(row,(f.prev_day_ok?1:0));
   CsvAppend(row,DoubleToString(f.prev_day_distance_atr,5));
   CsvAppend(row,DoubleToString(f.prev_day_penetration_atr,5));
   CsvAppend(row,f.prev_day_pen_class);
   CsvAppend(row,DoubleToString(f.asia_high,_Digits));
   CsvAppend(row,DoubleToString(f.asia_low,_Digits));
   CsvAppend(row,(f.asia_ok?1:0));
   CsvAppend(row,DoubleToString(f.asia_distance_atr,5));
   CsvAppend(row,DoubleToString(f.asia_penetration_atr,5));
   CsvAppend(row,f.asia_pen_class);
   CsvAppend(row,DoubleToString(f.swing_level,_Digits));
   CsvAppend(row,f.swing_shift);
   CsvAppend(row,(f.swing_ok?1:0));
   CsvAppend(row,DoubleToString(f.swing_distance_atr,5));
   CsvAppend(row,DoubleToString(f.swing_penetration_atr,5));
   CsvAppend(row,f.swing_pen_class);
   CsvAppend(row,DoubleToString(f.fib_level,_Digits));
   CsvAppend(row,DoubleToString(f.fib_ratio,3));
   CsvAppend(row,(f.fib_ok?1:0));
   CsvAppend(row,DoubleToString(f.fib_distance_atr,5));
   CsvAppend(row,(f.m5_structure_break?1:0));
   CsvAppend(row,(f.seq_raid?1:0));
   CsvAppend(row,TimeToString(f.raid_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,(f.seq_reclaim?1:0));
   CsvAppend(row,TimeToString(f.reclaim_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,(f.seq_mss?1:0));
   CsvAppend(row,TimeToString(f.mss_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,(f.seq_displacement?1:0));
   CsvAppend(row,TimeToString(f.displacement_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,(f.seq_fvg?1:0));
   CsvAppend(row,TimeToString(f.fvg_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,DoubleToString(f.fvg_low,_Digits));
   CsvAppend(row,DoubleToString(f.fvg_high,_Digits));
   CsvAppend(row,DoubleToString(f.fvg_gap_atr,5));
   CsvAppend(row,(f.seq_retrace?1:0));
   CsvAppend(row,TimeToString(f.retrace_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,DoubleToString(f.fvg_retrace_depth,5));
   CsvAppend(row,DoubleToString(f.trendline_level,_Digits));
   CsvAppend(row,(f.trendline_ok?1:0));
   CsvAppend(row,DoubleToString(f.trendline_distance_atr,5));
   CsvAppend(row,DoubleToString(f.trendline_slope_atr_per_bar,6));
   CsvAppend(row,f.trendline_age_bars);
   CsvAppend(row,f.trendline_pivot_separation_bars);
   CsvAppend(row,DoubleToString(f.volume.daily_vwap,_Digits));
   CsvAppend(row,DoubleToString(f.volume.london_vwap,_Digits));
   CsvAppend(row,DoubleToString(f.volume.anchored_vwap,_Digits));
   CsvAppend(row,TimeToString(f.volume.anchored_vwap_time,TIME_DATE|TIME_MINUTES));
   CsvAppend(row,DoubleToString(f.volume.london_sigma,_Digits));
   CsvAppend(row,DoubleToString(f.volume.vwap_upper1,_Digits));
   CsvAppend(row,DoubleToString(f.volume.vwap_lower1,_Digits));
   CsvAppend(row,DoubleToString(f.volume.vwap_upper2,_Digits));
   CsvAppend(row,DoubleToString(f.volume.vwap_lower2,_Digits));
   CsvAppend(row,DoubleToString(f.volume.poc,_Digits));
   CsvAppend(row,DoubleToString(f.volume.val,_Digits));
   CsvAppend(row,DoubleToString(f.volume.vah,_Digits));
   CsvAppend(row,DoubleToString(f.volume.daily_vwap_distance_atr,5));
   CsvAppend(row,DoubleToString(f.volume.london_vwap_distance_atr,5));
   CsvAppend(row,DoubleToString(f.volume.anchored_vwap_distance_atr,5));
   CsvAppend(row,DoubleToString(f.volume.poc_distance_atr,5));
   CsvAppend(row,DoubleToString(f.volume.vwap_slope_atr_per_15m,6));
   CsvAppend(row,f.volume.value_area_state);
   CsvAppend(row,f.volume.source_quality);
   CsvAppend(row,DoubleToString(f.volume.real_volume_fraction,5));
   CsvAppend(row,(f.volume.vwap_reclaim?1:0));
   CsvAppend(row,(f.volume.value_area_reclaim?1:0));
   CsvAppend(row,(f.volume.mean_reversion_path?1:0));
   CsvAppend(row,(f.volume.volume_location_ok?1:0));
   CsvAppend(row,f.volume.score);
   CsvAppend(row,f.location_count);
   CsvAppend(row,f.feature_count);
   CsvAppend(row,f.feature_mask);
   CsvAppend(row,DoubleToString(ref_sl,_Digits));
   CsvAppend(row,DoubleToString(tp1,_Digits));
   CsvAppend(row,DoubleToString(tp2,_Digits));
   CsvAppend(row,DoubleToString(tp3,_Digits));
   CsvAppend(row,(int)InpTargetMode);
   CsvAppend(row,DoubleToString(stp1,_Digits));
   CsvAppend(row,DoubleToString(stp2,_Digits));
   CsvAppend(row,DoubleToString(stp3,_Digits));
   CsvAppend(row,(gates[VAR_CONTROL]?1:0));
   CsvAppend(row,(gates[VAR_PDH_PDL]?1:0));
   CsvAppend(row,(gates[VAR_ASIA_RANGE]?1:0));
   CsvAppend(row,(gates[VAR_SWING_SR]?1:0));
   CsvAppend(row,(gates[VAR_FIB]?1:0));
   CsvAppend(row,(gates[VAR_M5_STRUCTURE_BREAK]?1:0));
   CsvAppend(row,(gates[VAR_SEQ_M1_MSS]?1:0));
   CsvAppend(row,(gates[VAR_SEQ_DISPLACEMENT]?1:0));
   CsvAppend(row,(gates[VAR_SEQ_FVG]?1:0));
   CsvAppend(row,(gates[VAR_SEQ_RETRACE]?1:0));
   CsvAppend(row,(gates[VAR_TRENDLINE]?1:0));
   CsvAppend(row,(gates[VAR_LOCATION_COMPOSITE]?1:0));
   CsvAppend(row,(gates[VAR_SNIPER_COMPOSITE]?1:0));
   CsvAppend(row,(gates[VAR_VWAP_CONTEXT]?1:0));
   CsvAppend(row,(gates[VAR_VOLUME_PROFILE]?1:0));
   CsvAppend(row,(gates[VAR_VOLUME_COMPOSITE]?1:0));
   CsvAppend(row,(gates[VAR_SUPER_SCALPER]?1:0));
   CsvAppend(row,(gates[VAR_SUPER_SCALPER_VOLUME]?1:0));
   CsvAppend(row,ScalperStateName(scalper.state));
   CsvAppend(row,scalper.readiness);
   CsvAppend(row,DoubleToString(scalper.net_edge_r,6));
   CsvAppend(row,scalper.context_score);
   CsvAppend(row,scalper.micro_score);
   CsvAppend(row,scalper.timing_score);
   CsvAppend(row,scalper.execution_score);
   CsvAppend(row,scalper.reason);
   CsvAppend(row,ScalperStateName(volume_scalper.state));
   CsvAppend(row,volume_scalper.readiness);
   CsvAppend(row,DoubleToString(volume_scalper.net_edge_r,6));
   CsvAppend(row,volume_scalper.volume_score);
   CsvAppend(row,volume_scalper.reason);
   CsvWriteLine(h,row);

   FileClose(h);
  }

void WriteTradeEvidence(const int variant,
                        const VirtualTrade &p,
                        const datetime close_time,
                        const double exit_price,
                        const string reason,
                        const double result_r)
  {
   if(!InpWriteTradeEvidence)
      return;

   int h=FileOpen(InpTradeEvidenceFile,
                  FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,
                  ';');
   if(h==INVALID_HANDLE)
      return;

   if(FileSize(h)==0)
     {
      FileWrite(h,
        "research_id","signal_id","variant_id","variant","fold","halfyear","direction","signal_time","open_time","close_time",
        "entry","exit","sl","tp","risk_distance","exit_reason","R","cumulative_R","max_dd_R",
        "gold_rsi","gold_adx","gold_vol_ratio","gold_extension_atr","feature_count","feature_mask");
     }

   FileSeek(h,0,SEEK_END);
   FileWrite(h,
     (long)InpResearchId,p.signal_id,variant,g_stats[variant].name,p.fold,p.halfyear,p.direction,
     TimeToString(p.signal_time,TIME_DATE|TIME_MINUTES),TimeToString(p.open_time,TIME_DATE|TIME_SECONDS),TimeToString(close_time,TIME_DATE|TIME_SECONDS),
     DoubleToString(p.entry,_Digits),DoubleToString(exit_price,_Digits),DoubleToString(p.sl,_Digits),DoubleToString(p.tp,_Digits),DoubleToString(p.risk_distance,_Digits),
     reason,DoubleToString(result_r,6),DoubleToString(g_stats[variant].net_r,6),DoubleToString(g_stats[variant].max_dd_r,6),
     DoubleToString(p.gold_rsi,4),DoubleToString(p.gold_adx,4),DoubleToString(p.gold_vol_ratio,5),DoubleToString(p.gold_extension,5),
     p.feature_count,p.feature_mask);

   FileClose(h);
  }

void WriteEventEvidence(const EventProbe &p,const int horizon_bars,const datetime exit_time,const double exit_price,const double r)
  {
   if(!InpWriteEventEvidence)
      return;

   int h=FileOpen(InpEventEvidenceFile,
                  FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,
                  ';');
   if(h==INVALID_HANDLE)
      return;
   if(FileSize(h)==0)
     {
      FileWrite(h,"research_id","signal_id","variant_id","variant","fold","halfyear","direction",
                  "signal_time","entry_time","horizon_m5_bars","exit_time","entry","exit","risk_distance","forward_R");
     }
   FileSeek(h,0,SEEK_END);
   FileWrite(h,(long)InpResearchId,p.signal_id,p.variant,g_stats[p.variant].name,p.fold,p.halfyear,p.direction,
             TimeToString(p.signal_time,TIME_DATE|TIME_MINUTES),TimeToString(p.open_time,TIME_DATE|TIME_SECONDS),horizon_bars,
             TimeToString(exit_time,TIME_DATE|TIME_SECONDS),DoubleToString(p.entry,_Digits),DoubleToString(exit_price,_Digits),
             DoubleToString(p.risk_distance,_Digits),DoubleToString(r,6));
   FileClose(h);
  }

void UpdatePeriodTradeLabel(const string label,const int variant,const double r)
  {
   int i=GetPeriodStatIndex(label,variant,true);
   g_period_stats[i].trades++;
   g_period_stats[i].net_r+=r;
   if(r>0.0){g_period_stats[i].wins++;g_period_stats[i].gross_win_r+=r;}
   else if(r<0.0){g_period_stats[i].losses++;g_period_stats[i].gross_loss_r+=-r;}
   if(g_period_stats[i].net_r>g_period_stats[i].peak_r)
      g_period_stats[i].peak_r=g_period_stats[i].net_r;
   double dd=g_period_stats[i].peak_r-g_period_stats[i].net_r;
   if(dd>g_period_stats[i].max_dd_r) g_period_stats[i].max_dd_r=dd;
  }

void UpdatePeriodEventLabel(const string label,const int variant,const bool fast,const double r)
  {
   int i=GetPeriodStatIndex(label,variant,true);
   if(fast)
     {
      g_period_stats[i].event_fast_n++;
      g_period_stats[i].event_fast_sum_r+=r;
     }
   else
     {
      g_period_stats[i].event_slow_n++;
      g_period_stats[i].event_slow_sum_r+=r;
     }
  }

//----------------------- Independent Event Engine --------------------
void AddEventProbe(const int variant,const long signal_id,const GoldContext &gold,const MqlTick &tick)
  {
   if(variant<0 || variant>=VARIANT_COUNT || gold.atr<=0.0)
      return;

   EventProbe p;
   ZeroMemory(p);
   p.active=true;
   p.signal_id=signal_id;
   p.variant=variant;
   p.direction=gold.direction;
   p.signal_time=gold.signal_time;
   p.open_time=TimeCurrent();
   p.entry=(gold.direction>0 ? tick.ask+InpVirtualEntrySlippagePoints*_Point
                             : tick.bid-InpVirtualEntrySlippagePoints*_Point);
   p.risk_distance=InpVirtualSL_ATR*gold.atr;
   p.fold=gold.fold;
   p.halfyear=gold.halfyear;
   if(p.entry<=0.0 || p.risk_distance<=0.0)
      return;

   int n=ArraySize(g_probes);
   ArrayResize(g_probes,n+1);
   g_probes[n]=p;
  }

double EventResultR(const EventProbe &p,const MqlTick &tick,double &exit_price)
  {
   exit_price=(p.direction>0 ? tick.bid-InpVirtualExitSlippagePoints*_Point
                             : tick.ask+InpVirtualExitSlippagePoints*_Point);
   double r=((exit_price-p.entry)*p.direction)/p.risk_distance;
   r-=(InpVirtualCommissionPointsRT*_Point)/p.risk_distance;
   return r;
  }

void RecordEventResult(EventProbe &p,const bool fast,const MqlTick &tick,const datetime now)
  {
   double exit_price=0.0;
   double r=EventResultR(p,tick,exit_price);
   int v=p.variant;
   if(fast)
     {
      g_stats[v].event_fast_n++;
      g_stats[v].event_fast_sum_r+=r;
      p.fast_done=true;
      UpdatePeriodEventLabel(p.halfyear,v,true,r);
      UpdatePeriodEventLabel("FOLD_"+p.fold,v,true,r);
      WriteEventEvidence(p,InpEventHorizonFastM5Bars,now,exit_price,r);
     }
   else
     {
      g_stats[v].event_slow_n++;
      g_stats[v].event_slow_sum_r+=r;
      p.slow_done=true;
      UpdatePeriodEventLabel(p.halfyear,v,false,r);
      UpdatePeriodEventLabel("FOLD_"+p.fold,v,false,r);
      WriteEventEvidence(p,InpEventHorizonSlowM5Bars,now,exit_price,r);
     }
  }

void CompactEventProbes()
  {
   int n=ArraySize(g_probes);
   int w=0;
   for(int i=0;i<n;i++)
     {
      if(!g_probes[i].active)
         continue;
      if(w!=i) g_probes[w]=g_probes[i];
      w++;
     }
   if(w<n) ArrayResize(g_probes,w);
  }

void ManageEventProbes()
  {
   int n=ArraySize(g_probes);
   if(n<=0) return;
   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return;
   datetime now=TimeCurrent();

   for(int i=0;i<n;i++)
     {
      if(!g_probes[i].active) continue;
      int bars_since=iBarShift(_Symbol,PERIOD_M5,g_probes[i].open_time,false);
      if(bars_since<0) continue;

      if(!g_probes[i].fast_done && bars_since>=InpEventHorizonFastM5Bars)
         RecordEventResult(g_probes[i],true,tick,now);
      if(!g_probes[i].slow_done && bars_since>=InpEventHorizonSlowM5Bars)
         RecordEventResult(g_probes[i],false,tick,now);
      if(g_probes[i].fast_done && g_probes[i].slow_done)
         g_probes[i].active=false;
     }
   CompactEventProbes();
  }

//----------------------- Virtual Trade Engine ------------------------
void OpenVirtual(const int variant,
                 const long signal_id,
                 const GoldContext &gold,
                 const FeatureContext &f,
                 const MqlTick &tick)
  {
   if(variant<0 || variant>=VARIANT_COUNT || g_stats[variant].pos.active)
      return;

   double risk=InpVirtualSL_ATR*gold.atr;
   if(risk<=0.0)
      return;

   double entry=(gold.direction>0 ? tick.ask+InpVirtualEntrySlippagePoints*_Point
                                  : tick.bid-InpVirtualEntrySlippagePoints*_Point);
   if(entry<=0.0)
      return;

   VirtualTrade p;
   ZeroMemory(p);
   p.active=true;
   p.signal_id=signal_id;
   p.direction=gold.direction;
   p.signal_time=gold.signal_time;
   p.open_time=TimeCurrent();
   p.entry=entry;
   p.risk_distance=risk;
   p.sl=(gold.direction>0 ? entry-risk : entry+risk);
   p.tp=(gold.direction>0 ? entry+InpVirtualRR*risk : entry-InpVirtualRR*risk);
   p.gold_rsi=gold.rsi;
   p.gold_adx=gold.adx;
   p.gold_vol_ratio=gold.vol_ratio;
   p.gold_extension=gold.extension;
   p.feature_count=f.feature_count;
   p.feature_mask=f.feature_mask;
   p.fold=gold.fold;
   p.halfyear=gold.halfyear;

   g_stats[variant].pos=p;
   g_stats[variant].trades++;

   if(InpVerbose)
      PrintFormat("[AUREON V10.3] VIRTUAL OPEN %s | %s | entry=%.5f SL=%.5f TP=%.5f features=%d mask=%d",
                  g_stats[variant].name,(gold.direction>0?"LONG":"SHORT"),p.entry,p.sl,p.tp,f.feature_count,f.feature_mask);
  }

void CloseVirtual(const int variant,
                  const double exit_price,
                  const string reason,
                  const datetime close_time)
  {
   if(variant<0 || variant>=VARIANT_COUNT || !g_stats[variant].pos.active)
      return;

   VirtualTrade p=g_stats[variant].pos;
   if(p.risk_distance<=0.0)
     {
      g_stats[variant].pos.active=false;
      return;
     }

   double r=((exit_price-p.entry)*p.direction)/p.risk_distance;
   double commission_r=(InpVirtualCommissionPointsRT*_Point)/p.risk_distance;
   r-=commission_r;

   g_stats[variant].net_r+=r;
   if(r>0.0)
     {
      g_stats[variant].wins++;
      g_stats[variant].gross_win_r+=r;
     }
   else if(r<0.0)
     {
      g_stats[variant].losses++;
      g_stats[variant].gross_loss_r+=-r;
     }

   if(reason=="TIME")
      g_stats[variant].time_exits++;

   if(g_stats[variant].net_r>g_stats[variant].peak_r)
      g_stats[variant].peak_r=g_stats[variant].net_r;

   double dd=g_stats[variant].peak_r-g_stats[variant].net_r;
   if(dd>g_stats[variant].max_dd_r)
      g_stats[variant].max_dd_r=dd;

   UpdatePeriodTradeLabel(p.halfyear,variant,r);
   UpdatePeriodTradeLabel("FOLD_"+p.fold,variant,r);
   WriteTradeEvidence(variant,p,close_time,exit_price,reason,r);
   g_stats[variant].pos.active=false;

   if(InpVerbose)
      PrintFormat("[AUREON V10.3] VIRTUAL CLOSE %s | %s | R=%.4f | cumR=%.4f",
                  g_stats[variant].name,reason,r,g_stats[variant].net_r);
  }

void ManageVirtualPositions()
  {
   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return;

   datetime now=TimeCurrent();
   double slip=InpVirtualExitSlippagePoints*_Point;

   for(int v=0;v<VARIANT_COUNT;v++)
     {
      if(!g_stats[v].pos.active)
         continue;

      VirtualTrade p=g_stats[v].pos;
      double exit_price=0.0;
      string reason="";

      if(p.direction>0)
        {
         if(tick.bid<=p.sl)
           {
            bool gap=(tick.bid<p.sl-_Point);
            exit_price=MathMin(tick.bid,p.sl)-slip;
            reason=(gap ? "SL_GAP" : "SL");
           }
         else if(tick.bid>=p.tp)
           {
            exit_price=p.tp-slip; // conservative limit-style realization
            reason="TP";
           }
        }
      else
        {
         if(tick.ask>=p.sl)
           {
            bool gap=(tick.ask>p.sl+_Point);
            exit_price=MathMax(tick.ask,p.sl)+slip;
            reason=(gap ? "SL_GAP" : "SL");
           }
         else if(tick.ask<=p.tp)
           {
            exit_price=p.tp+slip;
            reason="TP";
           }
        }

      if(reason=="")
        {
         int bars_since=iBarShift(_Symbol,PERIOD_M5,p.open_time,false);
         if(bars_since>=InpVirtualMaxHoldM5Bars)
           {
            exit_price=(p.direction>0 ? tick.bid-slip : tick.ask+slip);
            reason="TIME";
           }
        }

      if(reason!="")
         CloseVirtual(v,exit_price,reason,now);
     }
  }

//-------------------------- Summary ----------------------------------
double VariantPF(const int v)
  {
   if(v<0 || v>=VARIANT_COUNT) return 0.0;
   if(g_stats[v].gross_loss_r<=0.0)
      return (g_stats[v].gross_win_r>0.0 ? 999.0 : 0.0);
   return g_stats[v].gross_win_r/g_stats[v].gross_loss_r;
  }

double VariantExpectancy(const int v)
  {
   if(v<0 || v>=VARIANT_COUNT || g_stats[v].trades<=0) return 0.0;
   return g_stats[v].net_r/(double)g_stats[v].trades;
  }

double VariantEventFastExp(const int v)
  {
   if(v<0 || v>=VARIANT_COUNT || g_stats[v].event_fast_n<=0) return 0.0;
   return g_stats[v].event_fast_sum_r/(double)g_stats[v].event_fast_n;
  }

double VariantEventSlowExp(const int v)
  {
   if(v<0 || v>=VARIANT_COUNT || g_stats[v].event_slow_n<=0) return 0.0;
   return g_stats[v].event_slow_sum_r/(double)g_stats[v].event_slow_n;
  }

void WriteSummary()
  {
   if(!InpWriteSummary)
      return;

   int h=FileOpen(InpSummaryFile,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,';');
   if(h==INVALID_HANDLE)
      return;

   FileWrite(h,
     "research_id","gold_symbol","variant_id","variant","eligible_signals","portfolio_trades","wins","losses","win_rate","profit_factor",
     "portfolio_expectancy_R","net_R","max_dd_R","recovery_R","time_exits",
     "event_fast_n","event_fast_expectancy_R","event_slow_n","event_slow_expectancy_R",
     "delta_portfolio_exp_vs_control","delta_pf_vs_control","delta_fast_event_exp_vs_control","delta_slow_event_exp_vs_control");

   double control_exp=VariantExpectancy(VAR_CONTROL);
   double control_pf=VariantPF(VAR_CONTROL);
   double control_fast=VariantEventFastExp(VAR_CONTROL);
   double control_slow=VariantEventSlowExp(VAR_CONTROL);

   for(int v=0;v<VARIANT_COUNT;v++)
     {
      double wr=(g_stats[v].trades>0 ? (double)g_stats[v].wins/(double)g_stats[v].trades : 0.0);
      double pf=VariantPF(v);
      double exp=VariantExpectancy(v);
      double fast=VariantEventFastExp(v);
      double slow=VariantEventSlowExp(v);
      double recovery=(g_stats[v].max_dd_r>0.0 ? g_stats[v].net_r/g_stats[v].max_dd_r : 0.0);

      FileWrite(h,(long)InpResearchId,_Symbol,v,g_stats[v].name,g_stats[v].eligible_signals,g_stats[v].trades,g_stats[v].wins,g_stats[v].losses,
                DoubleToString(wr,6),DoubleToString(pf,6),DoubleToString(exp,6),DoubleToString(g_stats[v].net_r,6),
                DoubleToString(g_stats[v].max_dd_r,6),DoubleToString(recovery,6),g_stats[v].time_exits,
                g_stats[v].event_fast_n,DoubleToString(fast,6),g_stats[v].event_slow_n,DoubleToString(slow,6),
                DoubleToString(exp-control_exp,6),DoubleToString(pf-control_pf,6),
                DoubleToString(fast-control_fast,6),DoubleToString(slow-control_slow,6));
     }
   FileClose(h);
  }

void WritePeriodSummary()
  {
   if(!InpWriteSummary)
      return;
   int h=FileOpen(InpPeriodSummaryFile,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,';');
   if(h==INVALID_HANDLE) return;

   FileWrite(h,"research_id","period_or_fold","variant_id","variant","trades","wins","losses","win_rate","profit_factor",
               "portfolio_expectancy_R","net_R","max_dd_R","event_fast_n","event_fast_expectancy_R","event_slow_n","event_slow_expectancy_R");

   for(int i=0;i<ArraySize(g_period_stats);i++)
     {
      PeriodVariantStats p=g_period_stats[i];
      double wr=(p.trades>0 ? (double)p.wins/(double)p.trades : 0.0);
      double pf=(p.gross_loss_r>0.0 ? p.gross_win_r/p.gross_loss_r : (p.gross_win_r>0.0 ? 999.0 : 0.0));
      double exp=(p.trades>0 ? p.net_r/(double)p.trades : 0.0);
      double ef=(p.event_fast_n>0 ? p.event_fast_sum_r/(double)p.event_fast_n : 0.0);
      double es=(p.event_slow_n>0 ? p.event_slow_sum_r/(double)p.event_slow_n : 0.0);
      FileWrite(h,(long)InpResearchId,p.label,p.variant,g_stats[p.variant].name,p.trades,p.wins,p.losses,
                DoubleToString(wr,6),DoubleToString(pf,6),DoubleToString(exp,6),DoubleToString(p.net_r,6),DoubleToString(p.max_dd_r,6),
                p.event_fast_n,DoubleToString(ef,6),p.event_slow_n,DoubleToString(es,6));
     }
   FileClose(h);
  }

void PrintSummary()
  {
   Print("================ AUREON V10 AUTONOMOUS HYPER SCALPER INTELLIGENCE ================");
   for(int v=0;v<VARIANT_COUNT;v++)
     {
      double wr=(g_stats[v].trades>0 ? 100.0*(double)g_stats[v].wins/(double)g_stats[v].trades : 0.0);
      PrintFormat("%d %-20s sig=%I64d trades=%I64d WR=%.2f%% PF=%.3f PortExp=%.4fR E12=%.4fR E36=%.4fR DD=%.2fR",
                  v,g_stats[v].name,g_stats[v].eligible_signals,g_stats[v].trades,wr,VariantPF(v),VariantExpectancy(v),
                  VariantEventFastExp(v),VariantEventSlowExp(v),g_stats[v].max_dd_r);
     }
   Print("=============================================================================");
  }

//----------------------------- Lifecycle -----------------------------
void InitStats()
  {
   string names[VARIANT_COUNT]=
     {
      "CONTROL",
      "PDH_PDL",
      "ASIA_RANGE",
      "SWING_SR",
      "FIB",
      "M5_STRUCTURE_BREAK",
      "SEQ_M1_MSS",
      "SEQ_DISPLACEMENT",
      "SEQ_FVG",
      "SEQ_RETRACE",
      "TRENDLINE_VALID",
      "LOCATION_COMPOSITE",
      "SNIPER_COMPOSITE",
      "VWAP_CONTEXT",
      "VOLUME_PROFILE",
      "VOLUME_COMPOSITE",
      "SUPER_SCALPER",
      "SUPER_SCALPER_VOLUME"
     };

   ArrayResize(g_probes,0);
   ArrayResize(g_period_stats,0);
   for(int i=0;i<VARIANT_COUNT;i++)
     {
      ZeroMemory(g_stats[i]);
      g_stats[i].name=names[i];
      g_stats[i].peak_r=0.0;
      g_stats[i].max_dd_r=0.0;
     }
  }

int OnInit()
  {
   InitStats();

   if(_Period!=PERIOD_M5)
      Print("[AUREON V10.3] WARNING: test/attach on XAUUSD M5.");

   if(InpEnforceGoldSymbol &&
      StringFind(_Symbol,"XAU")<0 && StringFind(_Symbol,"GOLD")<0 && StringFind(_Symbol,"Gold")<0)
     {
      Print("[AUREON V10.3] ERROR: Gold symbol enforcement failed: ",_Symbol);
      return INIT_PARAMETERS_INCORRECT;
     }

   g_is_tester=(bool)MQLInfoInteger(MQL_TESTER);
   g_effective_execution_mode=ResolveEffectiveExecutionMode();

   if(IsLiveAccount() && InpExecutionMode!=EXEC_VIRTUAL_ONLY)
      Print("[AUREON V10.3] LIVE account detected: order execution HARD BLOCKED; running monitor/virtual only.");
   else if(!g_is_tester && InpExecutionMode==EXEC_STRATEGY_TESTER)
      Print("[AUREON V10.3] TESTER mode requested on a chart: safely downgraded to VIRTUAL monitor mode.");
   else if(!g_is_tester && InpExecutionMode==EXEC_DEMO_ARMED && !InpArmDemoExecution)
      Print("[AUREON V10.3] DEMO mode is not armed: safely downgraded to VIRTUAL monitor mode.");

   if(InpGoldRSIPeriod<=0 || InpGoldADXPeriod<=0 || InpGoldATRPeriod<=0 || InpGoldEMAPeriod<=0 ||
      InpGoldSweepLookback<=0 || InpGoldVolMedianBars<=0 || InpVirtualSL_ATR<=0.0 || InpVirtualRR<=0.0 ||
      InpVirtualMaxHoldM5Bars<=0 || InpLevelToleranceATR<0.0 || InpMaxLevelPenetrationATR<0.0 ||
      InpSweepPenetrationATR<InpTouchPenetrationATR || InpMaxLevelPenetrationATR<InpSweepPenetrationATR ||
      InpSwingLookbackBars<20 || InpPivotSpanBars<1 || InpM5StructureLookbackBars<1 || InpM1MSSLookbackBars<1 ||
      InpM1DisplacementBodyATR<=0.0 || InpM1DisplacementBodyRatio<=0.0 || InpM1DisplacementBodyRatio>1.0 ||
      InpM1MinFVG_ATR<0.0 || InpM1FVGRetraceFraction<=0.0 || InpM1FVGRetraceFraction>1.0 ||
      InpLocationCompositeMinFeatures<1 || InpTrendlineMinPivotSeparationBars<1 || InpTrendlineMinAgeBars<1 ||
      InpPreviousTradingDaySearchDays<1 || InpMinTradingDayM5Bars<1 ||
      InpEventHorizonFastM5Bars<1 || InpEventHorizonSlowM5Bars<=InpEventHorizonFastM5Bars ||
      InpRiskPercent<=0.0 || InpMaxRiskPercent<=0.0 || InpRiskPercent>InpMaxRiskPercent || InpFixedLot<=0.0 ||
      InpMaxTradesPerDay<1 || InpMinimumPostExitSeconds<0 ||
      InpLongRiskMultiplier<=0.0 || InpLongRiskMultiplier>1.0 || InpShortRiskMultiplier<=0.0 || InpShortRiskMultiplier>1.0 ||
      InpQualifyingLossStreak<1 || InpQualifyingLossR>=0.0 ||
      InpLossStreakPauseMinutes<0 || InpDailyLossLimitPct<=0.0 || InpEquityDrawdownLimitPct<=0.0 ||
      InpMaxProductionSpreadPoints<=0.0 || InpMaxExpectedSlippagePoints<0.0 || InpExpectedSlippagePointsRT<0.0 || InpMaxTickAgeSeconds<0.0 ||
      InpOrderDeviationPoints<0 || InpAssumedGrossEdgeR<=0.0 || InpMinNetEdgeR<0.0 || InpMinNetEdgeR>=InpAssumedGrossEdgeR ||
      InpArmedReadiness<0 || InpTriggeredReadiness<=InpArmedReadiness || InpTriggeredReadiness>100 ||
      InpProductionSL_ATR<=0.0 || InpProductionTP1_R<=0.0 || InpProductionTP2_R<=InpProductionTP1_R ||
      InpProductionTP3_R<=InpProductionTP2_R || InpProductionMaxHoldM5Bars<1 ||
      InpTP1CloseFraction<0.0 || InpTP2CloseFraction<0.0 || InpTP1CloseFraction+InpTP2CloseFraction>=1.0 ||
      InpVolumeProfileBins<16 || InpVolumeProfileBins>256 || InpValueAreaFraction<=0.0 || InpValueAreaFraction>1.0 ||
      InpMinVolumeM1Bars<5 || InpVWAPSlopeLookbackMinutes<1 || InpVolumeLevelToleranceATR<0.0 ||
      InpVWAPBandSigma1<=0.0 || InpVWAPBandSigma2<=InpVWAPBandSigma1 ||
      InpMinVolumeScoreForExecution<0 || InpMinVolumeScoreForExecution>15 ||
      InpStructuralTP1MinR<=0.0 || InpStructuralTP2MinR<=InpStructuralTP1MinR || InpStructuralTP3MinR<=InpStructuralTP2MinR)
      return INIT_PARAMETERS_INCORRECT;

   if(InpSessionStartUTC<0 || InpSessionStartUTC>23 || InpSessionEndUTCExclusive<1 || InpSessionEndUTCExclusive>24 ||
      InpSessionStartUTC>=InpSessionEndUTCExclusive || InpValidationEndUTC<=InpDevelopmentEndUTC)
      return INIT_PARAMETERS_INCORRECT;

   hGoldATR=iATR(_Symbol,PERIOD_M5,InpGoldATRPeriod);
   hGoldRSI=iRSI(_Symbol,PERIOD_M5,InpGoldRSIPeriod,PRICE_CLOSE);
   hGoldADX=iADXWilder(_Symbol,PERIOD_M5,InpGoldADXPeriod);
   hGoldEMA21=iMA(_Symbol,PERIOD_M5,InpGoldEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   hGoldM1ATR=iATR(_Symbol,PERIOD_M1,InpGoldATRPeriod);
   hGoldEMA55M5=iMA(_Symbol,PERIOD_M5,55,0,MODE_EMA,PRICE_CLOSE);
   hGoldEMA100M5=iMA(_Symbol,PERIOD_M5,100,0,MODE_EMA,PRICE_CLOSE);
   hGoldEMA200M5=iMA(_Symbol,PERIOD_M5,200,0,MODE_EMA,PRICE_CLOSE);
   hGoldEMA100H1=iMA(_Symbol,PERIOD_H1,100,0,MODE_EMA,PRICE_CLOSE);
   hGoldEMA21M1=iMA(_Symbol,PERIOD_M1,21,0,MODE_EMA,PRICE_CLOSE);
   hGoldEMA100M1=iMA(_Symbol,PERIOD_M1,100,0,MODE_EMA,PRICE_CLOSE);

   if(hGoldATR==INVALID_HANDLE || hGoldRSI==INVALID_HANDLE || hGoldADX==INVALID_HANDLE ||
      hGoldEMA21==INVALID_HANDLE || hGoldM1ATR==INVALID_HANDLE || hGoldEMA55M5==INVALID_HANDLE ||
      hGoldEMA100M5==INVALID_HANDLE || hGoldEMA200M5==INVALID_HANDLE || hGoldEMA100H1==INVALID_HANDLE ||
      hGoldEMA21M1==INVALID_HANDLE || hGoldEMA100M1==INVALID_HANDLE)
     {
      Print("[AUREON V10.3] ERROR: indicator initialization failed.");
      return INIT_FAILED;
     }

   g_last_m5_bar=iTime(_Symbol,PERIOD_M5,0);
   RecoverRiskGovernorState();
   ZeroMemory(g_last_scalper);
   ZeroMemory(g_last_volume);
   g_last_scalper.state=SCALPER_WATCH;
   g_last_scalper.reason="INIT";
   RecoverProductionState();

   PrintFormat("[AUREON V10.3] INIT | Gold=%s | TF=M5 | PRODTEST | variants=%d",_Symbol,VARIANT_COUNT);
   PrintFormat("[AUREON V10.3] Control RSI %.0f/%.0f ADX<=%.1f ext>=%.2fATR vol[%.2f,%.2f) UTC %02d-%02d",
               InpGoldRSILongMax,InpGoldRSIShortMin,InpGoldADXMax,InpGoldExtensionATR,
               InpGoldVolRatioMin,InpGoldVolRatioMaxExclusive,InpSessionStartUTC,InpSessionEndUTCExclusive);
   PrintFormat("[AUREON V10.3] Clock base UTC%+d DSTadd=%d rule=%d | DEV<=%s VALID<=%s",
               InpBrokerBaseUTCOffsetHours,InpBrokerDSTAddHours,(int)InpBrokerDSTRule,
               TimeToString(InpDevelopmentEndUTC,TIME_DATE|TIME_MINUTES),TimeToString(InpValidationEndUTC,TIME_DATE|TIME_MINUTES));
   PrintFormat("[AUREON V10.3] RequestedMode=%s EffectiveMode=%s tester=%d demoArm=%d magic=%I64u risk=%.2f%% LIVE=HARD_BLOCK",
               ExecutionModeName(InpExecutionMode),ExecutionModeName(g_effective_execution_mode),
               (g_is_tester?1:0),(InpArmDemoExecution?1:0),InpMagic,InpRiskPercent);
   PrintFormat("[AUREON V10.3] VolumeIntel=%d bins=%d VA=%.0f%% requireForExec=%d minVScore=%d targetMode=%d",
               (InpEnableVolumeIntelligence?1:0),InpVolumeProfileBins,InpValueAreaFraction*100.0,
               (InpRequireVolumeConfirmationForExecution?1:0),InpMinVolumeScoreForExecution,(int)InpTargetMode);

   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   Comment("");
   MqlTick tick={};
   if(SymbolInfoTick(_Symbol,tick) && tick.ask>0.0 && tick.bid>0.0)
     {
      datetime now=TimeCurrent();
      double slip=InpVirtualExitSlippagePoints*_Point;
      for(int v=0;v<VARIANT_COUNT;v++)
        {
         if(g_stats[v].pos.active)
           {
            double exit_price=(g_stats[v].pos.direction>0 ? tick.bid-slip : tick.ask+slip);
            CloseVirtual(v,exit_price,"END_OF_TEST",now);
           }
        }
     }

   PrintSummary();
   WriteSummary();
   WritePeriodSummary();

   if(hGoldATR!=INVALID_HANDLE)   IndicatorRelease(hGoldATR);
   if(hGoldRSI!=INVALID_HANDLE)   IndicatorRelease(hGoldRSI);
   if(hGoldADX!=INVALID_HANDLE)   IndicatorRelease(hGoldADX);
   if(hGoldEMA21!=INVALID_HANDLE) IndicatorRelease(hGoldEMA21);
   if(hGoldM1ATR!=INVALID_HANDLE) IndicatorRelease(hGoldM1ATR);
   if(hGoldEMA55M5!=INVALID_HANDLE) IndicatorRelease(hGoldEMA55M5);
   if(hGoldEMA100M5!=INVALID_HANDLE) IndicatorRelease(hGoldEMA100M5);
   if(hGoldEMA200M5!=INVALID_HANDLE) IndicatorRelease(hGoldEMA200M5);
   if(hGoldEMA100H1!=INVALID_HANDLE) IndicatorRelease(hGoldEMA100H1);
   if(hGoldEMA21M1!=INVALID_HANDLE) IndicatorRelease(hGoldEMA21M1);
   if(hGoldEMA100M1!=INVALID_HANDLE) IndicatorRelease(hGoldEMA100M1);
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0 || !g_prod.active || g_prod.position_id==0) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol) return;
   if((ulong)HistoryDealGetInteger(trans.deal,DEAL_MAGIC)!=InpMagic) return;
   if((ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID)!=g_prod.position_id) return;

   ENUM_DEAL_ENTRY de=(ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
   if(de!=DEAL_ENTRY_OUT && de!=DEAL_ENTRY_OUT_BY) return;

   ulong ticket=0;
   bool still_open=SelectManagedPosition(ticket);
   if(still_open && (ulong)PositionGetInteger(POSITION_IDENTIFIER)==g_prod.position_id) return;

   ProductionState closed=g_prod;
   UpdateLossStreakQuarantine(closed);
   g_last_production_exit=TimeCurrent();
   SaveRiskGovernorState();
   WriteExecutionEvidence("CLOSED_TX",g_last_scalper,closed.signal_id,closed.direction,closed.ticket,0.0,closed.entry,0.0,
                          closed.tp1,closed.tp2,closed.tp3,"DEAL_CONFIRMED_POSITION_CLOSE");
   ClearProductionState();
  }

void OnTick()
  {
   UpdateRiskGovernor();
   ManageProductionPosition();
   ManageVirtualPositions();
   RefreshAutonomousTrendAnchor();
   UpdateMicroEngine();
   UpdateDashboard();

   if(!IsNewM5Bar())
      return;

   // Event probes are independent of the one-position portfolio and settle
   // only at M5 bar boundaries, preserving bar-count horizons across weekends.
   ManageEventProbes();

   int required_bars=InpSwingLookbackBars+InpGoldVolMedianBars+InpGoldSweepLookback+50;
   int min_gold_bars=(required_bars>250 ? required_bars : 250);
   if(Bars(_Symbol,PERIOD_M5)<min_gold_bars || Bars(_Symbol,PERIOD_M1)<500)
      return;

   GoldContext gold;
   if(!EvaluateGoldControl(gold))
      return;

   FeatureContext f;
   BuildFeatureContext(gold,f);
   g_signal_id++;
   g_anchor_valid=true;
   g_anchor_signal_id=g_signal_id;
   g_anchor_gold=gold;
   g_anchor_features=f;
   g_control_anchor_priority_until=TimeCurrent()+600;

   bool gates[VARIANT_COUNT];
   for(int i=0;i<VARIANT_COUNT;i++) gates[i]=false;
   gates[VAR_CONTROL]=true;
   gates[VAR_PDH_PDL]=f.prev_day_ok;
   gates[VAR_ASIA_RANGE]=f.asia_ok;
   gates[VAR_SWING_SR]=f.swing_ok;
   gates[VAR_FIB]=f.fib_ok;
   gates[VAR_M5_STRUCTURE_BREAK]=f.m5_structure_break;
   gates[VAR_SEQ_M1_MSS]=f.seq_mss;
   gates[VAR_SEQ_DISPLACEMENT]=f.seq_displacement;
   gates[VAR_SEQ_FVG]=f.seq_fvg;
   gates[VAR_SEQ_RETRACE]=f.seq_retrace;
   gates[VAR_TRENDLINE]=f.trendline_ok;
   gates[VAR_LOCATION_COMPOSITE]=(f.location_count>=InpLocationCompositeMinFeatures);
   gates[VAR_SNIPER_COMPOSITE]=(f.location_count>=1 && f.seq_mss && f.seq_displacement && f.seq_fvg);
   gates[VAR_VWAP_CONTEXT]=(f.volume.valid && f.volume.vwap_reclaim);
   gates[VAR_VOLUME_PROFILE]=(f.volume.valid && (f.volume.value_area_reclaim || f.volume.mean_reversion_path));
   gates[VAR_VOLUME_COMPOSITE]=(f.volume.valid && f.volume.volume_location_ok && f.volume.score>=InpMinVolumeScoreForExecution);

   MqlTick tick={};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0)
      return;

   ScalperDecision scalper=BuildScalperDecision(gold,f,tick,false);
   ScalperDecision volume_scalper=BuildScalperDecision(gold,f,tick,true);
   gates[VAR_SUPER_SCALPER]=(scalper.state==SCALPER_TRIGGERED);
   gates[VAR_SUPER_SCALPER_VOLUME]=(volume_scalper.state==SCALPER_TRIGGERED);
   ScalperDecision production_scalper;
   if(InpRequireVolumeConfirmationForExecution) production_scalper=volume_scalper;
   else production_scalper=scalper;
   g_last_scalper=production_scalper;
   g_last_volume=f.volume;
   WriteSignalEvidence(g_signal_id,gold,f,gates,scalper,volume_scalper);

   for(int v=0;v<VARIANT_COUNT;v++)
     {
      if(!gates[v]) continue;
      g_stats[v].eligible_signals++;

      // Every eligible signal receives an independent forward-return probe,
      // even when that portfolio already has an open virtual position.
      AddEventProbe(v,g_signal_id,gold,tick);

      if(!g_stats[v].pos.active)
         OpenVirtual(v,g_signal_id,gold,f,tick);
     }

   bool production_gate=(InpRequireVolumeConfirmationForExecution ? gates[VAR_SUPER_SCALPER_VOLUME] : gates[VAR_SUPER_SCALPER]);
   if(production_gate)
      WriteExecutionEvidence("ANCHOR_ARMED",production_scalper,g_signal_id,gold.direction,0,0.0,gold.signal_close,0.0,0.0,0.0,0.0,"WAIT_MICRO_5S");
   else
      WriteExecutionEvidence("DECISION",production_scalper,g_signal_id,gold.direction,0,0.0,gold.signal_close,0.0,0.0,0.0,0.0,production_scalper.reason);

   UpdateDashboard();

   if(InpVerbose)
      PrintFormat("[AUREON V10.3] SIGNAL #%I64d %s %s %s off=%+d | RSI=%.1f ADX=%.1f ext=%.2f vol=%.2f | loc=%d feat=%d mask=%d | PD=%d Asia=%d SR=%d Fib=%d M5=%d MSS=%d DISP=%d FVG=%d RET=%d TL=%d",
                  g_signal_id,(gold.direction>0?"LONG":"SHORT"),gold.fold,gold.halfyear,gold.historical_utc_offset,
                  gold.rsi,gold.adx,gold.extension,gold.vol_ratio,f.location_count,f.feature_count,f.feature_mask,
                  (f.prev_day_ok?1:0),(f.asia_ok?1:0),(f.swing_ok?1:0),(f.fib_ok?1:0),(f.m5_structure_break?1:0),
                  (f.seq_mss?1:0),(f.seq_displacement?1:0),(f.seq_fvg?1:0),(f.seq_retrace?1:0),(f.trendline_ok?1:0));
   if(InpVerbose)
      PrintFormat("[AUREON V10.3] SUPER base=%s/%d volume=%s/%d VScore=%d net=%.4fR VWAP=%.2f POC=%.2f VAL=%.2f VAH=%.2f reason=%s",
                  ScalperStateName(scalper.state),scalper.readiness,ScalperStateName(volume_scalper.state),volume_scalper.readiness,
                  f.volume.score,production_scalper.net_edge_r,f.volume.london_vwap,f.volume.poc,f.volume.val,f.volume.vah,production_scalper.reason);
   if(InpVerbose)
      PrintFormat("[AUREON V10.3] EMA100 state=%s M5=%.2f H1=%.2f slope=%.4fATR sep21/100=%.3fATR stack=%d",
                  EMA100StateName(gold.ema100_state),gold.ema100_m5,gold.ema100_h1,gold.ema100_slope_atr,gold.ema21_100_sep_atr,(gold.ema_stack_aligned?1:0));
  }

// Optimization score is informational only; optimization remains OFF for the
// first evidence run. Unseen-period stability still controls promotion.
double OnTester()
  {
   int v=(InpRequireVolumeConfirmationForExecution ? VAR_SUPER_SCALPER_VOLUME : VAR_SUPER_SCALPER);
   if(g_stats[v].trades<30)
      return -1000.0+(double)g_stats[v].trades;

   double pf=VariantPF(v);
   double exp=VariantExpectancy(v);
   double dd=g_stats[v].max_dd_r;
   double event_exp=VariantEventSlowExp(v);
   return (exp+event_exp)*0.5*MathMin(pf,4.0)*MathSqrt((double)g_stats[v].trades)/(1.0+dd);
  }
//+------------------------------------------------------------------+
