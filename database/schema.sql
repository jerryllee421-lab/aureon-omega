-- Reviewed migration input. Apply through Supabase apply_migration or create a
-- migration with `supabase migration new aureon_foundation`, then copy this SQL.
begin;
create schema if not exists private;
revoke all on schema private from public,anon,authenticated;
grant usage on schema private to service_role;
create table public.scans (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  engine_version text not null,
  canonical jsonb not null check (jsonb_typeof(canonical) = 'object'),
  result jsonb not null check (jsonb_typeof(result) = 'object'),
  unique (id,user_id)
);
create index scans_owner_created on public.scans(user_id,created_at desc);
create table public.setup_events (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid not null,
  user_id uuid not null,
  opportunity_index integer not null check (opportunity_index between 0 and 3),
  created_at timestamptz not null default now(),
  state text not null check (state in ('WATCH','INVALIDATED','EXPIRED','CLOSED')),
  source text not null default 'USER_SUPPLIED' check (source = 'USER_SUPPLIED'),
  note text not null check (length(note) <= 3000),
  foreign key (scan_id,user_id) references public.scans(id,user_id) on delete cascade
);
create index setup_events_owner_created on public.setup_events(user_id,created_at desc);
create index setup_events_scan on public.setup_events(scan_id,opportunity_index,created_at desc);
create table private.analysis_claims (
  user_id uuid not null references auth.users(id) on delete cascade,
  run_id uuid not null,
  stage text not null check (stage in ('VISION','STRUCTURE ANALYST','OPPORTUNITY ANALYST','RISK CRITIC','FINAL')),
  created_at timestamptz not null default now(),
  primary key (user_id,run_id,stage)
);
create index analysis_claims_owner_created on private.analysis_claims(user_id,created_at desc);
alter table public.scans enable row level security;
alter table public.setup_events enable row level security;
revoke all on public.scans, public.setup_events from anon,authenticated;
revoke all on private.analysis_claims from public,anon,authenticated;
grant select on public.scans, public.setup_events to authenticated;
grant all on public.scans, public.setup_events to service_role;
grant all on private.analysis_claims to service_role;
create policy scans_owner_read on public.scans for select to authenticated using ((select auth.uid()) = user_id);
create policy events_owner_read on public.setup_events for select to authenticated using ((select auth.uid()) = user_id);
-- Invoker functions execute only as the server service role, not as public users.
create function public.claim_analysis_stage(p_user uuid,p_run uuid,p_stage text) returns boolean
language plpgsql security invoker set search_path = '' as $$
begin
  perform pg_advisory_xact_lock(hashtextextended(p_user::text,0));
  if (select count(*) from private.analysis_claims where user_id=p_user and created_at>now()-interval '1 hour') >= 60 then return false; end if;
  if p_stage <> 'VISION' and not exists (select 1 from private.analysis_claims where user_id=p_user and run_id=p_run and stage='VISION' and created_at>now()-interval '15 minutes') then return false; end if;
  insert into private.analysis_claims(user_id,run_id,stage) values(p_user,p_run,p_stage) on conflict do nothing;
  return found;
end $$;
revoke all on function public.claim_analysis_stage(uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.claim_analysis_stage(uuid,uuid,text) to service_role;
create function public.record_setup_event(p_user uuid,p_scan uuid,p_index integer,p_state text,p_note text) returns uuid
language plpgsql security invoker set search_path = '' as $$
declare saved_result jsonb; previous text; event_id uuid;
begin
  select result into saved_result from public.scans where id=p_scan and user_id=p_user for update;
  if not found or p_index < 0 or p_index >= jsonb_array_length(saved_result->'opportunities') then raise exception 'SETUP_NOT_FOUND'; end if;
  select state into previous from public.setup_events where scan_id=p_scan and user_id=p_user and opportunity_index=p_index order by created_at desc limit 1;
  if previous in ('INVALIDATED','EXPIRED','CLOSED') then raise exception 'SETUP_TERMINAL'; end if;
  insert into public.setup_events(scan_id,user_id,opportunity_index,state,note) values(p_scan,p_user,p_index,p_state,p_note) returning id into event_id;
  return event_id;
end $$;
revoke all on function public.record_setup_event(uuid,uuid,integer,text,text) from public,anon,authenticated;
grant execute on function public.record_setup_event(uuid,uuid,integer,text,text) to service_role;
commit;
