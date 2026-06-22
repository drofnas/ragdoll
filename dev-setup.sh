#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.dev.yml"
API_ENV_FILE="$ROOT_DIR/apps/api/.env"
WEB_ENV_FILE="$ROOT_DIR/apps/web/.env"
API_ENV_EXAMPLE="$ROOT_DIR/apps/api/.env.example"
WEB_ENV_EXAMPLE="$ROOT_DIR/apps/web/.env.example"

print_help() {
  cat <<EOF
Usage: ./dev-setup.sh [command] [args...]

Canonical convenience entrypoint for local runtime and test flows.

Runtime startup commands auto-create missing env files from:
  apps/api/.env.example -> apps/api/.env
  apps/web/.env.example -> apps/web/.env

Commands:
  up                 Start the Phase 1 dev stack in the foreground (default)
  daemon, d          Start the Phase 1 dev stack in the background
  build              Alias of up
  build-daemon       Alias of daemon
  build-d, bd        Alias of build-daemon
  infra [command]    Manage the local dependency stack (up, down, ps, logs, upgrade)
  down               Stop the Phase 1 dev stack
  ps, status         Show Phase 1 dev stack status
  logs               Tail Phase 1 dev stack logs
  test-backend       Run backend platform tests from apps/api
  test-frontend      Run frontend runtime/bootstrap tests from apps/web
  test, test-all     Run backend and frontend test entrypoints in sequence
  test-infra         Run the opt-in Docker-backed Phase 7 local dependency smoke suite
  test-e2e           Run the Docker-backed Playwright smoke E2E suite
  help, -h, --help   Show this help message
EOF
}

require_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "Error: 'docker compose' is required for Phase 1 runtime commands."
    exit 1
  fi
}

require_runtime_env_files() {
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

run_compose_logs() {
  cd "$ROOT_DIR"
  exec docker compose -f "$COMPOSE_FILE" logs -f "$@"
}

run_compose_up_daemon() {
  cd "$ROOT_DIR"
  exec docker compose -f "$COMPOSE_FILE" up --build -d "$@"
}

COMMAND=${1:-up}
if [ $# -gt 0 ]; then
  shift
fi

case "$COMMAND" in
  up|build)
    require_docker_compose
    require_runtime_env_files
    exec "$ROOT_DIR/scripts/dev/up.sh" "$@"
    ;;
  daemon|d|build-daemon|build-d|bd)
    require_docker_compose
    require_runtime_env_files
    run_compose_up_daemon "$@"
    ;;
  infra)
    require_docker_compose
    if [ $# -eq 0 ]; then
      set -- up
    fi
    exec "$ROOT_DIR/scripts/dev/infra.sh" "$@"
    ;;
  down)
    require_docker_compose
    exec "$ROOT_DIR/scripts/dev/down.sh" "$@"
    ;;
  ps|status)
    require_docker_compose
    exec "$ROOT_DIR/scripts/dev/status.sh" "$@"
    ;;
  logs)
    require_docker_compose
    run_compose_logs "$@"
    ;;
  test-backend)
    if [ "${1:-}" = "--" ]; then
      shift
    fi
    exec "$ROOT_DIR/scripts/test/backend.sh" "$@"
    ;;
  test-frontend)
    if [ "${1:-}" = "--" ]; then
      shift
    fi
    exec "$ROOT_DIR/scripts/test/frontend.sh" "$@"
    ;;
  test|test-all)
    if [ "${1:-}" = "--" ]; then
      shift
    fi
    exec "$ROOT_DIR/scripts/test/all.sh" "$@"
    ;;
  test-infra)
    if [ "${1:-}" = "--" ]; then
      shift
    fi
    exec "$ROOT_DIR/scripts/test/infra.sh" "$@"
    ;;
  test-e2e)
    if [ "${1:-}" = "--" ]; then
      shift
    fi
    exec "$ROOT_DIR/scripts/test/e2e.sh" "$@"
    ;;
  help|-h|--help)
    print_help
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo
    print_help
    exit 1
    ;;
esac
