# `packages/contracts`

Canonical public contract home for the rebuild.

The source of truth for wire models lives in the backend module API schemas under `apps/api/src/ragdoll/modules/<module>/api/schemas.py`. This package holds generated artifacts and ownership notes so the web app and later integrations consume explicit shared contracts instead of re-declaring shapes ad hoc.

## Subareas

- `openapi/`
  - generated OpenAPI snapshots exported from the FastAPI app
- `schemas/`
  - ownership notes for shared and module-specific schema groups
- `typescript/`
  - generated TypeScript output derived from the OpenAPI snapshot for frontend consumption

## Rules

- Do not hand-maintain canonical TypeScript wire types separately from backend schemas.
- Treat the old private repository as reconstruction input only, never as a second contract authority.
- Keep public route ownership versioned under `/api/v1`.
