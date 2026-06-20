# `apps/api`

Canonical home for the FastAPI backend application.

Phase 1 now includes the backend runtime and DB foundations:

- application package under `src/ragdoll/`
- FastAPI app entrypoint at `ragdoll.main:app`
- clean liveness endpoint at `GET /health`
- clean readiness contract at `GET /api/v1/health`
- shared backend core services under `src/ragdoll/core/`
- DB engine, session, and Alembic scaffolding under `src/ragdoll/platform/db/`
- backend platform bootstrap tests under `tests/platform/`
- a Phase 2 `/api/v1` module registry scaffold across planned backend modules
- a Phase 2 contract-export entrypoint in `packages/tooling/scripts/generate_contracts.py`

Current nearby ownership:

- application source under `src/ragdoll/`
- backend tests under `tests/`
- Python dependency manifest using `requirements.txt`
- Alembic migrations owned by this app

Still deferred:

- concrete feature behavior behind module route mounts under `/api/v1`
- worker startup and platform adapters
- feature-specific models and migrations
- queue runtime and long-running worker execution

## Local Commands

- start dev server: `uvicorn ragdoll.main:app --host 0.0.0.0 --port 8000 --reload`
- run platform tests: `../../scripts/test/backend.sh`
- export OpenAPI + contract scaffold from Docker: `docker compose -f ../../infra/docker/compose.dev.yml run --rm -w /workspace backend python3 packages/tooling/scripts/generate_contracts.py`
- run Alembic upgrades: `alembic upgrade head`
