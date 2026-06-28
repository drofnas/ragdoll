# Ragdoll Implementation Plan

## How To Use This Plan

This document is the canonical progress tracker for building Ragdoll. The phases below are intentionally linear: each one represents the next bounded chunk of work rather than a broad umbrella that is later split into lettered sub-phases.

Use the checkboxes as follows:

- Mark a phase complete only when all child tasks and acceptance checks under it are done.
- Keep implementation updates in this file synchronized with architecture, contract, and workflow changes.
- Leave later-phase items unchecked rather than removing them when they are intentionally deferred.

## Phase 0 - Repo Foundation

Goal: establish the repository skeleton, shared conventions, and baseline developer workflows so every later phase builds on a stable structure instead of ad hoc setup work.

Depends on: none

- [x] Phase complete
- [x] Create the canonical repo skeleton under `apps/`, `packages/`, `tests/`, `infra/`, `scripts/`, and `docs/`
  - [x] Add the `apps/api` directory scaffold
  - [x] Add the `apps/web` directory scaffold
  - [x] Add the `packages/contracts`, `packages/config`, and `packages/tooling` directory scaffold
  - [x] Add the `tests/e2e` directory scaffold
  - [x] Add the `infra/docker`, `infra/supabase`, and `infra/ollama` directory scaffold
  - [x] Add the `scripts/dev`, `scripts/test`, and `scripts/ops` directory scaffold
  - [x] Verify the on-disk structure matches the architecture docs
  - [x] Add a checklist note or README reference for any intentionally empty placeholder directories
- [x] Add root tooling baselines and environment examples
  - [x] Add root package/runtime documentation describing Python, web, and shared tooling expectations
  - [x] Add `packages/config/env/api.env.example`
  - [x] Add `packages/config/env/web.env.example`
  - [x] Add shared formatting, lint, and test config placeholders in `packages/config`
  - [x] Confirm `.gitignore` covers local env files, build outputs, caches, and `_tmp/`
  - [x] Verify no committed file requires private local path configuration
- [x] Define package and runtime conventions
  - [x] Decide the Python dependency and execution convention for `apps/api`
  - [x] Decide the Node package manager and app boot convention for `apps/web`
  - [x] Define naming and placement rules for shared tooling scripts
  - [x] Document how contracts are generated and consumed at a high level
  - [x] Ensure conventions align with `docs/architecture`
- [x] Establish local developer bootstrap commands and starter repo docs
  - [x] Add a root README with bootstrap expectations
  - [x] Add a minimal local development startup flow under `scripts/dev`
  - [x] Add a minimal local test entrypoint flow under `scripts/test`
  - [x] Add a note describing where future operational scripts belong
  - [x] Verify a new contributor can understand where each major subsystem will live

## Phase 1 - Platform And Runtime Base

Goal: stand up the runtime skeleton for the API, web app, config, auth primitives, error handling, database access, and readiness checks before feature-specific modules are implemented.

Depends on: Phase 0

- [x] Phase complete
- [x] Bootstrap the `apps/api` runtime
  - [x] Create the FastAPI app entrypoint in `apps/api`
  - [x] Add base router composition for `/api/v1`
  - [x] Add shared dependency wiring for request-scoped concerns
  - [x] Add error translation scaffolding for consistent problem responses
  - [x] Add health and readiness endpoint scaffolding
  - [x] Verify the API app can boot without feature modules fully implemented
- [x] Bootstrap the `apps/web` runtime
  - [x] Create the web app entrypoint in `apps/web`
  - [x] Add the app router scaffold
  - [x] Add provider scaffolding for auth/session, query state, and Space scope
  - [x] Add public, authenticated, and admin shell placeholders
  - [x] Verify the web app can render shell routes without feature pages completed
- [x] Add shared core runtime services
  - [x] Implement config loading and validation scaffolding
  - [x] Implement logging scaffolding for API requests and workers
  - [x] Implement auth primitives for token signing and password hashing
  - [x] Implement feature-flag resolution scaffolding
  - [x] Implement pagination and shared response primitives
  - [x] Verify shared core services can be imported without circular dependency issues
- [x] Add database session and migration foundations
  - [x] Add DB engine and session management scaffolding
  - [x] Add model base and migration directory scaffolding
  - [x] Add migration execution workflow documentation
  - [x] Verify the API runtime can start with DB wiring enabled
