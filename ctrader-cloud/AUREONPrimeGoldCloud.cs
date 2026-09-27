using System;
using cAlgo.API;
using cAlgo.API.Indicators;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class AUREONPrimeGoldCloud : Robot
    {
        [Parameter("Risk %", DefaultValue = 1.0, MinValue = 0.1, MaxValue = 2.0)]
        public double RiskPercent { get; set; }

        [Parameter("Hard Effective Risk %", DefaultValue = 1.25, MinValue = 0.1, MaxValue = 2.0)]
        public double HardRiskPercent { get; set; }

        [Parameter("Reward/Risk", DefaultValue = 30.0, MinValue = 1.0)]
        public double RewardRisk { get; set; }

        [Parameter("ATR Period", DefaultValue = 14, MinValue = 2)]
        public int AtrPeriod { get; set; }

        [Parameter("Min FVG ATR", DefaultValue = 0.15, MinValue = 0)]
        public double MinFvgAtr { get; set; }

        [Parameter("Min Body ATR", DefaultValue = 0.50, MinValue = 0)]
        public double MinBodyAtr { get; set; }

        [Parameter("Min Body Ratio", DefaultValue = 0.60, MinValue = 0, MaxValue = 1)]
        public double MinBodyRatio { get; set; }

        [Parameter("Max Spread (pips)", DefaultValue = 8.0, MinValue = 0)]
        public double MaxSpreadPips { get; set; }

        [Parameter("Daily Loss %", DefaultValue = 3.0, MinValue = 0)]
        public double DailyLossPercent { get; set; }

        [Parameter("Max Drawdown %", DefaultValue = 6.0, MinValue = 0)]
        public double MaxDrawdownPercent { get; set; }

        [Parameter("Allow Long", DefaultValue = true)]
        public bool AllowLong { get; set; }

        [Parameter("Allow Short", DefaultValue = true)]
        public bool AllowShort { get; set; }

        private AverageTrueRange _atr;
        private double _dayStartEquity;
        private double _peakEquity;
        private DateTime _day;
        private const string Label = "AUREON_PRIME_GOLD_CLOUD";

        protected override void OnStart()
        {
            if (!SymbolName.Contains("XAU", StringComparison.OrdinalIgnoreCase))
            {
                Print("BLOCKED: XAUUSD-only executor.");
                Stop();
                return;
            }
            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Exponential);
            _day = Server.Time.Date;
            _dayStartEquity = Account.Equity;
            _peakEquity = Account.Equity;
            Print("AUREON PRIME Cloud executor started. DEMO certification build; LIVE use is not certified.");
        }

        protected override void OnTick()
        {
            RefreshRiskState();
            ManagePosition();
            if (!RiskGovernorAllowsEntry()) return;
            if (Positions.Find(Label, SymbolName) != null) return;
            EvaluateFvgRetest();
        }

        private void RefreshRiskState()
        {
            if (Server.Time.Date != _day)
            {
                _day = Server.Time.Date;
                _dayStartEquity = Account.Equity;
            }
            if (Account.Equity > _peakEquity) _peakEquity = Account.Equity;
        }

        private bool RiskGovernorAllowsEntry()
        {
            if (_dayStartEquity > 0 && 100.0 * (_dayStartEquity - Account.Equity) / _dayStartEquity >= DailyLossPercent)
                return false;
            if (_peakEquity > 0 && 100.0 * (_peakEquity - Account.Equity) / _peakEquity >= MaxDrawdownPercent)
                return false;
            var spreadPips = (Symbol.Ask - Symbol.Bid) / Symbol.PipSize;
            if (spreadPips > MaxSpreadPips) return false;
            return true;
        }

        private void EvaluateFvgRetest()
        {
            // Parity-safe first implementation: closed bars only.
            // MT5 V2.12 exact entry semantics remain the authority until parity tests pass.
            int i = Bars.Count - 2;
            if (i < 3) return;

            double atr = _atr.Result[i];
            if (atr <= 0) return;

            double body = Math.Abs(Bars.ClosePrices[i - 1] - Bars.OpenPrices[i - 1]);
            double range = Bars.HighPrices[i - 1] - Bars.LowPrices[i - 1];
            if (range <= 0 || body < MinBodyAtr * atr || body / range < MinBodyRatio) return;

            bool bullish = Bars.LowPrices[i] > Bars.HighPrices[i - 2];
            bool bearish = Bars.HighPrices[i] < Bars.LowPrices[i - 2];
            if (!bullish && !bearish) return;

            double gap = bullish ? Bars.LowPrices[i] - Bars.HighPrices[i - 2] : Bars.LowPrices[i - 2] - Bars.HighPrices[i];
            if (gap < MinFvgAtr * atr) return;

            double zoneLow = bullish ? Bars.HighPrices[i - 2] : Bars.HighPrices[i];
            double zoneHigh = bullish ? Bars.LowPrices[i] : Bars.LowPrices[i - 2];
            double price = bullish ? Symbol.Ask : Symbol.Bid;
            if (price < zoneLow || price > zoneHigh) return;

            if (bullish && AllowLong) TryEnter(TradeType.Buy, atr);
            if (bearish && AllowShort) TryEnter(TradeType.Sell, atr);
        }

        private void TryEnter(TradeType side, double atr)
        {
            double entry = side == TradeType.Buy ? Symbol.Ask : Symbol.Bid;
            double stopDistance = Math.Max(atr * 0.15, Symbol.PipSize);
            double stopPips = stopDistance / Symbol.PipSize;
            double targetPips = stopPips * RewardRisk;

            double riskMoney = Account.Equity * Math.Min(RiskPercent, HardRiskPercent) / 100.0;
            double volume = Symbol.VolumeForFixedRisk(riskMoney, stopPips);
            volume = Symbol.NormalizeVolumeInUnits(volume, RoundingMode.Down);
            if (volume < Symbol.VolumeInUnitsMin) return;

            var result = ExecuteMarketOrder(side, SymbolName, volume, Label, stopPips, targetPips);
            if (!result.IsSuccessful)
                Print("EXECUTION_REJECTED: {0}", result.Error);
            else
                Print("ENTRY_ACCEPTED side={0} volume={1} spreadPips={2:F2}", side, volume, (Symbol.Ask-Symbol.Bid)/Symbol.PipSize);
        }

        private void ManagePosition()
        {
            // Deliberately minimal until exact V2.12 profit-lock/trailing semantics are ported and parity-tested.
            // Broker-side SL/TP remain mandatory on every entry.
        }
    }
}
