from __future__ import annotations

"""Generate and rank deterministic ASTRA MT5 design-of-experiments presets.

This is deliberately staged. It screens one parameter family at a time from a
known trade-producing diagnostic baseline, then combines promising deltas in a
separate cross-test stage. That reduces brute-force overfit while still testing
all material strategy geometry, execution, exit, session, and risk inputs.
"""

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path


def scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def read_set(path: Path):
    order=[]
    rows={}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if not line or "=" not in line:
            continue
        key,rest=line.split("=",1)
        parts=rest.split("||")
        order.append(key)
        rows[key]=parts
    return order,rows


def write_set(path: Path, order, rows, changes, csv_name, magic):
    local=deepcopy(rows)
    keys=list(order)
    def setv(k,v):
        sv=scalar(v)
        if k in local:
            p=local[k]
            if not p:
                p=[sv]
            else:
                p[0]=sv
            local[k]=p
        else:
            local[k]=[sv,sv,"0",sv,"N"]
            keys.append(k)
    for k,v in changes.items():
        setv(k,v)
    setv("InpMagic",magic)
    setv("InpCSVFile",csv_name)
    path.parent.mkdir(parents=True,exist_ok=True)
    lines=[k+"="+"||".join(local[k]) for k in keys]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")


DISCOVERY_BASE={
    "InpLongEnabled":True,
    "InpShortEnabled":True,
    "InpClosedCandleAuthority":True,
    "InpVisualDebug":False,
    "InpCSVLogging":True,
    "InpATRPeriod":14,
    "InpRequireH4Bias":False,
    "InpRequireH1Alignment":False,
    "InpRequireDIDirection":True,
    "InpLiquidityLookback":20,
    "InpEqualLevelATR":0.10,
    "InpUseRollingLiquidity":True,
    "InpSweepMinATR":0.05,
    "InpSweepMaxATR":1.00,
    "InpMinReclaimBody":0.30,
    "InpRequireDirectionalReclaim":False,
    "InpMSSLookback":5,
    "InpRequireClosedMSS":True,
    "InpMSSMaxBarsAfterSweep":12,
    "InpDisplacementATR":0.90,
    "InpMinBodyEfficiency":0.50,
    "InpUseVolumeFilter":False,
    "InpMinFVGATR":0.05,
    "InpMaxFVGATR":1.00,
    "InpEntryStyle":1,
    "InpExecutionMode":0,
    "InpEntryExpiryM5Bars":12,
    "InpSetupExpiryM15Bars":8,
    "InpCampaignMaxHours":8,
    "InpPendingExpiryBars":6,
    "InpCancelPendingOutsideSession":True,
    "InpCancelPendingOnInvalidation":True,
    "InpPendingPriceOffsetATR":0.00,
    "InpOptimalExtensionATR":0.15,
    "InpMaxEntryExtensionATR":0.35,
    "InpHardRejectExtensionATR":0.60,
    "InpMinimumRR":1.25,
    "InpMaxEntries":1,
    "InpCampaignLots":0.02,
    "InpEntryLot":0.02,
    "InpRequireProtectedAdds":True,
    "InpSizingMode":0,
    "InpRiskPercent":1.0,
    "InpMaxCampaignRiskPercent":1.0,
    "InpSLBufferATR":0.15,
    "InpStructureStopLookback":5,
    "InpUseStructuralTP1":True,
    "InpTP1R":1.50,
    "InpTP2R":2.50,
    "InpTP3R":4.00,
    "InpTP1ClosePercent":30.0,
    "InpTP2ClosePercent":30.0,
    "InpTP3ClosePercent":20.0,
    "InpUseSmartProtection":True,
    "InpProtectionTriggerR":1.00,
    "InpProtectionBufferATR":0.05,
    "InpUseRunner":True,
    "InpTrailStartR":2.50,
    "InpTrailStructureLookback":3,
    "InpTrailATRBuffer":0.10,
    "InpEnableScaleIns":False,
    "InpNoAddsAfterTP1":True,
    "InpUseLondon":False,
    "InpUseNewYork":False,
    "InpSessionHoursAreUTC":True,
    "InpUseDSTAdjustment":False,
    "InpUseSpreadFilter":False,
    "InpMaxSpreadPoints":800,
    "InpDeviationPoints":30,
    "InpMaxDailyLossPercent":3.0,
    "InpMaxDailyCampaigns":5,
    "InpMaxConsecutiveLosses":3,
    "InpMaxEquityDDPercent":6.0,
    "InpOneCampaignAtATime":True,
    "InpAllowReplacementBeforeEntry":True,
}


