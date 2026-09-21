import {useEffect,useState,type FormEvent} from 'react';
import App from './App';import MonitorPanel from './MonitorPanel';import {api,setSession,clearSession} from './api';
type Config={supabaseUrl:string|null;publishableKey:string|null};
type Health={ready:boolean;model:string;database:{ready:boolean;latencyMs:number|null};issues:string[]};
type SavedScan={id:string;created_at:string;result:{decision:string;readinessScore:number;opportunities:{setupType:string;direction:string;thesis:string}[]}};
type Quote={symbol:string;price:number|null;bid?:number|null;ask?:number|null;spreadBps?:number|null;crossProviderDeviationBps?:number|null;authority:string;reason:string;provider?:string;providerInstrument?:string;sourceTimestamp?:string|null};
type Event={id:string;scan_id:string;opportunity_index:number;state:string;note:string;created_at:string};
type Strategy={family:string;registered:number;evidenceMaturity:string;states:Record<string,number>;providerErrors:number;favorableRObserved:{count:number;mean:number|null;max:number|null};adverseRObserved:{count:number;mean:number|null;max:number|null}};
type Research={scope:{scans:number;monitoredSetups:number};qualification:string;explanation:string;strategies:Strategy[]};
type QuantFrame={status:string;timeframe:string;provider?:string;providerInstrument?:string;close?:number;ema20?:number;ema50?:number;rsi14?:number;atr14?:number;atrPercent?:number;adx14?:number;recentHigh?:number;recentLow?:number;structure?:string;bias?:string;regime?:string;lastClosedAt?:string;reason?:string;authority:string;executionEligible:false};
type SessionSnapshot={generatedAt:string;ownerLocal:{zone:string;localDate:string;localTime:string;weekday:string};london:{localTime:string;weekday:string;active:boolean;openWindow:boolean};newYork:{localTime:string;weekday:string;active:boolean;openWindow:boolean};overlap:boolean;focusWindow:string;authority:string;explanation:string};
type Capability={state:string;detail:string};
type Diagnostics={health:Health;providers:Quote[];capabilities:Record<string,Capability>;sessions:SessionSnapshot;obsoleteLongLivedSecrets:string[];generatedAt:string};
type QuantResult={symbol:string;generatedAt:string;authority:string;executionEligible:false;explanation:string;mtf:{alignment:string;up:number;down:number;neutral:number};sessions:SessionSnapshot;frames:QuantFrame[]};

