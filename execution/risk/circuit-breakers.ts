export interface GuardState{consecutiveLosses:number;dailyLossPct:number;drawdownPct:number;spread?:number;maxSpread?:number;pendingOrders:number;openPositions:number;lastReconciled:boolean}
export function circuitBreaker(s:GuardState){
 if(!s.lastReconciled)return {ok:false,reason:'UNRECONCILED_STATE'};
 if(s.pendingOrders>0)return {ok:false,reason:'PENDING_ORDER_EXISTS'};
 if(s.openPositions>0)return {ok:false,reason:'POSITION_ALREADY_OPEN'};
 if(s.dailyLossPct>=3)return {ok:false,reason:'DAILY_LOSS_LIMIT'};
 if(s.drawdownPct>=6)return {ok:false,reason:'DRAWDOWN_LIMIT'};
 if(s.consecutiveLosses>=3)return {ok:false,reason:'LOSS_STREAK_PAUSE'};
 if(s.spread!=null&&s.maxSpread!=null&&s.spread>s.maxSpread)return {ok:false,reason:'SPREAD_LIMIT'};
 return {ok:true};
}
