# Ragdoll Implementation Plan

## How To Use This Plan

This document is the canonical progress tracker for building Ragdoll. Each phase is ordered by dependency, starting with the foundations every later capability relies on and ending with the user-facing web application and OSS hardening work.

Use the checkboxes as follows:

- Mark major deliverables complete only when all child tasks and acceptance checks under them are done.
- Keep implementation updates in this file synchronized with architecture or contract changes.
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

Depends on: Phase 0, Phase 1

- [ ] Phase complete
- [ ] Create the `packages/contracts` foundation
  - [ ] Add the contracts directory structure for OpenAPI, schemas, and generated TypeScript types
  - [ ] Add baseline contract docs describing contract ownership
  - [ ] Add placeholder schema groupings for all planned product areas
  - [ ] Verify contract directories match the architecture docs
- [ ] Define the initial schema set
  - [ ] Add auth schema placeholders
  - [ ] Add spaces schema placeholders
  - [ ] Add documents schema placeholders
  - [ ] Add search schema placeholders
  - [ ] Add chat schema placeholders
  - [ ] Add entities schema placeholders
  - [ ] Add tracked state schema placeholders
  - [ ] Add changes schema placeholders
  - [ ] Add admin schema placeholders
  - [ ] Add usage schema placeholders
  - [ ] Define shared response envelopes such as pagination, mutation results, and problem responses
- [ ] Define contract generation strategy
  - [ ] Add OpenAPI generation workflow notes
  - [ ] Add TypeScript type generation workflow notes
  - [ ] Add a placeholder tooling entrypoint in `packages/tooling` for contract generation
  - [ ] Verify the generation strategy supports both backend-first and frontend consumption flows
- [ ] Build the `/api/v1` skeleton
  - [ ] Add versioned router composition for all planned backend modules
  - [ ] Add placeholder route mounts for auth, users, spaces, documents, ingestion, search, chat, entities, knowledge graph, tracked state, changes, corrections, admin, and usage
  - [ ] Add endpoint inventory notes or route placeholder coverage for each module
  - [ ] Verify every capability in `docs/architecture/capability-map.md` has an API home where applicable
- [ ] Add the baseline API test strategy
  - [ ] Add route presence tests for mounted endpoints where possible
  - [ ] Add request and response schema tests where possible
  - [ ] Add auth guard tests for protected endpoints where applicable
  - [ ] Add problem response tests for common failure cases where possible
  - [ ] Verify the implementation plan explicitly covers testing every API endpoint where practical

## Phase 3 - Core Data And Storage

Goal: define the durable record model, storage abstractions, provenance conventions, and cross-store boundaries needed before feature modules and processing pipelines can be implemented safely.

Depends on: Phase 1, Phase 2

- [ ] Phase complete
- [ ] Add relational schema foundations
  - [ ] Define user records and plan-tier fields
  - [ ] Define Space records and scope-related fields
  - [ ] Define document metadata and processing-state fields
  - [ ] Define entity and canonical entity fields
  - [ ] Define chat session and message fields
  - [ ] Define tracked field and tracked value fields
  - [ ] Define changes feed fields
  - [ ] Define correction and verification fields
  - [ ] Define usage tracking fields
  - [ ] Verify stable IDs and audit timestamps are present where required
- [ ] Add object storage abstraction
  - [ ] Define original file storage interface
  - [ ] Define derived artifact storage interface
  - [ ] Add storage error and cleanup behavior expectations
  - [ ] Verify object storage is not treated as the source of truth for metadata
- [ ] Add vector store abstraction
  - [ ] Define embedding write and query interfaces
  - [ ] Define chunk identity and payload requirements
  - [ ] Define delete and reprocess behavior for vector records
  - [ ] Verify vector operations align with citation and provenance needs
- [ ] Add graph store abstraction
  - [ ] Define graph node and edge write interfaces
  - [ ] Define graph exploration query interfaces
  - [ ] Define graph rebuild and idempotency expectations
  - [ ] Verify graph state is treated as a controlled projection
- [ ] Lock in provenance and state conventions
  - [ ] Define source-tier behavior
  - [ ] Define processing status model
  - [ ] Define current-state versus history conventions
  - [ ] Define Space scoping rules across relational and derived stores
  - [ ] Verify all cross-store abstractions align with `docs/architecture/data-and-storage.md`

## Phase 4 - Core Backend Modules

Goal: implement the foundational backend modules that other capabilities depend on, starting with identity, ownership, document metadata, and usage surfaces.

