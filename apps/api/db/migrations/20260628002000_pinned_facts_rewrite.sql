-- migrate:up

ALTER TABLE public.tracked_fields RENAME TO pinned_facts;
ALTER TABLE public.pinned_facts RENAME COLUMN label TO title;
ALTER TABLE public.pinned_facts RENAME COLUMN prompt TO description;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT tracked_fields_pkey TO pinned_facts_pkey;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT ux_tracked_fields_space_key TO ux_pinned_facts_space_key;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT tracked_fields_owner_user_id_fkey TO pinned_facts_owner_user_id_fkey;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT tracked_fields_space_id_fkey TO pinned_facts_space_id_fkey;
ALTER INDEX public.ix_tracked_fields_is_active RENAME TO ix_pinned_facts_is_active;
ALTER INDEX public.ix_tracked_fields_owner_user_id RENAME TO ix_pinned_facts_owner_user_id;
ALTER INDEX public.ix_tracked_fields_space_id RENAME TO ix_pinned_facts_space_id;

ALTER TABLE public.pinned_facts
    ADD COLUMN value_kind character varying(16),
    ADD COLUMN value_text text,
    ADD COLUMN value_json json,
    ADD COLUMN status character varying(32) DEFAULT 'unknown'::character varying NOT NULL,
    ADD COLUMN confidence double precision,
    ADD COLUMN source_document_id uuid,
    ADD COLUMN evidence json,
    ADD COLUMN last_checked_at timestamp with time zone;

WITH current_values AS (
    SELECT DISTINCT ON (tracked_field_id)
        tracked_field_id,
        value_text,
        citations,
        created_at
    FROM public.tracked_field_values
    WHERE is_current
    ORDER BY tracked_field_id, created_at DESC, id DESC
)
UPDATE public.pinned_facts AS pinned_fact
SET value_kind = CASE WHEN current_values.value_text IS NULL THEN NULL ELSE 'text' END,
    value_text = current_values.value_text,
    value_json = NULL,
    status = CASE WHEN current_values.value_text IS NULL THEN 'unknown' ELSE 'active' END,
    confidence = NULL,
    source_document_id = (
        SELECT (citation->>'document_id')::uuid
        FROM json_array_elements(COALESCE(current_values.citations, '[]'::json)) AS citation
        WHERE NULLIF(citation->>'document_id', '') IS NOT NULL
        LIMIT 1
    ),
    evidence = CASE
        WHEN current_values.value_text IS NULL THEN '[]'::json
        ELSE json_build_array(
            json_build_object(
                'quote',
                current_values.value_text,
                'citations',
                COALESCE(current_values.citations, '[]'::json),
                'source_chunk_ids',
                COALESCE(
                    (
                        SELECT json_agg(citation->>'chunk_id')
                        FROM json_array_elements(COALESCE(current_values.citations, '[]'::json)) AS citation
                        WHERE NULLIF(citation->>'chunk_id', '') IS NOT NULL
                    ),
                    '[]'::json
                )
            )
        )
    END,
    last_checked_at = COALESCE(current_values.created_at, pinned_fact.updated_at, pinned_fact.created_at)
FROM current_values
WHERE current_values.tracked_field_id = pinned_fact.id;

UPDATE public.pinned_facts
SET evidence = COALESCE(evidence, '[]'::json),
    last_checked_at = COALESCE(last_checked_at, updated_at, created_at);

ALTER TABLE public.pinned_facts
    ADD CONSTRAINT pinned_facts_source_document_id_fkey
    FOREIGN KEY (source_document_id) REFERENCES public.documents(id) ON DELETE SET NULL;

CREATE INDEX ix_pinned_facts_status ON public.pinned_facts USING btree (status);

ALTER TABLE public.change_events RENAME COLUMN tracked_field_id TO pinned_fact_id;
ALTER TABLE public.change_events RENAME CONSTRAINT change_events_tracked_field_id_fkey TO change_events_pinned_fact_id_fkey;
ALTER INDEX public.ix_change_events_tracked_field_id RENAME TO ix_change_events_pinned_fact_id;

ALTER TABLE public.correction_records RENAME COLUMN tracked_field_id TO pinned_fact_id;
ALTER TABLE public.correction_records RENAME CONSTRAINT correction_records_tracked_field_id_fkey TO correction_records_pinned_fact_id_fkey;
ALTER INDEX public.ix_correction_records_tracked_field_id RENAME TO ix_correction_records_pinned_fact_id;

