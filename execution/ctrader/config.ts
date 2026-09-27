export const CTRADER={
 demoHost:'demo.ctraderapi.com',jsonPort:5036,
 liveHost:'live.ctraderapi.com',jsonPortLive:5036,
 heartbeatMs:9000,nonHistoricalRps:40,historicalRps:4,
 liveExecutionEnabled:false
} as const;
export function assertDemoHost(host:string){if(host!==CTRADER.demoHost)throw new Error('LIVE_ENDPOINT_DISABLED');}
