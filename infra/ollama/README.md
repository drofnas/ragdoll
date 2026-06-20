# `infra/ollama`

Canonical home for Ollama setup notes and future local AI runtime helpers.

## Local Setup Expectations

Use `apps/api/.env.example` as the local template for backend env values. `./dev-setup.sh up` will create `apps/api/.env` from it automatically when the file is missing.

Relevant Phase 1 values:

- `OLLAMA_BASE_URL`
- optional `OLLAMA_WORKER_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_EMBEDDING_MODEL`

Phase 1 readiness checks use a read-only `GET /api/tags` probe:

- `healthy`: Ollama responds with a model catalog
- `unhealthy`: the configured endpoint is reachable but failing
- `not_configured`: `OLLAMA_BASE_URL` is missing
