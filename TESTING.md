# Testing

The repository now includes backend platform tests in `apps/api/tests/platform/` and frontend runtime/bootstrap tests in `apps/web/src/app/tests/` and `apps/web/src/shared/api/tests/`.

## Ownership

- Backend tests belong under `apps/api/tests/`
- Frontend feature tests belong with the owning feature in `apps/web`
- Product-level end-to-end tests belong under `tests/e2e/`
- Shared config for test tooling belongs under `packages/config/test/`

## Entry Points

- `./dev-setup.sh test-backend`
- `./dev-setup.sh test-frontend`
- `./dev-setup.sh test`
- `./dev-setup.sh test-infra`
- `./dev-setup.sh test-e2e`
- `scripts/test/all.sh`
- `scripts/test/backend.sh`
- `scripts/test/frontend.sh`
- `scripts/test/infra.sh`
- `scripts/test/e2e.sh`

The root wrapper is the primary human-facing entrypoint. The underlying `scripts/test/*` files still own the thin app-local bootstrap suites for backend, frontend, infra, and E2E smoke coverage.

Runtime startup commands can auto-create missing app `.env` files. Backend and E2E Docker-backed test commands now ensure the required runtime env files exist before bootstrapping containers.

`./dev-setup.sh test-e2e` temporarily runs the frontend with Docker-internal API settings so Playwright can reach the backend from inside the Compose network. After the E2E command exits, the script restores the normal development stack so host browsers use the app-local `apps/web/.env` API URL again.

`./dev-setup.sh test-infra` is intentionally opt-in. It boots the Dockerized dependency stack, starts the app stack, and runs a live manual-upload smoke suite against local Supabase and Ollama. It is not part of the default lightweight `./dev-setup.sh test` flow.

## Current Scope

Current validation includes repository-level checks plus runtime/bootstrap coverage:

- confirm the directory structure matches the architecture docs
- confirm the shared env examples exist
- confirm the scripts and infra locations are obvious to contributors
- confirm no private machine-specific paths are committed
- confirm `ragdoll.main:app` imports without DB, worker, or feature wiring
- confirm `GET /health` and `GET /api/v1/health` return the scaffold/runtime readiness responses
- confirm `apps/web` renders public, authenticated, and admin scaffold shells
- confirm local infra bootstrap, backup restore, upstream Supabase population, and Ollama runtime selection logic through platform tests
- confirm the opt-in infra smoke suite can validate live readiness plus the manual upload -> process -> detail/download path
- confirm the shell smoke E2E suite renders the public scaffold and redirects anonymous `/dashboard` access to `/login`

Deeper feature-level and critical-path E2E automation remain deferred until the corresponding module and contract layers exist.
