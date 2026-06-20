# `scripts/test`

Thin test entrypoints belong here.

These scripts are the underlying owners for test flows and are also routed through the root `./dev-setup.sh` convenience wrapper.

Backend Python test commands are Docker-first and should not rely on host Python tooling.

Phase 1 wires the backend and frontend bootstrap commands:

- `all.sh`
- `backend.sh`
- `frontend.sh`
- `e2e.sh`

`e2e.sh` now runs a Docker-backed Playwright smoke suite against the live frontend and backend containers.

Current split:

- `backend.sh`: runs backend platform tests inside the Docker backend service
- `frontend.sh`: runs frontend tests inside the Docker frontend service
- `e2e.sh`: auto-starts the Docker app stack if needed and runs Playwright smoke specs inside the E2E container
