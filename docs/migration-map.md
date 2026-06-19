# Migration Map

This repository is the canonical home for the rebuild. During migration, use the previous private repository only as reconstruction input.

## Root Mapping

- old `backend/` -> new `apps/api/`
- old `frontend/` -> new `apps/web/`
- old `e2e/` -> new `tests/e2e/`
- old Docker compose files -> new `infra/docker/`
- old helper scripts -> new `scripts/dev/`, `scripts/test/`, and `scripts/ops/`

## Migration Rules

- Write public docs and committed code as if this repository is the only canonical source of truth.
- Prefer moving structure and conventions first, then migrate implementation code by bounded context.
- Do not preserve the old repo layout inside this repository as a compatibility layer.
- Keep private local references out of committed configuration and docs.
