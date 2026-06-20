#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)

"$ROOT_DIR/scripts/test/backend.sh"
"$ROOT_DIR/scripts/test/frontend.sh"
