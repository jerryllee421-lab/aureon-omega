create index monitored_setups_scan_owner on public.monitored_setups(scan_id,user_id);
create index setup_events_scan_owner on public.setup_events(scan_id,user_id);
