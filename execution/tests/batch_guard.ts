import type {ExecutionEvent} from '../telemetry/ledger.ts';
const REQUIRED=['SUBMIT','ACK','FILL','PROTECT','VERIFY','CLOSE','DEAL'];
export function reconcileTrade(events:ExecutionEvent[]){const phases=new Set(events.map(e=>e.phase));const missing=REQUIRED.filter(p=>!phases.has(p as any));return {ok:missing.length===0&&!phases.has('ERROR'),missing};}
export function mayContinueBatch(events:ExecutionEvent[],tradeId:string){const r=reconcileTrade(events.filter(e=>e.tradeId===tradeId));return r.ok;}
