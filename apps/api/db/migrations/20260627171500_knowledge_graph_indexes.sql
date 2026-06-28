-- migrate:up
CREATE INDEX IF NOT EXISTS ix_entities_canonical_entity_id_created_at_id
ON public.entities USING btree (canonical_entity_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS ix_entities_document_id_canonical_entity_id
ON public.entities USING btree (document_id, canonical_entity_id);

CREATE INDEX IF NOT EXISTS ix_graph_edges_document_id_weight_id
ON public.graph_edges USING btree (document_id, weight DESC, id ASC);

-- migrate:down
DROP INDEX IF EXISTS public.ix_graph_edges_document_id_weight_id;
DROP INDEX IF EXISTS public.ix_entities_document_id_canonical_entity_id;
DROP INDEX IF EXISTS public.ix_entities_canonical_entity_id_created_at_id;
