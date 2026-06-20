# Testing

The repository now includes backend platform tests in `apps/api/tests/platform/` and frontend runtime/bootstrap tests in `apps/web/src/app/tests/` and `apps/web/src/shared/api/tests/`.

## Ownership

- Backend tests belong under `apps/api/tests/`
- Frontend feature tests belong with the owning feature in `apps/web`
- Product-level end-to-end tests belong under `tests/e2e/`
- Shared config for test tooling belongs under `packages/config/test/`

## Entry Points

- `scripts/test/all.sh`
- `scripts/test/backend.sh`
- `scripts/test/frontend.sh`
- `scripts/test/e2e.sh`

These scripts now run the app-local bootstrap suites for backend and frontend. E2E remains intentionally partial until later phases.

## Current Scope

Current validation includes repository-level checks plus runtime/bootstrap coverage:

- confirm the directory structure matches the architecture docs
- confirm the shared env examples exist
- confirm the scripts and infra locations are obvious to contributors
- confirm no private machine-specific paths are committed
- confirm `ragdoll.main:app` imports without DB, worker, or feature wiring
- confirm `GET /health` and `GET /api/v1/health` return the scaffold/runtime readiness responses
- confirm `apps/web` renders public, authenticated, and admin scaffold shells

Feature-level and cross-system automation remain deferred until the corresponding module and contract layers exist.