- [x] Add local infra and readiness foundations
  - [x] Add Docker compose definitions for local app development
  - [x] Add Supabase dependency notes and local setup expectations
  - [x] Add Ollama dependency notes and local setup expectations
  - [x] Add readiness checks for DB, storage, vector, graph, and LLM dependencies
  - [x] Verify the readiness contract is stable enough for later automated tests

## Phase 2 - Shared Contracts And API Skeleton

Goal: define shared wire contracts, module route surfaces, and a baseline API test strategy so every later backend and frontend feature builds against explicit schemas rather than informal payloads.

Depends on: Phase 1

- [x] Phase complete
- [x] Create the `packages/contracts` foundation
  - [x] Add the contracts directory structure for OpenAPI, schemas, and generated TypeScript types
  - [x] Add baseline contract docs describing contract ownership
  - [x] Add placeholder schema groupings for all planned product areas
  - [x] Verify contract directories match the architecture docs
- [x] Define the initial schema set
  - [x] Add shared public wire primitives for `ProblemResponse`, `MutationResult`, `PaginatedResponse`, `HealthStatusResponse`, `SpaceScope`, `ProcessingStatus`, `PlanTier`, `FeatureFlags`, `SourceTier`, and `Citation`
  - [x] Add auth, users, spaces, documents, ingestion, search, chat, entities, knowledge graph, pinned facts, changes, corrections, admin, and usage schema placeholders
- [x] Define contract generation strategy
  - [x] Add OpenAPI generation workflow notes
  - [x] Add TypeScript type generation workflow notes
  - [x] Add a scaffolded tooling entrypoint in `packages/tooling` for contract generation
  - [x] Verify the generation strategy supports both backend-first and frontend consumption flows
- [x] Build the `/api/v1` skeleton
  - [x] Add versioned router composition for all planned backend modules
  - [x] Add placeholder route mounts for all planned modules
  - [x] Add endpoint inventory notes for each module
  - [x] Verify every capability in `docs/architecture/capability-map.md` has an API home where applicable
- [x] Add the auth and spaces migration-prep inventory
  - [x] Map legacy auth behavior into `modules/auth` and `modules/users`
  - [x] Map legacy spaces behavior into `modules/spaces`
  - [x] Record preserved, renamed, deferred, and dropped migration decisions
  - [x] Explicitly defer document, search, and chat migration until auth identity and Space scope contracts are stable
- [x] Add the baseline API test strategy
  - [x] Add module-registry coverage tests for mounted routers where possible
  - [x] Add OpenAPI export smoke coverage
  - [x] Add problem response tests for common failure cases where possible
  - [x] Verify the implementation plan explicitly covers testing every API endpoint where practical

## Phase 3 - Identity And Space Migration

Goal: implement the first concrete clean-room migration slice for identity and Space ownership so later document, search, and chat work can reuse stable auth and scope contracts instead of ad hoc legacy behavior.

Depends on: Phase 2

- [x] Phase complete
- [x] Add the minimal relational groundwork for identity and Space ownership
  - [x] Define user records with `plan_tier`, `feature_flag_overrides`, `must_change_password`, `is_admin`, and `last_login`
  - [x] Define Space records with `is_default`, `archived_at`, ownership, and audit timestamps
  - [x] Add ownership and one-default-space-per-user index constraints
  - [x] Add the first Alembic revision for the identity and Space slice
  - [x] Verify the runtime can boot and export contracts with the new models registered
- [x] Implement the auth module
  - [x] Add auth routes and concrete wire schemas
  - [x] Add auth registration and login commands
  - [x] Add current-user profile queries and patch behavior
  - [x] Add auth domain and infrastructure scaffolding in the canonical module shape
  - [x] Verify login, registration, session bootstrap, and protected route behavior under `/api/v1/auth`
- [x] Implement the users internal ownership layer
  - [x] Add user profile and update schemas consumed by auth-owned endpoints
  - [x] Add user commands and queries for profile updates and principal loading
  - [x] Add user domain policies for email normalization and plan-tier resolution
  - [x] Add user repository behavior for identity lookups and login-state writes
  - [x] Verify plan tier and feature-flag resolution are owned by `modules/users`
