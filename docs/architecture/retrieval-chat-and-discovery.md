# Retrieval, Chat, And Discovery

## Purpose

Define how search, graph exploration, chat, citations, tracked state, and related discovery surfaces compose retrieval behavior in the rebuild.

## Target Design

### Owning backend modules

- `modules/search`
- `modules/chat`
- `modules/entities`
- `modules/knowledge_graph`
- `modules/tracked_state`
- `modules/changes`
- `modules/corrections`

### Retrieval principles

- Retrieval is scope-aware first, ranking-aware second.
- Chat is an orchestrated consumer of retrieval systems, not a separate source of truth.
- Citations are required for user-facing answer trust.
- Graph exploration and semantic retrieval can differ in ranking behavior while sharing identifiers and provenance.
- Verified corrections outrank document- and derived-tier evidence for current-state and chat answer composition in the first interaction slice.

## Responsibilities and Boundaries

- `search`: combined, vector, graph, boolean, and related lookups
- `chat`: sessions, evidence fan-in, prompts, answer synthesis, suggestions, citation bundles
- `entities`: detail, history, provenance, entity-level editing or visibility
- `knowledge_graph`: graph-native explore and projection-aware graph reads
- `tracked_state`: current-value summaries and conflict views built from retrieved evidence
- `changes`: drift and "what changed" views derived from versioned state
- `corrections`: human feedback loop that can influence future truth

## Public Interfaces and Shared Types

- `SearchQuery`
- `SearchFilters`
- `SearchResult`
- `RelatedResult`
- `GraphNode`
- `GraphLink`
- `ChatAnswer`
- `Citation`
- `TrackedFieldSummary`
- `ConflictRecord`

## Primary Workflows

### Unified search

1. User submits a search query with Space scope and optional filters.
2. `modules/search` routes to vector, graph, boolean, or combined strategies.
3. Results are normalized into one typed response shape.
4. UI renders list or graph-oriented result presentations from the same contract family.

### Chat question

1. User sends a question inside a chat session.
2. `modules/chat` resolves Space scope, session context, and feature flags.
3. Chat gathers a bounded evidence packet from verified corrections, current tracked-state values, shared search/RAG results, Knowledge Graph relationships, and recent session history.
4. Chat classifies the answer intent, expands selected document hits from stored chunk text, and ranks evidence by answerability before source quotas are applied.
5. The configured chat model synthesizes a final answer from the evidence packet, using chat history only to resolve follow-up context and evidence IDs for provenance.
6. If no answer model is available, the service returns a deterministic evidence-backed fallback only when it can produce a reliable answer shape, such as extracting a Markdown technology-stack table into bullets.
7. Messages, citations, and a compact evidence audit are persisted to session history.
8. `apps/web` renders the selected transcript with assistant-ui's external-store runtime over the existing chat session detail query; the backend remains authoritative for messages, citations, evidence audit, suggestions, and corrections.

### Tracked state

1. User defines tracked fields for a Space.
2. Tracked-state queries gather candidate evidence from entities, documents, search, graph, and corrections.
3. Policies resolve current values, conflicts, and provenance with verified corrections ranked ahead of document or derived candidates.
4. Summary cards and conflict panels expose the result to the user.

## Failure Modes and Edge Cases

- Chat may receive strong vector evidence but weak graph context, or the reverse.
- Chat evidence can contain noisy snippets from diagrams, install paths, code blocks, or JSON payloads; answer-intent scoring must prevent those from crowding out direct section/table evidence for conceptual questions.
- Search graph mode can be disabled while list mode stays available.
- Citations must survive partial answer generation and degraded retrieval modes; if degraded fallback cannot produce a reliable answer, it should say so instead of attaching random citations.
- The public runtime status distinguishes Ollama catalog reachability from chat generation health because `/api/tags` can be healthy while `/api/chat` times out.
- Evidence audit records must remain compact; full document chunks and raw prompt payloads should not be exposed as a separate UI contract.
- Current-state answers can conflict with historical entity versions or pending corrections.
- Related-result exploration must not leak across Spaces when all-spaces is off.

## Acceptance Checks

- Search and chat both consume typed, scope-aware retrieval services.
- User-facing answers always expose provenance-bearing citations where applicable.
- Chat answer synthesis combines multiple evidence sources instead of selecting a single retrieval result as the answer.
- Graph exploration is documented as a first-class capability, not an incidental UI add-on.
- Tracked state and changes reuse retrieval evidence instead of inventing separate hidden pipelines.
- Corrections feed back into discovery through explicit application services.
- Single-Space write workflows reject `all_spaces=true` instead of inferring multi-Space truth.

## Deferred Notes

- Bot-read APIs may reuse search and knowledge-graph query services later, but they must not fork retrieval semantics.
- Dedicated graph visualizer work should extend existing graph result contracts rather than creating a parallel graph stack.
