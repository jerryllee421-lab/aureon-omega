export type SessionClock={
  zone:string;
  localDate:string;
  localTime:string;
  weekday:string;
  minutesOfDay:number;
  active:boolean;
  openWindow:boolean;
};

function clock(now:Date,zone:string){
  const parts=new Intl.DateTimeFormat('en-GB',{
    timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',
    weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
  }).formatToParts(now);
  const get=(type:Intl.DateTimeFormatPartTypes)=>parts.find(p=>p.type===type)?.value||'';
  const hour=Number(get('hour')),minute=Number(get('minute'));
  return {
    zone,
    localDate:`${get('year')}-${get('month')}-${get('day')}`,
    localTime:`${String(hour).padStart(2,'0')}:${String(minute).padStart(2,'0')}`,
    weekday:get('weekday'),
    minutesOfDay:hour*60+minute,
  };
}

function session(now:Date,zone:string,start:number,end:number,openEnd:number):SessionClock{
  const c=clock(now,zone);
  const weekday=!['Sat','Sun'].includes(c.weekday);
  return {
    ...c,
    active:weekday&&c.minutesOfDay>=start&&c.minutesOfDay<end,
    openWindow:weekday&&c.minutesOfDay>=start&&c.minutesOfDay<openEnd,
  };
}

export function marketSessions(nowMs=Date.now()){
  const now=new Date(nowMs);
  const london=session(now,'Europe/London',8*60,17*60,11*60);
  const newYork=session(now,'America/New_York',8*60,17*60,11*60);
  const johannesburg=clock(now,'Africa/Johannesburg');
  const overlap=london.active&&newYork.active;
  const focusWindow=overlap?'LONDON_NEW_YORK_OVERLAP'
    :newYork.openWindow?'NEW_YORK_OPEN'
    :london.openWindow?'LONDON_OPEN'
    :london.active?'LONDON_SESSION'
    :newYork.active?'NEW_YORK_SESSION'
    :'OFF_FOCUS';
  return {
    generatedAt:now.toISOString(),
    ownerLocal:{zone:johannesburg.zone,localDate:johannesburg.localDate,localTime:johannesburg.localTime,weekday:johannesburg.weekday},
    london,
    newYork,
    overlap,
    focusWindow,
    authority:'TIMEZONE_CALENDAR_REFERENCE',
    explanation:'Reference liquidity windows use 08:00–17:00 local London/New York time, with 08:00–11:00 treated as the open window. DST is handled by the IANA timezone database.',
  };
}