- [x] Implement the spaces module
  - [x] Add Space routes and concrete wire schemas
  - [x] Add Space commands and queries for create, list, detail, update, and archive flows
  - [x] Add Space domain policies for default-space protection
  - [x] Add Space repository behavior for owned-space reads and default-space reassignment
  - [x] Verify active-space and all-spaces behavior has API-contract support via stable Space records and scope primitives
- [x] Replace runtime scaffolds with real identity and scope dependencies
  - [x] Replace the current-user dependency scaffold with bearer-token principal loading
  - [x] Replace the admin guard scaffold with real admin authorization checks
  - [x] Finalize `SpaceScope` validation so `space_id` and `all_spaces=true` are mutually exclusive
  - [x] Keep later document, search, and chat route adoption deferred until their phases
- [x] Add the Phase 3 auth and Space test layer
  - [x] Add request and response schema tests where practical
  - [x] Add auth guard tests for protected endpoints where applicable
  - [x] Port auth and spaces API tests into `apps/api/tests/modules`
  - [x] Add contract export assertions for auth and Space schemas
  - [x] Verify the backend test wrapper runs module tests, not only platform tests

## Phase 4 - Document And Usage Foundations

Goal: finish the minimum shared data and adapter groundwork needed for the first post-auth vertical slice without prematurely pulling in ingestion, search, chat, or graph-query implementation scope.

Depends on: Phase 3

- [x] Phase complete
- [x] Add the first document and usage relational records
  - [x] Add the `Document` model with required Space scope, uploader ownership, storage reference, preview fields, stage-aware processing status, chunk counters, soft-delete support, and audit timestamps
  - [x] Add the `UsageEvent` and `UserUsageSnapshot` models for later quota and account summaries
  - [x] Add the follow-on Alembic revision for document and usage foundations
  - [x] Verify active-document indexes include a soft-delete-aware path for list reads
- [x] Add provider-agnostic storage and cleanup adapters
  - [x] Add original-file storage and derived-artifact cleanup interfaces under `platform/storage`
  - [x] Add the configured Supabase-backed document storage implementation
  - [x] Add in-memory document storage and cleanup test doubles for module tests
  - [x] Verify storage metadata remains relationally authoritative
- [x] Add minimal vector and graph cleanup seams
  - [x] Add document cleanup interfaces under `platform/vector` and `platform/graph`
  - [x] Add idempotent in-memory cleanup doubles for tests
  - [x] Keep live vector query, embedding write, graph write, and graph read behavior deferred
- [x] Lock in the first document-slice state conventions
  - [x] Use shared `ProcessingStatus` as the public transport contract for document state
  - [x] Keep all new document rows Space-scoped from day one
  - [x] Treat object, vector, and graph stores as cleanup-aware derived systems rather than metadata sources of truth
  - [x] Keep provider-specific sync metadata deferred to later ingestion work

## Phase 5 - Document Library And Usage Summary

Goal: land the first live clean-room vertical slice after auth and Spaces by implementing document-library reads and moves plus a read-only usage summary surface.

Depends on: Phase 4

- [x] Phase complete
- [x] Implement the documents module
  - [x] Add document list, detail, move, delete, and download routes under `/api/v1/documents`
  - [x] Add concrete document wire schemas using nested shared `ProcessingStatus`
  - [x] Add document queries, commands, domain policies, and repository behavior in the canonical module shape
  - [x] Support Space-scoped filters for `space_id`, `all_spaces`, `date_from`, `date_to`, `file_type`, and `uploaded_by`
  - [x] Use soft delete plus storage, vector, and graph cleanup hooks during document deletion
  - [x] Return a typed `409` problem when document metadata exists but the original blob is unavailable
  - [x] Add document module tests for auth, visibility, filtering, moves, deletes, and download error handling
- [x] Implement the usage module
  - [x] Add `GET /api/v1/usage/me`
  - [x] Add concrete usage summary wire schemas
  - [x] Add plan-limit resolution and usage recompute queries in the canonical module shape
  - [x] Add usage repository behavior for snapshots, owned-document metrics, and usage-event windows
  - [x] Keep document, chunk, and storage totals live while token windows default to zero until later chat and worker phases emit events
  - [x] Add usage module tests for summaries, percentages, recompute behavior, and token reset windows
