# `tests/e2e`

Canonical home for product-level end-to-end verification.

The initial clean-room E2E suite is intentionally minimal and smoke-focused.

Current coverage:

- public shell renders the known scaffold title
- anonymous access to `/dashboard` redirects to `/login`

Current structure:

- `fixtures/`
- `helpers/`
- `specs/`

E2E coverage should stay focused on true cross-surface user journeys rather than replacing backend or frontend unit tests.
