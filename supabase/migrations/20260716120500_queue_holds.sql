-- New table - no equivalent existed in the SQLite schema. Backs the
-- "hold your place in line, get texted instead of staying on hold" flow.
create table public.queue_holds (
  id            uuid primary key default gen_random_uuid(),
  business_id   uuid not null references public.businesses (id) on delete cascade,
  caller_number text not null,
  position      integer not null,
  status        text not null default 'waiting'
                  check (status in ('waiting', 'notified', 'expired', 'cancelled', 'served')),
  notified_at   timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

comment on table public.queue_holds is
  'Holds a caller''s place in a business''s queue so they can be texted their status instead of staying on hold.';

comment on column public.queue_holds.position is
  'Caller''s place in line for this business; lowest = next. Only meaningful while status = waiting.';

comment on column public.queue_holds.notified_at is
  'When the SMS telling the caller it is their turn (or near-turn) was sent. Null until that SMS goes out.';

create index queue_holds_business_id_idx on public.queue_holds (business_id);
create index queue_holds_business_status_position_idx
  on public.queue_holds (business_id, status, position);
create index queue_holds_caller_number_idx on public.queue_holds (caller_number);

-- Prevent two callers from holding the same position in the same
-- business's active (waiting) queue.
create unique index queue_holds_unique_active_position_idx
  on public.queue_holds (business_id, position)
  where status = 'waiting';

create trigger queue_holds_set_updated_at
  before update on public.queue_holds
  for each row
  execute function public.set_updated_at();

alter table public.queue_holds enable row level security;

create policy "queue_holds_tenant_isolation"
  on public.queue_holds
  for all
  to authenticated
  using (business_id = public.requesting_business_id())
  with check (business_id = public.requesting_business_id());