def v(name, **changes):
    return {"name":name,"changes":changes}


def family_variants(family: str):
    x=[v("BASE_DISCOVERY")]

    # ENUM_TIMEFRAMES integer values from the official MQL5 reference.
    # Every native MT5 timeframe is screened as an ASTRA entry timeframe.
    # Higher-horizon periods are diagnostic/sample-sufficiency tests; they are
    # not automatically eligible for promotion simply because they score well.
    if family=="timeframe":
        tf_values=[
            ("M1",1),("M2",2),("M3",3),("M4",4),("M5",5),("M6",6),
            ("M10",10),("M12",12),("M15",15),("M20",20),("M30",30),
            ("H1",16385),("H2",16386),("H3",16387),("H4",16388),
            ("H6",16390),("H8",16392),("H12",16396),
            ("D1",16408),("W1",32769),("MN1",49153),
        ]
        x=[v(f"ENTRY_{name}",InpEntryTF=value) for name,value in tf_values]
        # Coherent multi-timeframe cascades. The H1/H4-named inputs accept any
        # ENUM_TIMEFRAMES value, so these test architecture rather than labels.
        x += [
            v("CASCADE_M1_M5_M15_H1",InpEntryTF=1,InpLiquidityTF=5,InpH1TF=15,InpH4TF=16385),
            v("CASCADE_M2_M10_M30_H2",InpEntryTF=2,InpLiquidityTF=10,InpH1TF=30,InpH4TF=16386),
            v("CASCADE_M3_M15_H1_H4",InpEntryTF=3,InpLiquidityTF=15,InpH1TF=16385,InpH4TF=16388),
            v("CASCADE_M4_M20_H1_H4",InpEntryTF=4,InpLiquidityTF=20,InpH1TF=16385,InpH4TF=16388),
            v("CASCADE_M5_M15_H1_H4",InpEntryTF=5,InpLiquidityTF=15,InpH1TF=16385,InpH4TF=16388),
            v("CASCADE_M6_M20_H1_H4",InpEntryTF=6,InpLiquidityTF=20,InpH1TF=16385,InpH4TF=16388),
            v("CASCADE_M10_M30_H2_H6",InpEntryTF=10,InpLiquidityTF=30,InpH1TF=16386,InpH4TF=16390),
            v("CASCADE_M12_M30_H2_H6",InpEntryTF=12,InpLiquidityTF=30,InpH1TF=16386,InpH4TF=16390),
            v("CASCADE_M15_H1_H4_H12",InpEntryTF=15,InpLiquidityTF=16385,InpH1TF=16388,InpH4TF=16396),
            v("CASCADE_M20_H1_H4_H12",InpEntryTF=20,InpLiquidityTF=16385,InpH1TF=16388,InpH4TF=16396),
            v("CASCADE_M30_H2_H6_D1",InpEntryTF=30,InpLiquidityTF=16386,InpH1TF=16390,InpH4TF=16408),
            v("CASCADE_H1_H4_H12_D1",InpEntryTF=16385,InpLiquidityTF=16388,InpH1TF=16396,InpH4TF=16408),
            v("CASCADE_H2_H6_D1_W1",InpEntryTF=16386,InpLiquidityTF=16390,InpH1TF=16408,InpH4TF=32769),
            v("CASCADE_H4_D1_W1_MN1",InpEntryTF=16388,InpLiquidityTF=16408,InpH1TF=32769,InpH4TF=49153),
        ]

    elif family=="ema":
        # Coarse exhaustive EMA surface, followed by cross/OOS confirmation.
        # This is intentionally bounded to economically plausible trend spans;
        # integer-by-integer brute force would amplify multiple-testing overfit.
        fasts=[5,8,9,10,12,13,15,20,21,25,34,50]
        slows=[20,21,26,34,50,55,75,89,100,144,200]
        x=[]
        for fast in fasts:
            for slow in slows:
                if fast>=slow:
                    continue
                x.append(v(
                    f"EMA_{fast}_{slow}",
                    InpRequireH4Bias=True,
                    InpRequireH1Alignment=True,
                    InpMinADX=12.0,
                    InpH4FastEMA=fast,InpH4SlowEMA=slow,
                    InpH1FastEMA=fast,InpH1SlowEMA=slow,
                ))
        # A few asymmetric MTF combinations test whether the execution context
        # benefits from a faster H1 and slower H4 regime filter.
        x += [
            v("EMA_H1_9_21_H4_20_50",InpRequireH4Bias=True,InpRequireH1Alignment=True,InpMinADX=12.0,
              InpH1FastEMA=9,InpH1SlowEMA=21,InpH4FastEMA=20,InpH4SlowEMA=50),
            v("EMA_H1_20_50_H4_50_200",InpRequireH4Bias=True,InpRequireH1Alignment=True,InpMinADX=12.0,
              InpH1FastEMA=20,InpH1SlowEMA=50,InpH4FastEMA=50,InpH4SlowEMA=200),
            v("EMA_H1_13_34_H4_34_89",InpRequireH4Bias=True,InpRequireH1Alignment=True,InpMinADX=12.0,
              InpH1FastEMA=13,InpH1SlowEMA=34,InpH4FastEMA=34,InpH4SlowEMA=89),
        ]

    elif family=="risk":
        x=[
            v("RISK_FIXED_002",InpSizingMode=0,InpEntryLot=0.02,InpCampaignLots=0.02),
            v("RISK_025",InpSizingMode=1,InpRiskPercent=0.25,InpMaxCampaignRiskPercent=0.25),
            v("RISK_050",InpSizingMode=1,InpRiskPercent=0.50,InpMaxCampaignRiskPercent=0.50),
            v("RISK_075",InpSizingMode=1,InpRiskPercent=0.75,InpMaxCampaignRiskPercent=0.75),
            v("RISK_100",InpSizingMode=1,InpRiskPercent=1.00,InpMaxCampaignRiskPercent=1.00),
            v("RISK_125",InpSizingMode=1,InpRiskPercent=1.25,InpMaxCampaignRiskPercent=1.25),
            v("DAILY_LOSS_100",InpMaxDailyLossPercent=1.0),
            v("DAILY_LOSS_150",InpMaxDailyLossPercent=1.5),
            v("DAILY_LOSS_200",InpMaxDailyLossPercent=2.0),
            v("DAILY_LOSS_300",InpMaxDailyLossPercent=3.0),
            v("DAILY_LOSS_500",InpMaxDailyLossPercent=5.0),
            v("DD_300",InpMaxEquityDDPercent=3.0),
            v("DD_400",InpMaxEquityDDPercent=4.0),
            v("DD_600",InpMaxEquityDDPercent=6.0),
            v("DD_800",InpMaxEquityDDPercent=8.0),
            v("DD_1000",InpMaxEquityDDPercent=10.0),
            v("CAMPAIGNS_1",InpMaxDailyCampaigns=1),
            v("CAMPAIGNS_2",InpMaxDailyCampaigns=2),
            v("CAMPAIGNS_3",InpMaxDailyCampaigns=3),
            v("CAMPAIGNS_5",InpMaxDailyCampaigns=5),
            v("CAMPAIGNS_10",InpMaxDailyCampaigns=10),
            v("STREAK_1",InpMaxConsecutiveLosses=1),
            v("STREAK_2",InpMaxConsecutiveLosses=2),
            v("STREAK_3",InpMaxConsecutiveLosses=3),
            v("STREAK_5",InpMaxConsecutiveLosses=5),
        ]

    elif family=="structure":
        x += [
            v("SHORT_ONLY",InpLongEnabled=False),
            v("LONG_ONLY",InpShortEnabled=False),
            v("H4_ONLY",InpRequireH4Bias=True),
            v("H1_ONLY",InpRequireH1Alignment=True,InpMinADX=12.0),
            v("H1_ADX18",InpRequireH1Alignment=True,InpMinADX=18.0),
            v("H1_ADX25",InpRequireH1Alignment=True,InpMinADX=25.0),
            v("H1_NO_DI",InpRequireH1Alignment=True,InpMinADX=12.0,InpRequireDIDirection=False),
            v("H4_H1",InpRequireH4Bias=True,InpRequireH1Alignment=True,InpMinADX=12.0),
            v("EMA_FAST_9_21",InpRequireH4Bias=True,InpH4FastEMA=9,InpH4SlowEMA=21,InpRequireH1Alignment=True,InpH1FastEMA=9,InpH1SlowEMA=21,InpMinADX=12.0),
            v("EMA_SLOW_50_200",InpRequireH4Bias=True,InpH4FastEMA=50,InpH4SlowEMA=200,InpRequireH1Alignment=True,InpH1FastEMA=50,InpH1SlowEMA=200,InpMinADX=12.0),
            v("LIQ_LB10",InpLiquidityLookback=10),
            v("LIQ_LB30",InpLiquidityLookback=30),
            v("LIQ_LB40",InpLiquidityLookback=40),
            v("EQ_ATR_005",InpEqualLevelATR=0.05),
            v("EQ_ATR_020",InpEqualLevelATR=0.20),
            v("ROLLING_OFF",InpUseRollingLiquidity=False),
            v("SWEEP_TIGHT",InpSweepMinATR=0.03,InpSweepMaxATR=0.50),
            v("SWEEP_CLASSIC",InpSweepMinATR=0.10,InpSweepMaxATR=0.75),
            v("SWEEP_WIDE",InpSweepMinATR=0.10,InpSweepMaxATR=1.25),
            v("RECLAIM_020",InpMinReclaimBody=0.20),
            v("RECLAIM_040",InpMinReclaimBody=0.40),
            v("RECLAIM_060",InpMinReclaimBody=0.60),
            v("RECLAIM_DIRECTIONAL",InpRequireDirectionalReclaim=True),
            v("ATR7",InpATRPeriod=7),
            v("ATR21",InpATRPeriod=21),
        ]
    elif family=="trigger":
        x += [
            v("MSS_LB3",InpMSSLookback=3),
            v("MSS_LB8",InpMSSLookback=8),
            v("MSS_6BARS",InpMSSMaxBarsAfterSweep=6),
            v("MSS_18BARS",InpMSSMaxBarsAfterSweep=18),
            v("MSS_24BARS",InpMSSMaxBarsAfterSweep=24),
            v("DISP_070",InpDisplacementATR=0.70),
            v("DISP_080",InpDisplacementATR=0.80),
            v("DISP_110",InpDisplacementATR=1.10),
            v("DISP_130",InpDisplacementATR=1.30),
            v("EFF_040",InpMinBodyEfficiency=0.40),
            v("EFF_060",InpMinBodyEfficiency=0.60),
            v("EFF_070",InpMinBodyEfficiency=0.70),
            v("FVG_MIN_002",InpMinFVGATR=0.02),
            v("FVG_MIN_010",InpMinFVGATR=0.10),
            v("FVG_MIN_020",InpMinFVGATR=0.20),
            v("FVG_MAX_050",InpMaxFVGATR=0.50),
            v("FVG_MAX_150",InpMaxFVGATR=1.50),
            v("ENTRY_NEAR",InpEntryStyle=0),
            v("ENTRY_FAR",InpEntryStyle=2),
            v("EXPIRY_6",InpEntryExpiryM5Bars=6),
            v("EXPIRY_24",InpEntryExpiryM5Bars=24),
            v("EXT_TIGHT",InpMaxEntryExtensionATR=0.25,InpHardRejectExtensionATR=0.45),
            v("EXT_WIDE",InpMaxEntryExtensionATR=0.50,InpHardRejectExtensionATR=0.80),
            v("PENDING_MID",InpExecutionMode=1,InpEntryStyle=1,InpPendingExpiryBars=6,InpPendingPriceOffsetATR=0.00),
            v("PENDING_NEAR",InpExecutionMode=1,InpEntryStyle=0,InpPendingExpiryBars=6,InpPendingPriceOffsetATR=0.00),
            v("PENDING_OFFSET_005",InpExecutionMode=1,InpEntryStyle=1,InpPendingExpiryBars=8,InpPendingPriceOffsetATR=0.05),
            v("PENDING_OFFSET_010",InpExecutionMode=1,InpEntryStyle=1,InpPendingExpiryBars=12,InpPendingPriceOffsetATR=0.10),
        ]
    elif family=="exit":
        x += [
            v("RR_MIN_100",InpMinimumRR=1.00,InpTP1R=1.25),
            v("RR_MIN_150",InpMinimumRR=1.50,InpTP1R=1.50),
            v("RR_MIN_200",InpMinimumRR=2.00,InpTP1R=2.00,InpTP2R=3.00,InpTP3R=5.00),
            v("SLBUF_005",InpSLBufferATR=0.05),
            v("SLBUF_010",InpSLBufferATR=0.10),
            v("SLBUF_025",InpSLBufferATR=0.25),
            v("SLBUF_040",InpSLBufferATR=0.40),
            v("STOP_LB3",InpStructureStopLookback=3),
            v("STOP_LB8",InpStructureStopLookback=8),
            v("STOP_LB12",InpStructureStopLookback=12),
            v("FIXED_TP1",InpUseStructuralTP1=False),
            v("TP_LADDER_FAST",InpUseStructuralTP1=False,InpTP1R=1.25,InpTP2R=2.00,InpTP3R=3.00),
            v("TP_LADDER_BAL",InpUseStructuralTP1=False,InpTP1R=1.50,InpTP2R=2.50,InpTP3R=4.00),
            v("TP_LADDER_WIDE",InpUseStructuralTP1=False,InpMinimumRR=1.50,InpTP1R=2.00,InpTP2R=3.50,InpTP3R=6.00),
            v("NO_SMART_PROTECT",InpUseSmartProtection=False),
            v("PROTECT_050",InpProtectionTriggerR=0.50,InpProtectionBufferATR=0.02),
            v("PROTECT_075",InpProtectionTriggerR=0.75,InpProtectionBufferATR=0.03),
            v("PROTECT_125",InpProtectionTriggerR=1.25,InpProtectionBufferATR=0.05),
            v("TRAIL_150",InpTrailStartR=1.50,InpTrailATRBuffer=0.10),
            v("TRAIL_200",InpTrailStartR=2.00,InpTrailATRBuffer=0.15),
            v("TRAIL_300",InpTrailStartR=3.00,InpTrailATRBuffer=0.20),
            v("NO_RUNNER",InpUseRunner=False,InpTP1ClosePercent=40.0,InpTP2ClosePercent=30.0,InpTP3ClosePercent=30.0),
            v("SCALE_3",InpMaxEntries=3,InpCampaignLots=0.06,InpEntryLot=0.02,InpEnableScaleIns=True,InpRequireProtectedAdds=True),
            v("SCALE_5",InpMaxEntries=5,InpCampaignLots=0.10,InpEntryLot=0.02,InpEnableScaleIns=True,InpRequireProtectedAdds=True),
            v("SCALE_EARLY",InpMaxEntries=3,InpCampaignLots=0.06,InpEntryLot=0.02,InpEnableScaleIns=True,InpE2MinMFER=0.15,InpE3MinMFER=0.40,InpRequireProtectedAdds=True),
        ]
    elif family=="session":
        x += [
            v("LONDON_UTC",InpUseLondon=True,InpUseNewYork=False,InpSessionHoursAreUTC=True,InpLondonStartHour=7,InpLondonEndHour=12),
            v("NY_UTC",InpUseLondon=False,InpUseNewYork=True,InpSessionHoursAreUTC=True,InpNewYorkStartHour=12,InpNewYorkEndHour=17),
            v("LDN_NY_UTC",InpUseLondon=True,InpUseNewYork=True,InpSessionHoursAreUTC=True,InpLondonStartHour=7,InpLondonEndHour=12,InpNewYorkStartHour=12,InpNewYorkEndHour=17),
            v("LDN_8_11",InpUseLondon=True,InpUseNewYork=False,InpSessionHoursAreUTC=True,InpLondonStartHour=8,InpLondonEndHour=11),
            v("NY_13_16",InpUseLondon=False,InpUseNewYork=True,InpSessionHoursAreUTC=True,InpNewYorkStartHour=13,InpNewYorkEndHour=16),
            v("OVERLAP_12_15",InpUseLondon=False,InpUseNewYork=True,InpSessionHoursAreUTC=True,InpNewYorkStartHour=12,InpNewYorkEndHour=15),
            v("SPREAD_400",InpUseSpreadFilter=True,InpMaxSpreadPoints=400),
            v("SPREAD_600",InpUseSpreadFilter=True,InpMaxSpreadPoints=600),
            v("SPREAD_800",InpUseSpreadFilter=True,InpMaxSpreadPoints=800),
            v("SPREAD_1000",InpUseSpreadFilter=True,InpMaxSpreadPoints=1000),
            v("SPREAD_1200",InpUseSpreadFilter=True,InpMaxSpreadPoints=1200),
            v("SPREAD_1600",InpUseSpreadFilter=True,InpMaxSpreadPoints=1600),
            v("DEVIATION_10",InpDeviationPoints=10),
            v("DEVIATION_30",InpDeviationPoints=30),
            v("DEVIATION_60",InpDeviationPoints=60),
        ]
    else:
        raise SystemExit(f"Unknown family {family}")
    return x


