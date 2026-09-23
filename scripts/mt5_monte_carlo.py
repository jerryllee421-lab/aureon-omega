from __future__ import annotations

"""Monte Carlo and daily-P/L stress analysis for MT5 HTML reports.

Uses closed-deal P/L grouped by UTC report date. This preserves partial-exit
clustering better than treating every deal as an independent trade.
"""

import argparse
import html
import json
import math
import random
import re
from pathlib import Path


def read_auto(path: Path) -> str:
    raw=path.read_bytes()
    for enc in ("utf-16","utf-8","cp1252"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8",errors="ignore")


def clean_cell(x: str) -> str:
    x=re.sub(r"<[^>]+>","",x)
    x=html.unescape(x).replace("\xa0"," ").strip()
    return re.sub(r"\s+"," ",x)


def num(s: str) -> float:
    s=s.replace(" ","").replace(",","")
    try:return float(s)
    except:return 0.0


def extract_daily_pl(path: Path):
    s=read_auto(path)
    i=s.find("<b>Deals</b>")
    if i<0:
        raise ValueError("Deals table not found")
    tail=s[i:]
    rows=re.findall(r"<tr[^>]*>(.*?)</tr>",tail,re.I|re.S)
    daily={}
    initial=10000.0
    header_seen=False
    for row in rows:
        cells=[clean_cell(x) for x in re.findall(r"<td[^>]*>(.*?)</td>",row,re.I|re.S)]
        if not cells:
            continue
        if "Direction" in cells and "Profit" in cells:
            header_seen=True
            continue
        if not header_seen or len(cells)<13:
            continue
        typ=cells[3].lower()
        direction=cells[4].lower()
        if typ=="balance":
            initial=num(cells[10]) or num(cells[11]) or initial
            continue
        if direction not in ("out","out by"):
            continue
        day=cells[0][:10]
        pl=num(cells[8])+num(cells[9])+num(cells[10])
        daily[day]=daily.get(day,0.0)+pl
    return initial,[daily[k] for k in sorted(daily)],daily


def path_stats(initial: float, pls):
    eq=initial
    peak=initial
    maxdd=0.0
    for p in pls:
        eq+=p
        peak=max(peak,eq)
        if peak>0:
            maxdd=max(maxdd,(peak-eq)/peak*100.0)
    return eq,maxdd


def pct(xs,p):
    if not xs:return 0.0
    ys=sorted(xs)
    k=(len(ys)-1)*p
    a=int(math.floor(k)); b=int(math.ceil(k))
    if a==b:return ys[a]
    return ys[a]*(b-k)+ys[b]*(k-a)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("report",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--sims",type=int,default=5000)
    ap.add_argument("--seed",type=int,default=260923)
    args=ap.parse_args()
    initial,pls,daily=extract_daily_pl(args.report)
    if not pls:
        raise SystemExit("No closed-deal daily P/L found")
    actual_end,actual_dd=path_stats(initial,pls)
    rng=random.Random(args.seed)
    ends=[]; dds=[]
    for _ in range(args.sims):
        sample=[rng.choice(pls) for _ in range(len(pls))]
        e,d=path_stats(initial,sample)
        ends.append(e); dds.append(d)
    result={
        "initial_balance":initial,
        "pl_days":len(pls),
        "positive_days":sum(1 for x in pls if x>0),
        "negative_days":sum(1 for x in pls if x<0),
        "actual_end_balance":actual_end,
        "actual_max_dd_percent":actual_dd,
        "daily_pl_mean":sum(pls)/len(pls),
        "daily_pl_median":pct(pls,0.5),
        "bootstrap_sims":args.sims,
        "ending_balance_percentiles":{
            "p05":pct(ends,0.05),"p25":pct(ends,0.25),"p50":pct(ends,0.50),"p75":pct(ends,0.75),"p95":pct(ends,0.95)
        },
        "max_dd_percentiles":{
            "p50":pct(dds,0.50),"p90":pct(dds,0.90),"p95":pct(dds,0.95),"p99":pct(dds,0.99)
        },
        "prob_end_below_start":sum(e<initial for e in ends)/len(ends),
        "prob_dd_gt_5pct":sum(d>5 for d in dds)/len(dds),
        "prob_dd_gt_10pct":sum(d>10 for d in dds)/len(dds),
        "prob_dd_gt_20pct":sum(d>20 for d in dds)/len(dds),
        "daily_pl":daily,
    }
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"monte_carlo.json").write_text(json.dumps(result,indent=2))
    lines=[
        "# MT5 Daily-P/L Monte Carlo",
        "",
        f"- P/L days: {result['pl_days']}",
        f"- Actual ending balance: {actual_end:.2f}",
        f"- Actual max DD: {actual_dd:.2f}%",
        f"- Bootstrap median ending balance: {result['ending_balance_percentiles']['p50']:.2f}",
        f"- Bootstrap 95th percentile max DD: {result['max_dd_percentiles']['p95']:.2f}%",
        f"- P(end below start): {result['prob_end_below_start']*100:.1f}%",
        f"- P(DD > 10%): {result['prob_dd_gt_10pct']*100:.1f}%",
    ]
    (args.out/"monte_carlo.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines))


if __name__=="__main__":
    main()
