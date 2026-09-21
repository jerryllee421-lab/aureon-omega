import {ChangeEvent,useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Crosshair,
  LoaderCircle,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Target,
  UploadCloud,
  X,
} from 'lucide-react';
import {api} from './api';

type AuthorityField={value:string|number|null;authority:string};
type Opportunity={
  direction:'BUY'|'SELL'|'NEUTRAL';
  status:string;
  setupType:string;
  timeframe:string;
  thesis:string;
  trigger:string|null;
  entryZone:string|null;
  stopLoss:string|null;
  tp1:string|null;
  tp2:string|null;
  tp3:string|null;
  rr1:string|null;
  rr2:string|null;
  rr3:string|null;
  invalidation:string|null;
  nextRequiredEvent:string|null;
  evidence:string[];
  contradictions:string[];
  readinessScore:number;
};
type ScanResult={
  scanId:string;
  generatedAt:string;
  leadModel:string;
  chartCount:number;
  imageQuality:string;
  symbol:AuthorityField;
  timeframe:AuthorityField;
  currentPrice:AuthorityField;
  decision:string;
  setupState:string;
  readinessScore:number;
  market:{bias?:string;structure?:string;volatility?:string;momentum?:string;mtfAlignment?:string};
  tradePlan:{
    direction:string|null;entryZone:string|null;stopLoss:string|null;
    tp1:string|null;tp2:string|null;tp3:string|null;
    rr1:string|null;rr2:string|null;rr3:string|null;
    trigger:string|null;invalidation:string|null;setupType:string|null;
  };
  opportunities:Opportunity[];
  nextRequiredEvent:string|null;
  nextBestInput:string|null;
  evidence:string[];
  contradictions:string[];
  limitations:string[];
  pipelineMs?:number;
};
type PreparedChart={id:string;name:string;previewUrl:string;dataUrl:string;kb:number;kind:'PRIMARY'|'CONTEXT'};
type EngineStatus={ready:boolean;engine:string;architecture:string;issue:string|null};

function label(value?:string|null){return value?value.replaceAll('_',' '):'—';}
function approxKb(dataUrl:string){const base64=dataUrl.split(',')[1]??'';return Math.round((base64.length*3/4)/1024);}
function errorText(error:unknown){
  const code=error instanceof Error?error.message:'SCAN_FAILED';
  if(code.includes('RATE_LIMIT'))return 'ASTRA is busy. Retry the scan.';
  if(code.includes('IMAGE_TOO_LARGE'))return 'The screenshot is too large. Crop unused phone UI and retry.';
  if(code.includes('VALID_IMAGE'))return 'Upload a valid chart screenshot.';
  if(code.includes('ENGINE_UNCONFIGURED'))return 'ASTRA is temporarily unavailable.';
  return code.replaceAll('_',' ');
}
function compressImage(file:File):Promise<string>{
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onerror=()=>reject(new Error('IMAGE_READ_FAILED'));
    reader.onload=()=>{
      const img=new Image();
      img.onerror=()=>reject(new Error('IMAGE_DECODE_FAILED'));
      img.onload=()=>{
        const maxSide=2048;
        const scale=Math.min(1,maxSide/Math.max(img.width,img.height));
        const canvas=document.createElement('canvas');
        canvas.width=Math.max(1,Math.round(img.width*scale));
        canvas.height=Math.max(1,Math.round(img.height*scale));
        const ctx=canvas.getContext('2d');
        if(!ctx)return reject(new Error('IMAGE_PROCESSING_FAILED'));
        ctx.drawImage(img,0,0,canvas.width,canvas.height);
        let output=canvas.toDataURL('image/jpeg',0.9);
        for(const quality of [0.84,0.78,0.72,0.66]){
          if(approxKb(output)<=1250)break;
          output=canvas.toDataURL('image/jpeg',quality);
        }
        if(approxKb(output)>1250&&Math.max(canvas.width,canvas.height)>1700){
          const reduced=document.createElement('canvas');
          const reduction=1700/Math.max(canvas.width,canvas.height);
          reduced.width=Math.max(1,Math.round(canvas.width*reduction));
          reduced.height=Math.max(1,Math.round(canvas.height*reduction));
          const reducedCtx=reduced.getContext('2d');
          if(reducedCtx){
            reducedCtx.drawImage(canvas,0,0,reduced.width,reduced.height);
            output=reduced.toDataURL('image/jpeg',0.8);
          }
        }
        resolve(output);
      };
      img.src=String(reader.result);
    };
    reader.readAsDataURL(file);
  });
}

