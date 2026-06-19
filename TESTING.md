# Testing

Phase 0 defines the ownership and entrypoints for testing without introducing product-runtime test execution yet.

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

These scripts are lightweight scaffolds in Phase 0. They establish the canonical command surface that later phases will wire to real backend, frontend, and E2E execution.

## Scope For This Phase

Phase 0 validation is repository-level only:

- confirm the directory structure matches the architecture docs
- confirm the shared env examples exist
- confirm the scripts and infra locations are obvious to contributors
- confirm no private machine-specific paths are committed

Feature-level test automation is deferred until the corresponding runtime layers exist.
