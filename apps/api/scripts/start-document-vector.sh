#!/usr/bin/env sh
set -eu

exec python3 -m ragdoll.workers.document_vector_worker
