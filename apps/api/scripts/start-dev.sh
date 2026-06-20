#!/usr/bin/env sh
set -eu

if [ "${ALEMBIC_AUTO_UPGRADE:-1}" = "1" ] && \
  { [ -n "${SUPABASE_DB_URL:-${DATABASE_URL:-}}" ] || [ -n "${SUPABASE_POSTGRES_HOST:-}" ]; }; then
  echo "Attempting Alembic upgrade head..."
  alembic upgrade head || echo "Alembic upgrade skipped or failed during scaffold startup."
else
  echo "Skipping Alembic auto-upgrade because no database URL is configured."
fi

exec uvicorn ragdoll.main:app --host 0.0.0.0 --port 8000 --reload
