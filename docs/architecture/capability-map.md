# Capability Map

## Purpose

Map each product capability to its owning backend module, frontend feature, contract surface, and primary test layer.

## Target Design

All ownership in this document assumes the canonical repository structure:

```text
apps/
  api/
  web/
packages/
  contracts/
tests/
  e2e/
```

## Responsibilities and Boundaries

| Capability | Backend owner | Frontend owner | Contract surface | Primary test layer |
| --- | --- | --- | --- | --- |
| Authentication | `modules/auth` | `features/auth` | auth schemas and session payloads | backend module tests + frontend feature tests |
| User profile and account settings | `modules/auth` and `modules/users` | `features/account` | auth and user profile contracts | backend module tests + frontend feature tests |
| Spaces and scope selection | `modules/spaces` | `features/spaces` | space list, detail, and scope contracts | backend module tests + frontend feature tests |
| Document library | `modules/documents` | `features/documents` | document list, detail, mutation, and status contracts | backend module tests + frontend feature tests |
| Upload and reprocessing | `modules/ingestion` | `features/documents` | upload, retry, and processing status contracts | backend module tests + E2E |
| Search and discovery | `modules/search` | `features/search` | search query, filters, results, and related contracts | backend module tests + frontend feature tests |
| Chat and answer generation | `modules/chat` | `features/chat` | chat message, session, citation, and suggestion contracts | backend module tests + E2E |
| Entities and graph exploration | `modules/entities` and `modules/knowledge_graph` | `features/entities` | entity detail, provenance, history, and graph contracts | backend module tests + frontend feature tests |
| Tracked state | `modules/tracked_state` | `features/tracked-state` | tracked field, summary, and conflict contracts | backend module tests + frontend feature tests |
| Changes feed | `modules/changes` | `features/changes` | change list, detail, and read-state contracts | backend module tests + frontend feature tests |
| Corrections and verification | `modules/corrections` | `features/corrections` and `features/chat` | correction submission and review contracts | backend module tests + E2E |
| Admin tooling | `modules/admin` | `features/admin` | admin user, effective-limits, readiness, and runtime-status contracts | backend module tests + guarded E2E |
| Usage and instance policy | `modules/usage` and `modules/admin` | `features/account` and `features/admin` | usage summary and effective-limit contracts | backend module tests |

## Public Interfaces and Shared Types

The capability map assumes these shared seams:

- HTTP APIs are served under `/api/v1`
- shared schemas and generated types live under `packages/contracts`
- backend modules define wire contracts through their API schemas
- frontend features consume generated or source-controlled shared types

## Primary Workflows

1. Define the product capability being implemented.
2. Route backend work to the owning module.
3. Route frontend work to the owning feature.
4. Reuse shared contracts instead of duplicating wire shapes.
5. Choose the primary test layer based on the user-visible behavior of the capability.

## Failure Modes and Edge Cases

- A capability can become hard to maintain if ownership is split across multiple unrelated modules.
- Shared helpers can become hidden owners if feature code pushes too much logic into generic folders.
- Cross-cutting capabilities such as usage or instance policy must still have a single place where decisions are resolved.
- E2E coverage should confirm stitched behavior, not replace module or feature tests.

## Acceptance Checks

- Every user-visible capability has a clear backend and frontend owner where applicable.
- Every capability uses an explicit contract surface.
- Test ownership is clear enough that implementers can add coverage without inventing structure.
- No capability relies on a catch-all folder as its main home.

## Deferred Notes

- New capabilities should extend this table before creating additional top-level architecture docs.
- If one capability grows into multiple independent product surfaces, split it into multiple rows rather than broadening a single owner definition.
