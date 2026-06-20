#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR/apps/api"

python3 -m pytest tests/platform -q "$@"
