# `infra/supabase`

Canonical home for the repo-owned local Supabase wrapper assets and setup notes.

## Local Setup Expectations

- `./dev-setup.sh infra up` will create `infra/docker/.env.infra` from `infra/docker/.env.infra.example` when it is missing.
- `./dev-setup.sh up` will create `apps/api/.env` from `apps/api/.env.example` when it is missing.
- `./dev-setup.sh infra up` also hydrates the local backend env when its Supabase integration values are still placeholders or old scaffold defaults.
- `./dev-setup.sh infra up` fetches upstream Supabase self-hosted Docker assets into ignored `infra/supabase/self-hosted/` when they are missing.
- `./dev-setup.sh infra upgrade` refreshes that ignored upstream tree to the repo-selected pinned commit before pulling newer images and restarting the local dependency stack.
- Tracked wrapper files live at `infra/supabase/docker-compose.yml` and `infra/supabase/docker-compose.override.yml`.
- `SUPABASE_UPSTREAM_GIT_SHA` can be set locally to test a different upstream commit without changing the repo default.

Required for a healthy local readiness response:

- `SUPABASE_DB_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`

This repo's local stack also ensures:

- Postgres starts with `pgvector` installed
- the `documents` storage bucket is created automatically
- Supabase Storage and Imgproxy persist objects in the repo-owned Docker named volume `ragdoll_supabase_storage`
- the app and infra stacks share the `ragdoll-dev` Docker network
- checked-in env examples keep placeholders only; real local secrets live in ignored `infra/docker/.env.infra`
- a local ignored `infra/docker/.env.infra.backup` is maintained so accidental deletion of `.env.infra` does not silently regenerate incompatible secrets on top of initialized Supabase data
- fresh clones do not carry the upstream Supabase Docker tree in git; local bootstrap fetches the repo-selected current upstream content on demand

Storage note:

- `infra/supabase/docker-compose.override.yml` is the source of truth for the local storage-volume override.
- `infra/supabase/self-hosted/volumes/storage` is no longer the active object-storage path for the running local stack.
- Recreating the infra stack is enough to migrate local development to the named-volume-backed storage runtime.

Phase 1 readiness meanings:

- `healthy`: the backend can connect to the configured Supabase dependency using read-only probes
- `degraded`: one or more dependencies are unavailable or intentionally deferred
- `not_configured`: required env or backing prerequisites are missing

Readiness in this phase stays read-only. Write-based round-trip storage/vector/graph validation is deferred to later admin/runtime tooling.
