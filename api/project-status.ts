import type {ProjectSnapshot} from "../backend/project-monitor/schema";
import {normalizeState} from "../backend/project-monitor/truth";

function env(){
 const url=process.env.SUPABASE_URL;
 const key=process.env.SUPABASE_SECRET_KEY||process.env.SUPABASE_SERVICE_ROLE_KEY;
 if(!url||!key) return null;
 return {url:url.replace(/\/$/,""),key};
}
async function getLatestEvent(e:{url:string,key:string}){
 const r=await fetch(e.url+"/rest/v1/project_status_events?select=*&order=observed_at.desc&limit=1",{headers:{apikey:e.key,Authorization:"Bearer "+e.key}});
 if(!r.ok) throw new Error("STATUS_STORE_READ_FAILED");
 return (await r.json())[0]??null;
}
async function getLatestResult(e:{url:string,key:string}){
 const r=await fetch(e.url+"/rest/v1/research_test_results?select=*&order=created_at.desc&limit=1",{headers:{apikey:e.key,Authorization:"Bearer "+e.key}});
 if(!r.ok) throw new Error("RESULT_STORE_READ_FAILED");
 return (await r.json())[0]??null;
}
const base=():ProjectSnapshot=>({schema:"aureon.project.snapshot.v1",state:"UNKNOWN",currentTask:null,stage:null,progress:null,gold:{first:null,last:null,rows:null,integrity:"UNKNOWN",timeframesValidated:null},tests:{queued:0,running:0,completed:0,rejected:0,promoted:0},champion:{name:"FVG_Scalper_V2_12_Research_R943K",net:942349.65,profitFactor:2.58,drawdownPct:21.55,trades:1135},challenger:{name:null,net:null,profitFactor:null,drawdownPct:null,trades:null,oosStatus:null,holdoutStatus:null},ctrader:{application:"SUBMITTED",auth:"PENDING_TRADING_SCOPE",demoCertification:"NOT_STARTED"},blocker:null,latestCommit:null,deployment:null,updatedAt:new Date(0).toISOString(),evidence:[]});
export default async function handler(_req:any,res:any){
 try{
  const e=env(); if(!e)return res.status(503).json({...base(),blocker:"SUPABASE_MONITOR_UNCONFIGURED"});
  const [ev,rr]=await Promise.all([getLatestEvent(e),getLatestResult(e)]); let s=base();
  if(ev)s={...s,state:ev.state,currentTask:ev.current_task,stage:ev.stage,progress:ev.total?{completed:Number(ev.completed||0),total:Number(ev.total),unit:ev.unit||"steps"}:null,blocker:ev.blocker,latestCommit:ev.commit_sha,updatedAt:ev.observed_at,evidence:[{source:"supabase-status",artifact:ev.artifact||undefined,commitSha:ev.commit_sha||undefined,datasetSha256:ev.dataset_sha256||undefined,observedAt:ev.observed_at}]};
  if(rr)s={...s,challenger:{name:rr.candidate,net:rr.net==null?null:Number(rr.net),profitFactor:rr.profit_factor==null?null:Number(rr.profit_factor),drawdownPct:rr.drawdown_pct==null?null:Number(rr.drawdown_pct),trades:rr.trades,oosStatus:rr.oos_status,holdoutStatus:rr.holdout_status}};
  return res.status(200).json(normalizeState(s));
 }catch{return res.status(503).json({...base(),state:"UNKNOWN",blocker:"PROJECT_MONITOR_READ_FAILED"});}
}
