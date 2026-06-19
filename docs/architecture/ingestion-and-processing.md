# Ingestion And Processing

## Purpose

Define the upload, sync, parsing, extraction, embedding, graph population, retry, and worker boundaries for Ragdoll's ingestion pipeline.

## Target Design

### Owning backend areas

- `modules/documents`: metadata lifecycle after a document exists
- `modules/ingestion`: upload intake, processing commands, retry commands, status APIs
- `workers/document_pipeline.py`: background job runner
- `platform/storage`, `platform/vector`, `platform/graph`, `platform/llm`, `platform/queues`: external systems

### Processing stages

1. Intake
2. Blob persistence
3. Text extraction
4. Chunking
5. Embedding generation
6. Vector upsert
7. Entity extraction
8. Graph projection
9. Status finalization and change emission

## Responsibilities and Boundaries

- HTTP routes accept uploads, explicit process requests, reprocess requests, and status lookups.
- Application commands create document records, enqueue jobs, and update stage state.
- Worker code runs long-lived stage transitions and retries.
- Platform adapters parse file content, call LLMs, and write to external stores.
- Documents remain readable in partially processed states, but APIs must surface exact stage health.

## Public Interfaces and Shared Types

- `UploadRequest`
- `ProcessingJob`
- `ProcessingStage`
- `RetryMode`
- `DocumentStatus`
- `ProcessingError`

## Primary Workflows

### Manual upload

1. User uploads a file into a selected Space from `apps/web`.
2. `modules/ingestion` validates file type, size, scope, and actor.
3. API persists initial document metadata and object-store location.
4. Job is enqueued for background processing.
5. Worker extracts text, chunks content, embeds chunks, writes vector rows, extracts entities, and projects graph records.
6. Final status and change/provenance events are written back to SQL.

### Manual reprocess

1. User or admin requests a full reprocess or targeted retry.
2. Command decides whether to clear derived artifacts fully or rerun one stage.
3. Worker replays the required stages idempotently.
4. Status and change feed reflect retry outcome.

## Failure Modes and Edge Cases

- File parses can succeed while embeddings or graph projection fail later.
- Retry mode must distinguish full reprocess from vector-only or graph-only repair.
- Large documents may require truncation or chunk-window extraction policies that are explicitly documented.
- Worker crashes must leave recoverable stage state and re-runnable jobs.

## Acceptance Checks

- Upload and reprocessing flows converge into the same document-processing pipeline where appropriate.
- Stage transitions are explicit and observable through API status.
- Worker retries are idempotent for blobs, vectors, entities, and graph writes.
- Manual and automated repair paths do not bypass provenance recording.
- Space scope is assigned before processing fan-out begins.

## Deferred Notes

- Advanced OCR or multi-pass chunk extraction can extend the parsing stage without changing the owning module boundaries.
- Future document-version-line grouping should layer on top of document and ingestion commands instead of forking the pipeline.
