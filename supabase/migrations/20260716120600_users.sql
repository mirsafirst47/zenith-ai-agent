create table public.users (
  id              uuid primary key default gen_random_uuid(),
  business_id     uuid not null references public.businesses (id) on delete cascade,
  email           text not null unique,
  hashed_password text not null,
  full_name       text,
  role            text not null default 'admin',
  is_active       boolean not null default true,
  last_login      timestamptz,
  created_at      timestamptz not null default now()
);

comment on table public.users is
  'Kept structurally as-is from the SQLAlchemy model - not yet linked to Supabase Auth (auth.users). Auth is a follow-up piece of work; see requesting_business_id() in 20260716120000_extensions_and_helpers.sql for how this table is expected to plug into RLS once a signed-in session can be tied back to a row here.';

create index users_business_id_idx on public.users (business_id);

alter table public.users enable row level security;

create policy "users_tenant_isolation"
  on public.users
  for all
  to authenticated
  using (business_id = public.requesting_business_id())
  with check (business_id = public.requesting_business_id());