- [x] Update contract export coverage for the new slice
  - [x] Verify OpenAPI export includes documents and usage paths
  - [x] Verify generated contract artifacts include shared `ProcessingStatus`

## Phase 6 - Manual Upload And Processing Backbone

Goal: land the first live ingestion slice by implementing manual uploads, queue-backed parsing, chunk projection, status reads, and parsing repair paths without prematurely pulling embeddings, retrieval, entities, or graph projection into scope.

Depends on: Phase 5

- [x] Phase complete
- [x] Implement the ingestion module
  - [x] Add upload, status, batch-status, reprocess, and retry-parsing routes under `/api/v1/ingestion`
  - [x] Add concrete ingestion wire schemas for upload responses, job status, and batch status reads
  - [x] Add ingestion commands, queries, policies, and repository behavior in the canonical module shape
  - [x] Re-home filename sanitization, file-type validation, and upload guard behavior into `modules/ingestion/domain`
  - [x] Resolve uploads into an owned Space or the caller's active default Space
  - [x] Reuse usage-plan file-size, document-count, storage, and per-document chunk constraints
- [x] Add parsing-job and chunk relational foundations
  - [x] Add the `DocumentChunk` relational projection with stable chunk identity, previews, checksums, and Space scope
  - [x] Add the `DocumentProcessingJob` record for queued parsing work, retry attempts, timestamps, and visible failure detail
  - [x] Add the follow-on Alembic revision for chunk and processing-job tables
  - [x] Verify reprocess can replace chunk projections idempotently
- [x] Add queue and worker runtime seams
  - [x] Add the first concrete `platform/queues` adapter with SQL-backed claiming and in-memory test registration
  - [x] Add `workers/document_pipeline.py` as the document parsing worker entrypoint
  - [x] Keep request handlers limited to metadata creation and queue submission rather than inline parsing
  - [x] Verify queued jobs can be processed without HTTP request context
- [x] Implement text extraction and chunking for the manual-upload slice
  - [x] Support manual upload parsing for `pdf`, `docx`, `md`, `markdown`, and `txt`
  - [x] Store extracted preview and original text back onto `Document`
  - [x] Write logical chunk projections and update chunk counters after parsing completes
  - [x] Mark `vector`, `extraction`, and `graph` stages as `deferred` in public processing status during this slice
- [x] Add contract and test coverage for the slice
  - [x] Add ingestion module tests for auth, Space ownership, validation, upload success, and batch visibility
  - [x] Add platform and worker tests for queue claiming, missing-blob failure handling, and chunk replacement
  - [x] Verify OpenAPI export includes ingestion paths and the `deferred` processing-stage enum value
  - [x] Verify parsed uploads are visible through existing document list and detail reads

## Phase 7 - Local Dependency Runtime And Integration Foundations

Goal: pull the third-party local runtime forward so developers can run the app against Dockerized Supabase, Postgres, and Ollama before deeper retrieval and enrichment work continues.

Depends on: Phase 6

- [x] Phase complete
- [x] Reconcile the tracker to current repo truth
  - [x] Keep Phase 7 focused on completion, validation, and operator guidance rather than re-describing already-landed infra assets as future work
  - [x] Mark the repo-owned Supabase wrapper assets and on-demand upstream fetch workflow as landed
  - [x] Mark the Ollama compose assets and `cpu`, `amd`, and `nvidia` runtime selection as landed
  - [x] Mark the shared named Docker network between the app stack and dependency stack as landed
- [x] Lock the local dependency stack behind repo-owned workflows
  - [x] Treat `./dev-setup.sh infra up|down|ps|logs|upgrade` as the canonical public interface for local dependency management
  - [x] Keep the app stack in `infra/docker/compose.dev.yml` and the dependency stack in `infra/docker/compose.infra.yml`
  - [x] Keep fetched upstream Supabase Docker assets ignored and hydrated on demand
  - [x] Keep checked-in compose and docs free of absolute local filesystem paths
- [x] Align local env and readiness behavior
  - [x] Keep backend env examples targeting the shared local Docker network cleanly
  - [x] Ensure the infra workflow auto-creates `infra/docker/.env.infra` from the repo-owned example when missing
  - [x] Ensure local Postgres comes up with `pgvector` installed
  - [x] Ensure the local Supabase storage bucket used by the app is created automatically
  - [x] Verify local readiness can report `healthy` for `database`, `storage`, `vector`, `graph`, and `llm` when the dependency stack is running
