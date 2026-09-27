export type Environment='demo'|'live';
export type Side='BUY'|'SELL';
export interface ExecutionRequest{symbol:string;side:Side;volume:number;stopLoss?:number;takeProfit?:number;clientOrderId:string}
export interface ExecutionReceipt{accepted:boolean;brokerOrderId?:string;positionId?:string;requestedAt:number;ackAt?:number;fillAt?:number;requestedPrice?:number;fillPrice?:number;spread?:number;slippage?:number;errorCode?:string}
export interface AccountSnapshot{accountId:string;environment:Environment;balance:number;equity:number;freeMargin:number}
