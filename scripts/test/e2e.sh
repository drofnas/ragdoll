#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
DEV_COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.dev.yml"
E2E_COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.e2e.yml"
API_ENV_FILE="$ROOT_DIR/apps/api/.env"
WEB_ENV_FILE="$ROOT_DIR/apps/web/.env"
API_ENV_EXAMPLE="$ROOT_DIR/apps/api/.env.example"
WEB_ENV_EXAMPLE="$ROOT_DIR/apps/web/.env.example"

require_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "Error: 'docker compose' is required for E2E execution."
    exit 1
  fi
}

ensure_runtime_env_files() {
  if [ ! -f "$API_ENV_FILE" ] && [ ! -f "$API_ENV_EXAMPLE" ]; then
    echo "Error: missing required example file apps/api/.env.example"
    exit 1
  fi

  if [ ! -f "$WEB_ENV_FILE" ] && [ ! -f "$WEB_ENV_EXAMPLE" ]; then
    echo "Error: missing required example file apps/web/.env.example"
    exit 1
  fi

  if [ ! -f "$API_ENV_FILE" ]; then
    cp "$API_ENV_EXAMPLE" "$API_ENV_FILE"
    echo "Created apps/api/.env from apps/api/.env.example"
  fi

  if [ ! -f "$WEB_ENV_FILE" ]; then
    cp "$WEB_ENV_EXAMPLE" "$WEB_ENV_FILE"
    echo "Created apps/web/.env from apps/web/.env.example"
  fi
}

require_docker_compose
"$ROOT_DIR/dev-setup.sh" infra up
ensure_runtime_env_files

cd "$ROOT_DIR"

restore_dev_stack() {
  status=$?
  restore_status=0
  trap - EXIT

  docker compose -f "$DEV_COMPOSE_FILE" up --build -d backend document-vector frontend || restore_status=$?
  if [ "$status" -eq 0 ] && [ "$restore_status" -ne 0 ]; then
    exit "$restore_status"
  fi
  exit "$status"
}

trap restore_dev_stack EXIT

docker compose -f "$DEV_COMPOSE_FILE" -f "$E2E_COMPOSE_FILE" up --build -d backend document-vector frontend
docker compose -f "$DEV_COMPOSE_FILE" -f "$E2E_COMPOSE_FILE" run --build --rm e2e npm test -- "$@"
