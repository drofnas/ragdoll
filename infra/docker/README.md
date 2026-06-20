# `infra/docker`

Canonical home for local Docker Compose assets and related container-runtime notes.

Phase 1 now includes a runnable local development compose file rooted in the clean-room app structure.

- `compose.dev.yml` boots:
  - `apps/api` on host port `8031`
  - `apps/web` on host port `8030`
- backend healthcheck uses `GET /health`
- frontend waits for backend liveness before starting

Still deferred:

- full E2E compose parity
- worker-specific compose services
- local compose automation for third-party dependencies beyond app boot
