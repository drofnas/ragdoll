# Cross-Cutting Concerns

## Purpose

Capture shared rules for auth, authorization, config, instance policy, secrets, observability, rate limiting, and error handling across the rebuild.

## Target Design

### Shared backend homes

- `core/config.py`
- `core/security.py`
- `core/auth.py`
- `core/instance_policy.py`
- `core/logging.py`
- `core/exceptions.py`
- `api/dependencies.py`
- `api/errors.py`

### Shared frontend homes

- `app/providers.tsx`
- `shared/api/client.ts`
- `shared/state/*`
- `shared/lib/*`

## Responsibilities and Boundaries

### Auth and authorization

- Auth identity is resolved once per request through shared dependencies.
- Route handlers may guard by user or admin, but business authorization stays in module policies.
- Frontend gating is advisory; backend authorization is authoritative.

### Config

- Environment variables are parsed once by `core/config.py`.
- App-local examples live at `apps/api/.env.example` and `apps/web/.env.example`.
- Mirrored shared copies remain under `packages/config/env/` for centralized repo config assets.
- `ALLOWED_ORIGINS` accepts either CSV syntax or a JSON array of strings and is normalized by backend config.
- `apps/api/.env` and `apps/web/.env` are runtime conveniences, not architecture anchors outside the `apps/` shape.

### Instance policy

- Self-hosted limits are resolved from backend settings, not per-user commercial plan state.
- One shared resolver owns effective limits for ingestion, usage summaries, and admin/operator reads.
- Defaults should be mostly unlimited for cumulative quotas while keeping bounded request and document safety limits.
- Capability toggles that remain useful operationally belong in config with runtime-oriented names, not product feature-flag language.

### Errors

- Domain and application layers raise structured exceptions.
- `api/errors.py` maps them to stable HTTP problem responses.
- Frontend transport normalizes problem responses into predictable UI error states.

### Secrets and encryption

- Password hashing, token signing, and third-party token encryption live in `core/security.py`.
- Secrets are sourced from environment or secret managers, never committed.
- External integration credentials stay in platform adapters, not page or route code.

### Observability

- Request logging, worker logging, and correlation IDs are standardized.
- Health/readiness endpoints report DB, storage, vector, graph, LLM, and queue dependency health.
- Background jobs emit stage and retry logs with document and Space context.

### Rate limits

- Upload, bot, or expensive retrieval surfaces use explicit rate-limit policies.
- Limits are configured centrally and applied through dependencies or middleware.

## Public Interfaces and Shared Types

- `CurrentUser`
- `ProblemResponse`
- `HealthStatusResponse`
- `ReadinessDependencyStatus`
- `RateLimitState`

## Primary Workflows

1. Config loads and validates runtime settings.
2. Session bootstrap returns user identity and admin status.
3. Requests pass through shared auth and Space-scope dependencies before module handlers.
4. Errors are translated into stable problem shapes.
5. Frontend transport maps those shapes into feature-friendly behavior.
6. Health, status, and admin effective-limits views expose operational state for development and deployment checks.

## Failure Modes and Edge Cases

- Missing env vars can leave the app half-configured unless startup validation is strict.
- Config drift between documented limits and enforced runtime policy can create broken flows.
- Admin test tools can become unsafe if they bypass shared policy or secret handling layers.
- LLM, vector, or graph outages must degrade predictably and visibly.
- Hard redirects on auth expiration must not lose unsaved user context where recoverable.

## Acceptance Checks

- Shared config, auth, instance policy, and error translation have explicit homes.
- No feature implements its own incompatible auth or limit-resolution path.
- Health/readiness semantics include all major dependencies.
- Secrets and tokens are never treated as frontend-managed values.
- Rate limits are documented for high-cost operations.

## Deferred Notes

- More advanced tracing can be added later, but log and health semantics should remain stable.
