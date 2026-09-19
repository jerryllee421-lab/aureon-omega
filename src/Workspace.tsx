import { useEffect, useState, type FormEvent } from 'react';
import App from './App';
import MonitorPanel from './MonitorPanel';
import { api, setAccessToken } from './api';
type Config = {supabaseUrl:string|null;publishableKey:string|null};
type SavedScan = {id:string;created_at:string;result:{decision:string;readinessScore:number;opportunities:{setupType:string;direction:string;thesis:string}[]}};
type Quote = {symbol:string;price:number|null;authority:string;reason:string;providerInstrument?:string;sourceTimestamp?:string|null};
type Event = {id:string;scan_id:string;opportunity_index:number;state:string;note:string;created_at:string};
export default function Workspace() {
  const [config,setConfig] = useState<Config|null>(null);
  const [signedIn,setSignedIn] = useState(false);
  const [email,setEmail] = useState(''); const [password,setPassword] = useState('');
  const [busy,setBusy] = useState(false); const [error,setError] = useState('');
  const [tab,setTab] = useState('scanner'); const [scans,setScans] = useState<SavedScan[]>([]);
  const [quotes,setQuotes] = useState<Quote[]>([]); const [events,setEvents] = useState<Event[]>([]);
  const [note,setNote] = useState(''); const [loaded,setLoaded] = useState(false);
  useEffect(()=>{api.get('/api/config').then(r=>setConfig(r.data)).catch(()=>setError('Unable to reach the application server.'));},[]);
  async function login(e:FormEvent) {
    e.preventDefault(); if (!config?.supabaseUrl || !config.publishableKey) return;
    setBusy(true);setError('');
    try {
      const r = await fetch(config.supabaseUrl + '/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:config.publishableKey,'Content-Type':'application/json'},body:JSON.stringify({email,password})});
      const data = await r.json(); if (!r.ok || !data.access_token) throw new Error('Sign-in failed. Check your owner account credentials.');
      setAccessToken(data.access_token);
      await api.get('/api/journal'); // Enforce server owner authorization before opening the desk.
      setPassword('');setSignedIn(true);
    } catch(e) {setAccessToken(null);setError(e instanceof Error?e.message:'Sign-in failed.');}
    finally {setBusy(false);}
  }
  async function refresh() {
    setBusy(true);setError('');setLoaded(false);
    try {
      if(tab==='journal') {const [s,e]=await Promise.all([api.get('/api/journal'),api.get('/api/events')]);setScans(s.data);setEvents(e.data);}
      else setQuotes((await api.get('/api/market')).data);
      setLoaded(true);
    } catch(e) {setError(e instanceof Error?e.message:'Request failed.');}
    finally {setBusy(false);}
  }
  async function register(scanId:string,opportunityIndex:number){setBusy(true);setError('');try{await api.post('/api/monitor/register',{scanId,opportunityIndex});setTab('monitor');}catch(e){setError(e instanceof Error?e.message:'Could not register setup.');}finally{setBusy(false);}}
  async function record(scanId:string,opportunityIndex:number,state:string) {
    if(!note.trim()) {setError('Add an observation before recording a lifecycle event.');return;}
    setBusy(true);setError('');
    try {await api.post('/api/events',{scanId,opportunityIndex,state,note});setNote('');await refresh();}
    catch(e) {setError(e instanceof Error?e.message:'Could not record event.');}
    finally {setBusy(false);}
  }
  return <>
    <nav className='workspace-nav' aria-label='Workspace'>
      <strong>AUREON Ω</strong>
      {signedIn && <><button onClick={()=>{setTab('scanner');setError('');}}>Scanner</button><button onClick={()=>{setTab('journal');setLoaded(false);setError('');}}>Journal</button><button onClick={()=>{setTab('monitor');setError('');}}>Monitor</button><button onClick={()=>{setTab('market');setLoaded(false);setError('');}}>Data truth</button><button onClick={()=>{setAccessToken(null);setSignedIn(false);setScans([]);setEvents([]);setQuotes([]);setTab('scanner');}}>Sign out</button></>}
    </nav>
    {!signedIn ? <main className='shell'><section className='scanner-card auth-panel'><div className='eyebrow'>ASTRA INTELLIGENCE ENGINE</div><h1>Your market workspace</h1><p>Sign in to scan charts and keep an evidence-backed journal.</p>
      {config && !config.supabaseUrl && <p role='status'>Workspace setup is incomplete. Authentication and analysis remain unavailable.</p>}
      <form onSubmit={login}><label>Email<input type='email' autoComplete='username' required value={email} onChange={e=>setEmail(e.target.value)}/></label><label>Password<input type='password' autoComplete='current-password' required value={password} onChange={e=>setPassword(e.target.value)}/></label><button className='primary-button' disabled={busy||!config?.supabaseUrl}>{busy?'Signing in…':'Sign in'}</button></form>
      {error&&<p role='alert'>{error}</p>}<p className='muted'>Manual execution only. No broker orders.</p></section></main> : <>
      {tab==='scanner' ? <App/> : tab==='monitor' ? <MonitorPanel/> : <main className='shell'><section className='scanner-card auth-panel'><div className='eyebrow'>{tab==='journal'?'PERSISTENT EVIDENCE':'PROVIDER VERIFICATION'}</div><h1>{tab==='journal'?'Journal & setup monitor':'Data truth'}</h1><button onClick={()=>void refresh()} disabled={busy}>{busy?'Loading…':'Refresh'}</button>{error&&<p role='alert'>{error}</p>}
      {!loaded&&!busy&&<p>Refresh to load your latest {tab==='journal'?'saved scans and lifecycle events':'provider references'}.</p>}
      {tab==='market'&&loaded&&quotes.map(q=><article key={q.symbol} className='journal-item'><h2>{q.symbol} · {q.authority}</h2><p>{q.price===null?'Unavailable':q.price.toLocaleString(undefined,{maximumFractionDigits:2})}</p><p>{q.providerInstrument}</p><p>{q.reason}</p><small>{q.sourceTimestamp?'Source time: '+q.sourceTimestamp:'Source timestamp unavailable'}</small></article>)}
      {tab==='journal'&&loaded&&<><p>Events are your observations. They do not certify fills, profit or execution readiness.</p><label>Observation<textarea maxLength={3000} value={note} onChange={e=>setNote(e.target.value)} placeholder='What changed in the setup?'/></label>{scans.length===0&&<p>No saved scans yet. Completed analyses will appear here.</p>}{scans.map(scan=><article className='journal-item' key={scan.id}><h2>{scan.result.decision.replaceAll('_',' ')}</h2><small>{new Date(scan.created_at).toLocaleString()}</small><p>Readiness {scan.result.readinessScore}/100 — not a win probability.</p>{scan.result.opportunities.map((o,index)=>{const history=events.filter(e=>e.scan_id===scan.id&&e.opportunity_index===index);const terminal=history.some(e=>['CLOSED','INVALIDATED','EXPIRED'].includes(e.state));return <section key={index}><h3>{o.direction} · {o.setupType.replaceAll('_',' ')}</h3><p>{o.thesis}</p><div className='event-actions'><button disabled={busy||terminal} onClick={()=>void register(scan.id,index)}>Monitor price path</button>{['WATCH','INVALIDATED','EXPIRED','CLOSED'].map(state=><button key={state} disabled={busy||terminal} onClick={()=>void record(scan.id,index,state)}>{state}</button>)}</div>{history.map(e=><p key={e.id}><strong>{e.state}</strong> · {e.note}</p>)}</section>;})}</article>)}<p>Forward validation: no verified outcome dataset yet. Expectancy, win rate and profit factor are unavailable.</p></>}
      </section></main>}
    </>}
  </>;
}
