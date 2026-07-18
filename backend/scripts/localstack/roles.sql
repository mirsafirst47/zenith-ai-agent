-- Supabase-parity roles for a plain local Postgres (idempotent)
do $$ begin
  if not exists (select from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
  if not exists (select from pg_roles where rolname='anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname='service_role') then create role service_role nologin bypassrls; end if;
end $$;
grant service_role, authenticated, anon to zenith;
grant usage on schema public to authenticated, anon, service_role;
