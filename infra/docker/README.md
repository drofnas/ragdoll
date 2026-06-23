# `infra/docker`

Canonical home for local Docker Compose assets and related container-runtime notes.

This directory now owns both the app stack and the local dependency stack used during development.

- `compose.dev.yml` boots:
  - `apps/api` on host port `8031`
  - `apps/web` on host port `8030`
- `compose.infra.yml` boots:
  - the local self-hosted Supabase stack
  - Ollama plus model pre-pull helpers
  - the bootstrap job that creates the `documents` storage bucket
  - the repo-owned override that keeps Supabase object storage on the Docker named volume `ragdoll_supabase_storage`
- `compose.e2e.yml` adds the Dockerized Playwright runner used by `./dev-setup.sh test-e2e`
- backend healthcheck uses `GET /health`
- frontend waits for backend liveness before starting
- backend also mounts the repo root at `/workspace` so repo-root Python tooling can run inside the backend container
- both stacks share the `ragdoll-dev` Docker network so the backend can reach `db`, `kong`, and `ollama`

Key workflows:

- `./dev-setup.sh up` starts the app stack
- `./dev-setup.sh daemon` starts the app stack in the background
- `./dev-setup.sh infra up` creates `infra/docker/.env.infra` when missing, fetches the repo-selected upstream Supabase Docker tree into ignored local storage when missing, hydrates matching local backend env values when needed, and starts the local dependency stack
- `./dev-setup.sh infra upgrade` refreshes the local upstream Supabase Docker tree to the repo-selected pinned commit, pulls newer infra images, and restarts the dependency stack
- `./dev-setup.sh test-infra` runs the opt-in Docker-backed Phase 7 readiness and manual-upload smoke suite
- `./dev-setup.sh infra logs` tails local dependency logs

Recommended local full-stack flow:

- `./dev-setup.sh infra up`
- `./dev-setup.sh daemon`
- `./dev-setup.sh test-infra`
- `./dev-setup.sh logs` or `./dev-setup.sh infra logs`
- `./dev-setup.sh down`
- `./dev-setup.sh infra down`

Local env behavior:

- `infra/docker/.env.infra.example` stays placeholder-only in git
- `./dev-setup.sh infra up` creates and populates ignored `infra/docker/.env.infra`
- `./dev-setup.sh infra up` also keeps an ignored `infra/docker/.env.infra.backup` so accidental local deletion of `.env.infra` can be recovered on later boots
- fetched upstream Supabase Docker assets live in ignored `infra/supabase/self-hosted/`
- `SUPABASE_UPSTREAM_GIT_SHA` can be set locally to test a different upstream commit without changing repo defaults
- the generated infra values are reused on later runs and are not rotated automatically once real values exist
- local object blobs now live in the Docker-managed volume `ragdoll_supabase_storage`, not `infra/supabase/self-hosted/volumes/storage`

Still deferred:

- worker-specific long-running compose services beyond the current ingestion entrypoint
- deeper critical-path E2E coverage beyond the initial shell smoke suite and the opt-in Phase 7 infra smoke path

Phase 7 readiness remains infrastructure-focused. A healthy readiness response and a passing `test-infra` run prove local database, storage, vector prerequisites, graph prerequisites, LLM reachability, and manual-upload processing confidence. They do not prove retrieval, embeddings, entities, or graph projection behavior.
