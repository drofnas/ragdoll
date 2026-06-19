# `apps/api`

Canonical home for the FastAPI backend application.

Phase 1 now includes the initial runtime bootstrap:

- application package under `src/ragdoll/`
- FastAPI app entrypoint at `ragdoll.main:app`
- clean liveness endpoint at `GET /health`
- clean readiness scaffold at `GET /api/v1/health`
- backend platform bootstrap tests under `tests/platform/`

Current nearby ownership:

- application source under `src/ragdoll/`
- backend tests under `tests/`
- Python dependency manifest using `requirements.txt`
- Alembic migrations owned by this app

Still deferred:

- database session and migration wiring
- auth, security, and feature flag primitives
- module route mounts under `/api/v1`
- worker startup and platform adapters
