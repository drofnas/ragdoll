#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
INFRA_COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.infra.yml"
INFRA_ENV_FILE="$ROOT_DIR/infra/docker/.env.infra"
INFRA_ENV_EXAMPLE="$ROOT_DIR/infra/docker/.env.infra.example"
SUPABASE_UPSTREAM_COMPOSE_FILE="$ROOT_DIR/infra/supabase/self-hosted/docker-compose.yml"
ACTIVE_INFRA_ENV_FILE=

select_infra_env_file() {
  if [ -f "$INFRA_ENV_FILE" ]; then
    ACTIVE_INFRA_ENV_FILE="$INFRA_ENV_FILE"
    return 0
  fi

  if [ -f "$INFRA_ENV_EXAMPLE" ]; then
    ACTIVE_INFRA_ENV_FILE="$INFRA_ENV_EXAMPLE"
    return 0
  fi

  echo "Error: missing infra/docker/.env.infra and infra/docker/.env.infra.example."
  exit 1
}

load_ollama_runtime() {
  OLLAMA_RUNTIME=$(
    awk -F= '
      $1 == "OLLAMA_RUNTIME" {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2)
        print $2
      }
    ' "$ACTIVE_INFRA_ENV_FILE" | tail -n 1
  )

  if [ -z "${OLLAMA_RUNTIME:-}" ]; then
    OLLAMA_RUNTIME=cpu
  fi

  case "$OLLAMA_RUNTIME" in
    cpu|amd|nvidia) ;;
    *)
      active_file=${ACTIVE_INFRA_ENV_FILE#$ROOT_DIR/}
      echo "Error: unsupported OLLAMA_RUNTIME '$OLLAMA_RUNTIME' in $active_file"
      echo "Use one of: cpu, amd, nvidia"
      exit 1
      ;;
  esac

  OLLAMA_RUNTIME_COMPOSE_FILE="$ROOT_DIR/infra/docker/compose.ollama.$OLLAMA_RUNTIME.yml"
}

run_compose() {
  docker compose \
    --env-file "$ACTIVE_INFRA_ENV_FILE" \
    -f "$INFRA_COMPOSE_FILE" \
    -f "$OLLAMA_RUNTIME_COMPOSE_FILE" \
    "$@"
}

ensure_infra_env_template() {
  "$ROOT_DIR/scripts/dev/bootstrap-infra-env.sh" --ensure-env-only
}

hydrate_infra_env() {
  "$ROOT_DIR/scripts/dev/bootstrap-infra-env.sh" --hydrate-only
}

ensure_supabase_upstream() {
  sh "$ROOT_DIR/scripts/dev/bootstrap-supabase-upstream.sh" ensure
}

refresh_supabase_upstream() {
  sh "$ROOT_DIR/scripts/dev/bootstrap-supabase-upstream.sh" refresh
}

require_supabase_upstream() {
  if [ ! -f "$SUPABASE_UPSTREAM_COMPOSE_FILE" ]; then
    echo "Error: missing infra/supabase/self-hosted/docker-compose.yml. Run './dev-setup.sh infra up' first."
    exit 1
  fi
}

COMMAND=${1:-up}
if [ $# -gt 0 ]; then
  shift
fi

case "$COMMAND" in
  up)
    ensure_infra_env_template
    ensure_supabase_upstream
    hydrate_infra_env
    select_infra_env_file
    load_ollama_runtime
    cd "$ROOT_DIR"
    run_compose up -d --remove-orphans "$@"
    ;;
  upgrade)
    ensure_infra_env_template
    refresh_supabase_upstream
    hydrate_infra_env
    select_infra_env_file
    load_ollama_runtime
    cd "$ROOT_DIR"
    run_compose pull "$@"
    run_compose up -d --remove-orphans "$@"
    ;;
  down)
    select_infra_env_file
    require_supabase_upstream
    load_ollama_runtime
    cd "$ROOT_DIR"
    run_compose down --remove-orphans "$@"
    ;;
  ps|status)
    select_infra_env_file
    require_supabase_upstream
    load_ollama_runtime
    cd "$ROOT_DIR"
    run_compose ps "$@"
    ;;
  logs)
    select_infra_env_file
    require_supabase_upstream
    load_ollama_runtime
    cd "$ROOT_DIR"
    run_compose logs -f "$@"
    ;;
  *)
    echo "Unknown infra command: $COMMAND"
    echo "Usage: ./dev-setup.sh infra [up|down|ps|logs|upgrade] [args...]"
    exit 1
    ;;
esac
