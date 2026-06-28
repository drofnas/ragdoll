# `apps/web`

Canonical home for the Vite + React web application.

The web app now includes the first live workspace slice:

- TypeScript + Vite app bootstrap under `src/`
- app-level router, providers, shells, and guards
- real auth/session bootstrap and owned-Space scope loading
- live auth, Spaces, documents, dashboard, and account pages
- shared API transport plus generated contract consumption from `packages/contracts/typescript`

Planned nearby ownership:

- application source under `src/`
- static assets under `public/`
- feature-owned UI and tests under the app tree
- `npm` as the package manager during the initial rebuild

Still deferred:

- retrieval-heavy web features such as search, chat, entities, pinned facts, changes, and corrections
- deeper admin tooling and public marketing pages
- fuller E2E critical-path coverage beyond the current repo-owned test suite

## Local Commands

- install dependencies: `npm install`
- start dev server: `npm run dev`
- run frontend tests: `npm run test`