def generate(args):
    order,rows=read_set(Path(args.base))
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    variants=family_variants(args.family)
    manifest=[]
    for i,item in enumerate(variants):
        changes=dict(DISCOVERY_BASE)
        changes.update(item["changes"])
        name=item["name"]
        fn=f"{args.family.upper()}_{i:02d}_{name}.set"
        csv=f"ASTRA_DOE_{args.family.upper()}_{i:02d}.csv"
        write_set(out/fn,order,rows,changes,csv,args.magic_base+i)
        manifest.append({"index":i,"name":name,"preset":fn,"family":args.family,"changes":item["changes"]})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"family":args.family,"count":len(manifest),"out":str(out)},indent=2))


def metric(m,key,default=0.0):
    try:
        return float(m["metrics"][key]["value"])
    except Exception:
        return default


def rank(args):
    root=Path(args.analysis)
    manifest=json.loads(Path(args.manifest).read_text())
    rows=[]
    for item in manifest:
        p=root/item["name"]/"mt5_metrics.json"
        if not p.exists():
            rows.append({**item,"missing":True,"trades":0,"score":-1e9})
            continue
        d=json.loads(p.read_text())
        trades=metric(d,"total_trades")
        pf=metric(d,"profit_factor")
        exp=metric(d,"expected_payoff")
        net=metric(d,"net_profit")
        dd=max(metric(d,"max_equity_dd_relative"),metric(d,"max_balance_dd_relative"))
        sharpe=metric(d,"sharpe_ratio")
        win=0.0
        try: win=float(d["metrics"]["profit_trades"]["percent"] or 0.0)
        except Exception: pass
        # Screening score: sample size + PF + payoff + Sharpe, penalize DD.
        # It is only a research ordering; promotion requires cross validation.
        sample=min(1.0,trades/20.0)
        pf_cap=min(max(pf,0.0),3.0)
        exp_term=math.tanh(exp/20.0)
        sharpe_term=math.tanh(sharpe/3.0)
        score=(2.0*sample)+(1.5*(pf_cap-1.0))+exp_term+0.5*sharpe_term-(dd/10.0)
        if trades<3: score-=3.0
        rows.append({**item,"trades":int(trades),"pf":pf,"expected_payoff":exp,"net_profit":net,
                     "dd_percent":dd,"sharpe":sharpe,"win_rate":win,"score":score,"missing":False})
    rows.sort(key=lambda r:r["score"],reverse=True)
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"ranking.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    # Cross-family generation must not be driven by tiny-sample headline
    # metrics. Keep the full ranking for research, but admit only variants with
    # at least 10 trades and positive basic economics to top.json. If an entire
    # family has no such variant, fall back to the ranking so the pipeline can
    # finish and the later OOS gate can reject it explicitly.
    eligible=[
        r for r in rows
        if not r.get("missing")
        and int(r.get("trades",0))>=10
        and float(r.get("pf",0.0))>1.0
        and float(r.get("expected_payoff",0.0))>0.0
        and float(r.get("net_profit",0.0))>0.0
    ]
    top=(eligible if eligible else rows)[:max(1,args.top)]
    (out/"top.json").write_text(json.dumps(top,indent=2),encoding="utf-8")
    print("| Variant | Trades | PF | Exp | Net | DD% | Sharpe | Win% | Score |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        print(f"| {r['name']} | {r['trades']} | {r.get('pf',0):.3f} | {r.get('expected_payoff',0):.2f} | {r.get('net_profit',0):.2f} | {r.get('dd_percent',0):.2f} | {r.get('sharpe',0):.2f} | {r.get('win_rate',0):.1f} | {r['score']:.3f} |")


def valid_changes(ch):
    try:
        if float(ch.get("InpSweepMaxATR", DISCOVERY_BASE["InpSweepMaxATR"])) <= float(ch.get("InpSweepMinATR", DISCOVERY_BASE["InpSweepMinATR"])):
            return False
        minrr=float(ch.get("InpMinimumRR",DISCOVERY_BASE["InpMinimumRR"]))
        t1=float(ch.get("InpTP1R",DISCOVERY_BASE["InpTP1R"]))
        t2=float(ch.get("InpTP2R",DISCOVERY_BASE["InpTP2R"]))
        t3=float(ch.get("InpTP3R",DISCOVERY_BASE["InpTP3R"]))
        if t1 < minrr or not (t2>t1 and t3>t2):
            return False
        return True
    except Exception:
        return False


def cross_generate(args):
    order,rows=read_set(Path(args.base))
    roots=sorted(Path(args.tops).glob("*/top.json"))
    if len(roots)<6:
        raise SystemExit(f"Expected top.json for six signal families under {args.tops}; found {len(roots)}")
    family_map={}
    for p in roots:
        arr=json.loads(p.read_text())
        family=p.parent.name
        if family.startswith("astra-doe-"):
            family=family[len("astra-doe-"):]
        family_map[family]=arr[:args.per_family]
    required=["timeframe","ema","structure","trigger","exit","session"]
    missing=[x for x in required if x not in family_map]
    if missing:
        raise SystemExit(f"Missing family top results: {missing}")

    from itertools import product
    combos=[]
    seen=set()
    for picks in product(*(family_map[f] for f in required)):
        delta={}
        labels=[]
        for f,item in zip(required,picks):
            delta.update(item.get("changes",{}))
            labels.append(item["name"])
        if not valid_changes({**DISCOVERY_BASE,**delta}):
            continue
        key=json.dumps(delta,sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        combos.append({"name":"__".join(labels),"changes":delta,"components":dict(zip(required,labels))})

    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for i,item in enumerate(combos):
        changes=dict(DISCOVERY_BASE); changes.update(item["changes"])
        fn=f"CROSS_{i:02d}.set"
        write_set(out/fn,order,rows,changes,f"ASTRA_CROSS_{i:02d}.csv",args.magic_base+i)
        manifest.append({"index":i,"name":f"CROSS_{i:02d}","preset":fn,"family":"cross",
                         "changes":item["changes"],"components":item["components"]})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"cross_count":len(manifest),"components":required},indent=2))


