create table public.businesses (
  id                 uuid primary key default gen_random_uuid(),
  name               text not null,
  phone_number       text not null unique,
  business_type      text not null,
  description        text,
  hours_of_operation jsonb not null default '{}'::jsonb,
  config             jsonb not null default '{}'::jsonb,
  is_active          boolean not null default true,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

comment on table public.businesses is
  'One row per tenant. phone_number is the tenant key used to route inbound Twilio/Vapi calls to a business.';

comment on column public.businesses.business_type is
  'Vertical, e.g. mechanic, salon, restaurant, clinic. Free text by design (no default, no check constraint) so a new vertical never needs a migration.';

comment on column public.businesses.config is
  'Vertical-specific data that used to be separate restaurant-shaped columns/objects. Conventional keys:
   - service_catalog: replaces the old flat menu/services list (works for a mechanic''s services, a salon''s services, a restaurant''s menu, a clinic''s procedures)
   - appointment_capacity: replaces the old party_size/total_capacity fields (max concurrent appointments, bookable resources, etc.)
   - faq, policies, specials: carried over as-is from the old knowledge base shape
   Deliberately schemaless - each vertical can populate a different subset of keys.';

create index businesses_business_type_idx on public.businesses (business_type);
create index businesses_is_active_idx on public.businesses (is_active) where is_active;

create trigger businesses_set_updated_at
  before update on public.businesses
  for each row
  execute function public.set_updated_at();

alter table public.businesses enable row level security;

-- A business can only read/write its own row.
create policy "businesses_tenant_isolation"
  on public.businesses
  for all
  to authenticated
  using (id = public.requesting_business_id())
  with check (id = public.requesting_business_id());
