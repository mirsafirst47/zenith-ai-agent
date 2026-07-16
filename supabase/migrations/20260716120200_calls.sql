create table public.calls (
  id                    uuid primary key default gen_random_uuid(),
  business_id           uuid not null references public.businesses (id) on delete cascade,
  call_sid              text not null unique,
  caller_number         text not null,
  direction             text,
  status                text,
  detected_language     text,
  intent                text,
  emotion               text,
  transcript            jsonb not null default '[]'::jsonb,
  summary               text,
  action_taken          text,
  booking_id            uuid,
  escalated_to_human    boolean not null default false,
  escalation_reason     text,
  duration_seconds      integer,
  response_time_avg_ms  numeric,
  customer_satisfaction integer,
  recording_url         text,
  started_at            timestamptz not null default now(),
  ended_at              timestamptz,
  created_at            timestamptz not null default now()
);

comment on table public.calls is
  'Kept structurally as-is from the SQLAlchemy model. Only change: sentiment was renamed to emotion.';

comment on column public.calls.emotion is
  'Renamed from the old sentiment column. This has always stored the caller''s detected emotion (neutral/happy/frustrated/angry/confused/...), not a sentiment polarity score - the rename just makes the column match its actual contents.';

comment on column public.calls.booking_id is
  'Soft link to bookings.id. Left nullable with no FK here because bookings does not exist yet at this point in the migration sequence; the FK constraint is added in 20260716120400_calls_booking_fk.sql once it does.';

create index calls_business_id_idx on public.calls (business_id);
create index calls_started_at_idx on public.calls (started_at);
create index calls_detected_language_idx on public.calls (detected_language);
create index calls_intent_idx on public.calls (intent);
create index calls_status_idx on public.calls (status);

alter table public.calls enable row level security;

create policy "calls_tenant_isolation"
  on public.calls
  for all
  to authenticated
  using (business_id = public.requesting_business_id())
  with check (business_id = public.requesting_business_id());
