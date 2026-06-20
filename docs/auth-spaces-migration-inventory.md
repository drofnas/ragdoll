# Auth And Spaces Migration Inventory

This document captures the Phase 2 migration-prep decisions for the first bounded slice: `auth`, `users`, and `spaces`.

The previous private repository is reconstruction input only. This document records the clean-room target behavior for the canonical rebuild.

## Module Mapping

| Legacy area | New backend owner | Notes |
| --- | --- | --- |
| `backend/app/routers/auth.py` | `modules/auth` and `modules/users` | Authentication stays separate from user lifecycle and plan-tier ownership. |
| `backend/app/schemas/auth.py` | `modules/auth/api/schemas.py` | Session and auth response contracts migrate first. |
| `backend/app/routers/spaces.py` | `modules/spaces` | Space CRUD and default-space behavior become a dedicated bounded context. |
| `backend/app/schemas/spaces.py` | `modules/spaces/api/schemas.py` | Space wire models become module-owned contracts. |

## Preserve

- Versioned route ownership under `/api/v1/auth/*` and `/api/v1/spaces/*`.
- Auth follow-on endpoints:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - `PATCH /api/v1/auth/me`
- Spaces follow-on endpoints:
  - `GET /api/v1/spaces`
  - `POST /api/v1/spaces`
  - `GET /api/v1/spaces/{space_id}`
  - `PATCH /api/v1/spaces/{space_id}`
  - `DELETE /api/v1/spaces/{space_id}`
- Auth session responses keep `plan_tier` and resolved `feature_flags`.
- Spaces keep `is_default` as an explicit contract field.
- Default-space behavior remains product-important and stays in scope for the first migration slice.

## Rename Or Restructure

- Legacy unversioned `/api/auth/*` and `/api/spaces/*` paths become `/api/v1/...`.
- Auth implementation splits into:
  - `modules/auth` for registration, login, session bootstrap, password verification, and guards
  - `modules/users` for user lifecycle, plan-tier ownership, and feature-flag overrides
- Space scope becomes a shared contract concept instead of repeated ad hoc query params across modules.
- Backend transport models move from legacy shared schema folders into module-local `api/schemas.py` files.

## Defer

- Concrete document, search, and chat scoping parameters until they can adopt the shared `SpaceScope` contract cleanly.
- Space aggregate counts for documents, chat sessions, and entities until those owning modules are migrated into the clean repo.
- Final decision on `POST /api/v1/auth/login` request encoding until the auth slice is implemented. The response contract and route path stay preserved; transport cleanup is intentionally deferred for that slice.
- Account-facing user profile endpoints outside `/auth/me` until the `users` module has concrete behavior.

## Drop

- Legacy route aliases without API versioning.
- Private implementation details such as auth cache internals as contract obligations.
- Any assumption that legacy nullable or loosely scoped Space data should be preserved as a rebuild default.

## First Slice Acceptance Direction

The first real migration slice should be considered ready when:

- `auth`, `users`, and `spaces` have module-owned routes and schemas in the clean repo
- old auth/spaces tests are ported to `/api/v1`
- `plan_tier`, `feature_flags`, and `is_default` are represented explicitly in the new wire contracts
- shared `SpaceScope` is stable enough for later document, search, and chat adoption
