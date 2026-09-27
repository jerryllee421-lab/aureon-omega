export type TokenRecord={accessToken:string;refreshToken:string;expiresAt:number};
export function tokenNeedsRefresh(t:TokenRecord,now=Date.now()){return t.expiresAt-now<24*60*60*1000;}
export function redactToken<T extends Record<string,unknown>>(v:T){const out={...v};for(const k of ['accessToken','refreshToken','clientSecret'])if(k in out)out[k]='[REDACTED]';return out;}
