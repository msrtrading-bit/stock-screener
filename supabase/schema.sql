-- NORTHSTAR single-owner persistent state table.
-- Run this in Supabase SQL Editor. Keep the service-role key only in Streamlit Secrets.
create table if not exists public.northstar_state (
    id text primary key,
    portfolio jsonb not null default '[]'::jsonb,
    journal jsonb not null default '[]'::jsonb,
    notes jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.northstar_state enable row level security;

-- Intentionally no anon/authenticated policies. The server-side service-role key
-- is used only by the Streamlit backend and bypasses RLS. Never expose that key
-- in the repository, browser code, screenshots, or chat.
