# Repository Index for Code Navigation

Use this file as the first stop for finding where to update pages, add logic, place new files, and choose the right test location. Humans and agents should read this before traversing the repo in depth.

## High-Level Edit Map

- Add frontend pages in `apps/web/src/features/<feature>/pages/`.
- Update frontend route wiring in `apps/web/src/app/router.tsx`.
- Add app-wide providers in `apps/web/src/app/providers.tsx`.
- Add route guards in `apps/web/src/app/guards/`.
- Add shell-level layout chrome in `apps/web/src/app/shell/`.
- Add shared frontend API clients in `apps/web/src/shared/api/`.
- Add shared frontend state in `apps/web/src/shared/state/`.
- Add shared frontend types in `apps/web/src/shared/types/`.
- Add backend API modules in `apps/api/src/ragdoll/modules/<module>/`.
- Register backend v1 API surface in `apps/api/src/ragdoll/modules/registry.py`.
- Update top-level API composition in `apps/api/src/ragdoll/api/` when router-wide behavior changes.
- Add backend platform services in `apps/api/src/ragdoll/platform/`.
- Add worker entrypoints in `apps/api/src/ragdoll/workers/`.
- Update local Docker infra and scalable runtime services in `infra/docker/`.
- Update shared contracts in `packages/contracts/`.
- Put shared env, lint, and test config in `packages/config/`.
- Put repo-owned generation and utility scripts in `packages/tooling/` or `scripts/` based on whether they are codegen/tooling or operator entrypoints.
- Put product-level E2E coverage in `tests/e2e/`.
- Use `./dev-setup.sh` and `scripts/` as the main operational entrypoints.

## Root Structure

- `apps/` - Application roots. Most product code lives here.
- `apps/api/` - FastAPI backend app, tests, Docker dev image, and Alembic config.
- `apps/web/` - Vite + React frontend app, app shell, feature pages, and shared browser code.
- `packages/` - Shared contracts, config, and repo tooling.
- `tests/` - Product-level E2E harness and Playwright project.
- `infra/` - Docker, Supabase, and local infrastructure assets.
- `scripts/` - Thin developer, test, and ops entrypoints.
- `docs/` - Architecture notes, migration maps, and implementation docs.
- `_tmp/` - Scratch output. Do not treat as source of truth.
- `README.md` - Repo overview and bootstrap entrypoints.
- `AGENTS.md` - Agent workflow rules for this repository.
- `INDEX.md` - This navigation index.
- Do not edit local caches or generated artifacts by hand, including `.pytest_cache/`, `.venv/`, and other machine-local outputs unless a task explicitly targets them.

## Frontend Structure

### `apps/web/`

- `apps/web/src/main.tsx` - Browser bootstrap entrypoint.
- `apps/web/src/app/` - App-level composition.
- `apps/web/src/app/router.tsx` - Central route table. Update this when adding or re-homing pages.
- `apps/web/src/app/providers.tsx` - Query client, Mantine theme, and app-wide React providers.
- `apps/web/src/app/guards/` - Route access guards such as authenticated or admin gates.
- `apps/web/src/app/shell/` - Public, authenticated, and admin shell layouts.
- `apps/web/src/app/tests/` - App composition tests for router, guards, and providers.
- `apps/web/src/components/assistant-ui/` - Assistant-ui presentation primitives adapted for Ragdoll feature surfaces.
- `apps/web/src/features/` - Feature-owned UI and pages. New page-level work should usually start here.
- `apps/web/src/features/<feature>/pages/` - Add routed page components here.
- `apps/web/src/shared/api/` - Shared API client code used across features.
- `apps/web/src/shared/state/` - Cross-feature React context and shared state ownership.
- `apps/web/src/shared/types/` - Shared frontend-only types and app contracts.
- `apps/web/src/styles/` - Global app styling.
- `apps/web/public/` - Static public assets served directly by the frontend app.

### Frontend Placement Rules

- Add a new routed page under `apps/web/src/features/<feature>/pages/` and wire it into `apps/web/src/app/router.tsx`.
- Keep feature-specific UI, hooks, and helpers with the owning feature unless they are reused across features.
- Promote reusable browser code into `apps/web/src/shared/` only after it is truly cross-feature.
- Put app-wide provider changes in `apps/web/src/app/providers.tsx`, not inside feature pages.
- Put access-control flow in `apps/web/src/app/guards/`.
- Put shell or role-layout changes in `apps/web/src/app/shell/`.
- Place frontend tests near the owning area:
  - app wiring tests in `apps/web/src/app/tests/`
  - shared API tests in `apps/web/src/shared/api/tests/`
  - feature tests alongside the owning feature when that structure is added

## Backend Structure

### `apps/api/`

