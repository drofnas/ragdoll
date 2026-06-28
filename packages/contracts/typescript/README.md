# `packages/contracts/typescript`

Generated TypeScript output for frontend and integration consumption.

Source of truth: the OpenAPI snapshot in `packages/contracts/openapi`, which is exported from the FastAPI app.

Generation entrypoint: `packages/tooling/scripts/generate_contracts.py`

Artifacts written here:

- `index.ts` with generated schema and operation types
- `manifest.json` with generation metadata and the canonical entrypoint

Feature clients in `apps/web` should keep using the shared transport layer and import request or response types from this directory rather than generating request helpers.
