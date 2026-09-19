import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { PGlite } from '@electric-sql/pglite';
const owner='11111111-1111-4111-8111-111111111111';
const other='22222222-2222-4222-8222-222222222222';
const scan='33333333-3333-4333-8333-333333333333';
test('Postgres schema enforces owner isolation, server-only writes, quota, replay and terminal lifecycle',async()=>{
 const db=new PGlite();
 try {
 await db.exec(`create role anon; create role authenticated; create role service_role bypassrls; create schema auth; create table auth.users(id uuid primary key); create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$; grant usage on schema auth to authenticated; grant execute on function auth.uid() to authenticated; insert into auth.users values('${owner}'),('${other}');`);
 await db.exec(await readFile(new URL('../database/schema.sql',import.meta.url),'utf8'));
 await db.exec(await readFile(new URL('../database/monitoring.sql',import.meta.url),'utf8'));
 await db.query('insert into scans(id,user_id,engine_version,canonical,result) values($1,$2,$3,$4,$5)',[scan,owner,'test',{}, {opportunities:[{setupType:'TEST_ONLY'}]}]);
 await db.exec(`set role authenticated; set request.jwt.claim.sub='${other}';`);
 assert.equal((await db.query('select * from scans')).rows.length,0);
 await db.exec(`set request.jwt.claim.sub='${owner}';`);
 assert.equal((await db.query('select * from scans')).rows.length,1);
 await assert.rejects(()=>db.query("update scans set result='{}'"));
 await assert.rejects(()=>db.query('select claim_analysis_stage($1,$2,$3)',[owner,scan,'VISION']));
 await db.exec('reset role; set role anon;');
 await assert.rejects(()=>db.query('select * from scans'));
 await db.exec('reset role; set role service_role;');
 const claim=async(stage:string)=>(await db.query<{ok:boolean}>('select claim_analysis_stage($1,$2,$3) as ok',[owner,scan,stage])).rows[0].ok;
 assert.equal(await claim('FINAL'),false);
 assert.equal(await claim('VISION'),true);assert.equal(await claim('VISION'),false);
 assert.equal(await claim('RISK CRITIC'),true);
 await db.query('select record_setup_event($1,$2,0,$3,$4)',[owner,scan,'WATCH','Observed by owner']);
 await assert.rejects(()=>db.query('select record_setup_event($1,$2,0,$3,$4)',[other,scan,'WATCH','Wrong owner']));
 await db.query('select record_setup_event($1,$2,0,$3,$4)',[owner,scan,'INVALIDATED','Setup invalidated']);
 await assert.rejects(()=>db.query('select record_setup_event($1,$2,0,$3,$4)',[owner,scan,'WATCH','Cannot reopen terminal state']));
 await db.exec(`insert into private.analysis_claims(user_id,run_id,stage) select '${owner}',gen_random_uuid(),'VISION' from generate_series(1,58)`);
 assert.equal(await claim('FINAL'),false);
 } finally {await db.close();}
});
