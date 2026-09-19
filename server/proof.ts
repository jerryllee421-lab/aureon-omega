import { createHmac, timingSafeEqual } from 'node:crypto';
import { getVercelOidcToken } from '@vercel/oidc';

const SERVICE_URL='https://hfjglluombfnrwslfbuw.supabase.co/functions/v1/aureon-service';
const TEAM_ID='team_FPtl41FOOM8ICOLcwunfkyf8';

function onVercel(){return Boolean(process.env.VERCEL||process.env.VERCEL_OIDC_TOKEN);}
function localSecret(){
  const source=process.env.PIPELINE_SIGNING_KEY||process.env.SUPABASE_SECRET_KEY||process.env.SUPABASE_SERVICE_ROLE_KEY;
  if(!source||source.length<32)throw new Error('SIGNING_KEY_UNCONFIGURED');
  return createHmac('sha256',source).update('AUREON_PIPELINE_SIGNING_V1').digest();
}
async function serviceCall(input:Record<string,unknown>){
  const token=await getVercelOidcToken({
    audience:SERVICE_URL,
    project:process.env.VERCEL_PROJECT_ID||'aureon-omega',
    team:process.env.VERCEL_TEAM_ID||TEAM_ID,
    expirationBufferMs:60_000,
  });
  if(!token)throw new Error('SIGNING_SERVICE_UNAVAILABLE');
  const r=await fetch(SERVICE_URL,{
    method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},
    body:JSON.stringify(input),signal:AbortSignal.timeout(15000),
  });
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(data.error==='INVALID_STAGE_PROOF'?'INVALID_STAGE_PROOF':'SIGNING_SERVICE_UNAVAILABLE');
  return data;
}

export async function sign(payload:unknown,userId:string,stage:string){
  if(onVercel()){
    const data=await serviceCall({operation:'proof_sign',payload,userId,stage});
    if(typeof data.token!=='string')throw new Error('SIGNING_SERVICE_UNAVAILABLE');
    return data.token;
  }
  const body=Buffer.from(JSON.stringify({payload,userId,stage,expires:Date.now()+15*60_000})).toString('base64url');
  return body+'.'+createHmac('sha256',localSecret()).update(body).digest('base64url');
}

export async function verify(token:unknown,userId:string,stage:string):Promise<any>{
  if(onVercel()){
    const data=await serviceCall({operation:'proof_verify',token,userId,stage});
    return data.payload;
  }
  if(typeof token!=='string'||token.length>250_000)throw new Error('INVALID_STAGE_PROOF');
  const [body,mac,extra]=token.split('.');
  if(!body||!mac||extra)throw new Error('INVALID_STAGE_PROOF');
  const expected=createHmac('sha256',localSecret()).update(body).digest(),actual=Buffer.from(mac,'base64url');
  if(actual.length!==expected.length||!timingSafeEqual(actual,expected))throw new Error('INVALID_STAGE_PROOF');
  const decoded=JSON.parse(Buffer.from(body,'base64url').toString());
  if(decoded.userId!==userId||decoded.stage!==stage||decoded.expires<=Date.now())throw new Error('INVALID_STAGE_PROOF');
  return decoded.payload;
}
