#!/usr/bin/env bash
# Start the local Supabase-parity stack (Postgres + PostgREST) for tests.
set -e
service postgresql status >/dev/null 2>&1 || service postgresql start
if ! pgrep -x postgrest >/dev/null; then
  nohup postgrest /home/claude/localstack/postgrest.conf > /tmp/postgrest.log 2>&1 &
  sleep 2
fi
echo "localstack up"
