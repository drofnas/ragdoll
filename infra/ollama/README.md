# `infra/ollama`

Canonical home for Ollama setup notes and the local runtime expectations used by `./dev-setup.sh infra up`.

## Local Setup Expectations

- `./dev-setup.sh infra up` will create `infra/docker/.env.infra` from `infra/docker/.env.infra.example` when it is missing.
- `./dev-setup.sh up` will create `apps/api/.env` from `apps/api/.env.example` when it is missing.
- `./dev-setup.sh infra up` also hydrates the local backend env with Ollama connection defaults when those values are still placeholders or legacy scaffold defaults.
- `./dev-setup.sh infra upgrade` is the explicit refresh path for pulling newer Ollama images after first bootstrap.
- The local stack supports `OLLAMA_RUNTIME=cpu|amd|nvidia` and selects the matching override file automatically.

Relevant Phase 1 values:

- `OLLAMA_BASE_URL`
- optional `OLLAMA_WORKER_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_EMBEDDING_MODEL`
- `ENTITY_EXTRACTION_MODE`
- `ENTITY_EXTRACTION_BATCH_SIZE`
- `ENTITY_EXTRACTION_MAX_PARALLEL_BATCHES`

Relevant local infra values:

- `OLLAMA_HOST_PORT`
- `OLLAMA_RUNTIME`
- `OLLAMA_MODEL`
- `OLLAMA_EMBEDDING_MODEL`

Phase 1 readiness checks use a read-only `GET /api/tags` probe:

- `healthy`: Ollama responds with a model catalog
- `unhealthy`: the configured endpoint is reachable but failing
- `not_configured`: `OLLAMA_BASE_URL` is missing
