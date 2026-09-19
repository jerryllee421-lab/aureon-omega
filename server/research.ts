import { database } from './database.ts';

type ScanRow={id:string;result:any};
type MonitorRow={scan_id:string;opportunity_index:number;observation:any;last_error:string|null};

const maturity=(n:number)=>n===0?'EMPTY':n<10?'EARLY':n<30?'DEVELOPING':'SUBSTANTIAL_REFERENCE_SAMPLE';

export async function researchSummary(userId:string){
  const [scans,setups]=await Promise.all([
    database(`scans?user_id=eq.${userId}&select=id,result&order=created_at.desc&limit=200`) as Promise<ScanRow[]>,
    database(`monitored_setups?user_id=eq.${userId}&select=scan_id,opportunity_index,observation,last_error&order=created_at.desc&limit=500`) as Promise<MonitorRow[]>,
  ]);
  const byScan=new Map(scans.map(scan=>[scan.id,scan]));
  const families=new Map<string,{family:string;registered:number;states:Record<string,number>;providerErrors:number;favorable:number[];adverse:number[]}>();
  for(const row of setups){
    const opportunity=byScan.get(row.scan_id)?.result?.opportunities?.[row.opportunity_index];
    const family=String(opportunity?.setupType||'UNCLASSIFIED');
    const entry=families.get(family)||{family,registered:0,states:{},providerErrors:0,favorable:[],adverse:[]};
    entry.registered++;
    const state=String(row.observation?.state||'UNKNOWN');entry.states[state]=(entry.states[state]||0)+1;
    if(row.last_error)entry.providerErrors++;
    if(Number.isFinite(row.observation?.favorableR))entry.favorable.push(Number(row.observation.favorableR));
    if(Number.isFinite(row.observation?.adverseR))entry.adverse.push(Number(row.observation.adverseR));
    families.set(family,entry);
  }
  const mean=(v:number[])=>v.length?Number((v.reduce((a,b)=>a+b,0)/v.length).toFixed(3)):null;
  return {
    generatedAt:new Date().toISOString(),
    scope:{scans:scans.length,monitoredSetups:setups.length,maxScans:200,maxSetups:500},
    qualification:'RESEARCH_ONLY',
    explanation:'Counts and excursions describe reference-market observations only. They are not verified fills, P&L, win rate, expectancy or strategy profitability.',
    strategies:[...families.values()].map(v=>({
      family:v.family,registered:v.registered,evidenceMaturity:maturity(v.registered),states:v.states,providerErrors:v.providerErrors,
      favorableRObserved:{count:v.favorable.length,mean:mean(v.favorable),max:v.favorable.length?Math.max(...v.favorable):null},
      adverseRObserved:{count:v.adverse.length,mean:mean(v.adverse),max:v.adverse.length?Math.max(...v.adverse):null},
      winRate:null,expectancy:null,profitFactor:null,
    })).sort((a,b)=>b.registered-a.registered),
  };
}
