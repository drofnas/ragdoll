# `tests/e2e`

Canonical home for product-level end-to-end verification.

The self-hosted E2E suite starts with the public/auth shell and expands into real workspace journeys over time.

Current coverage:

- anonymous `/` renders login
- registration redirects back to login with a success state
- login reaches the authenticated dashboard
- authenticated upload reaches document detail
- the public `Status` link targets a live backend `/status` page

Current structure:

- `fixtures/`
- `helpers/`
- `specs/`

E2E coverage should stay focused on true cross-surface user journeys rather than replacing backend or frontend unit tests.
