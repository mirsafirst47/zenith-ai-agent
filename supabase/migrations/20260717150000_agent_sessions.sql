-- Persistent conversation session state.
--
-- One row per live call, keyed by the telephony provider's call id.
-- Lets any backend instance pick up a call mid-conversation (webhooks
-- are not sticky) and survives process restarts. Rows are short-lived:
-- deleted on clean call end, swept by expires_at otherwise.
create table if not exists agent_sessions (
  call_sid text primary key,
  business_id uuid references businesses(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  expires_at timestamptz not null default now() + interval '2 hours',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_agent_sessions_expires on agent_sessions (expires_at);

create trigger agent_sessions_updated_at
  before update on agent_sessions
  for each row execute function public.set_updated_at();

-- Voice-pipeline internals: only the service role touches these.
-- RLS on with no policies = authenticated/anon get nothing (fail closed).
alter table agent_sessions enable row level security;
grant all on agent_sessions to service_role;