def make_oos(args):
    ranking=json.loads(Path(args.ranking).read_text())
    selected=[r for r in ranking if not r.get("missing") and r.get("trades",0)>=args.min_trades][:args.top]
    if not selected:
        selected=[r for r in ranking if not r.get("missing")][:args.top]
    source=Path(args.presets)
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for i,r in enumerate(selected):
        src=source/r["preset"]
        if not src.exists():
            raise SystemExit(f"Missing selected preset {src}")
        dst=out/f"OOS_{i:02d}_{r['name']}.set"
        dst.write_text(src.read_text(encoding="utf-8"),encoding="utf-8")
        manifest.append({"index":i,"name":f"OOS_{i:02d}_{r['name']}","preset":dst.name,
                         "source_variant":r["name"],"screen_metrics":{k:r.get(k) for k in ("trades","pf","expected_payoff","net_profit","dd_percent","sharpe","win_rate","score")},
                         "changes":r.get("changes",{}),"components":r.get("components",{})})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps({"oos_count":len(manifest)},indent=2))

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    g=sub.add_parser("generate")
    g.add_argument("--family",required=True,choices=["timeframe","ema","structure","trigger","exit","session","risk"])
    g.add_argument("--base",required=True)
    g.add_argument("--out",required=True)
    g.add_argument("--magic-base",type=int,default=26100000)
    g.set_defaults(func=generate)
    r=sub.add_parser("rank")
    r.add_argument("--analysis",required=True)
    r.add_argument("--manifest",required=True)
    r.add_argument("--out",required=True)
    r.add_argument("--top",type=int,default=3)
    r.set_defaults(func=rank)
    x=sub.add_parser("cross")
    x.add_argument("--base",required=True)
    x.add_argument("--tops",required=True)
    x.add_argument("--out",required=True)
    x.add_argument("--per-family",type=int,default=2)
    x.add_argument("--magic-base",type=int,default=26200000)
    x.set_defaults(func=cross_generate)
    o=sub.add_parser("oos")
    o.add_argument("--ranking",required=True)
    o.add_argument("--presets",required=True)
    o.add_argument("--out",required=True)
    o.add_argument("--top",type=int,default=4)
    o.add_argument("--min-trades",type=int,default=10)
    o.set_defaults(func=make_oos)
    args=ap.parse_args()
    args.func(args)

if __name__=="__main__":
    main()
