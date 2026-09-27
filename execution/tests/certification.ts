import type {ExecutionEvent} from '../telemetry/ledger.ts';
import {reconcileTrade} from './batch_guard.ts';
export function certifyTenTradeBatch(events:ExecutionEvent[]){
 const ids=[...new Set(events.map(e=>e.tradeId))];
 const results=ids.map(id=>({id,...reconcileTrade(events.filter(e=>e.tradeId===id))}));
 return {certified:ids.length===10&&results.every(r=>r.ok),tradeCount:ids.length,failures:results.filter(r=>!r.ok)};
}
