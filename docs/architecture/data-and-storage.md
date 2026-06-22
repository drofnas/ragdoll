# Data And Storage

## Purpose

Define canonical data ownership across relational data, object storage, vector search, graph search, and shared provenance rules for the rebuild.

## Target Design

### Storage roles

- Relational DB: authoritative product records, user data, Spaces, documents, entities, tracked state, changes, corrections, usage, and processing status
- Object storage: original uploaded files and derived artifacts that must be re-opened or downloaded
- Vector store: chunk embeddings and retrieval payloads
- Graph store: relationship-first exploration and graph-native traversals

### Canonical ownership rules

- Product lifecycle state lives in the relational DB.
- Original files live in object storage; relational rows keep stable references.
- Semantic retrieval indexes live in vector storage and are reproducible from relational + object storage state.
- Graph nodes and edges are derived but product-important; rebuild jobs must treat graph writes as controlled projections from application state, not ad hoc side effects.

### Core records

- `User`
- `Space`
- `Document`
- `DocumentChunk` projection or derived chunk record
- `Entity`
- `CanonicalEntity`
- `ChatSession`
- `ChatMessage`
- `TrackedField`
- `TrackedFieldValue`
- `ChangeEvent`
- `CorrectionRecord`
- `UsageRecord` or usage projection

## Responsibilities and Boundaries

### Relational DB

Owns:

- stable IDs
- ownership and access control
- Space scoping
- processing status
- versioning and current-state indicators
- audit timestamps
- feature flags and plan tiers
- user-submitted corrections and verification state

Must not own:

- raw embedding vectors as the canonical search API
- transient LLM prompts
- graph traversal behavior

### Object storage

Owns:

- original file blobs
- downloadable artifacts
- optionally extracted previews or cached render assets

Must not own:

- access policy rules
- authoritative document metadata

### Vector store

Owns:

- chunk embedding rows keyed by document and deterministic chunk identity
- search payload fields required for fast semantic retrieval
- the first durable implementation uses Postgres-backed projection rows with pgvector-compatible embedding payloads

Must not own:

- authoritative document deletion state
- current-state truth resolution

### Graph store

Owns:

- graph-native traversal performance
- entity and relationship exploration
- document/entity connectivity projections
- the first durable implementation uses Postgres-backed graph node and edge projection tables behind the graph adapter

Must not own:

- user ownership
- admin policy
- truth resolution without relational backing

## Public Interfaces and Shared Types

- `DocumentId`, `EntityId`, `SpaceId`, `UserId`, and `SessionId` are stable identifiers shared through contracts
- `SourceTier` and provenance shapes must travel through API responses
- `ProcessingStatus` must distinguish upload, parsing, vector, extraction, and graph stages
- `Citation` and `EntityRelationshipSummary` must resolve back to relational and document identifiers

## Primary Workflows

1. Create `Document` metadata in SQL with Space, uploader, and processing state.
2. Store original file in object storage and persist the reference.
3. Produce chunk projections and write embeddings to vector storage.
4. Persist extracted entity mentions plus Space-scoped canonical entities in SQL.
5. Project graph nodes and chunk-level co-occurrence edges from extracted or verified records.
6. Resolve search, chat, tracked state, and history views by combining relational truth with vector or graph projections.

## Failure Modes and Edge Cases

- Derived stores can drift from relational truth after partial failures or manual fixes.
- Legacy nullable `space_id` or older truth metadata must not be treated as valid rebuild defaults.
- Entity current-state and graph supersession can disagree unless reconciliation rules are explicit.
- Deletion must remove or tombstone derived vector and graph state without destroying auditability.
- Reprocessing must overwrite derived artifacts idempotently rather than duplicating them.

## Acceptance Checks

- Each record type has one primary store of truth.
- Space scoping is relationally authoritative and available to derived stores.
- Provenance survives search, chat, tracked state, and correction workflows.
- Derived stores are documented as rebuildable projections with idempotent update behavior.
- Reprocessing identical content preserves deterministic chunk identity and does not duplicate vector, entity, or graph projections.

## Deferred Notes

- If document version history is added, it extends relational ownership first and then updates derived retrieval and graph projections.
- If bot-read APIs are added later, they must consume the same identifiers and provenance contracts rather than inventing parallel schemas.
