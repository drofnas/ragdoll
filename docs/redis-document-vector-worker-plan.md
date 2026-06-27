# Redis-Backed `document-vector` Worker Plan

This planning note is historical context only. The current implementation uses Redis-backed RQ workers rather than the older Redis Streams design described below.

## Summary

The change adds Redis to the local infra stack, renames the scalable document worker service to `document-vector`, and moves document-processing dispatch from DB polling to Redis Streams while keeping `document_processing_jobs` as the durable status ledger.

Decisions locked:

- `document-vector` runs the existing full document pipeline: parsing, vector, extraction, graph.
- Redis is required when selected; no silent SQL fallback.
- Worker count is controlled with Docker Compose scaling, e.g. `./dev-setup.sh daemon --scale document-vector=3`.

## Interfaces And Config

- Add backend settings:
  - `DOCUMENT_PROCESSING_QUEUE_BACKEND=redis|sql|memory`, default `sql`; checked-in API env examples set `redis`.
  - `REDIS_URL=redis://redis:6379/0`.
  - `DOCUMENT_VECTOR_QUEUE_STREAM=ragdoll:queues:document-vector`.
  - `DOCUMENT_VECTOR_CONSUMER_GROUP=document-vector`.
  - `DOCUMENT_VECTOR_BLOCK_TIMEOUT_SECONDS=5`.
  - `DOCUMENT_VECTOR_REPAIR_INTERVAL_SECONDS=30`.
  - `DOCUMENT_VECTOR_STREAM_MAXLEN=10000`.
- Add `redis==8.0.1` to `apps/api/requirements.txt`; PyPI lists it as the latest release on June 23, 2026 and Python `>=3.10`.
- No HTTP API or contract changes.
- Keep `DocumentProcessingQueueService` public methods unchanged. Add `RedisDocumentProcessingQueue` internally.

## Implementation Changes

- Infra:
  - Add `redis` to `infra/docker/compose.infra.yml` using `redis:8-alpine`, AOF persistence, a named volume, `redis-cli ping` healthcheck, network alias `redis`, and optional host port `REDIS_HOST_PORT=16379`.
  - Update `infra/docker/.env.infra.example`, `apps/api/.env.example`, `packages/config/env/api.env.example`, `scripts/dev/bootstrap-infra-env.sh`, `infra/docker/README.md`, and `scripts/dev/README.md`.
- App compose:
  - Rename `worker` service to `document-vector` in `infra/docker/compose.dev.yml`.
  - Remove `container_name` from `document-vector` so `--scale document-vector=3` works.
  - Update `compose.e2e.yml` and scripts that reference `worker`.
- Queue behavior:
  - Use Redis Streams commands: `XGROUP CREATE ... MKSTREAM`, `XADD`, `XREADGROUP`, `XACK`, and `XAUTOCLAIM`/pending cleanup.
  - Redis messages carry `job_id`; SQL remains authoritative for status and payload fields.
  - Claim jobs with an atomic SQL status update from `queued` to `processing`; duplicate Redis messages are acked/skipped if SQL is no longer `queued`.
  - `enqueue()` raises a queue-unavailable error on Redis failure and never falls back to SQL. Add a repair loop that periodically XADDs still-`queued` SQL jobs so dual-write gaps do not strand work.
  - Preserve existing stale-processing reconciliation: crashed/abandoned jobs become failed by timeout and remain manually retryable.
- Worker runtime:
  - Add `ragdoll.workers.document_vector_worker` or refactor `document_worker.py` to log as `document-vector`; keep compatibility imports where tests/scripts rely on old names.
  - Derive Redis consumer name from hostname + pid unless `DOCUMENT_VECTOR_CONSUMER_NAME` is set.
  - Readiness `/api/v1/health` and `/status` must report queue backend `redis` and actually ping Redis when configured.

## Test Plan

- Backend platform tests:
  - Redis settings parse correctly.
  - Redis queue creates consumer group, enqueues job IDs, claims one job per worker, acks completion/failure, skips duplicate messages, and raises on Redis outage.
  - SQL and in-memory queue tests still pass when explicitly selected.
  - Readiness reports Redis healthy/unhealthy/not configured correctly.
- Script/compose tests:
  - Env bootstrap hydrates `REDIS_URL`.
  - Compose service names are updated to `document-vector`.
  - Scaling docs and examples use `--scale document-vector=3`.
- Integration/E2E:
  - `./dev-setup.sh test-infra` verifies Redis ping plus an upload processed by the worker.
  - `./dev-setup.sh test-e2e` starts or requires infra, then verifies document processing still reaches `completed`.
- Final validation:
  - `./dev-setup.sh test`
  - `./dev-setup.sh test-e2e`
  - Run `./dev-setup.sh daemon --scale document-vector=3` and upload multiple documents to confirm they drain from the same stream without duplicate processing.

## Assumptions And References

- No DB migration is required unless implementation discovers a need to persist Redis stream IDs.
- Redis Streams are chosen instead of Redis lists because consumer groups support multi-worker reads and acknowledgements.
- Sources used: [redis-py on PyPI](https://pypi.org/project/redis/) and [Redis Streams docs](https://redis.io/docs/latest/develop/data-types/streams/).
