#!/usr/bin/env sh
set -eu

resolve_database_url() {
  python3 - <<'PY'
import os
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse


def normalize_for_dbmate(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return url
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" in query:
        return url
    if parsed.hostname not in {"db", "localhost", "127.0.0.1"}:
        return url
    query["sslmode"] = "disable"
    return urlunparse(parsed._replace(query=urlencode(query)))

truthy = {"1", "true", "yes", "on"}
use_test_db = os.getenv("RAGDOLL_USE_TEST_DB", "").strip().lower() in truthy

if use_test_db:
    test_url = os.getenv("SUPABASE_TEST_DB_URL", "").strip()
    if test_url:
        print(normalize_for_dbmate(test_url))
        raise SystemExit

for key in ("SUPABASE_DB_URL", "DATABASE_URL"):
    value = os.getenv(key, "").strip()
    if value:
        print(normalize_for_dbmate(value))
        raise SystemExit

host = os.getenv("SUPABASE_POSTGRES_HOST", "").strip()
port = os.getenv("SUPABASE_POSTGRES_PORT", "").strip()
database = os.getenv("SUPABASE_POSTGRES_DB", "").strip()
user = os.getenv("SUPABASE_POSTGRES_USER", "").strip()
password = os.getenv("SUPABASE_POSTGRES_PASSWORD", "")

if all((host, port, database, user, password)):
    print(normalize_for_dbmate(f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"))
PY
}

DATABASE_URL_EFFECTIVE="$(resolve_database_url)"

if [ "${DBMATE_AUTO_MIGRATE:-1}" = "1" ] && [ -n "$DATABASE_URL_EFFECTIVE" ]; then
  echo "Attempting DBmate up..."
  DATABASE_URL="$DATABASE_URL_EFFECTIVE" \
    dbmate \
      --migrations-dir /app/db/migrations \
      --schema-file /app/db/schema.sql \
      --no-dump-schema \
      up || echo "DBmate migration skipped or failed during scaffold startup."
else
  echo "Skipping DBmate auto-migrate because no database URL is configured."
fi

exec uvicorn ragdoll.main:app --host 0.0.0.0 --port 8000 --reload
