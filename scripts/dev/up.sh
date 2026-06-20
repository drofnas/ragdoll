#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

docker compose -f infra/docker/compose.dev.yml up --build "$@"
