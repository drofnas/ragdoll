# Agent Workflow Notes

This repository is Docker-first for backend and Python work.

## Navigation Rule

- Read `INDEX.md` at the repository root before broad codebase traversal when you need to edit an existing file or decide where a new file should go.
- Use `INDEX.md` first to narrow the target area for pages, logic, tests, contracts, scripts, and new files.
- Fall back to deeper traversal only after `INDEX.md` has narrowed the likely ownership area.
- Keep `INDEX.md` up to date when structural ownership or file-placement conventions change.

## Backend Python Rule

- Do not rely on host-installed `python3`, `pip`, `pytest`, `alembic`, or similar tools for repo backend tasks.
- Run backend and Python verification inside the Docker backend service defined by `infra/docker/compose.dev.yml`.
- Prefer the repo wrappers when they exist:
  - `./dev-setup.sh test-backend`
  - `./scripts/test/backend.sh`

## Canonical Docker Patterns

Use these commands for one-off backend work:

```sh
docker compose -f infra/docker/compose.dev.yml run --rm -w /workspace/apps/api backend python3 -m pytest tests/platform -q
docker compose -f infra/docker/compose.dev.yml run --rm -w /workspace/apps/api backend alembic upgrade head
docker compose -f infra/docker/compose.dev.yml run --rm -w /workspace backend python3 packages/tooling/scripts/generate_contracts.py
```

## Environment Bootstrapping

- If `apps/api/.env` is missing, create it from `apps/api/.env.example` before running backend Docker commands.
- Prefer repo-owned scripts over ad hoc host setup steps.

## Change Validation Rule

- After each non-doc code or config change, run `./dev-setup.sh test` and `./dev-setup.sh test-e2e` before considering the work complete.

## Scope Notes

- Backend and repo-owned validation commands should prefer Docker-backed wrappers over host-local toolchains.
- Frontend-only Node tasks should also prefer the repo wrappers when available.
- Keep [docs](docs/) up to date when a fundamental architectural change lands so the repository documentation stays aligned with the source of truth.
- The old private repository remains reconstruction input only; this repository is the canonical source of truth.