export default function Workspace(){
 const [config,setConfig]=useState<Config|null>(null),[health,setHealth]=useState<Health|null>(null),[signedIn,setSignedIn]=useState(false);
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[magicSent,setMagicSent]=useState(false);
 const [tab,setTab]=useState('scanner'),[scans,setScans]=useState<SavedScan[]>([]),[quotes,setQuotes]=useState<Quote[]>([]),[events,setEvents]=useState<Event[]>([]);
 const [research,setResearch]=useState<Research|null>(null),[quant,setQuant]=useState<QuantResult|null>(null),[quantSymbol,setQuantSymbol]=useState('BTCUSD'),[diagnostics,setDiagnostics]=useState<Diagnostics|null>(null),[note,setNote]=useState(''),[loaded,setLoaded]=useState(false);
 useEffect(()=>{
  Promise.all([api.get('/api/config'),api.get('/api/health')]).then(async([c,h])=>{
   setConfig(c.data);setHealth(h.data);
   const hash=new URLSearchParams(window.location.hash.replace(/^#/,''));
   const accessToken=hash.get('access_token'),refreshToken=hash.get('refresh_token');
   if(accessToken&&c.data?.supabaseUrl&&c.data?.publishableKey){
    setBusy(true);setError('');
    try{
     setSession({accessToken,refreshToken:refreshToken||null,supabaseUrl:c.data.supabaseUrl,publishableKey:c.data.publishableKey});
     await api.get('/api/journal');
     history.replaceState(null,'',window.location.pathname+window.location.search);
     setSignedIn(true);
    }catch{
     clearSession();setError('Secure sign-in link was invalid, expired, or not for the AUREON owner account.');
    }finally{setBusy(false);}
   }
  }).catch(()=>setError('Unable to reach the production health service.'));
 },[]);
 async function login(e:FormEvent){
  e.preventDefault();if(!config?.supabaseUrl||!config.publishableKey)return;setBusy(true);setError('');
  try{
   const r=await fetch(config.supabaseUrl+'/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:config.publishableKey,'Content-Type':'application/json'},body:JSON.stringify({email,password})});
   const data=await r.json();if(!r.ok||!data.access_token)throw new Error('Sign-in failed. Check your owner account credentials.');
   setSession({accessToken:data.access_token,refreshToken:data.refresh_token||null,supabaseUrl:config.supabaseUrl,publishableKey:config.publishableKey});
   await api.get('/api/journal');setPassword('');setSignedIn(true);
  }catch(e){clearSession();setError(e instanceof Error?e.message:'Sign-in failed.');}finally{setBusy(false);}
 }
 async function requestMagicLink(){
  if(!config?.supabaseUrl||!config.publishableKey||!email.trim())return;
  setBusy(true);setError('');setMagicSent(false);
  try{
   const redirectTo=window.location.origin+window.location.pathname;
   const r=await fetch(config.supabaseUrl+'/auth/v1/otp?redirect_to='+encodeURIComponent(redirectTo),{
    method:'POST',
    headers:{apikey:config.publishableKey,'Content-Type':'application/json'},
    body:JSON.stringify({email:email.trim(),create_user:false})
   });
   const data=await r.json().catch(()=>({}));
   if(!r.ok)throw new Error(data.msg||data.message||data.error_description||'Unable to send secure sign-in link.');
   setMagicSent(true);
  }catch(e){setError(e instanceof Error?e.message:'Unable to send secure sign-in link.');}
  finally{setBusy(false);}
 }
 async function refresh(){
  setBusy(true);setError('');setLoaded(false);
  try{
   if(tab==='journal'){const [s,e]=await Promise.all([api.get('/api/journal'),api.get('/api/events')]);setScans(s.data);setEvents(e.data);}
   else if(tab==='research')setResearch((await api.get('/api/research')).data);
   else if(tab==='quant')setQuant((await api.get('/api/quant?symbol='+encodeURIComponent(quantSymbol))).data);
   else {const [m,d]=await Promise.all([api.get('/api/market'),api.get('/api/diagnostics')]);setQuotes(m.data);setHealth(d.data.health);setDiagnostics(d.data);}
   setLoaded(true);
  }catch(e){setError(e instanceof Error?e.message:'Request failed.');}finally{setBusy(false);}
 }
 async function register(scanId:string,opportunityIndex:number){setBusy(true);setError('');try{await api.post('/api/monitor/register',{scanId,opportunityIndex});setTab('monitor');}catch(e){setError(e instanceof Error?e.message:'Could not register setup.');}finally{setBusy(false);}}
 async function record(scanId:string,opportunityIndex:number,state:string){
  if(!note.trim()){setError('Add an observation before recording a lifecycle event.');return;}setBusy(true);setError('');
  try{await api.post('/api/events',{scanId,opportunityIndex,state,note});setNote('');await refresh();}catch(e){setError(e instanceof Error?e.message:'Could not record event.');}finally{setBusy(false);}
 }
 const signOut=()=>{clearSession();setSignedIn(false);setScans([]);setEvents([]);setQuotes([]);setResearch(null);setQuant(null);setDiagnostics(null);setTab('scanner');};
 return <>
  <nav className='workspace-nav' aria-label='Workspace'><strong>AUREON Ω</strong>{signedIn&&<>
   <button onClick={()=>{setTab('scanner');setError('');}}>Scanner</button><button onClick={()=>{setTab('journal');setLoaded(false);}}>Journal</button>
   <button onClick={()=>setTab('monitor')}>Monitor</button><button onClick={()=>{setTab('quant');setLoaded(false);}}>Quant</button><button onClick={()=>{setTab('research');setLoaded(false);}}>Research</button>
   <button onClick={()=>{setTab('market');setLoaded(false);}}>Data truth</button><button onClick={signOut}>Sign out</button></>}</nav>
  {!signedIn?<main className='shell'><section className='scanner-card auth-panel'><div className='eyebrow'>ASTRA INTELLIGENCE ENGINE</div><h1>Your market workspace</h1>
   <p>Sign in to scan charts and keep an evidence-backed journal.</p>
   <p role='status'>Production health: <strong>{health?.ready?'READY':'CHECKING / BLOCKED'}</strong>{health?.model?' · '+health.model:''}</p>
   <form onSubmit={login}><label>Email<input type='email' autoComplete='username' required value={email} onChange={e=>setEmail(e.target.value)}/></label>
   <label>Password<input type='password' autoComplete='current-password' required value={password} onChange={e=>setPassword(e.target.value)}/></label>
   <button className='primary-button' disabled={busy||!config?.supabaseUrl}>{busy?'Signing in…':'Sign in'}</button></form>
   <div className='auth-divider'><span>OR</span></div>
   <button type='button' className='magic-link-button' disabled={busy||!config?.supabaseUrl||!email.trim()} onClick={()=>void requestMagicLink()}>{busy?'Working…':'Email me a secure sign-in link'}</button>
   <p className='muted'>Passwordless sign-in sends a one-time link to the email entered above. Existing users only — AUREON will not create a new account.</p>
   {magicSent&&<p role='status' className='magic-success'>Secure sign-in link sent. Open the email on this phone and tap the link to enter AUREON automatically.</p>}
   {error&&<p role='alert'>{error}</p>}
   <p className='muted'>Manual execution only. No broker orders. Session refresh tokens remain in memory only.</p></section></main>:<>
   {tab==='scanner'?<App/>:tab==='monitor'?<MonitorPanel/>:<main className='shell'><section className='scanner-card auth-panel'>
    <div className='eyebrow'>{tab==='journal'?'PERSISTENT EVIDENCE':tab==='research'?'RESEARCH EVIDENCE':tab==='quant'?'CLOSED-CANDLE QUANT':'PROVIDER VERIFICATION'}</div>
    <h1>{tab==='journal'?'Journal & setup monitor':tab==='research'?'Strategy evidence maturity':tab==='quant'?'Native multi-timeframe context':'Data truth & diagnostics'}</h1>
    <button onClick={()=>void refresh()} disabled={busy}>{busy?'Loading…':'Refresh'}</button>{error&&<p role='alert'>{error}</p>}
    {!loaded&&!busy&&<p>Refresh to load current evidence.</p>}
    {tab==='market'&&loaded&&<><p>Engine: <strong>{health?.ready?'READY':'BLOCKED'}</strong> · DB {health?.database?.ready?'READY':'BLOCKED'} {health?.database?.latencyMs!==null&&health?.database?.latencyMs!==undefined?'· '+health.database.latencyMs+' ms':''}</p>
     {diagnostics?.sessions&&<article className='journal-item'><h2>London / New York session engine</h2><p><strong>{diagnostics.sessions.focusWindow.replaceAll('_',' ')}</strong>{diagnostics.sessions.overlap?' · OVERLAP ACTIVE':''}</p><div className='session-grid'><div><span>LONDON</span><strong>{diagnostics.sessions.london.localTime}</strong><small>{diagnostics.sessions.london.active?'ACTIVE':'OFF'}{diagnostics.sessions.london.openWindow?' · OPEN WINDOW':''}</small></div><div><span>NEW YORK</span><strong>{diagnostics.sessions.newYork.localTime}</strong><small>{diagnostics.sessions.newYork.active?'ACTIVE':'OFF'}{diagnostics.sessions.newYork.openWindow?' · OPEN WINDOW':''}</small></div><div><span>OWNER LOCAL</span><strong>{diagnostics.sessions.ownerLocal.localTime}</strong><small>{diagnostics.sessions.ownerLocal.localDate}</small></div></div><small>{diagnostics.sessions.explanation}</small></article>}
     {diagnostics&&<article className='journal-item'><h2>Capability matrix</h2><div className='capability-grid'>{Object.entries(diagnostics.capabilities).map(([name,item])=><div key={name}><span>{name.replace(/([A-Z])/g,' $1').toUpperCase()}</span><strong>{item.state.replaceAll('_',' ')}</strong><small>{item.detail}</small></div>)}</div>{diagnostics.obsoleteLongLivedSecrets.length>0?<p role='status'>Cleanup available: obsolete production secret names detected — {diagnostics.obsoleteLongLivedSecrets.join(', ')}. Their values are never exposed.</p>:<p className='muted'>No obsolete long-lived production secret variables detected.</p>}</article>}
     {quotes.map(q=><article key={q.symbol} className='journal-item'><h2>{q.symbol} · {q.authority}</h2><p>{q.price===null?'Unavailable':q.price.toLocaleString(undefined,{maximumFractionDigits:2})}</p>
      {q.bid&&q.ask?<p>Bid {q.bid.toLocaleString()} · Ask {q.ask.toLocaleString()} · Spread {q.spreadBps?.toFixed(2)} bps</p>:null}
      {q.crossProviderDeviationBps!==null&&q.crossProviderDeviationBps!==undefined?<p>Cross-provider deviation: {q.crossProviderDeviationBps.toFixed(2)} bps</p>:null}
      <p>{q.provider} {q.providerInstrument||''}</p><p>{q.reason}</p><small>{q.sourceTimestamp?'Source time: '+q.sourceTimestamp:'Source timestamp unavailable'}</small></article>)}</>}
    {tab==='quant'&&<><label>Instrument<select value={quantSymbol} onChange={e=>{setQuantSymbol(e.target.value);setLoaded(false);setQuant(null);}}><option>BTCUSD</option><option>XAUUSD</option></select></label>
     {loaded&&quant?<><p><strong>{quant.symbol}</strong> · {quant.mtf.alignment.replaceAll('_',' ')} · UP {quant.mtf.up} / DOWN {quant.mtf.down} / NEUTRAL {quant.mtf.neutral}</p><p>Session focus: <strong>{quant.sessions.focusWindow.replaceAll('_',' ')}</strong>{quant.sessions.overlap?' · London/NY overlap':''}</p><p>{quant.explanation}</p>
      {quant.frames.map(frame=><article className='journal-item' key={frame.timeframe}><h2>{frame.timeframe} · {frame.status}</h2>{frame.status==='READY'?<><p>{frame.regime?.replaceAll('_',' ')} · Bias {frame.bias} · Structure {frame.structure}</p>
       <p>Close {frame.close} · EMA20 {frame.ema20} · EMA50 {frame.ema50}<br/>RSI14 {frame.rsi14} · ADX14 {frame.adx14} · ATR {frame.atr14} ({frame.atrPercent}%)</p>
       <p>20-bar range: {frame.recentLow} – {frame.recentHigh}</p><small>{frame.provider} {frame.providerInstrument} · Closed {frame.lastClosedAt} · {frame.authority.replaceAll('_',' ')}</small></>:<p>{frame.reason?.replaceAll('_',' ')||'Unavailable'}</p>}</article>)}</>:null}</>}
    {tab==='research'&&loaded&&<>{research?<><p>{research.explanation}</p><p>{research.scope.scans} scans · {research.scope.monitoredSetups} monitored setups · {research.qualification}</p>
     {research.strategies.length===0?<p>No monitored strategy evidence yet.</p>:research.strategies.map(s=><article className='journal-item' key={s.family}><h2>{s.family.replaceAll('_',' ')}</h2>
      <p>{s.registered} registered · {s.evidenceMaturity.replaceAll('_',' ')}</p><p>States: {Object.entries(s.states).map(([k,v])=>k.replaceAll('_',' ')+' '+v).join(' · ')||'none'}</p>
      <p>Observed favorable R: mean {s.favorableRObserved.mean??'—'} · max {s.favorableRObserved.max??'—'}<br/>Observed adverse R: mean {s.adverseRObserved.mean??'—'} · max {s.adverseRObserved.max??'—'}</p>
      <small>Provider errors: {s.providerErrors}. No win rate, expectancy or profit factor is inferred.</small></article>)}</>:null}</>}
    {tab==='journal'&&loaded&&<><p>Events are your observations. They do not certify fills, profit or execution readiness.</p><label>Observation<textarea maxLength={3000} value={note} onChange={e=>setNote(e.target.value)} placeholder='What changed in the setup?'/></label>
     {scans.length===0&&<p>No saved scans yet. Completed analyses will appear here.</p>}
     {scans.map(scan=><article className='journal-item' key={scan.id}><h2>{scan.result.decision.replaceAll('_',' ')}</h2><small>{new Date(scan.created_at).toLocaleString()}</small><p>Readiness {scan.result.readinessScore}/100 — not a win probability.</p>
      {scan.result.opportunities.map((o,index)=>{const history=events.filter(e=>e.scan_id===scan.id&&e.opportunity_index===index),terminal=history.some(e=>['CLOSED','INVALIDATED','EXPIRED'].includes(e.state));return <section key={index}><h3>{o.direction} · {o.setupType.replaceAll('_',' ')}</h3><p>{o.thesis}</p><div className='event-actions'><button disabled={busy||terminal} onClick={()=>void register(scan.id,index)}>Monitor price path</button>{['WATCH','INVALIDATED','EXPIRED','CLOSED'].map(state=><button key={state} disabled={busy||terminal} onClick={()=>void record(scan.id,index,state)}>{state}</button>)}</div>{history.map(e=><p key={e.id}><strong>{e.state}</strong> · {e.note}</p>)}</section>;})}</article>)}
     <p>Forward validation: no verified execution dataset yet. Expectancy, win rate and profit factor remain unavailable.</p></>}
   </section></main>}</>}
 </>;
}