- `apps/api/src/ragdoll/main.py` - FastAPI app bootstrap, middleware, logging, CORS, and lifespan wiring.
- `apps/api/src/ragdoll/api/` - Top-level API composition, shared dependencies, shared schemas, errors, and health routes.
- `apps/api/src/ragdoll/api/v1/router.py` - Versioned API router composition from the module registry.
- `apps/api/src/ragdoll/core/` - App-wide primitives such as config, auth, security, logging, pagination, feature flags, and shared result types.
- `apps/api/src/ragdoll/modules/` - Feature and capability modules. Most new business functionality belongs here.
- `apps/api/src/ragdoll/modules/registry.py` - Central list of v1 modules and route/schema registration metadata.
- `apps/api/src/ragdoll/platform/` - Shared infrastructure services for DB, storage, queues, graph, and vector concerns.
- `apps/api/src/ragdoll/platform/queues/` - Document-processing queue adapters; Redis Streams is the scalable runtime queue, with SQL and memory adapters for explicit fallback/test modes.
- `apps/api/src/ragdoll/platform/db/models/` - SQLAlchemy models.
- `apps/api/src/ragdoll/platform/db/migrations/` - Alembic environment and migration versions.
- `apps/api/src/ragdoll/workers/` - Worker entrypoints and background pipeline wiring; `document_vector_worker.py` is the scalable document-processing worker entrypoint.
- `apps/api/tests/platform/` - Platform and bootstrap coverage.
- `apps/api/tests/modules/` - Module-level API and contract coverage.

### Backend Module Placement Rules

- Add a new backend capability under `apps/api/src/ragdoll/modules/<module>/`.
- Add HTTP route handlers in `apps/api/src/ragdoll/modules/<module>/api/routes.py`.
- Add request and response schemas in `apps/api/src/ragdoll/modules/<module>/api/schemas.py`.
- Add application-layer commands, queries, and orchestration in `apps/api/src/ragdoll/modules/<module>/application/` when the module uses that split.
- Add domain rules and policies in `apps/api/src/ragdoll/modules/<module>/domain/`.
- Add repositories and persistence adapters in `apps/api/src/ragdoll/modules/<module>/infrastructure/`.
- Register new v1 modules in `apps/api/src/ragdoll/modules/registry.py`.
- Put app-wide cross-cutting concerns in `apps/api/src/ragdoll/core/`, not inside a feature module.
- Put shared runtime services in `apps/api/src/ragdoll/platform/` when they support multiple modules.
- Put scalable local worker service changes in `infra/docker/compose.dev.yml` under the `document-vector` service.
- Put DB models in `apps/api/src/ragdoll/platform/db/models/` and migrations in `apps/api/src/ragdoll/platform/db/migrations/versions/`.
- Put backend tests in the matching area under `apps/api/tests/modules/` or `apps/api/tests/platform/`.

## Shared Packages

- `packages/contracts/` - Shared API contracts.
- `packages/contracts/openapi/` - Exported OpenAPI artifacts.
- `packages/contracts/schemas/` - Source schemas grouped by capability.
- `packages/contracts/typescript/` - Generated TypeScript contract package output.
- `packages/config/` - Shared env templates plus lint and test config ownership.
- `packages/tooling/` - Repo tooling, codegen support, and utility scripts such as contract generation.

### Shared Package Placement Rules

- Update `packages/contracts/` when a backend or frontend interface should be shared across app boundaries.
- Put mirrored env examples in `packages/config/env/` when they are shared repo defaults.
- Put shared lint/test configuration under `packages/config/`, not inside app-local runtime code.
- Put codegen and reusable maintenance tooling in `packages/tooling/`.

## Testing And Validation

- Backend tests live in `apps/api/tests/`.
- Frontend app-wiring tests live in `apps/web/src/app/tests/`.
- Shared frontend API tests live in `apps/web/src/shared/api/tests/`.
- Product-level Playwright coverage lives in `tests/e2e/`.
- E2E helpers belong in `tests/e2e/helpers/` and reusable fixtures in `tests/e2e/fixtures/`.
- Preferred validation entrypoints:
  - `./dev-setup.sh test`
  - `./dev-setup.sh test-backend`
  - `./dev-setup.sh test-frontend`
  - `./dev-setup.sh test-e2e`
- Backend Python verification should run through the Docker-backed repo wrappers, not host-installed Python tools.

## Placement Rules

- If you are editing a page, start in `apps/web/src/features/` and then update `apps/web/src/app/router.tsx` if routing changes.
- If you are adding shared browser logic, prefer `apps/web/src/shared/` over duplicating code across features.
- If you are adding a backend feature, start in `apps/api/src/ragdoll/modules/` and register it through `apps/api/src/ragdoll/modules/registry.py`.
- If you are adding platform plumbing used by multiple backend modules, place it in `apps/api/src/ragdoll/platform/`.
- If you are adding a repo-level command, prefer `scripts/` for operator entrypoints and `packages/tooling/` for codegen or reusable tooling internals.
- If you are adding tests, place them with the owning layer instead of creating a new top-level test area.
- Keep `INDEX.md` updated when directory ownership or placement conventions change so future contributors do not need to rediscover the structure.
