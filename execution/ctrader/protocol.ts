export type OAEnvelope={clientMsgId:string;payloadType:number;payload:Record<string,unknown>};
export const PT={APP_AUTH_REQ:2100,ACCOUNT_AUTH_REQ:2102,NEW_ORDER_REQ:2106,CANCEL_ORDER_REQ:2108,AMEND_ORDER_REQ:2109,AMEND_POSITION_SLTP_REQ:2110,CLOSE_POSITION_REQ:2111,ASSET_LIST_REQ:2112,SYMBOLS_LIST_REQ:2114,SYMBOL_BY_ID_REQ:2116} as const;
export function envelope(payloadType:number,payload:Record<string,unknown>,clientMsgId:string):OAEnvelope{
 if(!clientMsgId)throw new Error('CLIENT_MSG_ID_REQUIRED'); return {clientMsgId,payloadType,payload};
}