- [x] Add explicit local acceptance coverage
  - [x] Add repo-owned script-level coverage for env bootstrap, backup restore, Supabase upstream population, and Ollama runtime override selection
  - [x] Add `./dev-setup.sh test-infra` as the opt-in Docker-backed Phase 7 smoke path
  - [x] Verify manual upload flows can be smoke-tested locally against the Dockerized dependencies without widening this phase into retrieval or enrichment work
  - [x] Keep worker/runtime integration limited to what is required for local ingestion confidence in this phase
- [x] Align docs and operator guidance
  - [x] Document how to boot the app stack and infra stack together
  - [x] Document the new `test-infra` entrypoint and its opt-in scope
  - [x] Keep readiness documented as infrastructure verification rather than proof of higher-level retrieval correctness

## Phase 8 - Retrieval Projection And Enrichment

Goal: extend the ingestion backbone with derived retrieval projections and enrichment stages once manual upload, parsing, chunk state, and the local dependency runtime are stable.

Depends on: Phase 7

- [X] Phase complete
- [x] Complete the retrieval-facing data and adapter foundations
  - [x] Define entity and canonical entity relational fields
  - [x] Define vector chunk identity and payload requirements
  - [x] Define graph node and edge write interfaces
  - [x] Define graph rebuild and idempotency expectations
  - [x] Verify graph state is treated as a controlled projection
- [x] Implement embeddings and vector upsert flow
  - [x] Add embedding provider integration
  - [x] Add vector upsert behavior
  - [x] Add vector retry and cleanup behavior
  - [x] Add embeddings and vector tests
  - [x] Verify reprocessing does not duplicate vector projections
- [x] Implement entity extraction and graph projection flow
  - [x] Add entity extraction integration
  - [x] Add relational entity persistence behavior
  - [x] Add graph projection behavior
  - [x] Add entity and graph stage tests
  - [x] Verify provenance survives extraction and graph projection

## Phase 9 - Search, Entities, And Graph Read Surfaces

Goal: expose the first public retrieval read surfaces on top of Phase 8 projections so processed documents become searchable, entity-aware, and graph-explorable before chat and current-state workflows are added.

Depends on: Phase 8

- [x] Phase complete
- [x] Lock retrieval read contracts and scope rules
  - [x] Reuse `SpaceScope` across search, entity, and graph reads with owned-Space enforcement and active/default Space fallback when `space_id` is omitted
  - [x] Finalize concrete `search`, `entities`, and `knowledge_graph` transport schemas in their module `api/schemas.py` files
  - [x] Reuse shared `Citation` and `SourceTier`; keep this phase limited to document- and derived-tier provenance
  - [x] Treat `CanonicalEntity.id` as the public entity identifier; keep raw mention IDs nested inside provenance payloads only
  - [x] Verify OpenAPI and generated TypeScript artifacts include the new retrieval read contracts
- [x] Implement read-side vector and graph query seams
  - [x] Add vector retrieval helpers over `DocumentChunkVector` scoped by owned Spaces and non-deleted documents
  - [x] Add graph read helpers over `GraphNode` and `GraphEdge` for seeded subgraph and neighbor expansion
  - [x] Add shared ranking and dedup logic that can merge boolean, vector, and graph candidates into one ordered result set
  - [x] Keep Phase 8 projection writers authoritative; do not add new retrieval-owned tables in this phase
- [x] Implement the search module
  - [x] Add `GET /api/v1/search`
  - [x] Support `mode=boolean|vector|graph|combined`, query text, pagination, `space_id|all_spaces`, and first-pass filters for `document_id`, `file_type`, and `entity_type`
  - [x] Return normalized results with score, result kind, document metadata, preview text, optional entity summary, and at least one citation
  - [x] Ensure combined mode deduplicates repeated hits by chunk/entity identity and degrades cleanly when one retrieval branch has no candidates
  - [x] Verify soft-deleted documents and out-of-scope Spaces never appear in search results