Depends on: Phase 1, Phase 2, Phase 3

- [ ] Phase complete
- [ ] Implement the auth module
  - [ ] Add auth routes and wire schemas
  - [ ] Add auth commands and queries
  - [ ] Add auth domain types and policies
  - [ ] Add auth repository behavior
  - [ ] Add auth module tests
  - [ ] Update auth contracts
  - [ ] Verify login, registration, session bootstrap, and protected route behavior
- [ ] Implement the users module
  - [ ] Add user routes and wire schemas where needed
  - [ ] Add user commands and queries
  - [ ] Add user domain types and policies
  - [ ] Add user repository behavior
  - [ ] Add user module tests
  - [ ] Update user and usage-adjacent contracts
  - [ ] Verify plan tier and feature-flag override ownership
- [ ] Implement the spaces module
  - [ ] Add Space routes and wire schemas
  - [ ] Add Space commands and queries
  - [ ] Add Space domain types and policies
  - [ ] Add Space repository behavior
  - [ ] Add Space module tests
  - [ ] Update Space contracts
  - [ ] Verify active-space and all-spaces behaviors have API support
- [ ] Implement the documents module
  - [ ] Add document routes and wire schemas
  - [ ] Add document commands and queries
  - [ ] Add document domain types and policies
  - [ ] Add document repository behavior
  - [ ] Add document module tests
  - [ ] Update document contracts
  - [ ] Verify list, detail, move, download, delete, and status behaviors
- [ ] Implement the usage module
  - [ ] Add usage routes and wire schemas
  - [ ] Add usage queries and plan-limit logic
  - [ ] Add usage domain types and policies
  - [ ] Add usage repository behavior
  - [ ] Add usage module tests
  - [ ] Update usage contracts
  - [ ] Verify usage summaries can support account and admin surfaces

## Phase 5 - Ingestion And Background Processing

Goal: implement the document intake and processing pipeline that transforms uploads into searchable, citeable, graph-aware knowledge.

Depends on: Phase 1, Phase 2, Phase 3, Phase 4

- [ ] Phase complete
- [ ] Implement upload intake
  - [ ] Add upload routes and wire schemas
  - [ ] Add upload validation for file types and limits
  - [ ] Add initial object storage write behavior
  - [ ] Add initial document record creation and processing-state updates
  - [ ] Add upload endpoint tests
  - [ ] Update upload contracts
- [ ] Implement processing job and queue foundations
  - [ ] Define processing job payloads
  - [ ] Define queue interface and retry semantics
  - [ ] Add worker bootstrap and execution wiring
  - [ ] Add queue and worker tests where practical
  - [ ] Verify jobs can run without coupling to HTTP request context
- [ ] Implement text extraction and chunking
  - [ ] Add text extraction pipeline behavior
  - [ ] Add chunking rules and chunk identity behavior
  - [ ] Add extraction failure handling and status reporting
  - [ ] Add extraction and chunking tests
  - [ ] Verify chunk output supports later citation behavior
- [ ] Implement embeddings and vector upsert flow
  - [ ] Add embedding provider integration
  - [ ] Add vector upsert behavior
  - [ ] Add vector retry and cleanup behavior
  - [ ] Add embeddings and vector tests
  - [ ] Verify reprocessing does not duplicate chunk records
- [ ] Implement entity extraction and graph projection flow
  - [ ] Add entity extraction integration
  - [ ] Add relational entity persistence behavior
  - [ ] Add graph projection behavior
  - [ ] Add entity and graph stage tests
  - [ ] Verify provenance survives extraction and graph projection
- [ ] Implement reprocess, retry, and status APIs
  - [ ] Add full reprocess endpoint behavior
  - [ ] Add targeted retry endpoint behavior
  - [ ] Add batch or single-document status reads
  - [ ] Add retry and status tests
  - [ ] Update processing contracts

## Phase 6 - Retrieval, Graph, And Chat

Goal: implement the knowledge and interaction layers that turn processed data into search, graph, tracked-state, correction, and chat experiences.

Depends on: Phase 2, Phase 3, Phase 4, Phase 5

- [ ] Phase complete
- [ ] Implement search
  - [ ] Complete the search backend module
  - [ ] Add vector, graph, boolean, and combined query behavior
  - [ ] Add search endpoint tests
  - [ ] Add search result scoring, filtering, and fallback behavior
  - [ ] Update search contracts
  - [ ] Verify search outputs support citations and later chat use
