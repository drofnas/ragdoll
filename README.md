# Ragdoll

Ragdoll is being rebuilt in this repository as the canonical clean-room source of truth. The repository now includes the Phase 0 foundation work and a full Phase 1 platform/runtime skeleton across `apps/api`, `apps/web`, and local dev infrastructure.

## Current Status

This repository currently implements:

- **Phase 0 - Repo Foundation**
- **Phase 1 - Platform And Runtime Base**

- The canonical application roots are `apps/api` and `apps/web`.
- Shared contracts live in `packages/contracts`.
- Shared env and tooling configuration live in `packages/config`.
- Product-level end-to-end tests live in `tests/e2e`.
- Local infrastructure assets live under `infra/`.
- The previous repository is private migration input only and is not part of the public structure here.

The clean repo now provides:

- a bootable FastAPI scaffold with shared core/runtime primitives
- a bootable Vite + React scaffold with role-aware shells and providers
- lazy DB/Alembic foundations
- runnable local dev Docker wiring for the new app roots
- a Phase 2 contract package layout and `/api/v1` module registry scaffold

## Preserved Phase 0 Conventions

The rebuild currently preserves the original stack direction while the structure is being cleaned up:

- Backend runtime: FastAPI in `apps/api`
- Backend dependency convention: `requirements.txt` plus Docker-based local execution
- Frontend runtime: Vite + React in `apps/web`
- Frontend package manager: `npm`
- Database migrations: Alembic
- Local development orchestration: Docker Compose
- Shared contracts: scaffolded now in `packages/contracts`, with a Phase 2 OpenAPI export and TypeScript-generation workflow stub
- Script ownership: thin developer entrypoints under `scripts/dev`, `scripts/test`, and `scripts/ops`

## Repository Structure

```text
ragdoll-redux/
  apps/
    api/
    web/
  packages/
    contracts/
    config/
    tooling/
  tests/
    e2e/
  infra/
    docker/
    supabase/
    ollama/
  scripts/
    dev/
    test/
    ops/
  docs/
```

See [docs/migration-map.md](docs/migration-map.md) for the old-to-new root mapping used during the rebuild.

## Bootstrap Entry Points

The repo now has a runnable two-app development skeleton with `./dev-setup.sh` as the main convenience entrypoint and `scripts/` as the underlying thin command owners.

- Primary convenience entrypoint: `./dev-setup.sh`
- Typical first commands:
  - `./dev-setup.sh up`
  - `./dev-setup.sh daemon`
  - `./dev-setup.sh ps`
  - `./dev-setup.sh test`
- Runtime startup commands auto-create:
  - `apps/api/.env` from `apps/api/.env.example`
  - `apps/web/.env` from `apps/web/.env.example`
- Edit app-local defaults here when needed:
  - `apps/api/.env.example`
  - `apps/web/.env.example`
- Development entrypoints: `scripts/dev/`
- Test entrypoints: `scripts/test/`
- Ops notes and future operational commands: `scripts/ops/`
- Testing ownership and expectations: [TESTING.md](TESTING.md)
- Shared mirrored env templates: `packages/config/env/`
- Local Docker ownership: `infra/docker/`

## What Is Deferred

The following work is still deferred:

- feature module API routes and feature pages
- generated shared contracts
- real auth/session bootstrap endpoints
- worker entrypoints and queue runtime
- full E2E compose parity

## Placeholder Directories

Some directories intentionally remain scaffolds so the architecture stays clean while feature code is migrated incrementally in later phases.
