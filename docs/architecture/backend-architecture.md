# Backend Architecture

## Purpose

Define the `apps/api` blueprint for the rebuild, including API composition, shared layers, workers, and bounded backend modules.

## Target Design

### `apps/api` tree

```text
apps/api/
  src/ragdoll/
    main.py
    api/
      router.py
      dependencies.py
      errors.py
      health.py
      v1/
        router.py
    core/
      config.py
      logging.py
      security.py
      auth.py
      instance_policy.py
      pagination.py
      exceptions.py
      result.py
    platform/
      db/
      storage/
      vector/
      graph/
      llm/
      queues/
      integrations/
    workers/
      document_pipeline.py
      pinned_facts_recompute.py
      archivist.py
    modules/
      auth/
      users/
      spaces/
      documents/
      ingestion/
      search/
      chat/
      entities/
      knowledge_graph/
      pinned_facts/
      changes/
      corrections/
      admin/
      usage/
  tests/
```

### Backend Layer Rules

- `api/`: transport-only concerns
- `core/`: cross-cutting policy and runtime primitives
- `platform/`: concrete implementations for storage, graph, vector, LLM, queue, and third-party systems
- `workers/`: background job entrypoints
- `modules/`: product logic by bounded context

## Responsibilities and Boundaries

### Shared areas

- `main.py`: create FastAPI app, wire lifespan, register routers, and bootstrap worker-compatible runtime components
- `api/router.py`: compose router tree and version mounting
- `api/dependencies.py`: session, user, admin, pagination, and Space scope dependencies
- `api/errors.py`: map domain/application errors to stable HTTP problem shapes
- `core/config.py`: environment settings grouped by auth, storage, DB, vector, graph, LLM, rate-limit, and instance-policy concern
- `core/security.py`: token signing, password hashing, encryption helpers, auth guard utilities
- `core/instance_policy.py`: config-driven effective limits and self-hosted quota policy resolution
- `platform/db/*`: engine, session, model base, migrations, and repository primitives
- `platform/storage/*`: original file and derived artifact storage
- `platform/vector/*`: embedding provider and vector-store access
- `platform/graph/*`: graph-store access and query helpers
- `platform/llm/*`: orchestration and worker-facing model calls
- `platform/queues/*`: Redis-backed RQ queue helpers, runtime inspection, job payload transport, and retry semantics

### Canonical module shape

```text
modules/<module>/
  api/
    routes.py
    schemas.py
  application/
    commands.py
    queries.py
    service.py
  domain/
    entities.py
    value_objects.py
    policies.py
  infrastructure/
    repository.py
    gateways.py
```

### Module ownership

- `auth`: register, login, current-user profile, password changes, token issuance
- `users`: user lifecycle, profile updates, admin ownership metadata, purge, usage summary joins
- `spaces`: create, rename, archive, default-space rules, scope resolution
- `documents`: list, detail, pagination, preview, move, download, delete
- `ingestion`: upload, process, retry, clean derived artifacts, status transitions
- `search`: combined, vector, graph, boolean, related results
- `chat`: query orchestration, answer synthesis, citations, sessions, suggestions
- `entities`: catalog, detail, provenance, history, visibility, canonicalization hooks
- `knowledge_graph`: graph population, graph exploration, document or Space subgraph reads
- `pinned_facts`: field definitions, recompute, summaries, conflicts, resolution
- `changes`: timeline, detail, read-state mutation
- `corrections`: submit, verify, reject, edit, delete, promote-to-fact behavior
- `admin`: user operations, effective limit reads, readiness views, guarded operational mutations
- `usage`: per-user usage and quota reporting

## Public Interfaces and Shared Types

- Canonical HTTP routes live under `/api/v1`
- Shared response primitives:
  - `ProblemResponse`
  - `MutationResult`
  - `PaginatedResponse`
  - `HealthStatusResponse`
- Shared domain-facing values:
  - `SpaceScope`
  - `ProcessingStatus`
  - `Citation`
  - `SourceTier`

## Primary Workflows

1. `auth` resolves user identity and admin status.
2. `spaces` resolves request scope once and passes it through services.
3. `documents` and `ingestion` accept file uploads or sync requests, persist metadata, and enqueue background jobs.
4. The `document-vector` RQ worker invokes `workers/document_pipeline.py` to perform extraction, chunking, embedding, vector writes, graph writes, and processing status updates.
5. `usage`, `ingestion`, and admin reads resolve effective self-hosted limits through shared instance-policy code instead of tier logic.
6. `search`, `chat`, and `pinned_facts` retrieve evidence through repositories and gateways, then compose user-facing outputs.
7. `changes` and `corrections` expose historical and human-in-the-loop surfaces without bypassing provenance rules.

## Failure Modes and Edge Cases

- Partial persistence across stores must be represented in processing state, not hidden.
- Worker retries must be idempotent for document chunks, entity extraction, and graph writes.
- Graph and vector timeouts must degrade gracefully into partial-answer behavior where allowed.
- Admin tools must remain guarded by policy layers, not direct repository access.
- Runtime startup must not force long-running worker behavior into the web process in production.

## Acceptance Checks

- Every capability area has exactly one owning backend module.
- No product logic is placed in `api/` or `platform/`.
- Worker entrypoints exist for long-running document and pinned-facts jobs.
- Shared config, auth, instance policy, and error handling have explicit `core/` homes.
- `/api/v1` is the documented source of truth.

## Deferred Notes

- `archivist.py` remains a reserved worker entrypoint for lifecycle features already tracked in product docs.
- Bot-read API support should be added under versioned API routing, not as an ad hoc module bypass.
