# `apps/web`

Canonical home for the Vite + React workspace.

## Current Responsibilities

`apps/web` owns:

- route composition in `src/app/router.tsx`
- app-wide providers in `src/app/providers.tsx`
- public, authenticated, and admin shells in `src/app/shell/`
- route guards in `src/app/guards/`
- feature pages and feature-local API wrappers in `src/features/`
- shared browser transport and shared state in `src/shared/`

The live route surface includes:

- public: `/`, `/login`, `/register`, `/status`
- authenticated: `/dashboard`, `/spaces`, `/documents`, `/documents/:documentId`, `/search`, `/chat`, `/chat/:sessionId`, `/entities`, `/entities/:entityId`, `/pinned-facts`, `/pinned-facts/create`, `/pinned-facts/:factId`, `/changes`, `/account`
- admin: `/admin`

## Implementation Notes

- Query state is provided through TanStack Query
- auth session and selected space scope are app-wide providers
- feature request shapes come from `packages/contracts/typescript`
- the backend remains authoritative for runtime status, messages, citations, changes, and pinned-fact state

## Local Commands

- install dependencies: `npm install`
- start dev server: `npm run dev`
- run frontend tests: `npm run test`
- run full repo validation from the repo root: `../../dev-setup.sh test`

## Working In This Area

- Add pages under `src/features/<feature>/pages/`
- Wire routes in `src/app/router.tsx`
- Keep cross-feature transport in `src/shared/api/`
- Keep app-wide state in `src/shared/state/`
- Add app wiring tests in `src/app/tests/` and feature tests near the owning feature

For system-level architecture, start with [../../docs/architecture/frontend-architecture.md](../../docs/architecture/frontend-architecture.md).
