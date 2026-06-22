#!/bin/sh

set -eu

ROOT_DIR="${RAGDOLL_ROOT_DIR:-$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)}"
SUPABASE_UPSTREAM_DIR="${RAGDOLL_SUPABASE_UPSTREAM_DIR:-$ROOT_DIR/infra/supabase/self-hosted}"
SUPABASE_UPSTREAM_COMPOSE="${RAGDOLL_SUPABASE_UPSTREAM_COMPOSE:-$SUPABASE_UPSTREAM_DIR/docker-compose.yml}"
SUPABASE_UPSTREAM_GIT_REMOTE="${SUPABASE_UPSTREAM_GIT_REMOTE:-https://github.com/supabase/supabase.git}"
SUPABASE_UPSTREAM_GIT_SHA="${SUPABASE_UPSTREAM_GIT_SHA:-3a72b128de26e966e445463af09aa2b3468400fd}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: '$1' is required to fetch upstream Supabase Docker assets."
    exit 1
  fi
}

fetch_supabase_upstream() {
  mode=$1

  if [ "$mode" = "ensure" ] && [ -f "$SUPABASE_UPSTREAM_COMPOSE" ]; then
    exit 0
  fi

  require_command git

  tmp_root=$(mktemp -d "${TMPDIR:-/tmp}/ragdoll-supabase.XXXXXX")
  trap 'rm -rf "$tmp_root"' EXIT HUP INT TERM

  ws="$tmp_root/ws"
  fetched_dir="$tmp_root/self-hosted"

  mkdir -p "$ws"
  git -C "$ws" init -q
  git -C "$ws" remote add origin "$SUPABASE_UPSTREAM_GIT_REMOTE"

  if ! git -C "$ws" fetch --depth 1 origin "$SUPABASE_UPSTREAM_GIT_SHA"; then
    echo "Error: git fetch failed for supabase/supabase commit $SUPABASE_UPSTREAM_GIT_SHA."
    echo "Check network access or override SUPABASE_UPSTREAM_GIT_SHA with a reachable commit."
    exit 1
  fi

  git -C "$ws" checkout -q FETCH_HEAD

  mkdir -p "$fetched_dir"
  cp -a "$ws/docker/." "$fetched_dir/"

  mkdir -p "$(dirname "$SUPABASE_UPSTREAM_DIR")"
  if [ -d "$SUPABASE_UPSTREAM_DIR" ]; then
    mv "$SUPABASE_UPSTREAM_DIR" "$tmp_root/previous-self-hosted"
  fi
  mv "$fetched_dir" "$SUPABASE_UPSTREAM_DIR"

  if [ "$mode" = "refresh" ]; then
    echo "Refreshed infra/supabase/self-hosted from supabase/supabase@$SUPABASE_UPSTREAM_GIT_SHA"
  else
    echo "Populated infra/supabase/self-hosted from supabase/supabase@$SUPABASE_UPSTREAM_GIT_SHA"
  fi
}

COMMAND=${1:-ensure}
if [ $# -gt 0 ]; then
  shift
fi

case "$COMMAND" in
  ensure)
    fetch_supabase_upstream ensure
    ;;
  refresh)
    fetch_supabase_upstream refresh
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo "Usage: scripts/dev/bootstrap-supabase-upstream.sh [ensure|refresh]"
    exit 1
    ;;
esac
