begin;
create schema if not exists private;
revoke all on schema private from public,anon,authenticated;
grant usage on schema private to service_role;
drop policy if exists claims_no_client_access on public.analysis_claims;
alter table public.analysis_claims set schema private;
revoke all on private.analysis_claims from public,anon,authenticated;
grant all on private.analysis_claims to service_role;
create or replace function public.claim_analysis_stage(p_user uuid,p_run uuid,p_stage text) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
  perform pg_advisory_xact_lock(hashtextextended(p_user::text,0));
  if (select count(*) from private.analysis_claims where user_id=p_user and created_at>now()-interval '1 hour') >= 60 then return false; end if;
  if p_stage <> 'VISION' and not exists (select 1 from private.analysis_claims where user_id=p_user and run_id=p_run and stage='VISION' and created_at>now()-interval '15 minutes') then return false; end if;
  insert into private.analysis_claims(user_id,run_id,stage) values(p_user,p_run,p_stage) on conflict do nothing;
  return found;
end $$;
revoke all on function public.claim_analysis_stage(uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.claim_analysis_stage(uuid,uuid,text) to service_role;
commit;
