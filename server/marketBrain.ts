export type MarketBrainFrame={
  status?:string;
  timeframe:string;
  intervalMinutes:number;
  close?:number|null;
  atrPercent?:number|null;
  adx14?:number|null;
  structure?:string;
  bias?:string;
  regime?:string;
};

export type MarketBrainSessions={
  focusWindow?:string;
  london?:{active?:boolean;openWindow?:boolean};
  newYork?:{active?:boolean;openWindow?:boolean};
  overlap?:boolean;
};

const ready=(frames:MarketBrainFrame[])=>frames.filter(f=>f.status!=='UNAVAILABLE');

export function deriveMarketBrain(symbol:string,frames:MarketBrainFrame[],sessions:MarketBrainSessions){
  const usable=ready(frames).sort((a,b)=>a.intervalMinutes-b.intervalMinutes);
  const up=usable.filter(f=>f.bias==='UP').length;
  const down=usable.filter(f=>f.bias==='DOWN').length;
  const hhhl=usable.filter(f=>f.structure==='HH_HL').length;
  const lhll=usable.filter(f=>f.structure==='LH_LL').length;
  const trendUp=usable.filter(f=>f.regime==='TREND_UP').length;
  const trendDown=usable.filter(f=>f.regime==='TREND_DOWN').length;
  const range=usable.filter(f=>f.regime==='RANGE_OR_TRANSITION').length;

  const directionalState=usable.length<2?'INSUFFICIENT'
    :up>=3&&down===0?'BULLISH_ALIGNMENT'
    :down>=3&&up===0?'BEARISH_ALIGNMENT'
    :up>down?'BULLISH_LEAN'
    :down>up?'BEARISH_LEAN'
    :'NEUTRAL';

  const structureState=usable.length<2?'INSUFFICIENT'
    :hhhl>=3&&lhll===0?'HH_HL_DOMINANT'
    :lhll>=3&&hhhl===0?'LH_LL_DOMINANT'
    :hhhl>lhll?'BULLISH_MIXED'
    :lhll>hhhl?'BEARISH_MIXED'
    :'MIXED';

  const regimeState=usable.length<2?'INSUFFICIENT'
    :trendUp>=3&&trendDown===0?'TREND_UP'
    :trendDown>=3&&trendUp===0?'TREND_DOWN'
    :range>=Math.ceil(usable.length/2)?'RANGE_OR_TRANSITION'
    :'MIXED_REGIME';

  const contradictions:string[]=[];
  if(up>0&&down>0)contradictions.push('MTF_BIAS_CONFLICT');
  if(hhhl>0&&lhll>0)contradictions.push('MTF_STRUCTURE_CONFLICT');
  if((directionalState==='BULLISH_ALIGNMENT'&&structureState.startsWith('BEAR'))||
     (directionalState==='BEARISH_ALIGNMENT'&&structureState.startsWith('BULL')))
    contradictions.push('DIRECTION_STRUCTURE_CONFLICT');

  const qedge01=(range>=2?2:0)+(structureState.includes('MIXED')?1:0);
  const qedge02=(directionalState.endsWith('ALIGNMENT')?3:0)+(regimeState.startsWith('TREND_')?2:0);
  const qedge03=(regimeState==='RANGE_OR_TRANSITION'?2:0)+(usable.some(f=>(f.adx14||0)>=25)?1:0);
  const london=Boolean(sessions.london?.active||sessions.london?.openWindow);
  const ny=Boolean(sessions.newYork?.active||sessions.newYork?.openWindow);
  const qedge04=london?3:0;
  const qedge05=ny?3:0;

  const candidates=[
    {strategy:'QEDGE_01_LIQUIDITY_REVERSAL',compatibilityPoints:qedge01},
    {strategy:'QEDGE_02_TREND_PULLBACK',compatibilityPoints:qedge02},
    {strategy:'QEDGE_03_BREAKOUT_RETEST',compatibilityPoints:qedge03},
    {strategy:'QEDGE_04_LONDON_RAID',compatibilityPoints:qedge04},
    {strategy:'QEDGE_05_NY_CONT_REV',compatibilityPoints:qedge05},
  ].sort((a,b)=>b.compatibilityPoints-a.compatibilityPoints);

  const preferred=candidates[0]?.compatibilityPoints>=3?candidates[0].strategy:'WAIT';
  const nextRequiredEvent=usable.length<2?'WAIT_FOR_REFERENCE_DATA'
    :preferred==='QEDGE_02_TREND_PULLBACK'?'WAIT_FOR_PULLBACK_AND_EXECUTION_CONFIRMATION'
    :preferred==='QEDGE_04_LONDON_RAID'?'WAIT_FOR_LIQUIDITY_RAID_AND_RECLAIM'
    :preferred==='QEDGE_05_NY_CONT_REV'?'WAIT_FOR_LONDON_RANGE_INTERACTION'
    :preferred==='QEDGE_03_BREAKOUT_RETEST'?'WAIT_FOR_BREAKOUT_AND_RETEST'
    :preferred==='QEDGE_01_LIQUIDITY_REVERSAL'?'WAIT_FOR_SWEEP_RECLAIM_MSS'
    :'WAIT_FOR_STRATEGY_COMPATIBLE_STATE';

  return {
    version:'ASTRA_MARKET_BRAIN_V8',
    symbol,
    generatedAt:new Date().toISOString(),
    marketState:{
      directionalState,
      structureState,
      regimeState,
      session:String(sessions.focusWindow||'UNKNOWN'),
      readyFrames:usable.length,
      contradictions,
    },
    dataAuthority:{
      priceContext:'CLOSED_CANDLE_REFERENCE',
      liquidityGeometry:'PARTIAL_NOT_EVALUATED_FROM_SNAPSHOT_ONLY',
      volumeProfile:'UNAVAILABLE',
      cvd:'UNAVAILABLE',
      orderFlow:'UNAVAILABLE',
      gex:'UNAVAILABLE',
      brokerExecution:'UNAVAILABLE',
    },
    strategyRouter:{
      preferred,
      candidates,
      nextRequiredEvent,
      meaning:'Compatibility points are deterministic routing evidence, not win probability or trade confidence.',
    },
    executionEligible:false,
    explanation:'Market Brain V8 consolidates deterministic MTF state and strategy compatibility. It does not infer missing order-flow/volume/options data and cannot authorize execution.',
  };
}
