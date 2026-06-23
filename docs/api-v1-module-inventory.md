# API v1 Module Inventory

This document is the Phase 2 inventory for the canonical `/api/v1` surface.

The current goal is ownership and composition, not feature parity. Empty module routers are intentional where feature migrations have not started yet.

## Module Registry

| Module | Public prefix | Current Phase 2 status | Notes |
| --- | --- | --- | --- |
| `auth` | `/api/v1/auth` | scaffolded | First concrete migration slice after Phase 2. |
| `users` | `/api/v1/users` | implemented through Phase 13 | Owns user lifecycle, profile reads and updates, and operator-managed account metadata even when session bootstrap stays under auth. |
| `spaces` | `/api/v1/spaces` | scaffolded | First concrete migration slice after Phase 2. |
| `documents` | `/api/v1/documents` | implemented in Phase 5 | Owns list, detail, move, delete, and download flows with shared `SpaceScope` filtering and nested `ProcessingStatus`. |
| `ingestion` | `/api/v1/ingestion` | implemented through Phase 8 | Owns manual upload, stage-aware processing-job queueing, status reads, full reprocess, and targeted parsing/vector/extraction/graph retries; public retrieval read APIs live in the retrieval modules. |
| `search` | `/api/v1/search` | implemented in Phase 9 | Owns search query, boolean/vector/graph/combined retrieval, ranking merge, and citation-bearing search contracts. |
| `chat` | `/api/v1/chat` | implemented in Phase 10 | Owns session list/create, session detail, retrieval-backed answer composition, persisted message history, citations, and fallback suggestions. |
| `entities` | `/api/v1/entities` | implemented in Phase 9 | Owns canonical entity list/detail, provenance, history, and related-document reads rooted in extracted mentions. |
| `knowledge_graph` | `/api/v1/knowledge-graph` | implemented in Phase 9 | Public path uses kebab-case; backend module keeps snake_case and exposes read-only subgraph and document-graph surfaces. |
| `tracked_state` | `/api/v1/tracked-state` | implemented in Phase 10 | Owns tracked field definitions, current-value summaries, conflict views, and synchronous recompute with append-only value history. |
| `changes` | `/api/v1/changes` | implemented in Phase 10 | Owns append-only change events, detail reads, and per-user read-state markers for processing, tracked-state, and correction activity. |
| `corrections` | `/api/v1/corrections` | implemented in Phase 10 | Owns correction submission, verification, rejection, and verified-evidence handoff into tracked-state and chat. |
| `admin` | `/api/v1/admin` | implemented in Phase 13 | Owns guarded user management, effective-instance-policy reads, and operator runtime views. |
| `usage` | `/api/v1/usage` | implemented through Phase 13 | Exposes read-only account usage summary at `/me` using config-driven instance limits instead of plan tiers. |

## Phase 2 Rules

- Public HTTP ownership is versioned under `/api/v1` only.
- Legacy `/api/*` route aliases are intentionally not preserved in this repository.
- Backend transport models remain owned by `apps/api/src/ragdoll/modules/<module>/api/schemas.py`.
- `packages/contracts/openapi` and `packages/contracts/typescript` are generated artifacts, not hand-maintained contract sources.
- `GET /health` and `GET /api/v1/health` remain the only live endpoints during the scaffold phase.

## Follow-On Slice

The first concrete slices after this foundation pass landed in sequence:

1. `auth`
2. `users`
3. `spaces`
4. `documents`
5. `ingestion`
6. retrieval reads through `search`, `entities`, and `knowledge_graph`

The follow-on Phase 10 slice implemented chat, tracked-state, changes, and corrections on top of the shared retrieval contracts without adding parallel retrieval semantics.
