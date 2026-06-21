# API v1 Module Inventory

This document is the Phase 2 inventory for the canonical `/api/v1` surface.

The current goal is ownership and composition, not feature parity. Empty module routers are intentional where feature migrations have not started yet.

## Module Registry

| Module | Public prefix | Current Phase 2 status | Notes |
| --- | --- | --- | --- |
| `auth` | `/api/v1/auth` | scaffolded | First concrete migration slice after Phase 2. |
| `users` | `/api/v1/users` | scaffolded | Owns user lifecycle, plan tier, and feature-flag concerns even when early profile reads stay under auth. |
| `spaces` | `/api/v1/spaces` | scaffolded | First concrete migration slice after Phase 2. |
| `documents` | `/api/v1/documents` | implemented in Phase 5 | Owns list, detail, move, delete, and download flows with shared `SpaceScope` filtering and nested `ProcessingStatus`. |
| `ingestion` | `/api/v1/ingestion` | implemented in Phase 6 | Owns manual upload, parsing-job queueing, status reads, and parsing retries; vector, entity, and graph projection remain deferred. |
| `search` | `/api/v1/search` | scaffolded | Deferred until shared retrieval contracts are stable. |
| `chat` | `/api/v1/chat` | scaffolded | Deferred until search and citation contracts are stable. |
| `entities` | `/api/v1/entities` | scaffolded | Deferred until relational and provenance foundations land. |
| `knowledge_graph` | `/api/v1/knowledge-graph` | scaffolded | Public path uses kebab-case; backend module keeps snake_case. |
| `tracked_state` | `/api/v1/tracked-state` | scaffolded | Deferred until current-state conventions are locked. |
| `changes` | `/api/v1/changes` | scaffolded | Deferred until provenance and tracked-state surfaces are stable. |
| `corrections` | `/api/v1/corrections` | scaffolded | Deferred until chat and provenance flows are in place. |
| `admin` | `/api/v1/admin` | scaffolded | Guarded operational APIs remain deferred. |
| `usage` | `/api/v1/usage` | implemented in Phase 5 | Exposes read-only account usage summary at `/me`; later admin and plan-control surfaces remain deferred. |

## Phase 2 Rules

- Public HTTP ownership is versioned under `/api/v1` only.
- Legacy `/api/*` route aliases are intentionally not preserved in this repository.
- Backend transport models remain owned by `apps/api/src/ragdoll/modules/<module>/api/schemas.py`.
- `packages/contracts/openapi` and `packages/contracts/typescript` are generated artifacts, not hand-maintained contract sources.
- `GET /health` and `GET /api/v1/health` remain the only live endpoints during the scaffold phase.

## Follow-On Slice

The first real migration slice after this foundation pass is:

1. `auth`
2. `users`
3. `spaces`

Document, search, and chat surfaces stay deferred until identity and Space scope contracts are stable enough to reuse.