- [ ] Implement knowledge graph query surfaces
  - [ ] Complete the knowledge graph backend module
  - [ ] Add graph exploration and subgraph query behavior
  - [ ] Add graph endpoint tests
  - [ ] Add graph error and timeout behavior
  - [ ] Update graph-related contracts
  - [ ] Verify graph outputs align with entities and search surfaces
- [ ] Implement entities detail, provenance, and history
  - [ ] Complete the entities backend module
  - [ ] Add entity detail behavior
  - [ ] Add entity provenance and history behavior
  - [ ] Add entity endpoint tests
  - [ ] Update entity contracts
  - [ ] Verify current-state versus history behavior is explicit in responses
- [ ] Implement tracked state
  - [ ] Complete the tracked-state backend module
  - [ ] Add tracked field definition behavior
  - [ ] Add tracked summary and conflict behavior
  - [ ] Add tracked-state endpoint tests
  - [ ] Update tracked-state contracts
  - [ ] Verify conflict resolution and provenance behavior
- [ ] Implement changes feed
  - [ ] Complete the changes backend module
  - [ ] Add change list and detail behavior
  - [ ] Add read-state behavior
  - [ ] Add changes endpoint tests
  - [ ] Update changes contracts
  - [ ] Verify changes can reflect ingestion and current-state updates
- [ ] Implement corrections and verification
  - [ ] Complete the corrections backend module
  - [ ] Add correction submission behavior
  - [ ] Add correction review and verification behavior
  - [ ] Add corrections endpoint tests
  - [ ] Update corrections contracts
  - [ ] Verify corrections feed back into provenance-aware flows
- [ ] Implement chat orchestration
  - [ ] Complete the chat backend module
  - [ ] Add session lifecycle behavior
  - [ ] Add answer composition and citation packaging behavior
  - [ ] Add chat endpoint tests
  - [ ] Update chat contracts
  - [ ] Verify chat depends on stable search and retrieval contracts

## Phase 7 - Core Web Application

Goal: implement the core web shells, shared client behavior, and primary authenticated product features after the API, contracts, and backend capabilities are stable.

Depends on: Phase 1, Phase 2, Phase 4, Phase 5, Phase 6

- [ ] Phase complete
- [ ] Implement app-level shells and shared frontend runtime
  - [ ] Add app router and provider wiring
  - [ ] Add public shell
  - [ ] Add authenticated shell
  - [ ] Add admin shell placeholder
  - [ ] Add guarded route behavior
  - [ ] Add shared API client and request handling
  - [ ] Add shared session and Space-scope state
  - [ ] Add app-shell tests where practical
  - [ ] Verify shell and provider behavior match the architecture docs
- [ ] Implement the auth feature
  - [ ] Add auth page scaffolds
  - [ ] Add auth API client integration
  - [ ] Add loading, empty, and error states
  - [ ] Add auth feature tests
  - [ ] Verify auth contract alignment
- [ ] Implement the spaces feature
  - [ ] Add spaces page scaffolds
  - [ ] Add spaces API client integration
  - [ ] Add active-space and all-spaces UI behavior
  - [ ] Add spaces feature tests
  - [ ] Verify Space contract alignment
- [ ] Implement the documents feature
  - [ ] Add documents page scaffolds
  - [ ] Add document list, detail, and upload UI behavior
  - [ ] Add documents API client integration
  - [ ] Add loading, empty, and error states
  - [ ] Add documents feature tests
  - [ ] Verify document and processing contract alignment
- [ ] Implement the search feature
  - [ ] Add search page scaffolds
  - [ ] Add search API client integration
  - [ ] Add result list and filter behavior
  - [ ] Add loading, empty, and error states
  - [ ] Add search feature tests
  - [ ] Verify search contract alignment
- [ ] Implement the chat feature
  - [ ] Add chat page scaffolds
  - [ ] Add chat session and message UI behavior
  - [ ] Add chat API client integration
  - [ ] Add citation rendering and error states
  - [ ] Add chat feature tests
  - [ ] Verify chat contract alignment
- [ ] Implement the entities feature
  - [ ] Add entities list and detail page scaffolds
  - [ ] Add provenance, history, and graph UI behavior
  - [ ] Add entities API client integration
  - [ ] Add loading, empty, and error states
  - [ ] Add entities feature tests
  - [ ] Verify entity and graph contract alignment
