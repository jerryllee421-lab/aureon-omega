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

        [Parameter("Max SL ATR", DefaultValue = 3.0, MinValue = 0.1)]
        public double MaxSlAtr { get; set; }

        [Parameter("SL ATR Buffer", DefaultValue = 0.15, MinValue = 0)]
        public double SlAtrBuffer { get; set; }

        [Parameter("Min Projected Margin %", DefaultValue = 150.0, MinValue = 0)]
        public double MinProjectedMarginPercent { get; set; }

        [Parameter("Max Trade Margin % Equity", DefaultValue = 35.0, MinValue = 0, MaxValue = 100)]
        public double MaxTradeMarginPercent { get; set; }

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
        private bool _zoneValid, _zoneBullish, _zoneTraded;
        private double _zoneLow, _zoneHigh;
        private DateTime _zoneFormed;
        private int _lastScannedBar = -1;

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
            UpdateZoneOnNewBar();
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

        private void UpdateZoneOnNewBar()
        {
            int closed = Bars.Count - 2;
            if (closed < 3 || closed == _lastScannedBar) return;
            _lastScannedBar = closed;

            // Search newest first, matching MT5 V2.12's three-candle FVG scan.
            int oldest = Math.Max(2, closed - 1000);
            for (int i = closed; i >= oldest; i--)
            {
                int middle = i - 1, old = i - 2;
                if (old < 0) break;
                double atr = _atr.Result[i];
                if (atr <= 0) continue;
                double body = Math.Abs(Bars.ClosePrices[middle] - Bars.OpenPrices[middle]);
                double range = Bars.HighPrices[middle] - Bars.LowPrices[middle];
                if (range <= 0 || body < atr * MinBodyAtr || body / range < MinBodyRatio) continue;

                bool bull = Bars.HighPrices[old] < Bars.LowPrices[i] && Bars.ClosePrices[middle] > Bars.OpenPrices[middle];
                bool bear = Bars.LowPrices[old] > Bars.HighPrices[i] && Bars.ClosePrices[middle] < Bars.OpenPrices[middle];
                double gap = bull ? Bars.LowPrices[i] - Bars.HighPrices[old] :
                             bear ? Bars.LowPrices[old] - Bars.HighPrices[i] : 0;
                if ((!bull && !bear) || gap < atr * MinFvgAtr) continue;

                _zoneValid = true;
                _zoneBullish = bull;
                _zoneLow = bull ? Bars.HighPrices[old] : Bars.HighPrices[i];
                _zoneHigh = bull ? Bars.LowPrices[i] : Bars.LowPrices[old];
                _zoneFormed = Bars.OpenTimes[i];
                _zoneTraded = false;
                return;
            }
        }

        private void EvaluateFvgRetest()
        {
            if (!_zoneValid) return;
            double lastClosed = Bars.ClosePrices[Bars.Count - 2];
            if ((_zoneBullish && lastClosed < _zoneLow) || (!_zoneBullish && lastClosed > _zoneHigh))
            {
                _zoneValid = false;
                return;
            }

            double price = _zoneBullish ? Symbol.Ask : Symbol.Bid;
            if (price < _zoneLow || price > _zoneHigh) return;
            if (!CurrentBarRejection(_zoneBullish)) return;
            if (_zoneTraded) return; // certification-safe default; report-matched re-entry is enabled only after parity validation.

            if (_zoneBullish && AllowLong) { TryEnter(TradeType.Buy, _atr.Result.LastValue); _zoneTraded = true; }
            if (!_zoneBullish && AllowShort) { TryEnter(TradeType.Sell, _atr.Result.LastValue); _zoneTraded = true; }
        }

        private bool CurrentBarRejection(bool bullish)
        {
            int i = Bars.Count - 1;
            double range = Bars.HighPrices[i] - Bars.LowPrices[i];
            if (range <= 0) return false;
            double px = bullish ? Symbol.Bid : Symbol.Ask;
            double closePos = (px - Bars.LowPrices[i]) / range;
            return bullish ? closePos >= 0.55 : closePos <= 0.45;
        }

        private void TryEnter(TradeType side, double atr)
        {
            double entry = side == TradeType.Buy ? Symbol.Ask : Symbol.Bid;
            double zoneEdge = side == TradeType.Buy ? _zoneLow : _zoneHigh;
            double slPrice = side == TradeType.Buy ? zoneEdge - atr * SlAtrBuffer : zoneEdge + atr * SlAtrBuffer;
            double stopDistance = Math.Abs(entry - slPrice);
            if (stopDistance <= 0 || stopDistance > atr * MaxSlAtr) { Print("RISK_VETO: SL_DISTANCE"); return; }
            double stopPips = stopDistance / Symbol.PipSize;
            double targetPips = stopPips * RewardRisk;

            double riskMoney = Account.Equity * Math.Min(RiskPercent, HardRiskPercent) / 100.0;
            double volume = Symbol.VolumeForFixedRisk(riskMoney, stopPips);
            volume = Symbol.NormalizeVolumeInUnits(volume, RoundingMode.Down);
            if (volume < Symbol.VolumeInUnitsMin) return;

            double estimatedMargin = Symbol.GetEstimatedMargin(side, volume);
            if (estimatedMargin <= 0) { Print("RISK_VETO: MARGIN_ESTIMATE"); return; }
            if (Account.Equity > 0 && estimatedMargin / Account.Equity * 100.0 > MaxTradeMarginPercent) { Print("RISK_VETO: SINGLE_TRADE_MARGIN"); return; }
            double projectedMarginLevel = estimatedMargin > 0 ? Account.Equity / (Account.Margin + estimatedMargin) * 100.0 : 0;
            if (projectedMarginLevel < MinProjectedMarginPercent) { Print("RISK_VETO: PROJECTED_MARGIN_LEVEL"); return; }

            var result = ExecuteMarketOrder(side, SymbolName, volume, Label, stopPips, targetPips);
            if (!result.IsSuccessful)
                Print("EXECUTION_REJECTED: {0}", result.Error);
            else
                Print("ENTRY_ACCEPTED side={0} volume={1} spreadPips={2:F2}", side, volume, (Symbol.Ask-Symbol.Bid)/Symbol.PipSize);
        }

        private void ManagePosition()
        {
            var p = Positions.Find(Label, SymbolName);
            if (p == null || !p.TakeProfit.HasValue) return;
            double initialRisk = Math.Abs(p.TakeProfit.Value - p.EntryPrice) / RewardRisk;
            if (initialRisk <= 0) return;
            double price = p.TradeType == TradeType.Buy ? Symbol.Bid : Symbol.Ask;
            double rr = (p.TradeType == TradeType.Buy ? price - p.EntryPrice : p.EntryPrice - price) / initialRisk;
            if (rr <= 0) return;

            double? candidate = null;
            if (rr >= 1.0)
                candidate = p.TradeType == TradeType.Buy ? p.EntryPrice + initialRisk * 0.35 : p.EntryPrice - initialRisk * 0.35;
            else if (rr >= 0.5)
                candidate = p.TradeType == TradeType.Buy ? p.EntryPrice + initialRisk * 0.10 : p.EntryPrice - initialRisk * 0.10;

            if (rr >= 1.5)
            {
                double trail = _atr.Result.LastValue * 0.10;
                double t = p.TradeType == TradeType.Buy ? price - trail : price + trail;
                double floor = p.TradeType == TradeType.Buy ? p.EntryPrice + initialRisk * 0.35 : p.EntryPrice - initialRisk * 0.35;
                t = p.TradeType == TradeType.Buy ? Math.Max(t, floor) : Math.Min(t, floor);
                candidate = candidate.HasValue
                    ? (p.TradeType == TradeType.Buy ? Math.Max(candidate.Value, t) : Math.Min(candidate.Value, t))
                    : t;
            }

            if (!candidate.HasValue) return;
            bool better = !p.StopLoss.HasValue ||
                          (p.TradeType == TradeType.Buy ? candidate.Value > p.StopLoss.Value : candidate.Value < p.StopLoss.Value);
            if (!better) return;

            var result = ModifyPosition(p, candidate.Value, p.TakeProfit);
            if (!result.IsSuccessful) Print("SL_MODIFY_REJECTED: {0}", result.Error);
        }
    }
}
