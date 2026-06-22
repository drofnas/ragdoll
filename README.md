# Ragdoll

Ragdoll is being rebuilt in this repository as the canonical clean-room source of truth. The repository now includes completed implementation work through the first end-to-end ingestion slice plus the Phase 7 local dependency runtime foundations across `apps/api`, `apps/web`, and `infra/`.

## Current Status

This repository currently implements:

- **Phase 0 - Repo Foundation**
- **Phase 1 - Platform And Runtime Base**
- **Phase 2 - Shared Contracts And API Skeleton**
- **Phase 3 - Identity And Space Migration**
- **Phase 4 - Document And Usage Foundations**
- **Phase 5 - Document Library And Usage Summary**
- **Phase 6 - Manual Upload And Processing Backbone**
- **Phase 7 - Local Dependency Runtime And Integration Foundations**

- The canonical application roots are `apps/api` and `apps/web`.
- Shared contracts live in `packages/contracts`.
- Shared env and tooling configuration live in `packages/config`.
- Product-level end-to-end tests live in `tests/e2e`.
- Local infrastructure assets live under `infra/`.
- The previous repository is private migration input only and is not part of the public structure here.

The clean repo now provides:

- a bootable FastAPI runtime with auth, spaces, documents, usage, and ingestion slices
- a bootable Vite + React scaffold with role-aware shells and providers
- shared contracts and OpenAPI export tooling
- Alembic-backed relational foundations for identity, spaces, documents, usage, and ingestion jobs
- runnable local dev Docker wiring for the app stack plus Dockerized Supabase and Ollama dependencies
- an opt-in Phase 7 infra smoke path for live readiness and manual-upload verification

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
  - `./dev-setup.sh infra up`
  - `./dev-setup.sh up`
  - `./dev-setup.sh daemon`
  - `./dev-setup.sh ps`
  - `./dev-setup.sh test`
  - `./dev-setup.sh test-infra`
- Runtime startup commands auto-create:
  - `apps/api/.env` from `apps/api/.env.example`
  - `apps/web/.env` from `apps/web/.env.example`
- Local dependency startup also auto-creates:
  - `infra/docker/.env.infra` from `infra/docker/.env.infra.example`
- Edit app-local defaults here when needed:
  - `apps/api/.env.example`
  - `apps/web/.env.example`
- Development entrypoints: `scripts/dev/`
- Test entrypoints: `scripts/test/`
- Ops notes and future operational commands: `scripts/ops/`
- Testing ownership and expectations: [TESTING.md](TESTING.md)
- Shared mirrored env templates: `packages/config/env/`
- Local Docker ownership: `infra/docker/`

## Local Full-Stack Flow

Use these commands for the Phase 7 local runtime:

- `./dev-setup.sh infra up` to bootstrap and start Dockerized Supabase plus Ollama
- `./dev-setup.sh daemon` to start the app stack in the background
- `./dev-setup.sh test-infra` to run the opt-in live readiness and manual-upload smoke suite
- `./dev-setup.sh infra ps` to inspect dependency containers
- `./dev-setup.sh logs` and `./dev-setup.sh infra logs` for app or dependency log inspection
- `./dev-setup.sh down` and `./dev-setup.sh infra down` to tear the stacks down

Phase 7 readiness and `test-infra` prove local infrastructure reachability plus ingestion confidence. They do not yet prove retrieval, embeddings, entities, or graph projection behavior, which remain Phase 8 work.

## What Is Deferred

The following work is still deferred:

- retrieval projection, embeddings, entity extraction, and graph projection
- search, chat, tracked-state, changes, corrections, and admin product surfaces
- full frontend feature implementation beyond the current shell/runtime scaffolds
- deeper critical-path E2E coverage beyond shell and opt-in infra smoke validation

## Placeholder Directories

Some directories intentionally remain scaffolds so the architecture stays clean while feature code is migrated incrementally in later phases.
