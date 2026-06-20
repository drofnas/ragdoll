# `infra/docker`

Canonical home for local Docker Compose assets and related container-runtime notes.

Phase 1 now includes a runnable local development compose file rooted in the clean-room app structure.

- `compose.dev.yml` boots:
  - `apps/api` on host port `8031`
  - `apps/web` on host port `8030`
- `compose.e2e.yml` adds the Dockerized Playwright runner used by `./dev-setup.sh test-e2e`
- backend healthcheck uses `GET /health`
- frontend waits for backend liveness before starting
- backend also mounts the repo root at `/workspace` so repo-root Python tooling can run inside the backend container

Still deferred:

- worker-specific compose services
- local compose automation for third-party dependencies beyond app boot
- deeper critical-path E2E coverage beyond the initial shell smoke suite