- [x] Implement the entities module
  - [x] Add `GET /api/v1/entities` list and `GET /api/v1/entities/{entity_id}` detail
  - [x] Add provenance and history reads rooted in canonical entities plus extracted mentions, related documents, and chunk citations
  - [x] Define history in this phase as chronological mention history from ingested documents, not user-edited fact/version history
  - [x] Verify entity detail responses line up with graph node identity and search result entity references
- [x] Implement the knowledge graph module
  - [x] Add a read-only subgraph endpoint seeded by public canonical `entity_id`
  - [x] Add document-scoped graph read behavior for exploring relationships present in one document
  - [x] Support depth and limit guards plus typed empty-graph responses
  - [x] Verify graph responses reuse the same canonical entity IDs and provenance conventions as entities and search
- [x] Add retrieval read tests and acceptance coverage
  - [x] Add module tests for auth, Space ownership, all-spaces behavior, empty states, and typed problem responses
  - [x] Add search tests for boolean, vector, graph, and combined modes, ranking merge, deduplication, and citation presence
  - [x] Add entity tests for list, detail, provenance, history behavior, and deleted-document exclusion
  - [x] Add knowledge-graph tests for seeded subgraph reads, document-scoped reads, and depth/limit enforcement
  - [x] Add an integration path proving a processed upload becomes searchable and graph/entity-readable after worker completion

## Phase 10 - Retrieval Answering And State Workflows

Goal: build the interaction and current-state layers that consume the new retrieval reads for pinned-facts, changes, corrections, and chat experiences.

Depends on: Phase 9

- [x] Phase complete
- [x] Lock in the remaining cross-store and provenance conventions
  - [x] Define source-tier behavior beyond document and derived provenance
  - [x] Define current-state versus history conventions
  - [x] Define Space scoping rules across relational and derived stores for chat and stateful workflows
  - [x] Verify all cross-store abstractions align with `docs/architecture/data-and-storage.md`
- [x] Add the remaining relational schema foundations
  - [x] Define chat session and message fields
  - [x] Define pinned-fact, candidate, and history fields
  - [x] Define changes feed fields
  - [x] Define correction and verification fields
  - [x] Verify stable IDs and audit timestamps are present where required
- [x] Implement pinned facts
  - [x] Complete the pinned-facts backend module
  - [x] Add pinned-fact definition behavior
  - [x] Add pinned-fact summary, candidate review, and conflict behavior
  - [x] Add pinned-facts endpoint tests
  - [x] Update pinned-facts contracts
  - [x] Verify conflict resolution and provenance behavior
- [x] Implement changes feed
  - [x] Complete the changes backend module
  - [x] Add change list and detail behavior
  - [x] Add read-state behavior
  - [x] Add changes endpoint tests
  - [x] Update changes contracts
  - [x] Verify changes can reflect ingestion and current-state updates
- [x] Implement corrections and verification
  - [x] Complete the corrections backend module
  - [x] Add correction submission behavior
  - [x] Add correction review and verification behavior
  - [x] Add corrections endpoint tests
  - [x] Update corrections contracts
  - [x] Verify corrections feed back into provenance-aware flows
- [x] Implement chat orchestration
  - [x] Complete the chat backend module
  - [x] Add session lifecycle behavior
  - [x] Add answer composition and citation packaging behavior
  - [x] Add chat endpoint tests
  - [x] Update chat contracts
  - [x] Verify chat depends on stable search and retrieval contracts

## Phase 11 - Web Workspace Foundations

Goal: turn `apps/web` from scaffold mode into the first real typed product surface for auth, Space selection, document library/upload/status, dashboard, and account usage/profile while keeping later retrieval-heavy UI work explicitly deferred.

Depends on: Phase 10

- [x] Phase complete
- [x] Replace scaffold-only contract consumption with real generated TypeScript artifacts
  - [x] Generate `packages/contracts/typescript/index.ts` from the exported OpenAPI document
  - [x] Keep request and response shapes imported from `packages/contracts/typescript`
  - [x] Keep feature clients as thin wrappers around shared transport instead of generating request helpers
  - [x] Add contract-generation coverage proving TypeScript output is real, not placeholder-only
