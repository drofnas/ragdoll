#!/usr/bin/env sh
set -eu

exec rq worker --url "${REDIS_URL}" "${DOCUMENT_PROCESSING_QUEUE_NAME:-document-processing}"