CREATE TABLE public.pinned_fact_candidates (
    id uuid NOT NULL,
    pinned_fact_id uuid NOT NULL,
    space_id uuid NOT NULL,
    source_document_id uuid,
    proposed_value_kind character varying(16) NOT NULL,
    proposed_value_text text,
    proposed_value_json json,
    change_type character varying(32) NOT NULL,
    confidence double precision,
    evidence json,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    idempotency_key character varying(255) NOT NULL,
    review_notes text,
    reviewed_by uuid,
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.pinned_fact_history (
    id uuid NOT NULL,
    pinned_fact_id uuid NOT NULL,
    space_id uuid NOT NULL,
    candidate_id uuid,
    restored_from_history_id uuid,
    actor_user_id uuid,
    actor_type character varying(32) DEFAULT 'system'::character varying NOT NULL,
    reason character varying(64) NOT NULL,
    old_value_kind character varying(16),
    old_value_text text,
    old_value_json json,
    new_value_kind character varying(16) NOT NULL,
    new_value_text text,
    new_value_json json,
    old_evidence json,
    new_evidence json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.pinned_fact_candidates
    ADD CONSTRAINT pinned_fact_candidates_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pinned_fact_history
    ADD CONSTRAINT pinned_fact_history_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pinned_fact_candidates
    ADD CONSTRAINT ux_pinned_fact_candidates_fact_idempotency UNIQUE (pinned_fact_id, idempotency_key);

CREATE INDEX ix_pinned_fact_candidates_pinned_fact_id ON public.pinned_fact_candidates USING btree (pinned_fact_id);
CREATE INDEX ix_pinned_fact_candidates_space_id ON public.pinned_fact_candidates USING btree (space_id);
CREATE INDEX ix_pinned_fact_candidates_source_document_id ON public.pinned_fact_candidates USING btree (source_document_id);
CREATE INDEX ix_pinned_fact_candidates_status ON public.pinned_fact_candidates USING btree (status);
CREATE INDEX ix_pinned_fact_history_pinned_fact_id ON public.pinned_fact_history USING btree (pinned_fact_id);
CREATE INDEX ix_pinned_fact_history_space_id ON public.pinned_fact_history USING btree (space_id);
CREATE INDEX ix_pinned_fact_history_created_at ON public.pinned_fact_history USING btree (created_at);

ALTER TABLE ONLY public.pinned_fact_candidates
    ADD CONSTRAINT pinned_fact_candidates_pinned_fact_id_fkey FOREIGN KEY (pinned_fact_id) REFERENCES public.pinned_facts(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.pinned_fact_candidates
    ADD CONSTRAINT pinned_fact_candidates_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.pinned_fact_candidates
    ADD CONSTRAINT pinned_fact_candidates_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES public.documents(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.pinned_fact_candidates
    ADD CONSTRAINT pinned_fact_candidates_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.pinned_fact_history
    ADD CONSTRAINT pinned_fact_history_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.pinned_fact_history
    ADD CONSTRAINT pinned_fact_history_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.pinned_fact_candidates(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.pinned_fact_history
    ADD CONSTRAINT pinned_fact_history_pinned_fact_id_fkey FOREIGN KEY (pinned_fact_id) REFERENCES public.pinned_facts(id) ON DELETE CASCADE;
ALTER TABLE ONLY public.pinned_fact_history
    ADD CONSTRAINT pinned_fact_history_restored_from_history_id_fkey FOREIGN KEY (restored_from_history_id) REFERENCES public.pinned_fact_history(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.pinned_fact_history
    ADD CONSTRAINT pinned_fact_history_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;

WITH ordered_values AS (
    SELECT
        tracked_field_values.id,
        tracked_field_values.tracked_field_id,
        tracked_field_values.space_id,
        tracked_field_values.resolved_from_correction_id,
        tracked_field_values.value_text,
        tracked_field_values.citations,
        tracked_field_values.created_at,
        ROW_NUMBER() OVER (
            PARTITION BY tracked_field_values.tracked_field_id
            ORDER BY tracked_field_values.created_at ASC, tracked_field_values.id ASC
        ) AS history_rank,
        LAG(tracked_field_values.value_text) OVER (
            PARTITION BY tracked_field_values.tracked_field_id
            ORDER BY tracked_field_values.created_at ASC, tracked_field_values.id ASC
        ) AS old_value_text,
        LAG(tracked_field_values.citations) OVER (
            PARTITION BY tracked_field_values.tracked_field_id
            ORDER BY tracked_field_values.created_at ASC, tracked_field_values.id ASC
        ) AS old_citations
    FROM public.tracked_field_values
)
INSERT INTO public.pinned_fact_history (
    id,
    pinned_fact_id,
    space_id,
    candidate_id,
    restored_from_history_id,
    actor_user_id,
    actor_type,
    reason,
    old_value_kind,
    old_value_text,
    old_value_json,
    new_value_kind,
    new_value_text,
    new_value_json,
    old_evidence,
    new_evidence,
    created_at
)
SELECT
    ordered_values.id,
    ordered_values.tracked_field_id,
    ordered_values.space_id,
    NULL,
    NULL,
    COALESCE(correction.reviewed_by, correction.submitted_by),
    CASE
        WHEN ordered_values.resolved_from_correction_id IS NOT NULL THEN 'user'
        ELSE 'system'
    END,
    CASE
        WHEN ordered_values.history_rank = 1 THEN 'migrated_created'
        WHEN ordered_values.resolved_from_correction_id IS NOT NULL THEN 'migrated_verified_correction'
        ELSE 'migrated_update'
    END,
    CASE
        WHEN ordered_values.old_value_text IS NULL THEN NULL
        ELSE 'text'
    END,
    ordered_values.old_value_text,
    NULL,
    'text',
    ordered_values.value_text,
    NULL,
    CASE
        WHEN ordered_values.old_value_text IS NULL THEN '[]'::json
        ELSE json_build_array(
            json_build_object(
                'quote',
                ordered_values.old_value_text,
                'citations',
                COALESCE(ordered_values.old_citations, '[]'::json),
                'source_chunk_ids',
                COALESCE(
                    (
                        SELECT json_agg(citation->>'chunk_id')
                        FROM json_array_elements(COALESCE(ordered_values.old_citations, '[]'::json)) AS citation
                        WHERE NULLIF(citation->>'chunk_id', '') IS NOT NULL
                    ),
                    '[]'::json
                )
            )
        )
    END,
    json_build_array(
        json_build_object(
            'quote',
            ordered_values.value_text,
            'citations',
            COALESCE(ordered_values.citations, '[]'::json),
            'source_chunk_ids',
            COALESCE(
                (
                    SELECT json_agg(citation->>'chunk_id')
                    FROM json_array_elements(COALESCE(ordered_values.citations, '[]'::json)) AS citation
                    WHERE NULLIF(citation->>'chunk_id', '') IS NOT NULL
                ),
                '[]'::json
            )
        )
    ),
    ordered_values.created_at
FROM ordered_values
LEFT JOIN public.correction_records AS correction
    ON correction.id = ordered_values.resolved_from_correction_id;

INSERT INTO public.pinned_fact_candidates (
    id,
    pinned_fact_id,
    space_id,
    source_document_id,
    proposed_value_kind,
    proposed_value_text,
    proposed_value_json,
    change_type,
    confidence,
    evidence,
    status,
    idempotency_key,
    review_notes,
    reviewed_by,
    reviewed_at,
    created_at
)
SELECT
    correction.id,
    correction.pinned_fact_id,
    correction.space_id,
    correction.document_id,
    'text',
    correction.proposed_value,
    NULL,
    'update',
    NULL,
    json_build_array(
        json_build_object(
            'quote',
            COALESCE(NULLIF(correction.locator_text, ''), correction.proposed_value),
            'citations',
            '[]'::json,
            'source_chunk_ids',
            '[]'::json
        )
    ),
    'pending',
    'legacy-pending-correction:' || correction.id::text,
    NULL,
    NULL,
    NULL,
    correction.created_at
FROM public.correction_records AS correction
WHERE correction.pinned_fact_id IS NOT NULL
  AND correction.status = 'pending';

DROP TABLE public.tracked_field_values;

-- migrate:down

CREATE TABLE public.tracked_field_values (
    id uuid NOT NULL,
    tracked_field_id uuid NOT NULL,
    space_id uuid NOT NULL,
    resolved_from_correction_id uuid,
    source_tier character varying(32) NOT NULL,
    value_text text NOT NULL,
    citations json,
    is_current boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_pkey PRIMARY KEY (id);

CREATE INDEX ix_tracked_field_values_created_at ON public.tracked_field_values USING btree (created_at);
CREATE INDEX ix_tracked_field_values_space_id ON public.tracked_field_values USING btree (space_id);
CREATE INDEX ix_tracked_field_values_tracked_field_id ON public.tracked_field_values USING btree (tracked_field_id);
CREATE UNIQUE INDEX ux_tracked_field_values_current_per_field ON public.tracked_field_values USING btree (tracked_field_id) WHERE is_current;

WITH ranked_history AS (
    SELECT
        pinned_fact_history.*,
        ROW_NUMBER() OVER (
            PARTITION BY pinned_fact_history.pinned_fact_id
            ORDER BY pinned_fact_history.created_at DESC, pinned_fact_history.id DESC
        ) AS current_rank
    FROM public.pinned_fact_history
)
INSERT INTO public.tracked_field_values (
    id,
    tracked_field_id,
    space_id,
    resolved_from_correction_id,
    source_tier,
    value_text,
    citations,
    is_current,
    created_at
)
SELECT
    ranked_history.id,
    ranked_history.pinned_fact_id,
    ranked_history.space_id,
    NULL,
    CASE
        WHEN ranked_history.reason IN ('verified_correction', 'migrated_verified_correction') THEN 'verified'
        WHEN ranked_history.actor_type = 'user' THEN 'user'
        ELSE 'document'
    END,
    COALESCE(ranked_history.new_value_text, ranked_history.new_value_json::text),
    COALESCE(ranked_history.new_evidence->0->'citations', '[]'::json),
    ranked_history.current_rank = 1,
    ranked_history.created_at
FROM ranked_history;

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_resolved_from_correction_id_fkey FOREIGN KEY (resolved_from_correction_id) REFERENCES public.correction_records(id) ON DELETE SET NULL;
ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;

DROP TABLE public.pinned_fact_history;
DROP TABLE public.pinned_fact_candidates;

DROP INDEX public.ix_pinned_facts_status;
ALTER TABLE public.pinned_facts DROP CONSTRAINT pinned_facts_source_document_id_fkey;
ALTER TABLE public.pinned_facts
    DROP COLUMN last_checked_at,
    DROP COLUMN evidence,
    DROP COLUMN source_document_id,
    DROP COLUMN confidence,
    DROP COLUMN status,
    DROP COLUMN value_json,
    DROP COLUMN value_text,
    DROP COLUMN value_kind;

ALTER TABLE public.change_events RENAME COLUMN pinned_fact_id TO tracked_field_id;
ALTER TABLE public.change_events RENAME CONSTRAINT change_events_pinned_fact_id_fkey TO change_events_tracked_field_id_fkey;
ALTER INDEX public.ix_change_events_pinned_fact_id RENAME TO ix_change_events_tracked_field_id;

ALTER TABLE public.correction_records RENAME COLUMN pinned_fact_id TO tracked_field_id;
ALTER TABLE public.correction_records RENAME CONSTRAINT correction_records_pinned_fact_id_fkey TO correction_records_tracked_field_id_fkey;
ALTER INDEX public.ix_correction_records_pinned_fact_id RENAME TO ix_correction_records_tracked_field_id;

ALTER TABLE public.pinned_facts RENAME CONSTRAINT pinned_facts_pkey TO tracked_fields_pkey;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT ux_pinned_facts_space_key TO ux_tracked_fields_space_key;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT pinned_facts_owner_user_id_fkey TO tracked_fields_owner_user_id_fkey;
ALTER TABLE public.pinned_facts RENAME CONSTRAINT pinned_facts_space_id_fkey TO tracked_fields_space_id_fkey;
ALTER INDEX public.ix_pinned_facts_is_active RENAME TO ix_tracked_fields_is_active;
ALTER INDEX public.ix_pinned_facts_owner_user_id RENAME TO ix_tracked_fields_owner_user_id;
ALTER INDEX public.ix_pinned_facts_space_id RENAME TO ix_tracked_fields_space_id;
ALTER TABLE public.pinned_facts RENAME COLUMN title TO label;
ALTER TABLE public.pinned_facts RENAME COLUMN description TO prompt;
ALTER TABLE public.pinned_facts RENAME TO tracked_fields;

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_tracked_field_id_fkey FOREIGN KEY (tracked_field_id) REFERENCES public.tracked_fields(id) ON DELETE CASCADE;