- [x] Implement app-level shells and shared frontend runtime for the first live workspace slice
  - [x] Replace env-based fake auth with a stored-token session provider backed by `/api/v1/auth/login` and `/api/v1/auth/me`
  - [x] Replace local-only Space state with live owned-Space loading from `/api/v1/spaces`
  - [x] Expand the shared API client to own bearer auth, JSON, form, multipart, query-string, problem-response, and blob handling
  - [x] Keep route ownership in `app/router.tsx` with `/`, `/login`, `/register`, `/dashboard`, `/spaces`, `/documents`, `/documents/{document_id}`, `/account`, and `/admin`
  - [x] Show current user, current scope, and logout behavior in the authenticated shell
  - [x] Add shared runtime tests for session bootstrap, redirects, admin gating, and scope persistence
- [x] Implement the auth feature
  - [x] Add live login and register pages
  - [x] Redirect successful registration back to `/login` instead of auto-logging in
  - [x] Add loading and typed error states
  - [x] Add auth feature tests
  - [x] Verify auth contract alignment
- [x] Implement the spaces feature
  - [x] Add the Spaces page for list, create, rename, set-default, and archive flows
  - [x] Add active-Space and all-spaces UI behavior
  - [x] Keep archived Spaces visible but visually separate from active Spaces
  - [x] Add Spaces feature tests
  - [x] Verify Space contract alignment
- [x] Implement the documents feature
  - [x] Add the documents list page with pagination and file-type filtering
  - [x] Add manual upload behavior backed by `/api/v1/ingestion/uploads`
  - [x] Add document detail, status polling, move, delete, and download behavior
  - [x] Reject write workflows that would otherwise infer a target Space while `all_spaces=true`
  - [x] Keep retry and reprocess controls deferred
  - [x] Add documents feature tests
  - [x] Verify document and processing contract alignment
- [x] Implement the account and dashboard features
  - [x] Add the account page for profile, optional password change, plan tier, feature flags, and usage summary
  - [x] Add the dashboard as the authenticated landing surface using current scope, recent documents, and usage summary
  - [x] Add account and dashboard feature tests
  - [x] Verify account, usage, and dashboard reads align with current contracts

## Phase 12 - Retrieval And Interaction Web Surfaces

Goal: add the first retrieval-heavy frontend experiences on top of the completed workspace foundations so search, chat, entities, pinned facts, changes, and corrections become usable in the web app without widening the earlier auth, scope, and document slice.

Depends on: Phase 11

- [x] Phase complete
- [x] Implement the search feature
  - [x] Add search page scaffolds
  - [x] Add search API client integration
  - [x] Add result list and filter behavior
  - [x] Add loading, empty, and error states
  - [x] Add search feature tests
  - [x] Verify search contract alignment
- [x] Implement the chat feature
  - [x] Add chat page scaffolds
  - [x] Add chat session and message UI behavior
  - [x] Add chat API client integration
  - [x] Add citation rendering and error states
  - [x] Add chat feature tests
  - [x] Verify chat contract alignment
- [x] Implement the entities feature
  - [x] Add entities list and detail page scaffolds
  - [x] Add provenance, history, and graph UI behavior
  - [x] Add entities API client integration
  - [x] Add loading, empty, and error states
  - [x] Add entities feature tests
  - [x] Verify entity and graph contract alignment
- [x] Implement the pinned facts feature
  - [x] Add pinned-facts page scaffolds
  - [x] Add tracked summary and conflict UI behavior
  - [x] Add pinned-facts API client integration
  - [x] Add loading, empty, and error states
  - [x] Add pinned-facts feature tests
  - [x] Verify pinned-facts contract alignment
- [x] Implement the changes and corrections features
  - [x] Add changes page scaffolds
  - [x] Add changes API client integration
  - [x] Add list, detail, and read-state UI behavior
  - [x] Add correction submission and review entrypoints where applicable
  - [x] Add loading, empty, and error states
  - [x] Add changes and corrections feature tests
  - [x] Verify changes and corrections contract alignment

## Phase 13 - Self-Hosted Operator Completion

Goal: finish the remaining product work for a local or self-hosted installation by removing public-marketing assumptions, tightening the logged-out surface, and completing the operator-facing admin and usage workflows.

Depends on: Phase 12

