import { createHash } from 'node:crypto';
import { database } from './database.ts';
import { acquireCandles } from './candles.ts';
import { observePlan, summarizeObservations, type Plan } from './forward.ts';
import { numbers } from './authority.ts';
const terminal=new Set(['TARGET_TOUCHED','STOP_TOUCHED','AMBIGUOUS','EXPIRED']);
export async function registerMonitor(userId:string,scanId:string,index:number) {
  if(!/^[0-9a-f-]{36}$/.test(scanId)||!Number.isInteger(index)||index<0||index>3)throw new Error('INVALID_SETUP_REFERENCE');
  const [scan]=await database(`scans?id=eq.${scanId}&user_id=eq.${userId}&select=id,created_at,result,canonical`);
  const setup=scan?.result?.opportunities?.[index];
  if(!setup)throw new Error('SETUP_NOT_FOUND');
  // Never remap BTCUSDT to BTCUSD or accept a user-supplied symbol hint as visual identity.
  const symbols=[...new Set((scan.canonical.charts||[]).map((c:any)=>String(c.symbol).toUpperCase().replace(/[^A-Z0-9]/g,'')))];
  if(symbols.length!==1||!['BTCUSD','XAUUSD'].includes(String(symbols[0])))throw new Error('EXACT_INSTRUMENT_UNSUPPORTED');
  const entry=numbers(setup.entryZone),stop=numbers(setup.stopLoss),target=numbers(setup.tp1);
  if(!entry.length||stop.length!==1||target.length!==1||!['BUY','SELL'].includes(setup.direction))throw new Error('SUPPORTED_PLAN_LEVELS_REQUIRED');
  const createdAt=Date.now(),expiresAt=createdAt+12*3600000;
  const plan:Plan={symbol:String(symbols[0]),direction:setup.direction,entryLow:Math.min(...entry),entryHigh:Math.max(...entry),stop:stop[0],target:target[0],createdAt,expiresAt};
  // Geometry validation runs even before any history is available.
  observePlan(plan,{symbol:plan.symbol,provider:'UNAVAILABLE',providerInstrument:'',intervalMs:300000,observedAt:createdAt,candles:[]},createdAt);
  return database('monitored_setups','POST',{user_id:userId,scan_id:scanId,opportunity_index:index,created_at:new Date(createdAt).toISOString(),expires_at:new Date(expiresAt).toISOString(),plan});
}
export async function checkMonitors(userId:string) {
 const rows=await database(`monitored_setups?user_id=eq.${userId}&order=created_at.desc&limit=100`);
 const active=rows.filter((r:any)=>!terminal.has(r.observation.state));
 const packs=new Map<string,Awaited<ReturnType<typeof acquireCandles>>>();const errors=new Map<string,string>();
 await Promise.all([...new Set<string>(active.map((r:any)=>r.plan.symbol))].map(async symbol=>{try{packs.set(symbol,await acquireCandles(symbol));}catch(e){errors.set(symbol,e instanceof Error?e.message:'PROVIDER_UNAVAILABLE');}}));
 for(const row of active) {
  const pack=packs.get(row.plan.symbol);
  if(!pack){await database(`monitored_setups?id=eq.${row.id}&user_id=eq.${userId}&version=eq.${row.version}`,'PATCH',{last_checked_at:new Date().toISOString(),last_error:errors.get(row.plan.symbol)||'UNAVAILABLE'});continue;}
  const observation=observePlan(row.plan,pack);
  const candles=pack.candles.filter(c=>c.time>=Math.floor(row.plan.createdAt/pack.intervalMs)*pack.intervalMs);
  await database('rpc/record_monitor_check','POST',{p_id:row.id,p_user:userId,p_version:row.version,p_observation:observation,p_provider:pack.provider,p_instrument:pack.providerInstrument,p_candle:new Date(pack.candles.at(-1)!.time).toISOString(),p_digest:createHash('sha256').update(JSON.stringify(candles)).digest('hex'),p_candles:candles});
 }
 return {checked:active.length,providerErrors:Object.fromEntries(errors)};
}
export async function monitorSummary(userId:string) {
 const rows=await database(`monitored_setups?user_id=eq.${userId}&order=created_at.desc&limit=100`);
 return {setups:rows,summary:summarizeObservations(rows.map((r:any)=>r.observation)),scope:'Latest 100 registered setups'};
}
