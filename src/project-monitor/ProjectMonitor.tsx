import React,{useEffect,useState} from "react";
import type {ProjectSnapshot} from "../../backend/project-monitor/schema";

const fmt=(n:number|null)=>n==null?"—":new Intl.NumberFormat("en-US",{maximumFractionDigits:2}).format(n);
export default function ProjectMonitor(){
 const [s,setS]=useState<ProjectSnapshot|null>(null);const [err,setErr]=useState("");
 useEffect(()=>{let live=true;const load=async()=>{try{const r=await fetch("/api/project-status",{cache:"no-store"});if(!r.ok)throw new Error();const j=await r.json();if(live){setS(j);setErr("")}}catch{if(live)setErr("STATUS FEED UNAVAILABLE")}};load();const id=setInterval(load,10000);return()=>{live=false;clearInterval(id)}},[]);
 if(!s)return <main className="project-monitor"><h1>AUREON Ω PRIME</h1><p>{err||"Connecting to evidence ledger…"}</p></main>;
 const p=s.progress?Math.round(100*s.progress.completed/s.progress.total):null;
 return <main className="project-monitor">
  <header><div><small>LIVE PROJECT MONITOR</small><h1>AUREON Ω PRIME</h1></div><strong className={"state "+s.state.toLowerCase()}>{s.state}</strong></header>
  <section className="hero"><small>CURRENT TASK</small><h2>{s.currentTask||"No active task"}</h2><p>{s.stage||"UNKNOWN"}</p>{p!=null&&<><progress max="100" value={p}/><b>{p}% · {s.progress!.completed}/{s.progress!.total} {s.progress!.unit}</b></>}</section>
  <div className="grid">
   <section><small>GOLD BRAIN</small><h3>{s.gold.integrity}</h3><p>{fmt(s.gold.rows)} rows · {s.gold.timeframesValidated??"—"}/21 TF</p><p>{s.gold.first||"—"} → {s.gold.last||"—"}</p></section>
   <section><small>TESTS</small><h3>{s.tests.running} running</h3><p>{s.tests.completed} completed · {s.tests.rejected} rejected · {s.tests.promoted} promoted</p></section>
   <section><small>FROZEN CHAMPION</small><h3>{s.champion.name}</h3><p>Net {fmt(s.champion.net)} · PF {s.champion.profitFactor??"—"} · DD {s.champion.drawdownPct??"—"}%</p></section>
   <section><small>BEST VERIFIED CHALLENGER</small><h3>{s.challenger.name||"None yet"}</h3><p>Net {fmt(s.challenger.net)} · PF {s.challenger.profitFactor??"—"} · DD {s.challenger.drawdownPct??"—"}%</p></section>
   <section><small>CTRADER</small><h3>{s.ctrader.application}</h3><p>{s.ctrader.auth} · {s.ctrader.demoCertification}</p></section>
   <section><small>SOURCE</small><h3>{s.latestCommit?.slice(0,10)||"—"}</h3><p>Updated {new Date(s.updatedAt).toLocaleString()}</p></section>
  </div>
  {s.blocker&&<section className="alert"><small>BLOCKER</small><b>{s.blocker}</b></section>}
  {err&&<p className="alert">{err}</p>}
 </main>
}
