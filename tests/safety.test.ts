// Artificial values below are isolated safety-test fixtures, never market feeds.
import test from 'node:test';
import assert from 'node:assert/strict';
import { sign, verify } from '../server/proof.ts';
import { harden, numbers } from '../server/authority.ts';
import { normalizeOpportunity } from '../backend/index.ts';
import { validateSchema, configurationIssues } from '../backend/runtime.ts';
import api from '../api/[...path].ts';
import { createServer } from 'node:http';

process.env.PIPELINE_SIGNING_KEY = 'test-only-signing-key-with-32-characters';
test('signed stages reject cross-user, cross-stage and changed payloads',()=>{
 const proof=sign({runId:'test-run',canonical:{symbol:'TEST'}},'owner','VISION');
 assert.equal(verify(proof,'owner','VISION').runId,'test-run');
 assert.throws(()=>verify(proof,'attacker','VISION'));
 assert.throws(()=>verify(proof,'owner','RISK CRITIC'));
 const [body,mac]=proof.split('.');
 const altered=JSON.parse(Buffer.from(body,'base64url').toString());altered.payload.canonical.symbol='ALTERED';
 assert.throws(()=>verify(Buffer.from(JSON.stringify(altered)).toString('base64url')+'.'+mac,'owner','VISION'));
});
test('expired stage cannot authorize a later analysis',()=>{
 const now=Date.now; Date.now=()=>1000; const proof=sign({},'owner','VISION'); Date.now=()=>10000000;
 try {assert.throws(()=>verify(proof,'owner','VISION'));} finally {Date.now=now;}
});
test('maximal AI gates never grant execution authority',()=>{
 const opportunity=normalizeOpportunity({direction:'BUY',status:'CONFIRMED',entryZone:'100',stopLoss:'95',tp1:'110',trigger:'AI claim',invalidation:'AI claim',gates:{structure:'HIGH',trigger:'CONFIRMED',invalidation:'CLEAR',target:'CLEAR',mtf:'ALIGNED',contradiction:'LOW'}},3);
 assert.equal(opportunity.executable,false);
});
const canonical={overallImageQuality:'GOOD',charts:[{symbol:'TESTUSD',priceScaleVisible:true,imageQuality:'GOOD',currentPrice:'100',levels:{support:['95'],resistance:['110','120'],swingHighs:[],swingLows:[]}}]};
function fixture() {return {opportunities:[{direction:'BUY',entryZone:'100',stopLoss:'95',tp1:'110',tp2:'120',tp3:'900',rr1:'1:99',readinessScore:100,executable:true}],tradePlan:{entryZone:'100',stopLoss:'95'},limitations:[]};}
test('unobserved target removed; RR recalculated from supported levels',()=>{
 const r=harden(fixture(),canonical); const o=r.opportunities[0];
 assert.equal(o.tp3,null);assert.equal(o.rr1,'1:2.00');assert.equal(o.rr2,'1:4.00');assert.equal(o.executable,false);assert.equal(r.tradePlan.entryZone,null);
});
test('invalid stop geometry blocks numeric risk calculation',()=>{
 const r=fixture();r.opportunities[0].stopLoss='110';const o=harden(r,canonical).opportunities[0];
 assert.equal(o.stopLoss,null);assert.equal(o.rr1,null);assert.ok(o.readinessScore<=55);
});
test('conflicting instruments reject the opportunity pack',()=>{
 const r=harden(fixture(),{...canonical,charts:[...canonical.charts,{...canonical.charts[0],symbol:'OTHERUSD'}]});assert.equal(r.opportunities.length,0);assert.equal(r.decision,'WAIT');
});
test('numeric parser rejects descriptive guesses and malformed input',()=>{
 for(const value of ['around 100','1e5','-100','NaN','100/200','']) assert.deepEqual(numbers(value),[]);
 assert.deepEqual(numbers('1,234.50 – 1,240'),[1234.5,1240]);
});
test('schema validator rejects missing, extra and wrong-type fields',()=>{
 const schema={type:'object',properties:{level:{type:'number'}},required:['level']};
 assert.equal(validateSchema({level:1},schema),true);assert.equal(validateSchema({level:'1'},schema),false);assert.equal(validateSchema({},schema),false);assert.equal(validateSchema({level:1,hidden:2},schema),false);
});
test('unconfigured API reports blocked state and denies journal access',async()=>{
 const server=createServer((req,res)=>void api(req,res));await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
 const address=server.address();assert.ok(address&&typeof address==='object');
 try {const base=`http://127.0.0.1:${address.port}`;
 const status=await (await fetch(base+'/api/status')).json();assert.equal(status.ready,false);assert.ok(configurationIssues().length);
 const r=await fetch(base+'/api/journal');assert.notEqual(r.status,200);
 const payload=await r.json();assert.ok(payload.error);assert.equal(payload.result,undefined);
 } finally {await new Promise<void>(resolve=>server.close(()=>resolve()));}
});
