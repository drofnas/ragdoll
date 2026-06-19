# Testing And Quality Gates

## Purpose

Define the test structure, coverage expectations, and acceptance gates for implementation work in the rebuilt repository.

## Target Design

### Test layout

```text
apps/api/tests/
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
    tracked_state/
    changes/
    corrections/
    admin/
    usage/
  platform/
  fixtures/

apps/web/src/features/*/tests/

tests/e2e/
  fixtures/
  helpers/
  specs/
```

### Test ownership rules

- Backend module tests stay near the module, grouped under `apps/api/tests/modules/`
- Backend platform tests verify adapters without embedding product rules
- Frontend tests live with the feature they validate
- `tests/e2e` covers true cross-surface flows only

## Responsibilities and Boundaries

- Unit tests validate domain policies, value objects, and pure helpers
- Integration tests validate repositories, adapters, and module services against realistic boundaries
- Contract tests validate backend schemas and generated frontend types remain aligned
- E2E tests validate high-value user journeys across app boundaries

### Required coverage areas

- Auth and session bootstrap
- Space scoping and all-spaces behavior
- Document upload and status transitions
- Search and chat citations
- Entity history and provenance
- Tracked-state conflict resolution
- Corrections verification path
- Admin guards and plan/flag behavior

## Public Interfaces and Shared Types

- API contracts under `packages/contracts` must have generation and verification steps
- Shared fixtures should expose typed builders for:
  - users
  - spaces
  - documents
  - entities
  - chat sessions
  - tracked fields

## Primary Workflows

1. Backend changes add or update module tests first.
2. Frontend changes add or update feature tests that consume typed contracts.
3. Contract generation runs before frontend type-dependent validation.
4. E2E coverage is added for user-visible cross-surface behavior, not every internal branch.
5. Architecture docs are updated when structural assumptions change.

## Failure Modes and Edge Cases

- Tests can accidentally validate outdated structural assumptions instead of the documented `apps/` structure.
- Shared fixtures can become a hidden integration layer if they grow too broad.
- Contract generation drift can break frontend compile-time safety without obvious runtime failures.
- E2E suites can become slow and flaky if they absorb unit or integration concerns.
- AI-generated code can pass type checks while missing module-boundary or provenance expectations.

## Acceptance Checks

- New implementation work includes tests at the owning layer.
- Product-level flows live in `tests/e2e`, not feature folders.
- Contract drift has an explicit verification step.
- Critical provenance and Space-scope behaviors are covered.
- Architecture docs remain aligned with any new module or feature structure.

## Deferred Notes

- CI wiring can evolve later, but the repo structure and test ownership rules should remain stable.
- Performance and load testing may be added later under `scripts/` or dedicated tooling without changing feature test placement.
