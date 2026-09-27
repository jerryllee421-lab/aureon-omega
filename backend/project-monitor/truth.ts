import type {ProjectSnapshot} from "./schema";
export const isFresh=(iso:string,maxAgeMs=120000)=>Date.now()-Date.parse(iso)<=maxAgeMs;
export function normalizeState(s:ProjectSnapshot):ProjectSnapshot{
 if(!s.updatedAt||!isFresh(s.updatedAt)) return {...s,state:"STALE"};
 if(s.blocker) return {...s,state:"BLOCKED"};
 return s;
}
export function safeProgress(completed:number,total:number,unit:string){
 if(!Number.isFinite(completed)||!Number.isFinite(total)||total<=0||completed<0||completed>total)return null;
 return {completed,total,unit};
}
