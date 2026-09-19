begin;
drop policy if exists claims_no_client_access on public.analysis_claims;
create policy claims_no_client_access on public.analysis_claims for all to authenticated using(false) with check(false);
commit;
