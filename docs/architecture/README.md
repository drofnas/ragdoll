# Ragdoll Architecture Docs

## Purpose

This directory is the canonical build spec for Ragdoll. It defines the repository structure, product boundaries, runtime ownership, and implementation rules that future code should follow.

## Canonical Repo Shape

All architecture docs in this directory assume this repository shape:

```text
ragdoll/
  apps/
    api/
    web/
  packages/
    contracts/
    config/
    tooling/
  tests/
    e2e/
  infra/
    docker/
    supabase/
    ollama/
  scripts/
  docs/
```

`apps/api` and `apps/web` are the only application roots. Shared schemas and generated types live in `packages/contracts`, and browser-level verification lives in `tests/e2e`.

## Reading Order

1. [system-overview.md](./system-overview.md)
2. [backend-architecture.md](./backend-architecture.md)
3. [frontend-architecture.md](./frontend-architecture.md)
4. [data-and-storage.md](./data-and-storage.md)
5. [ingestion-and-processing.md](./ingestion-and-processing.md)
6. [retrieval-chat-and-discovery.md](./retrieval-chat-and-discovery.md)
7. [cross-cutting-concerns.md](./cross-cutting-concerns.md)
8. [testing-and-quality-gates.md](./testing-and-quality-gates.md)
9. [capability-map.md](./capability-map.md)

## Architecture Principles

- Organize by bounded context first, not by global technical layer.
- Keep Ragdoll a modular monolith until runtime pressure proves a stronger split is needed.
- Treat background workers as first-class runtime entrypoints.
- Keep backend and frontend aligned through explicit shared contracts.
- Make Space scoping, provenance, and current-vs-history behavior explicit.
- Prefer clear ownership over convenience folders or catch-all utilities.

## Glossary

- `Space`: User-owned workspace boundary for documents, entities, chat sessions, and pinned facts.
- `Current state`: The best current answer for a fact or architectural entity.
- `Provenance`: The evidence trail linking a fact back to documents, graph relationships, and user actions.
- `Pinned facts`: User-defined fields whose values are recomputed from retrieved evidence.
- `Platform adapter`: Concrete implementation for storage, graph, vector, LLM, queue, or third-party integrations.
- `Module`: Backend bounded context with its own API, application, domain, infrastructure, and tests.

## Maintenance Rules

- When implementation changes the target structure or a public contract, update these docs in the same change.
- Add new runtime capabilities to the closest existing spec before creating a new architecture file.
- Keep public architecture docs self-contained and implementation-oriented.