- [x] Phase complete
- [x] Convert the logged-out web surface to the self-hosted shape
  - [x] Make the default public route render the login page instead of a marketing home page
  - [x] Keep the public route surface limited to login, registration, and the system status page
  - [x] Remove or de-route marketing pages from the active application flow
  - [x] Simplify the public shell navigation to match the reduced public route surface
  - [x] Add or update frontend tests covering the new public default route and redirects
- [x] Implement admin tooling
  - [x] Complete admin backend routes and policies
  - [x] Add admin user management UI
  - [x] Add admin readiness and tester UI
  - [x] Add admin feature tests and guarded endpoint tests
  - [x] Update admin contracts
  - [x] Verify admin depends on auth, users, usage, and readiness foundations
- [x] Complete self-hosted usage and account controls
  - [x] Add the remaining account usage dashboard behavior needed for local operators
  - [x] Add admin-side instance policy or plan-control behavior where applicable
  - [x] Add usage UI tests
  - [x] Verify usage surfaces align with feature-flag, plan-tier, and self-hosted policy behavior
  - [x] Remove or rewrite SaaS-oriented copy that implies pricing, public upgrade, or online subscription flows

## Phase 14 - Hardening And Self-Hosted Readiness

Goal: close testing gaps, verify end-to-end quality, align docs with the self-hosted product shape, and polish the repository for reliable local installation and operation.

Depends on: Phase 13

- [ ] Phase complete
- [ ] Review API and backend test coverage
  - [ ] Review endpoint coverage across all implemented modules
  - [ ] Add missing request, response, guard, and failure-case tests where practical
  - [ ] Review worker and platform adapter test gaps
  - [ ] Verify all feasible endpoints have automated coverage
- [ ] Review frontend and integration test coverage
  - [ ] Review feature test coverage across implemented web surfaces
  - [ ] Add missing loading, empty, error, and edge-case tests
  - [ ] Review contract alignment checks between backend and frontend
  - [ ] Verify no major feature relies on manual-only validation
- [ ] Complete E2E critical-path coverage
  - [x] Add authentication flow E2E coverage
  - [x] Add Space-scoped upload and document flow E2E coverage
  - [ ] Add search and chat E2E coverage
  - [ ] Add pinned-facts or changes critical-path E2E coverage
  - [ ] Add guarded admin E2E coverage where practical
  - [ ] Verify E2E tests cover stitched behavior rather than unit-level logic
- [ ] Align docs and developer workflow for self-hosted use
  - [x] Update architecture docs for any contract or structure changes made during implementation
  - [x] Update the implementation tracker as phases progress
  - [x] Review README and bootstrap docs for clarity
  - [ ] Review env examples, installer defaults, and secret handling for local deployment safety
  - [ ] Verify no private notes or local references leak into tracked docs
- [ ] Polish the repo for maintainable long-term operation
  - [ ] Review naming consistency across code, docs, and scripts
  - [ ] Review commit-ready developer workflow from clone to local startup
  - [ ] Review error messages and empty states for clarity
  - [ ] Review operator-facing docs for maintainability and professionalism
  - [ ] Verify the repo is strong enough to serve as a dependable self-hosted application

## Dependency Notes

| Area | Depends on |
| --- | --- |
| Web feature work | API contracts, shared frontend runtime, and owning backend modules |
| Chat | Search, retrieval contracts, session handling, and citation packaging |
| Pinned facts | Entities, provenance, search, and current-state conventions |
| Changes feed | Ingestion events, pinned facts updates, and history/provenance modeling |
| Admin tooling | Auth, users, usage, shared guards, and readiness surfaces |
| E2E coverage | Working app shells, stable API flows, and seedable local infrastructure |
| Logged-out surface conversion | Auth pages, status surface, public shell wiring, and route guards |
| Self-hosted operator workflows | Admin tooling, usage surfaces, readiness visibility, and local infra docs |

## Done Criteria

- [ ] Repo structure is complete and matches the architecture docs
- [ ] Local app and dependency stacks can be started through repo-owned workflows
- [ ] Platform adapters for storage, vector, graph, queue, and LLM services are wired
- [ ] All planned API modules have implemented routes
- [ ] All feasible endpoints have automated tests
- [ ] The public web surface is intentionally limited to login, registration, and system status
- [ ] Core web flows exist end-to-end
- [ ] Later-phase capabilities are either implemented or explicitly left unchecked
- [ ] Architecture docs and the implementation tracker are aligned
