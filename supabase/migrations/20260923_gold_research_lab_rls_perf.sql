drop policy if exists research_datasets_owner_all on public.research_datasets;
create policy research_datasets_owner_all on public.research_datasets
for all to authenticated
using (
  (select auth.uid()) = user_id
  and coalesce(((select auth.jwt()) ->> 'is_anonymous'), 'false') <> 'true'
)
with check (
  (select auth.uid()) = user_id
  and coalesce(((select auth.jwt()) ->> 'is_anonymous'), 'false') <> 'true'
);

drop policy if exists research_experiments_owner_all on public.research_experiments;
create policy research_experiments_owner_all on public.research_experiments
for all to authenticated
using (
  (select auth.uid()) = user_id
  and coalesce(((select auth.jwt()) ->> 'is_anonymous'), 'false') <> 'true'
)
with check (
  (select auth.uid()) = user_id
  and coalesce(((select auth.jwt()) ->> 'is_anonymous'), 'false') <> 'true'
);

drop policy if exists research_runs_owner_all on public.research_runs;
create policy research_runs_owner_all on public.research_runs
for all to authenticated
using (
  (select auth.uid()) = user_id
  and coalesce(((select auth.jwt()) ->> 'is_anonymous'), 'false') <> 'true'
)
with check (
  (select auth.uid()) = user_id
  and coalesce(((select auth.jwt()) ->> 'is_anonymous'), 'false') <> 'true'
);
