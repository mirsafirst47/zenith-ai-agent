#!/usr/bin/env bash
# Local Supabase-parity stack: Postgres + PostgREST with the production
# migrations and RLS. Lets the whole test suite run with zero cloud deps.
#
# Prereqs: postgresql installed, postgrest binary on PATH
#   (https://github.com/PostgREST/postgrest/releases — linux-static build)
# Usage: bash backend/scripts/localstack.sh   (from repo root or backend/)
set -e
cd "$(dirname "$0")/.."   # backend/
REPO_ROOT="$(cd .. && pwd)"

service postgresql status >/dev/null 2>&1 || service postgresql start || true

# Role + database (idempotent)
su postgres -c "psql -tc \"select 1 from pg_roles where rolname='zenith'\"" | grep -q 1 || \
  su postgres -c "psql -c \"create role zenith login password 'zenith' superuser;\""
su postgres -c "psql -tc \"select 1 from pg_database where datname='zenith'\"" | grep -q 1 || \
  su postgres -c "createdb -O zenith zenith"

export PGPASSWORD=zenith
psql -h 127.0.0.1 -U zenith -d zenith -q -f scripts/localstack/roles.sql

# Apply every migration (idempotent: create-if-not-exists patterns)
for f in "$REPO_ROOT"/supabase/migrations/*.sql; do
  psql -h 127.0.0.1 -U zenith -d zenith -v ON_ERROR_STOP=1 -q -f "$f" 2>/dev/null || true
done
psql -h 127.0.0.1 -U zenith -d zenith -q -c \
  "grant all on all tables in schema public to authenticated, service_role;"

if ! pgrep -x postgrest >/dev/null; then
  setsid nohup postgrest scripts/localstack/postgrest.conf > /tmp/postgrest.log 2>&1 &
  sleep 2
else
  pkill -USR1 postgrest  # reload schema cache in case migrations changed
fi
echo "localstack up (postgres :5432, postgrest :3000)"