export default function App(){
  const [engine,setEngine]=useState<EngineStatus|null>(null);
  const [charts,setCharts]=useState<PreparedChart[]>([]);
  const [busy,setBusy]=useState(false);
  const [result,setResult]=useState<ScanResult|null>(null);
  const [error,setError]=useState('');
  const fileRef=useRef<HTMLInputElement|null>(null);

  useEffect(()=>{api.get('/api/status').then(r=>setEngine(r.data)).catch(()=>setEngine({ready:false,engine:'ASTRA',architecture:'ASTRA_SINGLE_PASS_V3',issue:'UNAVAILABLE'}));},[]);
  useEffect(()=>()=>{charts.forEach(c=>URL.revokeObjectURL(c.previewUrl));},[charts]);

  const addFile=useCallback(async(event:ChangeEvent<HTMLInputElement>)=>{
    const file=event.target.files?.[0];event.target.value='';
    if(!file)return;
    setError('');
    if(!file.type.startsWith('image/')){setError('Upload a chart image.');return;}
    try{
      const dataUrl=await compressImage(file);
      const item:PreparedChart={
        id:crypto.randomUUID(),
        name:file.name,
        previewUrl:URL.createObjectURL(file),
        dataUrl,
        kb:approxKb(dataUrl),
        kind:charts.length===0?'PRIMARY':'CONTEXT'
      };
      setCharts(current=>{
        if(current.length>=2)return current;
        return [...current,item];
      });
      setResult(null);
    }catch(e){setError(errorText(e));}
  },[charts.length]);

  const removeChart=useCallback((id:string)=>{
    setCharts(current=>{
      const target=current.find(c=>c.id===id);
      if(target)URL.revokeObjectURL(target.previewUrl);
      return current.filter(c=>c.id!==id).map((c,i)=>({...c,kind:i===0?'PRIMARY':'CONTEXT'}));
    });
    setResult(null);setError('');
  },[]);

  const reset=useCallback(()=>{
    setCharts(current=>{current.forEach(c=>URL.revokeObjectURL(c.previewUrl));return[];});
    setResult(null);setError('');
  },[]);

  const scan=useCallback(async()=>{
    if(!charts.length||busy)return;
    setBusy(true);setResult(null);setError('');
    try{
      const response=await api.post('/api/analyze/scan',{imageDataUrls:charts.map(c=>c.dataUrl)});
      setResult(response.data as ScanResult);
    }catch(e){setError(errorText(e));}
    finally{setBusy(false);}
  },[charts,busy]);

  const best=result?.opportunities?.[0]??null;
  const decision=best?.direction==='BUY'?'BUY':best?.direction==='SELL'?'SELL':'WAIT';
  const hasPlan=Boolean(result?.tradePlan?.direction&&result.tradePlan.entryZone&&result.tradePlan.stopLoss);
  const evidence=useMemo(()=>result?.evidence?.slice(0,4)??[],[result]);
  const contradictions=useMemo(()=>result?.contradictions?.slice(0,3)??[],[result]);

  return <main className='astra-shell'>
    <header className='astra-header'>
      <div>
        <span className='astra-kicker'>AUREON Ω</span>
        <h1>ASTRA Chart Scanner</h1>
        <p>One chart. One deep AI scan. One clear decision.</p>
      </div>
      <span className={engine?.ready?'engine-dot ready':'engine-dot'}>{engine?.ready?'AI READY':'AI CHECK'}</span>
    </header>

    {!result&&<section className='scan-card'>
      <div className='upload-title'>
        <div><span>PRIMARY CHART</span><h2>{charts.length?'Chart ready':'Upload your trading chart'}</h2></div>
        <span className='chart-limit'>{charts.length}/2</span>
      </div>

      {charts.length===0?
        <button className='drop-button' onClick={()=>fileRef.current?.click()}>
          <UploadCloud size={34}/><strong>SELECT CHART SCREENSHOT</strong>
          <span>ASTRA automatically reads symbol, timeframe, price action and levels.</span>
        </button>:
        <div className='chart-stack'>
          {charts.map((chart,index)=><article className='chart-preview' key={chart.id}>
            <img src={chart.previewUrl} alt={chart.name}/>
            <div className='preview-bar'>
              <div><strong>{index===0?'PRIMARY':'OPTIONAL CONTEXT'}</strong><span>{chart.kb} KB</span></div>
              <button onClick={()=>removeChart(chart.id)} aria-label='Remove chart'><X size={17}/></button>
            </div>
          </article>)}
          {charts.length===1&&<button className='context-button' onClick={()=>fileRef.current?.click()}>
            <Plus size={18}/><div><strong>Add one context chart</strong><span>Optional — only if it genuinely helps.</span></div>
          </button>}
        </div>
      }
      <input ref={fileRef} className='hidden-input' type='file' accept='image/png,image/jpeg,image/webp' onChange={addFile}/>

      <div className='scan-guidance'>
        <ShieldCheck size={16}/>
        <span>Best results: clean candles, visible price scale, symbol and timeframe. No extra charts required.</span>
      </div>

      {error&&<div className='scan-error'><AlertTriangle size={17}/><span>{error}</span></div>}

      <button className='scan-button' disabled={!charts.length||busy||engine?.ready===false} onClick={()=>void scan()}>
        {busy?<><LoaderCircle className='spin' size={20}/>ASTRA IS READING THE CHART…</>:<><Sparkles size={20}/>SCAN FOR BEST SETUP</>}
      </button>
      {busy&&<p className='busy-copy'>Reading structure, liquidity, momentum, entry geometry and risk in one integrated pass.</p>}
    </section>}

    {result&&<section className='result-wrap'>
      <article className={'decision-card '+decision.toLowerCase()}>
        <div className='decision-top'>
          <div>
            <span>{label(String(result.symbol.value??'UNKNOWN'))} · {label(String(result.timeframe.value??'UNKNOWN'))}</span>
            <h2>{decision==='BUY'?<ArrowUpRight/>:decision==='SELL'?<ArrowDownRight/>:<Crosshair/>}{decision}</h2>
          </div>
          <div className='readiness'><strong>{result.readinessScore}</strong><span>READINESS</span></div>
        </div>
        <p className='decision-thesis'>{best?.thesis||'No setup currently meets the evidence threshold.'}</p>
        <div className='market-strip'>
          <div><span>BIAS</span><strong>{label(result.market?.bias)}</strong></div>
          <div><span>STRUCTURE</span><strong>{label(result.market?.structure)}</strong></div>
          <div><span>STATE</span><strong>{label(result.setupState)}</strong></div>
        </div>
      </article>

      {hasPlan&&<article className='trade-card'>
        <div className='card-heading'><Target size={19}/><h3>Trade plan</h3></div>
        <div className='levels-grid'>
          <div className='entry'><span>ENTRY</span><strong>{result.tradePlan.entryZone}</strong></div>
          <div className='stop'><span>STOP LOSS</span><strong>{result.tradePlan.stopLoss}</strong></div>
          <div><span>TP1</span><strong>{result.tradePlan.tp1||'—'}</strong><small>{result.tradePlan.rr1||''}</small></div>
          <div><span>TP2</span><strong>{result.tradePlan.tp2||'—'}</strong><small>{result.tradePlan.rr2||''}</small></div>
          <div><span>TP3</span><strong>{result.tradePlan.tp3||'—'}</strong><small>{result.tradePlan.rr3||''}</small></div>
        </div>
        {result.tradePlan.trigger&&<div className='trigger-box'><span>TRIGGER</span><strong>{result.tradePlan.trigger}</strong></div>}
        {result.tradePlan.invalidation&&<div className='invalid-box'><span>INVALIDATION</span><strong>{result.tradePlan.invalidation}</strong></div>}
      </article>}

      {!hasPlan&&<article className='wait-card'>
        <Crosshair size={22}/>
        <div><strong>{best?label(best.status)+' setup — not ready':'No valid setup yet'}</strong>
          <span>{result.nextRequiredEvent||best?.nextRequiredEvent||'Wait for clearer structure and a valid trigger.'}</span></div>
      </article>}

      {(evidence.length>0||best?.evidence?.length)&&<article className='evidence-card'>
        <div className='card-heading'><CheckCircle2 size={18}/><h3>Why ASTRA sees this</h3></div>
        {[...(best?.evidence??[]),...evidence].slice(0,5).map((item,i)=><p key={i}>{item}</p>)}
      </article>}

      {contradictions.length>0&&<article className='risk-card'>
        <div className='card-heading'><AlertTriangle size={18}/><h3>Risk / contradiction</h3></div>
        {contradictions.map((item,i)=><p key={i}>{item}</p>)}
      </article>}

      <div className='result-meta'>
        <span>{result.chartCount} chart{result.chartCount===1?'':'s'} · {result.pipelineMs??'—'} ms</span>
        <span>{result.leadModel}</span>
      </div>

      <button className='new-scan' onClick={reset}><RotateCcw size={18}/>NEW SCAN</button>
    </section>}

    <footer>AI chart analysis only · manual execution · verify live price before entering</footer>
  </main>;
}
