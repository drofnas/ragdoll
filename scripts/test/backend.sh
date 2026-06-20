#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.dev.yml"
API_ENV_FILE="$ROOT_DIR/apps/api/.env"
API_ENV_EXAMPLE="$ROOT_DIR/apps/api/.env.example"

require_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "Error: 'docker compose' is required for backend test execution."
    exit 1
  fi
}

ensure_api_env_file() {
  if [ ! -f "$API_ENV_FILE" ] && [ ! -f "$API_ENV_EXAMPLE" ]; then
    echo "Error: missing required example file apps/api/.env.example"
    exit 1
  fi

  if [ ! -f "$API_ENV_FILE" ]; then
    cp "$API_ENV_EXAMPLE" "$API_ENV_FILE"
    echo "Created apps/api/.env from apps/api/.env.example"
  fi
}

require_docker_compose
ensure_api_env_file

cd "$ROOT_DIR"
exec docker compose -f "$COMPOSE_FILE" run --rm -w /workspace/apps/api backend \
  python3 -m pytest tests -q "$@"
