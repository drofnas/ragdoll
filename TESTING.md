# Testing

The repository now includes the first backend platform bootstrap tests in `apps/api/tests/platform/`, while most feature and integration coverage is still deferred.

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

These scripts are still lightweight scaffolds. The first real backend bootstrap tests live directly under `apps/api/tests/platform/` and can be run from the app directory with `pytest`.

## Current Scope

Current validation includes repository-level checks plus backend bootstrap coverage:

- confirm the directory structure matches the architecture docs
- confirm the shared env examples exist
- confirm the scripts and infra locations are obvious to contributors
- confirm no private machine-specific paths are committed
- confirm `ragdoll.main:app` imports without DB, worker, or feature wiring
- confirm `GET /health` and `GET /api/v1/health` return the bootstrap scaffold responses

Feature-level and cross-system automation remain deferred until the corresponding runtime layers exist.
