# Testing Zenith

Two ways to verify the build: the full automated suite against a local
Supabase-parity stack, and a smoke test against your real Supabase
project.

## A. Full test suite (local, no cloud accounts needed)

Prereqs: Python 3.11+, PostgreSQL server, and the `postgrest` binary on
your PATH (grab the `linux-static` build from
https://github.com/PostgREST/postgrest/releases and drop it in
`/usr/local/bin`). On Mac: `brew install postgresql postgrest`.

```bash
cd backend
pip install -r requirements.txt

# 1. Start local Postgres + PostgREST with the production migrations + RLS
bash scripts/localstack.sh

# 2. Generate backend/.env for the local stack (only if you don't have one)
python scripts/mint_local_jwts.py > .env

# 3. Run everything
python -m pytest tests/ -q
```

Expected: **30 passed**. What the suites prove:

| Suite | Proves |
|---|---|
| `test_tenant_isolation.py` | RLS + JWT auth: tenant A can never read/write tenant B, at the API *and* raw-database layer; fail-closed with bad/missing tokens |
| `test_auth_routes.py` | Signup creates business + Supabase Auth user + mirror row; first-user bootstrap rule; login behavior |
| `test_voice_pipeline.py` | Twilio webhook cycle (`/incoming → /process → /status`) persists calls, transcripts, bookings, queue holds with the right tenant |
| `test_vertical_neutrality.py` | Same booking code serves salon / mechanic / restaurant purely via config; capacity limits enforced |
| `test_faq_wiring.py` | FAQ answers reach live conversations and the Claude system prompt |
| `test_session_persistence.py` | Mid-call state survives a process restart and instance switches |

Useful manual poke (local stack running, server up via
`uvicorn app.main:app --port 8000`):

```bash
curl -X POST http://localhost:8000/api/voice/test/simulate \
  -d "business_phone=<a business phone you created>" \
  -d "message=Do you take walk-ins?"
```

## B. Against your real Supabase project

1. **Apply migrations**: Supabase Dashboard → SQL Editor → run each file
   in `supabase/migrations/` in filename order (they're idempotent), or
   `supabase db push` if you use the CLI.
2. **backend/.env**:
   ```
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_ANON_KEY=<Settings → API → anon key>
   SUPABASE_SERVICE_ROLE_KEY=<Settings → API → service_role key>
   SUPABASE_JWT_SECRET=<Settings → API → JWT Secret>
   AUTH_ENABLED=true
   ANTHROPIC_API_KEY=<optional - enables real Claude replies>
   ```
   (No `POSTGREST_URL` — that's only for the local stack.)
3. **Smoke test** (`uvicorn app.main:app --port 8000`):
   ```bash
   # Create a tenant + admin login in one call
   curl -X POST localhost:8000/api/auth/signup -H 'Content-Type: application/json' -d '{
     "business_name":"Smoke Test Garage","phone_number":"+15550001111",
     "business_type":"mechanic","email":"you@example.com","password":"pick-one"}'
   # → returns access_token (a real Supabase Auth JWT)

   TOKEN=<paste it>
   curl localhost:8000/api/bookings/ -H "Authorization: Bearer $TOKEN"     # → []
   curl localhost:8000/api/bookings/ -H "Authorization: Bearer garbage"    # → 401

   # Simulated call against the tenant you just made
   curl -X POST localhost:8000/api/voice/test/simulate \
     -d "business_phone=+15550001111" \
     -d "message=Book me an oil change tomorrow at 2 PM, my name is Sam"
   ```
   Then check Supabase → Table Editor: `businesses`, `users`, `calls`,
   `bookings` should all have rows, and Auth → Users shows your login
   with `app_metadata.business_id` set.

Isolation spot-check on real Supabase: create a second tenant via
`/signup`, then hit `/api/bookings/` with tenant 2's token — you must
not see tenant 1's booking; RLS is enforcing it in Postgres itself.
