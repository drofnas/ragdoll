# `apps/api`

Canonical home for the FastAPI backend and worker-owned runtime.

## Current Responsibilities

`apps/api` owns:

- the HTTP application entrypoint at `src/ragdoll/main.py`
- top-level router composition under `src/ragdoll/api/`
- versioned backend modules registered by `src/ragdoll/modules/registry.py`
- shared runtime concerns in `src/ragdoll/core/`
- platform adapters in `src/ragdoll/platform/`
- background workers in `src/ragdoll/workers/`
- DBmate schema and migrations in `db/`

The current `/api/v1` module surface includes:

- `auth`, `users`, `spaces`
- `documents`, `ingestion`
- `search`, `chat`, `entities`, `knowledge_graph`
- `pinned_facts`, `changes`, `corrections`
- `admin`, `usage`

## Runtime Notes

- Liveness endpoint: `GET /health`
- Readiness endpoint: `GET /api/v1/health`
- Runtime status page data is served through the backend and powers `/status` in the web app
- CORS, request logging, and exception handling are bootstrapped in `src/ragdoll/main.py`
- The Redis-backed document processing queue is part of the live runtime shape

## Local Commands

Repository rules prefer Docker-backed wrappers for backend work.

- run backend tests: `../../scripts/test/backend.sh`
- run full repo validation: `../../dev-setup.sh test`
- run E2E validation: `../../dev-setup.sh test-e2e`
- export OpenAPI and contracts: `docker compose -f ../../infra/docker/compose.dev.yml run --rm -w /workspace backend python3 packages/tooling/scripts/generate_contracts.py`
- run DB migrations inside Docker: `docker compose -f ../../infra/docker/compose.dev.yml run --rm -w /workspace/apps/api backend alembic upgrade head`

## Working In This Area

- Add or update backend capability logic under `src/ragdoll/modules/<module>/`
- Keep app-wide policies in `src/ragdoll/core/`
- Keep shared runtime adapters in `src/ragdoll/platform/`
- Keep worker entrypoints in `src/ragdoll/workers/`
- Add module tests under `tests/modules/` and platform tests under `tests/platform/`

For system-level architecture, start with [../../docs/architecture/backend-architecture.md](../../docs/architecture/backend-architecture.md).
