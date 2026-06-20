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

Current nearby ownership:

- application source under `src/ragdoll/`
- backend tests under `tests/`
- Python dependency manifest using `requirements.txt`
- Alembic migrations owned by this app

Still deferred:

- module route mounts under `/api/v1`
- worker startup and platform adapters
- feature-specific models and migrations
- queue runtime and long-running worker execution

## Local Commands

- start dev server: `uvicorn ragdoll.main:app --host 0.0.0.0 --port 8000 --reload`
- run platform tests: `python3 -m pytest tests/platform -q`
- run Alembic upgrades: `alembic upgrade head`
