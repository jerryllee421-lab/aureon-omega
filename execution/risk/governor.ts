import type {ExecutionRequest,AccountSnapshot} from '../ctrader/types.ts';
export type Gate={ok:boolean;reason?:string};
export function demoExecutionGate(req:ExecutionRequest,a:AccountSnapshot):Gate{
 if(a.environment!=='demo') return {ok:false,reason:'LIVE_EXECUTION_DISABLED'};
 if(!req.clientOrderId) return {ok:false,reason:'MISSING_IDEMPOTENCY_KEY'};
 if(!(req.volume>0)) return {ok:false,reason:'INVALID_VOLUME'};
 if(a.freeMargin<=0) return {ok:false,reason:'NO_FREE_MARGIN'};
 return {ok:true};
}
