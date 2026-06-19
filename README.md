# Ragdoll

Ragdoll is being rebuilt in this repository as the canonical clean-room source of truth. Phase 0 establishes the repository shape, shared conventions, and contributor entrypoints without migrating feature code yet.

## Current Status

This repository currently implements **Phase 0 - Repo Foundation** only.

- The canonical application roots are `apps/api` and `apps/web`.
- Shared contracts live in `packages/contracts`.
- Shared env and tooling configuration live in `packages/config`.
- Product-level end-to-end tests live in `tests/e2e`.
- Local infrastructure assets live under `infra/`.
- The previous repository is private migration input only and is not part of the public structure here.

Feature runtime bootstrap, API wiring, database wiring, and web app bootstrapping are deferred to Phase 1.

## Preserved Phase 0 Conventions

Phase 0 intentionally preserves the current stack direction while the repo is restructured:

- Backend runtime: FastAPI in `apps/api`
- Backend dependency convention: `requirements.txt` plus Docker-based local execution
- Frontend runtime: Vite + React in `apps/web`
- Frontend package manager: `npm`
- Database migrations: Alembic
- Local development orchestration: Docker Compose
- Shared contracts: scaffolded now in `packages/contracts`, with generation deferred to a later phase
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

Phase 0 provides the command surface and canonical locations, not a full runnable product stack.

- Development entrypoints: `scripts/dev/`
- Test entrypoints: `scripts/test/`
- Ops notes and future operational commands: `scripts/ops/`
- Testing ownership and expectations: [TESTING.md](TESTING.md)
- Environment examples: `packages/config/env/`
- Local Docker ownership: `infra/docker/`

## What Is Deferred

The following work starts in Phase 1 or later:

- FastAPI app bootstrapping and `/api/v1` router composition
- Vite app bootstrapping and route shell rendering
- Database engine/session wiring and migrations setup
- Worker entrypoints
- Contract generation tooling
- Real backend, frontend, and E2E automation

## Placeholder Directories

Some directories intentionally contain only README or placeholder files in Phase 0 so the documented structure exists before feature code is migrated. Those placeholders are intentional and should be replaced incrementally as later phases land.
