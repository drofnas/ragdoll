# Ragdoll

Ragdoll is rebuilt in this repository as the canonical clean-room source of truth for a self-hosted local installation. The repository now includes the end-to-end workspace product surface through self-hosted operator completion across `apps/api`, `apps/web`, and `infra/`.

License: [Business Source License 1.1](LICENSE.txt)
Free for personal use and internal organizational use; see [License Summary](LICENSE-SUMMARY.md)
Apache License 2.0 on 2030-01-01

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
- **Phase 8 - Retrieval And Knowledge Foundations**
- **Phase 9 - Search, Entities, And Graph Exploration**
- **Phase 10 - Stateful Workflows And Chat Foundations**
- **Phase 11 - Web Workspace Foundations**
- **Phase 12 - Retrieval And Interaction Web Surfaces**
- **Phase 13 - Self-Hosted Operator Completion**

- The canonical application roots are `apps/api` and `apps/web`.
- Shared contracts live in `packages/contracts`.
- Shared env and tooling configuration live in `packages/config`.
- Product-level end-to-end tests live in `tests/e2e`.
- Local infrastructure assets live under `infra/`.
- The previous repository is private migration input only and is not part of the public structure here.

The clean repo now provides:

- a bootable FastAPI runtime with auth, spaces, documents, ingestion, search, chat, entities, pinned facts, changes, admin, and usage slices
- a bootable Vite + React workspace with public login/register/status routes plus authenticated and admin shells
- shared contracts and OpenAPI export tooling
- DBmate-backed relational foundations for identity, spaces, documents, usage, chat, pinned facts, changes, and corrections
- runnable local dev Docker wiring for the app stack plus Dockerized Supabase and Ollama dependencies
- operator-facing readiness, health, and effective-instance-policy surfaces for self-hosted installs

## Preserved Phase 0 Conventions

The rebuild currently preserves the original stack direction while the structure is being cleaned up:

- Backend runtime: FastAPI in `apps/api`
- Backend dependency convention: `requirements.txt` plus Docker-based local execution
- Frontend runtime: Vite + React in `apps/web`
- Frontend package manager: `npm`
- Database migrations: DBmate
- Local development orchestration: Docker Compose
- Shared contracts: exported from the backend and generated into `packages/contracts`
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

Use these commands for the local runtime:

- `./dev-setup.sh infra up` to bootstrap and start Dockerized Supabase plus Ollama
- `./dev-setup.sh daemon` to start the app stack in the background
- `./dev-setup.sh test-infra` to run the opt-in live readiness and manual-upload smoke suite
- `./dev-setup.sh infra ps` to inspect dependency containers
- `./dev-setup.sh logs` and `./dev-setup.sh infra logs` for app or dependency log inspection
- `./dev-setup.sh down` and `./dev-setup.sh infra down` to tear the stacks down

The logged-out surface intentionally stays small for self-hosted installs:

- `/` and `/login` render the login page
- `/register` supports open self-registration
- `/status` remains the backend-served system status page

## What Is Deferred

The following work is still deferred:

- broader critical-path E2E coverage across search, chat, pinned facts, and guarded admin workflows
- final hardening and timeout cleanup for the slowest frontend and integration paths
- additional operator documentation polish from clone to local production-style operation

## Placeholder Directories

Some directories intentionally remain scaffolds so the architecture stays clean while feature code is migrated incrementally in later phases.
