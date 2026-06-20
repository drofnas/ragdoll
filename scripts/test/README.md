# `scripts/test`

Thin test entrypoints belong here.

These scripts are the underlying owners for test flows and are also routed through the root `./dev-setup.sh` convenience wrapper.

Test commands remain host-local and do not auto-create app `.env` files in this phase.

Phase 1 wires the backend and frontend bootstrap commands:

- `all.sh`
- `backend.sh`
- `frontend.sh`
- `e2e.sh`

`e2e.sh` remains intentionally partial until later phases, so `./dev-setup.sh test-e2e` is not yet a real E2E runner.
