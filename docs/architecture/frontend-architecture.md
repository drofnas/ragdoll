# Frontend Architecture

## Purpose

Define the `apps/web` blueprint for route composition, feature ownership, shared client behavior, and contract usage in the rebuilt product.

## Target Design

### `apps/web` tree

```text
apps/web/src/
  app/
    router.tsx
    providers.tsx
    shell/
      PublicShell.tsx
      AuthenticatedShell.tsx
      AdminShell.tsx
    guards/
      ProtectedRoute.tsx
      AdminRoute.tsx
  features/
    auth/
    dashboard/
    spaces/
    documents/
    chat/
    search/
    entities/
    pinned-facts/
    changes/
    corrections/
    admin/
    account/
  shared/
    api/
    ui/
    hooks/
    lib/
    types/
    state/
```

### Feature module shape

```text
features/<feature>/
  pages/
  components/
  hooks/
  api/
  model/
  utils/
  tests/
```

## Responsibilities and Boundaries

- `app/router.tsx`: route table only
- `app/providers.tsx`: query client, auth/session bootstrap, Space scope provider, theme, error boundaries
- `app/shell/*`: page chrome and layout composition
- `app/guards/*`: authz gatekeeping only
- `shared/api/client.ts`: single transport layer with auth headers, cancellation, retry, and error translation
- `shared/ui/*`: reusable primitives only
- `shared/hooks/*`: generic hooks, not feature rules
- `shared/lib/*`: pure helper functions
- `features/*`: own page orchestration, view models, and feature-specific clients

### Feature ownership

- `auth`: login, register, session bootstrap
- `dashboard`: authenticated landing surface
- `spaces`: Space list, create/edit/archive, active/all-spaces selection
- `documents`: list, filters, preview, upload, download, delete, move, status refresh
- `chat`: sessions, message flow, citations, correction entrypoint
- `search`: query form, filters, related results, list/graph result presentation
- `entities`: list, detail, history, provenance, graph explorer
- `pinned-facts`: fields, summaries, conflicts, resolution controls
- `changes`: feed, detail, read-state actions
- `corrections`: verification dashboard
- `admin`: user management, readiness, runtime status, and effective-instance-policy reads
- `account`: profile, password, and usage management

## Public Interfaces and Shared Types

- All API request and response shapes are imported from `packages/contracts/typescript`
- Feature clients are thin wrappers around shared transport
- `apps/web` uses Tailwind CSS v4 through the Vite plugin; shared theme tokens live in `src/styles/app.css`
- Shared frontend state includes:
  - current user
  - current `SpaceScope`
  - query cache
  - route-safe error state

## Primary Workflows

1. App bootstraps providers and loads current session state.
2. User enters through `PublicShell`, `AuthenticatedShell`, or `AdminShell`.
3. Feature pages load typed data through feature-local API clients.
4. Shared transport injects auth, handles request cancellation, and normalizes errors.
5. Feature hooks maintain local query or mutation behavior without centralizing product logic in global utilities.
6. Graph visualizations, citations, and pinned-facts summaries reuse shared primitives but remain owned by their features.

## Failure Modes and Edge Cases

- Guarded routes must hide in navigation and hard-block on direct access.
- All-spaces views must make scope obvious to avoid accidental cross-project interpretation.
- Background processing pages must render partial status without implying finished retrieval or graph population.
- Search, chat, and graph UI must tolerate partial backend results and typed problem responses.
- Admin surfaces must not share user-facing route shells or bypass policy-driven data loading.

## Acceptance Checks

- Every authenticated capability has one feature page or one clearly owned feature surface in `apps/web`.
- The public shell stays limited to login, registration, and the backend status page.
- No feature relies on a monolithic global API utility bucket.
- Shared types come from `packages/contracts`, not hand-maintained duplicates.
- Route shells and guards are separated from page logic.

## Deferred Notes

- If a future native app or embedded UI appears, it should consume the same contracts rather than reshape current feature boundaries.
- Graph-heavy UI enhancements belong in `entities` or `search`, not a new global visualization app.
