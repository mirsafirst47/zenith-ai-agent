-- Enable extensions required for UUID generation.
-- Real Supabase projects already have the `extensions` schema; the
-- `if not exists` guard just makes this migration replayable against a
-- plain Postgres instance too (e.g. for local testing).
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;

-- Generic trigger function: keeps `updated_at` current on every row update.
-- Attached to businesses, bookings, and queue_holds - the tables in this
-- schema that carry an updated_at column.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Multi-tenant RLS helper: reads the caller's business_id out of their JWT.
--
-- Expects a custom claim at app_metadata.business_id. That claim doesn't
-- exist yet - auth isn't wired up. Once it is (e.g. via a Supabase Custom
-- Access Token Hook that looks up the signed-in user's row in
-- public.users and stamps business_id into app_metadata), every
-- tenant-scoped policy below starts working with no further schema
-- changes. Until then this returns null, and RLS fails closed: the
-- `authenticated` role gets no rows back on any tenant-scoped table.
--
-- This does not affect the backend service itself - a service_role key
-- bypasses RLS entirely, so the FastAPI/Vapi backend can keep operating
-- normally while end-user auth is still being built.
create or replace function public.requesting_business_id()
returns uuid
language sql
stable
security invoker
set search_path = ''
as $$
  select nullif(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb -> 'app_metadata' ->> 'business_id',
    ''
  )::uuid
$$;
