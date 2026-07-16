create table public.bookings (
  id                uuid primary key default gen_random_uuid(),
  business_id       uuid not null references public.businesses (id) on delete cascade,
  call_id           uuid references public.calls (id) on delete set null,
  customer_name     text not null,
  customer_phone    text not null,
  service_type      text,
  resource          text,
  scheduled_at      timestamptz not null,
  duration_minutes  integer not null default 60,
  status            text not null default 'pending'
                      check (status in ('pending', 'confirmed', 'modified', 'completed', 'cancelled', 'no_show')),
  confirmation_code text,
  booking_metadata  jsonb not null default '{}'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (business_id, confirmation_code)
);

comment on table public.bookings is
  'Generic appointment. Generalized from the old restaurant-only reservation shape (which hardcoded party size / table language) to cover any vertical''s bookable slot.';

comment on column public.bookings.service_type is
  'What is being booked - free text, vertical-specific vocabulary: oil_change, haircut, dinner_reservation, checkup, etc.';

comment on column public.bookings.resource is
  'What the appointment is booked against - a technician name, a table number, a service bay, a stylist. Whatever the vertical''s bookable resource is.';

comment on column public.bookings.booking_metadata is
  'Vertical-specific extras that don''t warrant their own column, e.g. party_size for a restaurant, vehicle_info for a mechanic, special_requests for a salon.';

create index bookings_business_id_idx on public.bookings (business_id);
create index bookings_call_id_idx on public.bookings (call_id);
create index bookings_scheduled_at_idx on public.bookings (scheduled_at);
create index bookings_status_idx on public.bookings (status);

create trigger bookings_set_updated_at
  before update on public.bookings
  for each row
  execute function public.set_updated_at();

alter table public.bookings enable row level security;

create policy "bookings_tenant_isolation"
  on public.bookings
  for all
  to authenticated
  using (business_id = public.requesting_business_id())
  with check (business_id = public.requesting_business_id());
