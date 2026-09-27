import type {ProjectSnapshot} from "../backend/project-monitor/schema";
import {normalizeState} from "../backend/project-monitor/truth";
const empty:ProjectSnapshot={schema:"aureon.project.snapshot.v1",state:"UNKNOWN",currentTask:null,stage:null,progress:null,gold:{first:null,last:null,rows:null,integrity:"UNKNOWN",timeframesValidated:null},tests:{queued:0,running:0,completed:0,rejected:0,promoted:0},champion:{name:"FVG_Scalper_V2_12_Research_R943K",net:942349.65,profitFactor:2.58,drawdownPct:21.55,trades:1135},challenger:{name:null,net:null,profitFactor:null,drawdownPct:null,trades:null,oosStatus:null,holdoutStatus:null},ctrader:{application:"SUBMITTED",auth:"PENDING_TRADING_SCOPE",demoCertification:"NOT_STARTED"},blocker:null,latestCommit:null,deployment:null,updatedAt:new Date(0).toISOString(),evidence:[]};
export default async function handler(_req:any,res:any){
 // Supabase-backed projector is the production source; until configured, return explicit stale/unknown truth rather than fabricate live state.
 res.status(200).json(normalizeState(empty));
}
