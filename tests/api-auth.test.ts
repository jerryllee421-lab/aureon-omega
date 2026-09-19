import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import api from '../api/[...path].ts';

const owner='11111111-1111-4111-8111-111111111111';
const other='22222222-2222-4222-8222-222222222222';
const protectedGets=[
  '/api/monitor',
  '/api/quant?symbol=BTCUSD',
  '/api/journal',
  '/api/events',
  '/api/research',
  '/api/diagnostics',
  '/api/market',
];

async function start(){
  const server=createServer((req,res)=>void api(req,res));
  await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
  const address=server.address();
  assert.ok(address&&typeof address==='object');
  return {server,base:`http://127.0.0.1:${address.port}`};
}

test('owner API surface is fail-closed while public readiness routes stay read-only',async()=>{
  const keys=['SUPABASE_URL','SUPABASE_PUBLISHABLE_KEY','OWNER_USER_ID','CRON_SECRET','VERCEL','VERCEL_OIDC_TOKEN'] as const;
  const saved=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
  const clientFetch=globalThis.fetch;
  let authMode:'reject'|'other'='reject';

  process.env.SUPABASE_URL='https://unit-test.supabase.co';
  process.env.SUPABASE_PUBLISHABLE_KEY='sb_publishable_test_only';
  process.env.OWNER_USER_ID=owner;
  process.env.CRON_SECRET='test-only-cron-secret-that-is-over-32-bytes';
  delete process.env.VERCEL;
  delete process.env.VERCEL_OIDC_TOKEN;

  globalThis.fetch=async(input:any,init?:RequestInit)=>{
    const url=typeof input==='string'?input:input?.url||String(input);
    if(url==='https://unit-test.supabase.co/auth/v1/user'){
      if(authMode==='other')return new Response(JSON.stringify({id:other,is_anonymous:false}),{status:200,headers:{'content-type':'application/json'}});
      return new Response(JSON.stringify({error:'invalid token'}),{status:401,headers:{'content-type':'application/json'}});
    }
    throw new Error('UNEXPECTED_NETWORK_CALL:'+url+':'+String(init?.method||'GET'));
  };

  const {server,base}=await start();
  try{
    const config=await clientFetch(base+'/api/config');
    assert.equal(config.status,200);
    const publicConfig=await config.json();
    assert.equal(publicConfig.supabaseUrl,'https://unit-test.supabase.co');
    assert.equal(publicConfig.publishableKey,'sb_publishable_test_only');

    for(const path of protectedGets){
      const r=await clientFetch(base+path);
      assert.equal(r.status,401,path+' must reject missing owner bearer token');
      assert.equal((await r.json()).error,'SIGN_IN_REQUIRED');
    }

    const analyze=await clientFetch(base+'/api/analyze/vision',{method:'POST',headers:{'content-type':'application/json'},body:'{}'});
    assert.equal(analyze.status,401);
    assert.equal((await analyze.json()).error,'SIGN_IN_REQUIRED');

    const invalid=await clientFetch(base+'/api/market',{headers:{authorization:'Bearer invalid'}});
    assert.equal(invalid.status,401);
    assert.equal((await invalid.json()).error,'SIGN_IN_REQUIRED');

    authMode='other';
    const nonOwner=await clientFetch(base+'/api/market',{headers:{authorization:'Bearer valid-for-other-user'}});
    assert.equal(nonOwner.status,403);
    assert.equal((await nonOwner.json()).error,'OWNER_ACCESS_REQUIRED');

    const cronMissing=await clientFetch(base+'/api/cron/monitor');
    assert.equal(cronMissing.status,401);
    assert.equal((await cronMissing.json()).error,'CRON_AUTH_REQUIRED');

    const cronWrong=await clientFetch(base+'/api/cron/monitor',{headers:{authorization:'Bearer wrong-secret'}});
    assert.equal(cronWrong.status,401);
    assert.equal((await cronWrong.json()).error,'CRON_AUTH_REQUIRED');
  }finally{
    globalThis.fetch=clientFetch;
    for(const key of keys){
      const value=saved[key];
      if(value===undefined)delete process.env[key];else process.env[key]=value;
    }
    await new Promise<void>(resolve=>server.close(()=>resolve()));
  }
});
