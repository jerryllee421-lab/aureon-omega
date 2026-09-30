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

        [Parameter("Environment", DefaultValue = "demo")]
        public string EnvironmentName { get; set; } = "";

        [Parameter("Execution Enabled", DefaultValue = false)]
        public bool ExecutionEnabled { get; set; }

        [Parameter("Expected Broker", DefaultValue = "Pepperstone")]
        public string ExpectedBroker { get; set; } = "";

        [Parameter("Max Stale Feed Seconds", DefaultValue = 3.0, MinValue = 1.0, MaxValue = 30.0)]
        public double MaxStaleFeedSeconds { get; set; }

        [Parameter("Max Spread Points", DefaultValue = 80.0, MinValue = 0)]
        public double MaxSpreadPoints { get; set; }

        [Parameter("Max Slippage Points", DefaultValue = 35.0, MinValue = 0)]
        public double MaxSlippagePoints { get; set; }

        [Parameter("Canary Run ID", DefaultValue = "V217_CANARY_001")]
        public string CanaryRunId { get; set; } = "";

        [Parameter("Canary Max Completed Trades", DefaultValue = 5, MinValue = 1, MaxValue = 5)]
        public int CanaryMaxCompletedTrades { get; set; }

        [Parameter("Max Trades / Day", DefaultValue = 1000, MinValue = 1)]
        public int MaxTradesPerDay { get; set; }

        [Parameter("One Trade/FVG", DefaultValue = false)]
        public bool OneTradePerFvg { get; set; }

        [Parameter("Allow Long", DefaultValue = true)]
        public bool AllowLong { get; set; }

        [Parameter("Allow Short", DefaultValue = true)]
        public bool AllowShort { get; set; }

        private AverageTrueRange _atr = null!;
        private double _dayStartEquity;
        private double _peakEquity;
        private DateTime _day;
        private const string Label = "AUREON_PRIME_GOLD_CLOUD";
        private bool _zoneValid, _zoneBullish, _zoneTraded;
        private double _zoneLow, _zoneHigh;
        private DateTime _zoneFormed;
        private int _lastScannedBar = -1;
        private int _tradesToday;
        private bool _riskHalt;
        private double _initialRiskPrice;
        private double _entryPrice;
        private double _maxMfeR;
        private double _maxMaeR;
        private DateTime _lastTickSeen = DateTime.MinValue;
        private bool _staleData = true;
        private bool _preflightPassed;
        private bool _reconciliationFailed;
        private string _activeTradeIntentId = "";

        private sealed class TradeIntent
        {
            public string Id { get; }
            public DateTime Timestamp { get; }
            public string AccountHash { get; }
            public TradeType Side { get; }
            public double EntryReference { get; }
            public double Bid { get; }
            public double Ask { get; }
            public double SpreadPoints { get; }
            public double ZoneLow { get; }
            public double ZoneHigh { get; }
            public double Atr { get; }
            public double StopLoss { get; }
            public double TakeProfit { get; }
            public double RiskPrice { get; }
            public double RequestedVolume { get; }
            public double ExpectedRiskMoney { get; }
            public double MarketDataAgeSeconds { get; }
            public int CanaryTradeNumber { get; }

            public TradeIntent(string id, DateTime timestamp, string accountHash, TradeType side,
                double entryReference, double bid, double ask, double spreadPoints, double zoneLow,
                double zoneHigh, double atr, double stopLoss, double takeProfit, double riskPrice,
                double requestedVolume, double expectedRiskMoney, double marketDataAgeSeconds,
                int canaryTradeNumber)
            {
                Id = id;
                Timestamp = timestamp;
                AccountHash = accountHash;
                Side = side;
                EntryReference = entryReference;
                Bid = bid;
                Ask = ask;
                SpreadPoints = spreadPoints;
                ZoneLow = zoneLow;
                ZoneHigh = zoneHigh;
                Atr = atr;
                StopLoss = stopLoss;
                TakeProfit = takeProfit;
                RiskPrice = riskPrice;
                RequestedVolume = requestedVolume;
                ExpectedRiskMoney = expectedRiskMoney;
                MarketDataAgeSeconds = marketDataAgeSeconds;
                CanaryTradeNumber = canaryTradeNumber;
            }
        }

        protected override void OnStart()
        {
            Print("STATE|BOOT|strategy=V2.17|executionEnabled={0}", ExecutionEnabled);

            if (!string.Equals(EnvironmentName, "demo", StringComparison.OrdinalIgnoreCase))
            {
                Print("STATE|HALTED|reason=ENV_NOT_DEMO");
                Stop();
                return;
            }

            if (Account.IsLive)
            {
                Print("STATE|HALTED|reason=LIVE_ACCOUNT");
                Stop();
                return;
            }

            if (string.IsNullOrWhiteSpace(ExpectedBroker) ||
                string.IsNullOrWhiteSpace(Account.BrokerName) ||
                Account.BrokerName.IndexOf(ExpectedBroker, StringComparison.OrdinalIgnoreCase) < 0)
            {
                Print("STATE|HALTED|reason=BROKER_MISMATCH|broker={0}|expectedContains={1}", Account.BrokerName, ExpectedBroker);
                Stop();
                return;
            }

            if (!SymbolName.Contains("XAU", StringComparison.OrdinalIgnoreCase))
            {
                Print("STATE|HALTED|reason=NON_XAU_SYMBOL|symbol={0}", SymbolName);
                Stop();
                return;
            }

            _atr = Indicators.AverageTrueRange(AtrPeriod, MovingAverageType.Exponential);
            Positions.Closed += OnPositionClosed;
            Timer.Start(1);
            _day = Server.Time.Date;
            _dayStartEquity = Account.Equity;
            _peakEquity = Account.Equity;

            Print("STATE|ACCOUNT_VERIFIED|environment=demo|isLive={0}|broker={1}|accountHash={2}|balance={3:F2}|equity={4:F2}|freeMargin={5:F2}",
                Account.IsLive, Account.BrokerName, SafeAccountHash(), Account.Balance, Account.Equity, Account.FreeMargin);
            Print("STATE|SYMBOL_RESOLVED|symbol={0}|digits={1}|pipSize={2}|tickSize={3}|minVolume={4}|maxVolume={5}|stepVolume={6}|bid={7}|ask={8}",
                SymbolName, Symbol.Digits, Symbol.PipSize, Symbol.TickSize, Symbol.VolumeInUnitsMin,
                Symbol.VolumeInUnitsMax, Symbol.VolumeInUnitsStep, Symbol.Bid, Symbol.Ask);

            RecoverRuntimeState();
            RecoverCanaryState();

            if (_reconciliationFailed)
            {
                _riskHalt = true;
                Print("STATE|HALTED|reason=RECONCILIATION_FAIL");
                return;
            }

            _preflightPassed = true;
            Print("STATE|READY|executionEnabled={0}|canaryCompleted={1}|canaryLimit={2}", ExecutionEnabled, _canaryCompletedTrades, CanaryMaxCompletedTrades);
        }

        protected override void OnTimer()
        {
            if (_lastTickSeen == DateTime.MinValue)
            {
                _staleData = true;
                return;
            }

            _staleData = (Server.Time - _lastTickSeen).TotalSeconds > MaxStaleFeedSeconds;
        }

        private string SafeAccountHash()
        {
            var value = Account.Number.ToString();
            unchecked
            {
                uint hash = 2166136261;
                foreach (char c in value)
                {
                    hash ^= c;
                    hash *= 16777619;
                }
                return hash.ToString("X8");
            }
        }

        private string ExtractTradeIntentId(string comment)
        {
            if (string.IsNullOrWhiteSpace(comment)) return "";
            string prefix = CanaryRunId + "|";
            return comment.StartsWith(prefix, StringComparison.Ordinal) ? comment.Substring(prefix.Length) : "";
        }

        private int CountTaggedPendingOrders()
        {
            int count = 0;
            foreach (var order in PendingOrders)
            {
                if (order.Label == Label && order.SymbolName == SymbolName)
                    count++;
            }
            return count;
        }

        private void RecoverRuntimeState()
        {
            var positions = Positions.FindAll(Label, SymbolName);
            int pending = CountTaggedPendingOrders();

            if (positions.Length > 1 || pending > 0)
            {
                _reconciliationFailed = true;
                Print("STATE|RECONCILIATION_FAIL|reason=UNEXPECTED_BROKER_STATE|positions={0}|pendingOrders={1}", positions.Length, pending);
                return;
            }

            if (positions.Length == 1)
            {
                var p = positions[0];
                if (!p.StopLoss.HasValue || !p.TakeProfit.HasValue)
                {
                    _reconciliationFailed = true;
                    Print("STATE|RECONCILIATION_FAIL|reason=PROTECTION_MISSING|positionId={0}", p.Id);
                    return;
                }

                _entryPrice = p.EntryPrice;
                _initialRiskPrice = Math.Abs(p.TakeProfit.Value - p.EntryPrice) / RewardRisk;
                _activeTradeIntentId = ExtractTradeIntentId(p.Comment);
                if (string.IsNullOrWhiteSpace(_activeTradeIntentId))
                {
                    _reconciliationFailed = true;
                    Print("STATE|RECONCILIATION_FAIL|reason=TRADE_INTENT_MISSING|positionId={0}", p.Id);
                    return;
                }

                Print("STATE|SYNCING|positionId={0}|tradeIntentId={1}|entry={2}|stop={3}|takeProfit={4}",
                    p.Id, _activeTradeIntentId, p.EntryPrice, p.StopLoss, p.TakeProfit);
            }

            UpdateZoneOnNewBar();
            Print("STATE|RECONCILED|positions={0}|pendingOrders={1}", positions.Length, pending);
        }

        private int _canaryCompletedTrades;
        private bool _canaryComplete;

        private void RecoverCanaryState()
        {
            if (string.IsNullOrWhiteSpace(CanaryRunId))
            {
                Print("BLOCKED: Canary Run ID must be non-empty.");
                _canaryComplete = true;
                return;
            }

            _canaryCompletedTrades = 0;
            foreach (var trade in History.FindAll(Label, SymbolName))
            {
                string comment = trade.Comment ?? "";
                if (string.Equals(comment, CanaryRunId, StringComparison.Ordinal) ||
                    comment.StartsWith(CanaryRunId + "|", StringComparison.Ordinal))
                    _canaryCompletedTrades++;
            }

            _canaryComplete = _canaryCompletedTrades >= CanaryMaxCompletedTrades;
            Print("CERTIFICATION|CANARY_RECOVERY|runId={0}|completed={1}|limit={2}|blocked={3}",
                CanaryRunId, _canaryCompletedTrades, CanaryMaxCompletedTrades, _canaryComplete);
            if (_canaryComplete)
                Print("STATE|HALTED|reason=CANARY_LIMIT_REACHED|completed={0}", _canaryCompletedTrades);
        }

        private void OnPositionClosed(PositionClosedEventArgs args)
        {
            var p = args.Position;
            if (p.Label != Label || p.SymbolName != SymbolName) return;

            double signedPriceMove = p.Pips * Symbol.PipSize;
            double closePrice = p.TradeType == TradeType.Buy
                ? p.EntryPrice + signedPriceMove
                : p.EntryPrice - signedPriceMove;
            double realizedR = _initialRiskPrice > 0 ? signedPriceMove / _initialRiskPrice : 0;
            double holdingSeconds = Math.Max(0, (Server.Time - p.EntryTime).TotalSeconds);

            var history = History.FindByPositionId(p.Id);
            bool reconciled = history != null && history.Length > 0;
            string tradeIntentId = string.IsNullOrWhiteSpace(_activeTradeIntentId)
                ? ExtractTradeIntentId(p.Comment)
                : _activeTradeIntentId;

            Print("TELEMETRY|CLOSE|time={0:o}|tradeIntentId={1}|positionId={2}|side={3}|entry={4}|closeDerived={5}|pips={6}|gross={7}|net={8}|realizedR={9:F4}|mfeR={10:F4}|maeR={11:F4}|holdingSeconds={12:F1}|reason={13}",
                Server.Time, tradeIntentId, p.Id, p.TradeType, p.EntryPrice, closePrice, p.Pips,
                p.GrossProfit, p.NetProfit, realizedR, _maxMfeR, _maxMaeR, holdingSeconds, args.Reason);

            _canaryCompletedTrades++;
            Print("STATE|RECONCILED|tradeIntentId={0}|positionId={1}|result={2}|completed={3}",
                tradeIntentId, p.Id, reconciled ? "PASS" : "FAIL", _canaryCompletedTrades);

            if (!reconciled)
            {
                _reconciliationFailed = true;
                _riskHalt = true;
                Print("STATE|HALTED|reason=RECONCILIATION_FAIL|positionId={0}", p.Id);
            }

            _initialRiskPrice = 0;
            _entryPrice = 0;
            _maxMfeR = 0;
            _maxMaeR = 0;
            _activeTradeIntentId = "";

            if (_canaryCompletedTrades >= CanaryMaxCompletedTrades)
            {
                _canaryComplete = true;
                _riskHalt = true;
                Print("CERTIFICATION|CANARY_COMPLETE|completed={0}|limit={1}|halt_reason=CANARY_LIMIT_REACHED|action=BLOCK_NEW_ENTRIES",
                    _canaryCompletedTrades, CanaryMaxCompletedTrades);
            }
        }

        protected override void OnTick()
        {
            _lastTickSeen = Server.Time;
            _staleData = false;

            RefreshRiskState();
            ManagePosition();
            UpdateZoneOnNewBar();

            if (!ExecutionEnabled) return;
            if (!_preflightPassed || _canaryComplete) return;
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
                _tradesToday = 0;
                _riskHalt = false;
            }
            if (Account.Equity > _peakEquity) _peakEquity = Account.Equity;
        }

        private bool RiskGovernorAllowsEntry()
        {
            if (!_preflightPassed || _riskHalt || _reconciliationFailed || _canaryComplete) return false;

            if (!string.Equals(EnvironmentName, "demo", StringComparison.OrdinalIgnoreCase) || Account.IsLive)
            {
                _riskHalt = true;
                Print("STATE|HALTED|reason=DEMO_BOUNDARY_BREACH");
                return false;
            }

            if (Account.BrokerName.IndexOf(ExpectedBroker, StringComparison.OrdinalIgnoreCase) < 0)
            {
                _riskHalt = true;
                Print("STATE|HALTED|reason=BROKER_MISMATCH");
                return false;
            }

            if (_staleData || _lastTickSeen == DateTime.MinValue ||
                (Server.Time - _lastTickSeen).TotalSeconds > MaxStaleFeedSeconds)
            {
                Print("RISK_VETO: STALE_DATA");
                return false;
            }

            if (!Symbol.MarketHours.IsOpened())
                return false;

            if (CountTaggedPendingOrders() > 0)
            {
                _reconciliationFailed = true;
                _riskHalt = true;
                Print("STATE|HALTED|reason=UNEXPECTED_PENDING_ORDER");
                return false;
            }

            if (_tradesToday >= MaxTradesPerDay) return false;
            if (_dayStartEquity > 0 && 100.0 * (_dayStartEquity - Account.Equity) / _dayStartEquity >= DailyLossPercent)
            { _riskHalt = true; Print("RISK_HALT: DAILY_LOSS"); return false; }
            if (_peakEquity > 0 && 100.0 * (_peakEquity - Account.Equity) / _peakEquity >= MaxDrawdownPercent)
            { _riskHalt = true; Print("RISK_HALT: DRAWDOWN"); return false; }

            var spreadPips = (Symbol.Ask - Symbol.Bid) / Symbol.PipSize;
            var spreadPoints = (Symbol.Ask - Symbol.Bid) / Symbol.TickSize;
            if (spreadPips > MaxSpreadPips || spreadPoints > MaxSpreadPoints)
            {
                Print("RISK_VETO: SPREAD|pips={0:F2}|points={1:F2}", spreadPips, spreadPoints);
                return false;
            }

            if (_canaryCompletedTrades >= CanaryMaxCompletedTrades)
            {
                _canaryComplete = true;
                _riskHalt = true;
                Print("STATE|HALTED|reason=CANARY_LIMIT_REACHED|completed={0}", _canaryCompletedTrades);
                return false;
            }

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
            if (OneTradePerFvg && _zoneTraded) return;

            if (_zoneBullish && AllowLong) TryEnter(TradeType.Buy, _atr.Result.LastValue);
            if (!_zoneBullish && AllowShort) TryEnter(TradeType.Sell, _atr.Result.LastValue);
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
            if (!RiskGovernorAllowsEntry()) return;

            double entry = side == TradeType.Buy ? Symbol.Ask : Symbol.Bid;
            double zoneEdge = side == TradeType.Buy ? _zoneLow : _zoneHigh;
            double slPrice = side == TradeType.Buy ? zoneEdge - atr * SlAtrBuffer : zoneEdge + atr * SlAtrBuffer;
            double stopDistance = Math.Abs(entry - slPrice);
            if (stopDistance <= 0 || stopDistance > atr * MaxSlAtr)
            {
                Print("RISK_VETO: SL_DISTANCE");
                return;
            }

            double stopPips = stopDistance / Symbol.PipSize;
            double targetPips = stopPips * RewardRisk;
            double tpPrice = side == TradeType.Buy
                ? entry + targetPips * Symbol.PipSize
                : entry - targetPips * Symbol.PipSize;

            double riskMoney = Account.Equity * Math.Min(RiskPercent, HardRiskPercent) / 100.0;
            double volume = Symbol.VolumeForFixedRisk(riskMoney, stopPips);
            volume = Symbol.NormalizeVolumeInUnits(volume, RoundingMode.Down);
            if (volume < Symbol.VolumeInUnitsMin || volume > Symbol.VolumeInUnitsMax)
            {
                Print("RISK_VETO: VOLUME|volume={0}|min={1}|max={2}", volume, Symbol.VolumeInUnitsMin, Symbol.VolumeInUnitsMax);
                return;
            }

            double estimatedMargin = Symbol.GetEstimatedMargin(side, volume);
            if (estimatedMargin <= 0 || estimatedMargin > Account.FreeMargin)
            {
                Print("RISK_VETO: MARGIN_ESTIMATE|estimated={0}|free={1}", estimatedMargin, Account.FreeMargin);
                return;
            }
            if (Account.Equity > 0 && estimatedMargin / Account.Equity * 100.0 > MaxTradeMarginPercent)
            {
                Print("RISK_VETO: SINGLE_TRADE_MARGIN");
                return;
            }
            double projectedMarginLevel = estimatedMargin > 0
                ? Account.Equity / (Account.Margin + estimatedMargin) * 100.0
                : 0;
            if (projectedMarginLevel < MinProjectedMarginPercent)
            {
                Print("RISK_VETO: PROJECTED_MARGIN_LEVEL");
                return;
            }

            double dataAgeSeconds = _lastTickSeen == DateTime.MinValue
                ? double.PositiveInfinity
                : Math.Max(0, (Server.Time - _lastTickSeen).TotalSeconds);
            string intentId = CanaryRunId + "-" + (_canaryCompletedTrades + 1).ToString("D2") + "-" + Guid.NewGuid().ToString("N");
            var intent = new TradeIntent(
                intentId, Server.Time, SafeAccountHash(), side, entry, Symbol.Bid, Symbol.Ask,
                (Symbol.Ask - Symbol.Bid) / Symbol.TickSize, _zoneLow, _zoneHigh, atr, slPrice,
                tpPrice, stopDistance, volume, riskMoney, dataAgeSeconds, _canaryCompletedTrades + 1);

            Print("STATE|TRADE_INTENT|trade_intent_id={0}|strategy=V2.17|time={1:o}|accountHash={2}|symbol={3}|direction={4}|entryReference={5}|bid={6}|ask={7}|spreadPoints={8:F2}|fvgLow={9}|fvgHigh={10}|atr={11}|sl={12}|tp={13}|riskPrice={14}|riskR=1.0|requestedVolume={15}|expectedRiskMoney={16:F2}|marketDataAgeSeconds={17:F3}|canaryTradeNumber={18}",
                intent.Id, intent.Timestamp, intent.AccountHash, SymbolName, intent.Side, intent.EntryReference,
                intent.Bid, intent.Ask, intent.SpreadPoints, intent.ZoneLow, intent.ZoneHigh, intent.Atr,
                intent.StopLoss, intent.TakeProfit, intent.RiskPrice, intent.RequestedVolume,
                intent.ExpectedRiskMoney, intent.MarketDataAgeSeconds, intent.CanaryTradeNumber);

            double marketRangePips = MaxSlippagePoints * Symbol.TickSize / Symbol.PipSize;
            string comment = CanaryRunId + "|" + intent.Id;
            Print("STATE|ORDER_SUBMITTED|tradeIntentId={0}|basePrice={1}|marketRangePips={2:F4}|maxSlippagePoints={3:F2}",
                intent.Id, entry, marketRangePips, MaxSlippagePoints);

            var result = ExecuteMarketRangeOrder(side, SymbolName, volume, marketRangePips, entry, Label, stopPips, targetPips, comment);
            if (!result.IsSuccessful)
            {
                Print("STATE|ORDER_REJECTED|tradeIntentId={0}|error={1}", intent.Id, result.Error);
                return;
            }

            var position = result.Position;
            if (position == null)
            {
                _reconciliationFailed = true;
                _riskHalt = true;
                Print("STATE|HALTED|reason=ACK_WITHOUT_POSITION|tradeIntentId={0}", intent.Id);
                return;
            }

            double actual = position.EntryPrice;
            double slippagePoints = Math.Abs(actual - entry) / Symbol.TickSize;
            string orderId = position.Deals.Count > 0
                ? position.Deals[position.Deals.Count - 1].OrderId.ToString()
                : "NA";

            _zoneTraded = true;
            _tradesToday++;
            _entryPrice = actual;
            _initialRiskPrice = stopDistance;
            _maxMfeR = 0;
            _maxMaeR = 0;
            _activeTradeIntentId = intent.Id;

            Print("STATE|ORDER_ACK|tradeIntentId={0}|positionId={1}|orderId={2}", intent.Id, position.Id, orderId);
            Print("STATE|FILLED|tradeIntentId={0}|positionId={1}|orderId={2}|requestedPrice={3}|actualFill={4}|requestedVolume={5}|actualVolume={6}|spreadPoints={7:F2}|slippagePoints={8:F2}|sl={9}|tp={10}|direction={11}|fvgLow={12}|fvgHigh={13}",
                intent.Id, position.Id, orderId, entry, actual, volume, position.VolumeInUnits,
                intent.SpreadPoints, slippagePoints, position.StopLoss, position.TakeProfit, side, _zoneLow, _zoneHigh);

            if (slippagePoints > MaxSlippagePoints + 0.0001)
            {
                _reconciliationFailed = true;
                _riskHalt = true;
                Print("STATE|HALTED|reason=SLIPPAGE_BREACH|tradeIntentId={0}|observedPoints={1:F2}|limitPoints={2:F2}",
                    intent.Id, slippagePoints, MaxSlippagePoints);
            }
        }

        private void ManagePosition()
        {
            var p = Positions.Find(Label, SymbolName);
            if (p == null || !p.TakeProfit.HasValue) return;
            if (_initialRiskPrice > 0)
            {
                double mark = p.TradeType == TradeType.Buy ? Symbol.Bid : Symbol.Ask;
                double move = p.TradeType == TradeType.Buy ? mark - _entryPrice : _entryPrice - mark;
                double er = move / _initialRiskPrice;
                if (er > _maxMfeR) _maxMfeR = er;
                if (er < 0 && -er > _maxMaeR) _maxMaeR = -er;
            }
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

            var result = p.ModifyStopLossPrice(candidate.Value);
            if (!result.IsSuccessful) Print("SL_MODIFY_REJECTED: {0}", result.Error);
        }
    }
}
