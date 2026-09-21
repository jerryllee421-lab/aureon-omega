import { handler } from '../backend/index.ts';
import { runtimeConfigurationIssues, configuredModel } from '../backend/runtime.ts';
import { database, ownerUserId } from '../server/database.ts';
import { sign, verify } from '../server/proof.ts';
import { harden } from '../server/authority.ts';
import { registerMonitor,checkMonitors,monitorSummary } from '../server/monitor.ts';
import { referenceQuote } from '../server/market.ts';
import { researchSummary } from '../server/research.ts';
import { multiTimeframeQuant } from '../server/quant.ts';
import { marketSessions } from '../server/session.ts';
import { randomUUID, createHash, timingSafeEqual } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';
type Request = IncomingMessage & { body?: any };
const roles = ['STRUCTURE ANALYST','OPPORTUNITY ANALYST','RISK CRITIC'];
export default async function api(req: Request, res: ServerResponse) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Type','application/json');
  const startedAt=Date.now();
  const requestId=typeof req.headers['x-request-id']==='string'&&/^[A-Za-z0-9._-]{1,80}$/.test(req.headers['x-request-id'])?req.headers['x-request-id']:randomUUID();
  res.setHeader('X-Request-Id',requestId);
  const requestUrl = new URL(req.url || '/', 'https://aureon.invalid');
  const path = requestUrl.pathname;
  const method = req.method || 'GET';
  const send = (status:number,data:unknown) => {
    res.statusCode=status;res.end(JSON.stringify(data));
    console.info(JSON.stringify({service:'aureon-api',requestId,method,path,status,durationMs:Date.now()-startedAt}));
  };
  try {
    if (method === 'GET' && path === '/api/config') return send(200, { accessMode:'SINGLE_OWNER_SERVER_BOUND' });
    if (method === 'GET' && path === '/api/status') {
      const response = await handler(method,path,{}); return send(response.status, await response.json());
    }
    if (method === 'GET' && path === '/api/health') {
      const issues=await runtimeConfigurationIssues();
      const dbStarted=Date.now();let databaseReady=true;let databaseLatencyMs:number|null=null;
      try{await database('scans?select=id&limit=1');databaseLatencyMs=Date.now()-dbStarted;}catch{databaseReady=false;}
      const ready=issues.length===0&&databaseReady;
      return send(ready?200:503,{ready,model:configuredModel(),database:{ready:databaseReady,latencyMs:databaseLatencyMs},issues,generatedAt:new Date().toISOString()});
    }
    if (method === 'GET' && path === '/api/cron/monitor') {
      const configured=process.env.CRON_SECRET;const supplied=req.headers.authorization;
      if(!configured||configured.length<32||typeof supplied!=='string') return send(401,{error:'CRON_AUTH_REQUIRED'});
      const expected=Buffer.from('Bearer '+configured),actual=Buffer.from(supplied);
      if(expected.length!==actual.length||!timingSafeEqual(expected,actual)||!process.env.OWNER_USER_ID) return send(401,{error:'CRON_AUTH_REQUIRED'});
      return send(200,await checkMonitors(process.env.OWNER_USER_ID));
    }
    const userId = ownerUserId();
    if (method === 'GET' && path === '/api/monitor') return send(200,await monitorSummary(userId));
    if (method === 'GET' && path === '/api/quant') {
      const symbol=String(requestUrl.searchParams.get('symbol')||'BTCUSD').toUpperCase();
      if(!['BTCUSD','XAUUSD'].includes(symbol))return send(400,{error:'EXACT_INSTRUMENT_UNSUPPORTED'});
      return send(200,await multiTimeframeQuant(symbol));
    }
    if (method === 'GET' && path === '/api/journal') return send(200, await database(`scans?user_id=eq.${userId}&select=id,created_at,result&order=created_at.desc&limit=50`));
    if (method === 'GET' && path === '/api/events') return send(200, await database(`setup_events?user_id=eq.${userId}&order=created_at.desc&limit=100`));
    if (method === 'GET' && path === '/api/research') return send(200,await researchSummary(userId));
    if (method === 'GET' && path === '/api/diagnostics') {
      const issues=await runtimeConfigurationIssues();const dbStarted=Date.now();let databaseReady=true;let databaseLatencyMs:number|null=null;
      try{await database('scans?select=id&limit=1');databaseLatencyMs=Date.now()-dbStarted;}catch{databaseReady=false;}
      const providerResults=await Promise.allSettled(['XAUUSD','BTCUSD'].map(referenceQuote));
      const cronReady=Boolean(process.env.CRON_SECRET&&process.env.CRON_SECRET.length>=32);
      const goldReady=Boolean(process.env.TWELVE_DATA_API_KEY);
      const obsoleteLongLivedSecrets=['AI_API_KEY','SUPABASE_SECRET_KEY','SUPABASE_SERVICE_ROLE_KEY','PIPELINE_SIGNING_KEY'].filter(k=>Boolean(process.env[k]));
      const capabilities={
        astra:{state:issues.some(v=>v.includes('AI_'))?'BLOCKED':'ACTIVE',detail:configuredModel()},
        database:{state:databaseReady?'ACTIVE':'BLOCKED',detail:databaseReady?'OIDC privileged bridge ready':'Privileged database bridge unavailable'},
        btcData:{state:'ACTIVE',detail:'Coinbase + Kraken reference adapters with fail-closed disagreement checks'},
        goldData:{state:goldReady?'ACTIVE':'NEEDS_PROVIDER_KEY',detail:goldReady?'Twelve Data XAU/USD enabled':'TWELVE_DATA_API_KEY is not configured'},
        quant:{state:'ACTIVE',detail:'M5 / M15 / H1 / H4 closed-candle context'},
        forwardMonitor:{state:'ACTIVE',detail:'Owner-triggered closed-candle reference monitoring'},
        scheduledMonitor:{state:cronReady?'ACTIVE':'BLOCKED',detail:cronReady?'Authenticated daily cron configured':'CRON_SECRET missing or too short'},
        highFrequencyMonitor:{state:'NOT_PROVISIONED',detail:'Current production schedule is daily/coarse; no continuous scanner is claimed'},
        brokerQuoteAuthority:{state:'NOT_IMPLEMENTED',detail:'Reference data is not a broker execution feed'},
        brokerExecution:{state:'DISABLED',detail:'Manual execution only; zero order endpoints'},
        chartArchive:{state:'NOT_IMPLEMENTED',detail:'Raw uploaded chart images are not retained'},
        strategyQualification:{state:'RESEARCH_ONLY',detail:'No profitability claim until execution-quality forward evidence exists'},
      };
      return send(200,{health:{ready:issues.length===0&&databaseReady,model:configuredModel(),database:{ready:databaseReady,latencyMs:databaseLatencyMs},issues},
        providers:providerResults.map((r,i)=>r.status==='fulfilled'?r.value:{symbol:['XAUUSD','BTCUSD'][i],authority:'UNAVAILABLE',reason:'Provider request failed.'}),
        capabilities,sessions:marketSessions(),obsoleteLongLivedSecrets,generatedAt:new Date().toISOString()});
    }
    if (method === 'GET' && path === '/api/market') {
      const settled = await Promise.allSettled(['XAUUSD','BTCUSD'].map(referenceQuote));
      return send(200, settled.map((r,i) => r.status === 'fulfilled' ? r.value : { symbol: ['XAUUSD','BTCUSD'][i], price:null, authority:'UNAVAILABLE', executionEligible:false, reason:'Provider request failed.' }));
    }
    let body = req.body;
    if (body === undefined) {
      const chunks: Buffer[] = []; let bytes = 0;
      for await (const chunk of req) { bytes += chunk.length; if (bytes > 3_800_000) return send(413,{error:'PAYLOAD_TOO_LARGE'}); chunks.push(Buffer.from(chunk)); }
      body = JSON.parse(Buffer.concat(chunks).toString() || '{}');
    } else if (typeof body === 'string') body = JSON.parse(body);
    if (!body || Array.isArray(body) || typeof body !== 'object' || Buffer.byteLength(JSON.stringify(body)) > 3_800_000) return send(400,{error:'INVALID_PAYLOAD'});
    if (method === 'POST' && path === '/api/monitor/register') return send(200,await registerMonitor(userId,body.scanId,body.opportunityIndex));
    if (method === 'POST' && path === '/api/monitor/check') return send(200,await checkMonitors(userId));
    if (method === 'POST' && path === '/api/events') {
      if (typeof body.scanId !== 'string' || !/^[0-9a-f-]{36}$/.test(body.scanId) || !Number.isInteger(body.opportunityIndex) || !['WATCH','INVALIDATED','EXPIRED','CLOSED'].includes(body.state) || typeof body.note !== 'string' || body.note.length > 3000) return send(400,{error:'INVALID_EVENT'});
      // A note is explicitly user supplied; it never upgrades readiness or records invented fills.
      return send(200, await database('rpc/record_setup_event','POST',{ p_user:userId, p_scan:body.scanId, p_index:body.opportunityIndex, p_state:body.state, p_note:body.note }));
    }
    if (method !== 'POST' || !['/api/analyze/vision','/api/analyze/specialist','/api/analyze/final'].includes(path)) return send(404,{error:'NOT_FOUND'});
    if ((await runtimeConfigurationIssues()).length) return send(503,{error:'ENGINE_UNCONFIGURED'});
    let context: any; let stage = 'VISION'; let input: any;
    if (path.endsWith('/vision')) {
      if (!Array.isArray(body.imageDataUrls) || body.imageDataUrls.length < 1 || body.imageDataUrls.length > 4 || body.imageDataUrls.some((v: unknown) => typeof v !== 'string' || !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(v))) return send(400,{error:'VALID_IMAGE_DATA_REQUIRED'});
      const hints = Object.fromEntries(['symbolHint','timeframeHint','session','tradeMode'].map(k => [k, typeof body[k] === 'string' ? body[k].slice(0,40) : null]));
      context = { runId:randomUUID(), hints, chartHashes: body.imageDataUrls.map((image: string) => createHash('sha256').update(image).digest('hex')) }; input = { ...hints, imageDataUrls:body.imageDataUrls };
    } else {
      context = await verify(body.visionProof,userId,'VISION');
      input = { ...context.hints, canonical:context.canonical, vision:context.report };
      if (path.endsWith('/specialist')) {
        if (!roles.includes(body.role)) return send(400,{error:'VALID_SPECIALIST_ROLE_REQUIRED'});
        stage = body.role; input.role = stage;
      } else {
        stage = 'FINAL'; const reports: any[] = [];
        for (const envelope of Array.isArray(body.reports) ? body.reports : []) {
          if (!roles.includes(envelope.role) || reports.some(v => v.role === envelope.role)) return send(400,{error:'INVALID_SPECIALIST_REPORTS'});
          const signed = await verify(envelope.proof,userId,envelope.role);
          if (signed.runId !== context.runId) return send(400,{error:'CROSS_SCAN_REPORT_REJECTED'});
          reports.push(signed.report);
        }
        input.reports = reports;
        input.failures = roles.filter(role => !reports.some(v=>v.role === role)).map(role=>({role,code:'UNAVAILABLE'}));
      }
    }
    // Distributed quota and per-stage replay protection; no process-memory limiter.
    const permitted = await database('rpc/claim_analysis_stage','POST',{ p_user:userId, p_run:context.runId, p_stage:stage });
    if (!permitted) return send(429,{error:'RATE_LIMIT_OR_STAGE_ALREADY_USED'});
    const response = await handler(method,path,input);
    const data = await response.json();
    if (!response.ok) return send(response.status,data);
    if (stage === 'VISION') data.proof = await sign({...context,canonical:data.canonical,report:data.report},userId,stage);
    else if (stage !== 'FINAL') data.proof = await sign({runId:context.runId,report:data},userId,stage);
    else {
      harden(data,context.canonical); data.scanId = context.runId; data.chartHashes = context.chartHashes;
      await database('scans','POST',{id:context.runId,user_id:userId,canonical:context.canonical,result:data,engine_version:'aureon-migration-1'});
      data.persisted = true;
    }
    return send(200,data);
  } catch (caught) {
    const code = caught instanceof Error ? caught.message : 'REQUEST_FAILED';
    const status = code === 'INVALID_STAGE_PROOF' ? 400 : 503;
    const allowed = ['OWNER_UNCONFIGURED','INVALID_STAGE_PROOF','DATABASE_UNCONFIGURED','DATABASE_REQUEST_FAILED','AUTH_UNCONFIGURED','SIGNING_KEY_UNCONFIGURED','SIGNING_SERVICE_UNAVAILABLE'];
    return send(status,{error:allowed.includes(code) ? code : 'REQUEST_FAILED'});
  }
}
