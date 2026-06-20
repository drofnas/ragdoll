# `infra/supabase`

Canonical home for Supabase setup notes, local expectations, and future helper assets.

## Local Setup Expectations

Create `apps/api/.env` from `packages/config/env/api.env.example`.

Required for a healthy Phase 1 readiness response:

- `SUPABASE_DB_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`

Phase 1 readiness meanings:

- `healthy`: the backend can connect to the configured Supabase dependency using read-only probes
- `degraded`: one or more dependencies are unavailable or intentionally deferred
- `not_configured`: required env or backing prerequisites are missing

Readiness in this phase stays read-only. Write-based round-trip storage/vector/graph validation is deferred to later admin/runtime tooling.
