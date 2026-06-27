#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
DEV_COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.dev.yml"
API_ENV_FILE="$ROOT_DIR/apps/api/.env"
API_ENV_EXAMPLE="$ROOT_DIR/apps/api/.env.example"
KEEP_RUNNING=0
TMP_DIR=
API_ENV_BACKUP_FILE=
API_ENV_EXISTED=0

print_help() {
  cat <<EOF
Usage: ./dev-setup.sh test-infra [--keep-running]

Runs the opt-in Docker-backed Phase 7 local dependency smoke suite.

This command:
  1. boots the local dependency stack through ./dev-setup.sh infra up
  2. starts the app stack through ./dev-setup.sh daemon
  3. runs the backend-side infra smoke helper against live services
  4. tears the stacks down unless --keep-running is provided
EOF
}

require_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "Error: 'docker compose' is required for infra smoke execution."
    exit 1
  fi
}

wait_for_backend() {
  attempts=0
  until docker compose -f "$DEV_COMPOSE_FILE" exec -T backend python3 -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()" \
    >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 60 ]; then
      echo "Error: backend did not become healthy within 60 seconds."
      exit 1
    fi
    sleep 1
  done
}

assert_file_exists() {
  if [ ! -f "$1" ]; then
    echo "Error: expected file '$1' to exist after infra bootstrap."
    exit 1
  fi
}

env_get() {
  awk -F= -v key="$2" '
    $1 == key {
      print substr($0, index($0, "=") + 1)
      exit
    }
  ' "$1"
}

assert_env_value_not_equal() {
  value=$(env_get "$1" "$2" || true)
  if [ "${value:-}" = "$3" ]; then
    echo "Error: key '$2' in '$1' still has placeholder value '$3'."
    exit 1
  fi
}

cleanup() {
  status=$?
  if [ -n "${API_ENV_BACKUP_FILE:-}" ] && [ -f "$API_ENV_BACKUP_FILE" ]; then
    mv "$API_ENV_BACKUP_FILE" "$API_ENV_FILE"
  elif [ "$API_ENV_EXISTED" -eq 0 ] && [ -f "$API_ENV_FILE" ]; then
    rm -f "$API_ENV_FILE"
  fi

  if [ -n "${TMP_DIR:-}" ] && [ -d "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi

  if [ "$KEEP_RUNNING" -ne 1 ]; then
    "$ROOT_DIR/dev-setup.sh" down >/dev/null 2>&1 || true
    "$ROOT_DIR/dev-setup.sh" infra down >/dev/null 2>&1 || true
  fi
  exit "$status"
}

prepare_smoke_api_env() {
  if [ ! -f "$API_ENV_EXAMPLE" ]; then
    echo "Error: missing required example file '$API_ENV_EXAMPLE'."
    exit 1
  fi

  TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ragdoll-test-infra.XXXXXX")
  API_ENV_BACKUP_FILE="$TMP_DIR/api.env.backup"

  if [ -f "$API_ENV_FILE" ]; then
    API_ENV_EXISTED=1
    cp "$API_ENV_FILE" "$API_ENV_BACKUP_FILE"
  fi

  cp "$API_ENV_EXAMPLE" "$API_ENV_FILE"
  "$ROOT_DIR/scripts/dev/bootstrap-infra-env.sh" --hydrate-only
}

while [ $# -gt 0 ]; do
  case "$1" in
    --keep-running)
      KEEP_RUNNING=1
      ;;
    help|-h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo
      print_help
      exit 1
      ;;
  esac
  shift
done

trap cleanup EXIT HUP INT TERM

require_docker_compose

"$ROOT_DIR/dev-setup.sh" infra up
prepare_smoke_api_env

assert_file_exists "$ROOT_DIR/infra/docker/.env.infra"
assert_file_exists "$ROOT_DIR/apps/api/.env"
assert_file_exists "$ROOT_DIR/infra/supabase/self-hosted/docker-compose.yml"
assert_env_value_not_equal "$ROOT_DIR/infra/docker/.env.infra" "POSTGRES_PASSWORD" "your-super-secret-and-long-postgres-password"
assert_env_value_not_equal \
  "$ROOT_DIR/apps/api/.env" \
  "SUPABASE_DB_URL" \
  "postgresql://postgres:replace-with-local-postgres-password@db:5432/postgres"
assert_env_value_not_equal "$ROOT_DIR/apps/api/.env" "SUPABASE_SERVICE_ROLE_KEY" "replace-with-local-service-role-key"
if [ "$(env_get "$ROOT_DIR/apps/api/.env" DOCUMENT_PROCESSING_QUEUE_NAME || true)" != "document-processing" ]; then
  echo "Error: expected DOCUMENT_PROCESSING_QUEUE_NAME=document-processing in apps/api/.env."
  exit 1
fi
if [ "$(env_get "$ROOT_DIR/apps/api/.env" REDIS_URL || true)" != "redis://redis:6379/0" ]; then
  echo "Error: expected REDIS_URL=redis://redis:6379/0 in apps/api/.env."
  exit 1
fi

"$ROOT_DIR/dev-setup.sh" infra ps
"$ROOT_DIR/dev-setup.sh" daemon

wait_for_backend

docker compose -f "$DEV_COMPOSE_FILE" exec -T backend \
  python3 /workspace/packages/tooling/scripts/infra_smoke.py

if [ "$KEEP_RUNNING" -eq 1 ]; then
  echo "Infra smoke completed successfully. App and infra stacks are still running."
else
  echo "Infra smoke completed successfully."
fi
