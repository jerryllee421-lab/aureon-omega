import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import api from '../api/[...path].ts';

const owner='11111111-1111-4111-8111-111111111111';

async function start(){
  const server=createServer((req,res)=>void api(req,res));
  await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
  const address=server.address();
  assert.ok(address&&typeof address==='object');
  return {server,base:`http://127.0.0.1:${address.port}`};
}

test('single-owner mode needs no browser auth but remains server-bound',async()=>{
  const keys=['SUPABASE_URL','SUPABASE_SECRET_KEY','SUPABASE_PUBLISHABLE_KEY','OWNER_USER_ID','CRON_SECRET','VERCEL','VERCEL_OIDC_TOKEN'] as const;
  const saved=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
  const clientFetch=globalThis.fetch;
  let observedDatabaseUrl='';

  process.env.SUPABASE_URL='https://unit-test.supabase.co';
  process.env.SUPABASE_SECRET_KEY='sb_secret_test_server_only';
  process.env.SUPABASE_PUBLISHABLE_KEY='sb_publishable_must_not_be_exposed';
  process.env.OWNER_USER_ID=owner;
  process.env.CRON_SECRET='test-only-cron-secret-that-is-over-32-bytes';
  delete process.env.VERCEL;
  delete process.env.VERCEL_OIDC_TOKEN;

  globalThis.fetch=async(input:any)=>{
    const url=typeof input==='string'?input:input?.url||String(input);
    if(url.startsWith('https://unit-test.supabase.co/rest/v1/scans?')){
      observedDatabaseUrl=url;
      return new Response(JSON.stringify([]),{status:200,headers:{'content-type':'application/json'}});
    }
    throw new Error('UNEXPECTED_NETWORK_CALL:'+url);
  };

  const {server,base}=await start();
  try{
    const config=await clientFetch(base+'/api/config');
    assert.equal(config.status,200);
    const publicConfig=await config.json();
    assert.deepEqual(publicConfig,{accessMode:'SINGLE_OWNER_SERVER_BOUND'});
    assert.equal(JSON.stringify(publicConfig).includes('supabase'),false);
    assert.equal(JSON.stringify(publicConfig).includes('publishable'),false);

    const journal=await clientFetch(base+'/api/journal');
    assert.equal(journal.status,200);
    assert.deepEqual(await journal.json(),[]);
    assert.ok(observedDatabaseUrl.includes('user_id=eq.'+owner),'journal query must remain owner-scoped');

    const invalidQuant=await clientFetch(base+'/api/quant?symbol=ETHUSD');
    assert.equal(invalidQuant.status,400);
    assert.equal((await invalidQuant.json()).error,'EXACT_INSTRUMENT_UNSUPPORTED');

    const invalidAnalyze=await clientFetch(base+'/api/analyze/vision',{
      method:'POST',headers:{'content-type':'application/json'},body:'{}'
    });
    assert.equal(invalidAnalyze.status,400);
    assert.equal((await invalidAnalyze.json()).error,'VALID_IMAGE_DATA_REQUIRED');

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

test('missing server owner binding fails closed',async()=>{
  const saved=process.env.OWNER_USER_ID;
  delete process.env.OWNER_USER_ID;
  const {server,base}=await start();
  try{
    const r=await fetch(base+'/api/journal');
    assert.equal(r.status,503);
    assert.equal((await r.json()).error,'OWNER_UNCONFIGURED');
  }finally{
    if(saved===undefined)delete process.env.OWNER_USER_ID;else process.env.OWNER_USER_ID=saved;
    await new Promise<void>(resolve=>server.close(()=>resolve()));
  }
});
