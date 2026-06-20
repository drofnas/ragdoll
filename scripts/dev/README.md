# `scripts/dev`

Thin local development entrypoints belong here.

These scripts are the underlying owners for runtime flows and are also routed through the root `./dev-setup.sh` convenience wrapper.

The root wrapper now auto-creates missing `apps/api/.env` and `apps/web/.env` files from the app-local `.env.example` templates before runtime startup commands.

Phase 1 wires these scripts to `infra/docker/compose.dev.yml`:

- `up.sh`
- `down.sh`
- `status.sh`