- [ ] Implement the tracked state feature
  - [ ] Add tracked-state page scaffolds
  - [ ] Add tracked summary and conflict UI behavior
  - [ ] Add tracked-state API client integration
  - [ ] Add loading, empty, and error states
  - [ ] Add tracked-state feature tests
  - [ ] Verify tracked-state contract alignment
- [ ] Implement the changes feature
  - [ ] Add changes page scaffolds
  - [ ] Add changes API client integration
  - [ ] Add list, detail, and read-state UI behavior
  - [ ] Add loading, empty, and error states
  - [ ] Add changes feature tests
  - [ ] Verify changes contract alignment
- [ ] Implement the account feature
  - [ ] Add account page scaffolds
  - [ ] Add profile and usage UI behavior
  - [ ] Add account API client integration
  - [ ] Add loading, empty, and error states
  - [ ] Add account feature tests
  - [ ] Verify account and usage contract alignment

## Phase 8 - Capability Completion

Goal: complete the remaining planned product surfaces that depend on the core runtime, processing, retrieval, and web foundations but are not required to establish the primary product path.

Depends on: Phase 4, Phase 5, Phase 6, Phase 7

- [ ] Phase complete
- [ ] Implement admin tooling
  - [ ] Complete admin backend routes and policies
  - [ ] Add admin user management UI
  - [ ] Add admin readiness and tester UI
  - [ ] Add admin feature tests and guarded endpoint tests
  - [ ] Update admin contracts
  - [ ] Verify admin depends on auth, users, and usage foundations
- [ ] Complete usage dashboards and plan controls
  - [ ] Add account usage dashboard behavior
  - [ ] Add admin plan-control behavior where applicable
  - [ ] Add usage UI tests
  - [ ] Verify usage surfaces align with feature-flag and plan-tier behavior
- [ ] Implement public marketing pages
  - [ ] Add home page content and layout
  - [ ] Add product page content and layout
  - [ ] Add pricing page content and layout
  - [ ] Add contact page content and layout
  - [ ] Add marketing feature tests
  - [ ] Verify public pages remain cleanly separated from authenticated product surfaces

## Phase 9 - Hardening, QA, And OSS Readiness

Goal: close testing gaps, verify end-to-end quality, align docs with implementation, and polish the repository for public open source use.

Depends on: Phase 0 through Phase 8

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
  - [ ] Add authentication flow E2E coverage
  - [ ] Add Space-scoped upload and document flow E2E coverage
  - [ ] Add search and chat E2E coverage
  - [ ] Add tracked-state or changes critical-path E2E coverage
  - [ ] Add guarded admin E2E coverage where practical
  - [ ] Verify E2E tests cover stitched behavior rather than unit-level logic
- [ ] Align docs and developer workflow for OSS use
  - [ ] Update architecture docs for any contract or structure changes made during implementation
  - [ ] Update the implementation tracker as phases progress
  - [ ] Review README and bootstrap docs for clarity
  - [ ] Review env examples and secret handling for public safety
  - [ ] Verify no private notes or local references leak into tracked docs
- [ ] Polish the repo for public presentation
  - [ ] Review naming consistency across code, docs, and scripts
  - [ ] Review commit-ready developer workflow from clone to local startup
  - [ ] Review error messages and empty states for clarity
  - [ ] Review OSS-facing docs for maintainability and professionalism
  - [ ] Verify the repo is strong enough to serve as a public portfolio artifact

## Dependency Notes

| Area | Depends on |
| --- | --- |
| Web feature work | API contracts, shared frontend runtime, and owning backend modules |
| Chat | Search, retrieval contracts, session handling, and citation packaging |
| Tracked state | Entities, provenance, search, and current-state conventions |
| Changes feed | Ingestion events, tracked state updates, and history/provenance modeling |
| Admin tooling | Auth, users, usage, shared guards, and readiness surfaces |
| E2E coverage | Working app shells, stable API flows, and seedable local infrastructure |
| Marketing pages | Web app shell, shared UI primitives, and public route wiring |

## Done Criteria

- [ ] Repo structure is complete and matches the architecture docs
- [ ] Platform adapters for storage, vector, graph, queue, and LLM services are wired
- [ ] All planned API modules have implemented routes
- [ ] All feasible endpoints have automated tests
- [ ] Core web flows exist end-to-end
- [ ] Later-phase capabilities are either implemented or explicitly left unchecked
- [ ] Architecture docs and the implementation tracker are aligned
