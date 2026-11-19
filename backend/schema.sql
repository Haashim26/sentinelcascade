-- Supabase SQL editor: run once (Part B's own project)
create table if not exists events (
  id bigint generated always as identity primary key,
  ts bigint,
  zone text,
  engine text,
  from_stage int,
  to_stage int,
  reason text,
  scenario text,
  label text,
  scenario_start_ts bigint
);
