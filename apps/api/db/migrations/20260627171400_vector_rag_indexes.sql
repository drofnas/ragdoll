-- migrate:up
CREATE INDEX IF NOT EXISTS ix_document_chunk_vectors_embedding_hnsw_cosine
ON public.document_chunk_vectors USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS ix_document_chunk_vectors_document_chunk_index
ON public.document_chunk_vectors USING btree (document_id, chunk_index);

CREATE INDEX IF NOT EXISTS ix_entities_chunk_id_entity_type
ON public.entities USING btree (chunk_id, entity_type);

-- migrate:down
DROP INDEX IF EXISTS public.ix_entities_chunk_id_entity_type;
DROP INDEX IF EXISTS public.ix_document_chunk_vectors_document_chunk_index;
DROP INDEX IF EXISTS public.ix_document_chunk_vectors_embedding_hnsw_cosine;
