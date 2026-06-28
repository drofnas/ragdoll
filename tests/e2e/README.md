# `tests/e2e`

Canonical home for product-level end-to-end verification.

The self-hosted E2E suite starts with the public/auth shell and expands into real workspace journeys over time.

Current coverage:

- anonymous `/` renders login
- the shared configured E2E user can self-provision once, then sign in on later runs
- login reaches the authenticated dashboard
- authenticated upload reaches document detail
- the public `Status` link targets a live backend `/status` page

Shared-user configuration:

- E2E browser tests read `E2E_TEST_USER_EMAIL`, `E2E_TEST_USER_PASSWORD`, and `E2E_TEST_USER_FULL_NAME`
  from `apps/api/.env`
- the default shared user email is `tests@ragdoll.local`
- the Playwright auth helper first attempts login, falls back to registration when the user does not exist yet,
  and resets that user's workspace before and after each authenticated test

Current structure:

- `fixtures/`
- `helpers/`
- `specs/`

E2E coverage should stay focused on true cross-surface user journeys rather than replacing backend or frontend unit tests.
