create extension if not exists pgcrypto;

create table if not exists public.research_datasets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  symbol text not null,
  source text not null check (source in ('DUKASCOPY_EXTERNAL','MT5_BROKER_NATIVE','USER_IMPORT')),
  period_start timestamptz not null,
  period_end timestamptz not null,
  dataset_sha256 text not null,
  manifest jsonb not null default '{}'::jsonb,
  unique(user_id, dataset_sha256)
);

create table if not exists public.research_experiments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  name text not null,
  strategy text not null,
  strategy_version text,
  source_commit text,
  config jsonb not null default '{}'::jsonb,
  status text not null default 'QUEUED' check (status in ('QUEUED','RUNNING','COMPLETED','FAILED','REJECTED'))
);

create table if not exists public.research_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  experiment_id uuid references public.research_experiments(id) on delete cascade,
  dataset_id uuid references public.research_datasets(id) on delete set null,
  created_at timestamptz not null default now(),
  timeframe text not null,
  execution_model text not null,
  parameters jsonb not null default '{}'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  monte_carlo jsonb,
  period_start timestamptz,
  period_end timestamptz,
  artifact_ref text,
  status text not null default 'COMPLETED' check (status in ('RUNNING','COMPLETED','FAILED','REJECTED'))
);

create index if not exists research_datasets_user_created_idx on public.research_datasets(user_id, created_at desc);
create index if not exists research_experiments_user_created_idx on public.research_experiments(user_id, created_at desc);
create index if not exists research_runs_user_created_idx on public.research_runs(user_id, created_at desc);
create index if not exists research_runs_experiment_idx on public.research_runs(experiment_id);

alter table public.research_datasets enable row level security;
alter table public.research_experiments enable row level security;
alter table public.research_runs enable row level security;

drop policy if exists research_datasets_owner_all on public.research_datasets;
create policy research_datasets_owner_all on public.research_datasets for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists research_experiments_owner_all on public.research_experiments;
create policy research_experiments_owner_all on public.research_experiments for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists research_runs_owner_all on public.research_runs;
create policy research_runs_owner_all on public.research_runs for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
