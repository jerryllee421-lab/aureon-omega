import { handler } from '../../backend/index.ts';
import { runtimeConfigurationIssues } from '../../backend/runtime.ts';
import { database, ownerUserId } from '../../server/database.ts';
import { harden } from '../../server/authority.ts';
import { randomUUID, createHash } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';

type Request = IncomingMessage & { body?: any };

export default async function scan(req: Request, res: ServerResponse) {
  res.setHeader('Cache-Control','no-store');
  res.setHeader('Content-Type','application/json');
  const startedAt=Date.now();
  const requestId=randomUUID();
  res.setHeader('X-Request-Id',requestId);
  const send=(status:number,data:unknown)=>{
    res.statusCode=status;
    res.end(JSON.stringify(data));
    console.info(JSON.stringify({service:'aureon-scan',requestId,method:req.method||'GET',path:'/api/analyze/scan',status,durationMs:Date.now()-startedAt}));
  };

  try{
    if((req.method||'GET')!=='POST') return send(405,{error:'METHOD_NOT_ALLOWED'});
    const userId=ownerUserId();

    if((await runtimeConfigurationIssues()).length) return send(503,{error:'ENGINE_UNCONFIGURED'});

    let body=req.body;
    if(body===undefined){
      const chunks:Buffer[]=[];
      let bytes=0;
      for await(const chunk of req){
        bytes+=chunk.length;
        if(bytes>2_000_000) return send(413,{error:'PAYLOAD_TOO_LARGE'});
        chunks.push(Buffer.from(chunk));
      }
      body=JSON.parse(Buffer.concat(chunks).toString()||'{}');
    }else if(typeof body==='string'){
      body=JSON.parse(body);
    }

    if(!body||Array.isArray(body)||typeof body!=='object') return send(400,{error:'INVALID_PAYLOAD'});
    if(!Array.isArray(body.imageDataUrls)||body.imageDataUrls.length!==1||
      body.imageDataUrls.some((v:unknown)=>typeof v!=='string'||!/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(v))){
      return send(400,{error:'VALID_IMAGE_DATA_REQUIRED'});
    }

    const runId=randomUUID();
    const chartHashes=body.imageDataUrls.map((image:string)=>createHash('sha256').update(image).digest('hex'));
    const permitted=await database('rpc/claim_analysis_stage','POST',{p_user:userId,p_run:runId,p_stage:'FINAL'});
    if(!permitted) return send(429,{error:'RATE_LIMIT_OR_STAGE_ALREADY_USED'});

    const response=await handler('POST','/api/analyze/scan',{
      symbolHint:typeof body.symbolHint==='string'?body.symbolHint.slice(0,40):null,
      timeframeHint:typeof body.timeframeHint==='string'?body.timeframeHint.slice(0,40):null,
      imageDataUrls:body.imageDataUrls,
    });
    const data=await response.json();
    if(!response.ok) return send(response.status,data);

    harden(data,data.canonical);
    data.scanId=runId;
    data.chartHashes=chartHashes;
    const canonical=data.canonical;
    await database('scans','POST',{
      id:runId,
      user_id:userId,
      canonical,
      result:data,
      engine_version:'astra-single-pass-v3',
    });
    delete data.canonical;
    data.persisted=true;
    return send(200,data);
  }catch(caught){
    const code=caught instanceof Error?caught.message:'REQUEST_FAILED';
    console.error('AUREON scan route failed',code);
    const allowed=['OWNER_UNCONFIGURED','DATABASE_UNCONFIGURED','DATABASE_REQUEST_FAILED','AI_OIDC_UNAVAILABLE'];
    return send(503,{error:allowed.includes(code)?code:'REQUEST_FAILED'});
  }
}
