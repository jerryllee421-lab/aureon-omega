import type {Candle} from './candles.ts';

const finite=(v:number)=>Number.isFinite(v);
const slope=(values:number[])=>{
  if(values.length<2||values.some(v=>!finite(v)))return 0;
  const n=values.length,xMean=(n-1)/2,yMean=values.reduce((a,b)=>a+b,0)/n;
  let num=0,den=0;
  for(let i=0;i<n;i++){num+=(i-xMean)*(values[i]-yMean);den+=(i-xMean)*(i-xMean);}
  return den===0?0:num/den;
};

export function candlestickPattern(candles:Candle[],atr:number|null){
  if(candles.length<2)return {name:'INSUFFICIENT',bias:0,quality:0};
  const c=candles.at(-1)!,p=candles.at(-2)!;
  const body=Math.abs(c.close-c.open),range=Math.max(c.high-c.low,Number.EPSILON);
  const upper=c.high-Math.max(c.open,c.close),lower=Math.min(c.open,c.close)-c.low;
  const bodyPct=body/range,upperPct=upper/range,lowerPct=lower/range;
  const prevBody=Math.abs(p.close-p.open);
  const bull=c.close>c.open,bear=c.close<c.open,prevBull=p.close>p.open,prevBear=p.close<p.open;
  if(bull&&prevBear&&c.open<=p.close&&c.close>=p.open&&body>=prevBody*1.05)return {name:'BULLISH_ENGULFING',bias:1,quality:70};
  if(bear&&prevBull&&c.open>=p.close&&c.close<=p.open&&body>=prevBody*1.05)return {name:'BEARISH_ENGULFING',bias:-1,quality:70};
  if(lower>=body*2&&upper<=body&&lowerPct>=.45&&bodyPct>=.12)return {name:bull?'HAMMER':'BULLISH_REJECTION_PIN',bias:1,quality:bull?60:58};
  if(upper>=body*2&&lower<=body&&upperPct>=.45&&bodyPct>=.12)return {name:bear?'SHOOTING_STAR':'BEARISH_REJECTION_PIN',bias:-1,quality:bear?60:58};
  if(atr!==null&&atr>0&&bodyPct>=.75&&body>=atr*.8)return {name:bull?'BULLISH_DISPLACEMENT_CANDLE':'BEARISH_DISPLACEMENT_CANDLE',bias:bull?1:-1,quality:55};
  if(c.high<p.high&&c.low>p.low)return {name:'INSIDE_BAR',bias:0,quality:30};
  if(c.high>p.high&&c.low<p.low)return {name:'OUTSIDE_BAR',bias:0,quality:35};
  if(bodyPct<=.10)return {name:'DOJI',bias:0,quality:20};
  return {name:'NONE',bias:0,quality:0};
}

function confirmedPivots(candles:Candle[],high:boolean){
  const out:Array<{index:number;price:number}>=[];
  for(let i=2;i<candles.length;i++){
    const a=candles[i-2],b=candles[i-1],c=candles[i];
    if(high?b.high>a.high&&b.high>=c.high:b.low<a.low&&b.low<=c.low)
      out.push({index:i-1,price:high?b.high:b.low});
  }
  return out;
}

export function chartPattern(candles:Candle[],atr:number|null){
  if(candles.length<25||atr===null||atr<=0)return {name:'INSUFFICIENT',bias:0,quality:0,status:'NONE'};
  const c=candles.at(-1)!,p=candles.at(-2)!;
  const base=candles.slice(-22,-2),priorHigh=Math.max(...base.map(v=>v.high)),priorLow=Math.min(...base.map(v=>v.low));
  if(p.close>priorHigh&&c.low<=priorHigh+.15*atr&&c.close>priorHigh)return {name:'BULLISH_BREAK_RETEST',bias:1,quality:82,status:'CONFIRMED'};
  if(p.close<priorLow&&c.high>=priorLow-.15*atr&&c.close<priorLow)return {name:'BEARISH_BREAK_RETEST',bias:-1,quality:82,status:'CONFIRMED'};

  const hp=confirmedPivots(candles,true).slice(-3),lp=confirmedPivots(candles,false).slice(-3);
  if(hp.length>=2){
    const [a,b]=hp.slice(-2);
    if(b.index-a.index>=3&&Math.abs(a.price-b.price)<=.3*atr){
      const valley=Math.min(...candles.slice(a.index,b.index+1).map(v=>v.low));
      if(c.close<valley)return {name:'DOUBLE_TOP_BREAK',bias:-1,quality:78,status:'CONFIRMED'};
      return {name:'DOUBLE_TOP_LIQUIDITY',bias:-1,quality:68,status:'DEVELOPING'};
    }
  }
  if(lp.length>=2){
    const [a,b]=lp.slice(-2);
    if(b.index-a.index>=3&&Math.abs(a.price-b.price)<=.3*atr){
      const peak=Math.max(...candles.slice(a.index,b.index+1).map(v=>v.high));
      if(c.close>peak)return {name:'DOUBLE_BOTTOM_BREAK',bias:1,quality:78,status:'CONFIRMED'};
      return {name:'DOUBLE_BOTTOM_LIQUIDITY',bias:1,quality:68,status:'DEVELOPING'};
    }
  }

  const w=candles.slice(-20),hs=slope(w.map(v=>v.high))/atr,ls=slope(w.map(v=>v.low))/atr;
  const older=candles.slice(-40,-20);
  const currentRange=Math.max(...w.map(v=>v.high))-Math.min(...w.map(v=>v.low));
  const oldRange=older.length>=10?Math.max(...older.map(v=>v.high))-Math.min(...older.map(v=>v.low)):currentRange;
  const contracted=oldRange>0&&currentRange<=oldRange*.85;
  if(contracted&&hs<-.01&&ls>.01)return {name:'SYMMETRICAL_TRIANGLE',bias:0,quality:66,status:'DEVELOPING'};
  if(contracted&&Math.abs(hs)<=.015&&ls>.01)return {name:'ASCENDING_TRIANGLE',bias:1,quality:70,status:'DEVELOPING'};
  if(contracted&&hs<-.01&&Math.abs(ls)<=.015)return {name:'DESCENDING_TRIANGLE',bias:-1,quality:70,status:'DEVELOPING'};
  if(hs>.02&&ls>.02&&Math.abs(hs-ls)<=.05)return {name:'RISING_CHANNEL',bias:1,quality:55,status:'ACTIVE'};
  if(hs<-.02&&ls<-.02&&Math.abs(hs-ls)<=.05)return {name:'FALLING_CHANNEL',bias:-1,quality:55,status:'ACTIVE'};
  return {name:'NONE',bias:0,quality:0,status:'NONE'};
}

export function patternSnapshot(candles:Candle[],atr:number|null){
  return {
    candlestick:candlestickPattern(candles,atr),
    chart:chartPattern(candles,atr),
    authority:'CLOSED_CANDLE_DETERMINISTIC_PATTERN_EVIDENCE',
    executionEligible:false,
  };
}
