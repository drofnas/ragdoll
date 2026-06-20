# `apps/web`

Canonical home for the Vite + React web application.

Phase 1 now includes the initial scaffold-only frontend runtime:

- TypeScript + Vite app bootstrap under `src/`
- app-level router, providers, shells, and guards
- scaffold auth/session and Space scope state
- placeholder public, authenticated, and admin pages
- shared API transport for future contract-driven clients

Planned nearby ownership:

- application source under `src/`
- static assets under `public/`
- feature-owned UI and tests under the app tree
- `npm` as the package manager during the initial rebuild

Still deferred:

- feature-specific pages and API clients
- generated contract consumption from `packages/contracts`
- real auth/session bootstrap requests
- E2E runtime wiring

## Local Commands

- install dependencies: `npm install`
- start dev server: `npm run dev`
- run frontend tests: `npm run test`
