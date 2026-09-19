begin;
create table public.monitored_setups (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 scan_id uuid not null,
 opportunity_index integer not null check(opportunity_index between 0 and 3),
 created_at timestamptz not null default now(),
 expires_at timestamptz not null,
 plan jsonb not null,
 observation jsonb not null default '{"state":"WATCH"}',
 last_checked_at timestamptz,
 provider text,
 provider_instrument text,
 last_error text,
 version integer not null default 0,
 unique(scan_id,opportunity_index),
 foreign key(scan_id,user_id) references public.scans(id,user_id) on delete cascade,
 check(expires_at>created_at)
);
create index monitored_setups_owner_time on public.monitored_setups(user_id,created_at desc);
create table public.monitor_evidence (
 id uuid primary key default gen_random_uuid(),
 setup_id uuid not null references public.monitored_setups(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 created_at timestamptz not null default now(),
 provider text not null,
 provider_instrument text not null,
 candle_time timestamptz not null,
 observation jsonb not null,
 candle_digest text not null,
 candles jsonb not null,
 unique(setup_id,candle_time)
);
create index monitor_evidence_owner on public.monitor_evidence(user_id,created_at desc);
alter table public.monitored_setups enable row level security;
alter table public.monitor_evidence enable row level security;
revoke all on public.monitored_setups,public.monitor_evidence from anon,authenticated;
grant select on public.monitored_setups,public.monitor_evidence to authenticated;
grant all on public.monitored_setups,public.monitor_evidence to service_role;
create policy monitored_owner_read on public.monitored_setups for select to authenticated using((select auth.uid())=user_id);
create policy monitor_evidence_owner_read on public.monitor_evidence for select to authenticated using((select auth.uid())=user_id);
create function public.record_monitor_check(p_id uuid,p_user uuid,p_version integer,p_observation jsonb,p_provider text,p_instrument text,p_candle timestamptz,p_digest text,p_candles jsonb) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 update public.monitored_setups set observation=p_observation,provider=p_provider,provider_instrument=p_instrument,last_checked_at=now(),last_error=null,version=version+1 where id=p_id and user_id=p_user and version=p_version;
 if not found then return false; end if;
 insert into public.monitor_evidence(setup_id,user_id,provider,provider_instrument,candle_time,observation,candle_digest,candles) values(p_id,p_user,p_provider,p_instrument,p_candle,p_observation,p_digest,p_candles) on conflict(setup_id,candle_time) do nothing;
 return true;
end $$;
revoke all on function public.record_monitor_check(uuid,uuid,integer,jsonb,text,text,timestamptz,text,jsonb) from public,anon,authenticated;
grant execute on function public.record_monitor_check(uuid,uuid,integer,jsonb,text,text,timestamptz,text,jsonb) to service_role;
commit;
