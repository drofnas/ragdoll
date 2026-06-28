-- migrate:up

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE public.canonical_entities (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    entity_type character varying(80) NOT NULL,
    normalized_name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: change_event_reads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_event_reads (
    id uuid NOT NULL,
    change_event_id uuid NOT NULL,
    user_id uuid NOT NULL,
    read_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: change_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_events (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    actor_user_id uuid,
    document_id uuid,
    tracked_field_id uuid,
    correction_id uuid,
    chat_session_id uuid,
    event_type character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    summary text NOT NULL,
    payload json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_messages (
    id uuid NOT NULL,
    session_id uuid NOT NULL,
    space_id uuid NOT NULL,
    author_user_id uuid,
    role character varying(32) NOT NULL,
    content text NOT NULL,
    citations json,
    suggestions json,
    retrieval_mode character varying(32),
    degraded boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    evidence json
);


--
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_sessions (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    owner_user_id uuid NOT NULL,
    title character varying(255) DEFAULT 'New chat'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    document_id uuid
);


--
-- Name: correction_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.correction_records (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    submitted_by uuid NOT NULL,
    chat_session_id uuid,
    chat_message_id uuid,
    tracked_field_id uuid,
    document_id uuid,
    entity_id uuid,
    locator_text text,
    proposed_value text NOT NULL,
    rationale text,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    review_notes text,
    reviewed_by uuid,
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_chunk_vectors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_chunk_vectors (
    chunk_id uuid NOT NULL,
    document_id uuid NOT NULL,
    space_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    checksum character varying(64) NOT NULL,
    embedding_model character varying(120) NOT NULL,
    embedding_dimensions integer NOT NULL,
    embedding public.vector(768) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_chunks (
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    space_id uuid NOT NULL,
    chunk_index integer NOT NULL,
    text_content text NOT NULL,
    text_preview text NOT NULL,
    checksum character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    start_line integer DEFAULT 1 NOT NULL
);


--
-- Name: document_processing_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_processing_jobs (
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    space_id uuid NOT NULL,
    uploaded_by uuid NOT NULL,
    requested_stage character varying(32) DEFAULT 'parsing'::character varying NOT NULL,
    status character varying(32) DEFAULT 'queued'::character varying NOT NULL,
    attempt integer DEFAULT 1 NOT NULL,
    visible_error_detail text,
    queued_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    job_kind character varying(32) DEFAULT 'upload'::character varying NOT NULL,
    cleanup_derived_artifacts boolean DEFAULT false NOT NULL,
    reset_document_content boolean DEFAULT false NOT NULL,
    clear_existing_chunks boolean DEFAULT false NOT NULL,
    clear_existing_entities boolean DEFAULT false NOT NULL,
    cleanup_vectors boolean DEFAULT false NOT NULL,
    cleanup_graph boolean DEFAULT false NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    uploaded_by uuid NOT NULL,
    title character varying(255) NOT NULL,
    original_filename character varying(255) NOT NULL,
    mime_type character varying(255) NOT NULL,
    file_type character varying(32) NOT NULL,
    file_size integer DEFAULT 0 NOT NULL,
    storage_key character varying(500) NOT NULL,
    source_kind character varying(32) DEFAULT 'manual_upload'::character varying NOT NULL,
    source_label character varying(500),
    preview_text text,
    original_text_content text,
    processing_status json NOT NULL,
    chunk_count integer DEFAULT 0 NOT NULL,
    indexed_chunk_count integer DEFAULT 0 NOT NULL,
    deleted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entities (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    document_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    canonical_entity_id uuid NOT NULL,
    entity_type character varying(80) NOT NULL,
    surface_text character varying(255) NOT NULL,
    normalized_name character varying(255) NOT NULL,
    confidence_score double precision,
    extraction_model character varying(120),
    extraction_metadata json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: graph_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_edges (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    document_id uuid NOT NULL,
    chunk_id uuid NOT NULL,
    source_node_id uuid NOT NULL,
    target_node_id uuid NOT NULL,
    relation_type character varying(80) DEFAULT 'co_occurs'::character varying NOT NULL,
    provenance_locator text NOT NULL,
    weight double precision DEFAULT '1'::double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: graph_nodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.graph_nodes (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    canonical_entity_id uuid NOT NULL,
    node_type character varying(80) NOT NULL,
    label character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: spaces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.spaces (
    id uuid NOT NULL,
    owner_user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_default boolean DEFAULT false NOT NULL,
    archived_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: tracked_field_values; Type: TABLE; Schema: public; Owner: -
--

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


--
-- Name: tracked_fields; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tracked_fields (
    id uuid NOT NULL,
    space_id uuid NOT NULL,
    owner_user_id uuid NOT NULL,
    key character varying(120) NOT NULL,
    label character varying(255) NOT NULL,
    prompt text NOT NULL,
    entity_type_hint character varying(80),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: usage_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usage_events (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    event_type character varying(64) NOT NULL,
    quantity bigint DEFAULT '0'::bigint NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    document_id uuid,
    space_id uuid,
    event_metadata json
);


--
-- Name: user_usage_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_usage_snapshots (
    user_id uuid NOT NULL,
    document_count integer DEFAULT 0 NOT NULL,
    chunk_count integer DEFAULT 0 NOT NULL,
    storage_bytes bigint DEFAULT '0'::bigint NOT NULL,
    tokens_5h bigint DEFAULT '0'::bigint NOT NULL,
    tokens_week bigint DEFAULT '0'::bigint NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255),
    is_active boolean DEFAULT true NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    must_change_password boolean DEFAULT false NOT NULL,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_entities canonical_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_entities
    ADD CONSTRAINT canonical_entities_pkey PRIMARY KEY (id);


--
-- Name: change_event_reads change_event_reads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_event_reads
    ADD CONSTRAINT change_event_reads_pkey PRIMARY KEY (id);


--
-- Name: change_events change_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: correction_records correction_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_pkey PRIMARY KEY (id);


--
-- Name: document_chunk_vectors document_chunk_vectors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunk_vectors
    ADD CONSTRAINT document_chunk_vectors_pkey PRIMARY KEY (chunk_id);


--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- Name: document_processing_jobs document_processing_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs
    ADD CONSTRAINT document_processing_jobs_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: entities entities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_pkey PRIMARY KEY (id);


--
-- Name: graph_edges graph_edges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT graph_edges_pkey PRIMARY KEY (id);


--
-- Name: graph_nodes graph_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_nodes
    ADD CONSTRAINT graph_nodes_pkey PRIMARY KEY (id);


--
-- Name: spaces spaces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT spaces_pkey PRIMARY KEY (id);


--
-- Name: tracked_field_values tracked_field_values_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_pkey PRIMARY KEY (id);


--
-- Name: tracked_fields tracked_fields_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_fields
    ADD CONSTRAINT tracked_fields_pkey PRIMARY KEY (id);


--
-- Name: usage_events usage_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_pkey PRIMARY KEY (id);


--
-- Name: user_usage_snapshots user_usage_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage_snapshots
    ADD CONSTRAINT user_usage_snapshots_pkey PRIMARY KEY (user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: canonical_entities ux_canonical_entities_space_type_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_entities
    ADD CONSTRAINT ux_canonical_entities_space_type_name UNIQUE (space_id, entity_type, normalized_name);


--
-- Name: change_event_reads ux_change_event_reads_event_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_event_reads
    ADD CONSTRAINT ux_change_event_reads_event_user UNIQUE (change_event_id, user_id);


--
-- Name: document_chunks ux_document_chunks_document_chunk_index; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT ux_document_chunks_document_chunk_index UNIQUE (document_id, chunk_index);


--
-- Name: graph_edges ux_graph_edges_document_chunk_relation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT ux_graph_edges_document_chunk_relation UNIQUE (document_id, chunk_id, source_node_id, target_node_id, relation_type);


--
-- Name: graph_nodes ux_graph_nodes_canonical_entity_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_nodes
    ADD CONSTRAINT ux_graph_nodes_canonical_entity_id UNIQUE (canonical_entity_id);


--
-- Name: tracked_fields ux_tracked_fields_space_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_fields
    ADD CONSTRAINT ux_tracked_fields_space_key UNIQUE (space_id, key);


--
-- Name: ix_canonical_entities_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_entities_space_id ON public.canonical_entities USING btree (space_id);


--
-- Name: ix_change_event_reads_change_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_event_reads_change_event_id ON public.change_event_reads USING btree (change_event_id);


--
-- Name: ix_change_event_reads_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_event_reads_user_id ON public.change_event_reads USING btree (user_id);


--
-- Name: ix_change_events_correction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_events_correction_id ON public.change_events USING btree (correction_id);


--
-- Name: ix_change_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_events_created_at ON public.change_events USING btree (created_at);


--
-- Name: ix_change_events_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_events_document_id ON public.change_events USING btree (document_id);


--
-- Name: ix_change_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_events_event_type ON public.change_events USING btree (event_type);


--
-- Name: ix_change_events_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_events_space_id ON public.change_events USING btree (space_id);


--
-- Name: ix_change_events_tracked_field_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_events_tracked_field_id ON public.change_events USING btree (tracked_field_id);


--
-- Name: ix_chat_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_created_at ON public.chat_messages USING btree (created_at);


--
-- Name: ix_chat_messages_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_session_id ON public.chat_messages USING btree (session_id);


--
-- Name: ix_chat_messages_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_space_id ON public.chat_messages USING btree (space_id);


--
-- Name: ix_chat_sessions_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_sessions_document_id ON public.chat_sessions USING btree (document_id);


--
-- Name: ix_chat_sessions_owner_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_sessions_owner_user_id ON public.chat_sessions USING btree (owner_user_id);


--
-- Name: ix_chat_sessions_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_sessions_space_id ON public.chat_sessions USING btree (space_id);


--
-- Name: ix_chat_sessions_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_sessions_updated_at ON public.chat_sessions USING btree (updated_at);


--
-- Name: ix_correction_records_chat_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correction_records_chat_session_id ON public.correction_records USING btree (chat_session_id);


--
-- Name: ix_correction_records_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correction_records_document_id ON public.correction_records USING btree (document_id);


--
-- Name: ix_correction_records_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correction_records_entity_id ON public.correction_records USING btree (entity_id);


--
-- Name: ix_correction_records_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correction_records_space_id ON public.correction_records USING btree (space_id);


--
-- Name: ix_correction_records_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correction_records_status ON public.correction_records USING btree (status);


--
-- Name: ix_correction_records_tracked_field_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_correction_records_tracked_field_id ON public.correction_records USING btree (tracked_field_id);


--
-- Name: ix_document_chunk_vectors_chunk_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_chunk_vectors_chunk_index ON public.document_chunk_vectors USING btree (chunk_index);


--
-- Name: ix_document_chunk_vectors_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_chunk_vectors_document_id ON public.document_chunk_vectors USING btree (document_id);


--
-- Name: ix_document_chunk_vectors_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_chunk_vectors_space_id ON public.document_chunk_vectors USING btree (space_id);


--
-- Name: ix_document_chunks_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_chunks_document_id ON public.document_chunks USING btree (document_id);


--
-- Name: ix_document_chunks_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_chunks_space_id ON public.document_chunks USING btree (space_id);


--
-- Name: ix_document_processing_jobs_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_processing_jobs_document_id ON public.document_processing_jobs USING btree (document_id);


--
-- Name: ix_document_processing_jobs_status_queued_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_processing_jobs_status_queued_at ON public.document_processing_jobs USING btree (status, queued_at);


--
-- Name: ix_document_processing_jobs_uploaded_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_processing_jobs_uploaded_by ON public.document_processing_jobs USING btree (uploaded_by);


--
-- Name: ix_documents_active_space_uploaded_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_active_space_uploaded_at ON public.documents USING btree (space_id, created_at) WHERE (deleted_at IS NULL);


--
-- Name: ix_documents_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_deleted_at ON public.documents USING btree (deleted_at);


--
-- Name: ix_documents_file_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_file_type ON public.documents USING btree (file_type);


--
-- Name: ix_documents_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_space_id ON public.documents USING btree (space_id);


--
-- Name: ix_documents_uploaded_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_uploaded_at ON public.documents USING btree (created_at);


--
-- Name: ix_documents_uploaded_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_uploaded_by ON public.documents USING btree (uploaded_by);


--
-- Name: ix_entities_canonical_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entities_canonical_entity_id ON public.entities USING btree (canonical_entity_id);


--
-- Name: ix_entities_chunk_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entities_chunk_id ON public.entities USING btree (chunk_id);


--
-- Name: ix_entities_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entities_document_id ON public.entities USING btree (document_id);


--
-- Name: ix_entities_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entities_space_id ON public.entities USING btree (space_id);


--
-- Name: ix_graph_edges_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_graph_edges_document_id ON public.graph_edges USING btree (document_id);


--
-- Name: ix_graph_edges_source_node_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_graph_edges_source_node_id ON public.graph_edges USING btree (source_node_id);


--
-- Name: ix_graph_edges_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_graph_edges_space_id ON public.graph_edges USING btree (space_id);


--
-- Name: ix_graph_edges_target_node_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_graph_edges_target_node_id ON public.graph_edges USING btree (target_node_id);


--
-- Name: ix_graph_nodes_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_graph_nodes_space_id ON public.graph_nodes USING btree (space_id);


--
-- Name: ix_spaces_archived_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_spaces_archived_at ON public.spaces USING btree (archived_at);


--
-- Name: ix_spaces_owner_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_spaces_owner_user_id ON public.spaces USING btree (owner_user_id);


--
-- Name: ix_tracked_field_values_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tracked_field_values_created_at ON public.tracked_field_values USING btree (created_at);


--
-- Name: ix_tracked_field_values_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tracked_field_values_space_id ON public.tracked_field_values USING btree (space_id);


--
-- Name: ix_tracked_field_values_tracked_field_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tracked_field_values_tracked_field_id ON public.tracked_field_values USING btree (tracked_field_id);


--
-- Name: ix_tracked_fields_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tracked_fields_is_active ON public.tracked_fields USING btree (is_active);


--
-- Name: ix_tracked_fields_owner_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tracked_fields_owner_user_id ON public.tracked_fields USING btree (owner_user_id);


--
-- Name: ix_tracked_fields_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tracked_fields_space_id ON public.tracked_fields USING btree (space_id);


--
-- Name: ix_usage_events_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_document_id ON public.usage_events USING btree (document_id);


--
-- Name: ix_usage_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_event_type ON public.usage_events USING btree (event_type);


--
-- Name: ix_usage_events_occurred_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_occurred_at ON public.usage_events USING btree (occurred_at);


--
-- Name: ix_usage_events_space_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_space_id ON public.usage_events USING btree (space_id);


--
-- Name: ix_usage_events_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usage_events_user_id ON public.usage_events USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ux_spaces_default_per_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_spaces_default_per_owner ON public.spaces USING btree (owner_user_id) WHERE is_default;


--
-- Name: ux_tracked_field_values_current_per_field; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_tracked_field_values_current_per_field ON public.tracked_field_values USING btree (tracked_field_id) WHERE is_current;


--
-- Name: canonical_entities canonical_entities_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_entities
    ADD CONSTRAINT canonical_entities_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: change_event_reads change_event_reads_change_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_event_reads
    ADD CONSTRAINT change_event_reads_change_event_id_fkey FOREIGN KEY (change_event_id) REFERENCES public.change_events(id) ON DELETE CASCADE;


--
-- Name: change_event_reads change_event_reads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_event_reads
    ADD CONSTRAINT change_event_reads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: change_events change_events_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: change_events change_events_chat_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_chat_session_id_fkey FOREIGN KEY (chat_session_id) REFERENCES public.chat_sessions(id) ON DELETE SET NULL;


--
-- Name: change_events change_events_correction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_correction_id_fkey FOREIGN KEY (correction_id) REFERENCES public.correction_records(id) ON DELETE SET NULL;


--
-- Name: change_events change_events_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: change_events change_events_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: change_events change_events_tracked_field_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_events
    ADD CONSTRAINT change_events_tracked_field_id_fkey FOREIGN KEY (tracked_field_id) REFERENCES public.tracked_fields(id) ON DELETE SET NULL;


--
-- Name: chat_messages chat_messages_author_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: chat_messages chat_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: chat_sessions chat_sessions_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chat_sessions chat_sessions_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: correction_records correction_records_chat_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_chat_message_id_fkey FOREIGN KEY (chat_message_id) REFERENCES public.chat_messages(id) ON DELETE SET NULL;


--
-- Name: correction_records correction_records_chat_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_chat_session_id_fkey FOREIGN KEY (chat_session_id) REFERENCES public.chat_sessions(id) ON DELETE SET NULL;


--
-- Name: correction_records correction_records_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: correction_records correction_records_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES public.canonical_entities(id) ON DELETE SET NULL;


--
-- Name: correction_records correction_records_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: correction_records correction_records_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: correction_records correction_records_submitted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_submitted_by_fkey FOREIGN KEY (submitted_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: correction_records correction_records_tracked_field_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correction_records
    ADD CONSTRAINT correction_records_tracked_field_id_fkey FOREIGN KEY (tracked_field_id) REFERENCES public.tracked_fields(id) ON DELETE SET NULL;


--
-- Name: document_chunk_vectors document_chunk_vectors_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunk_vectors
    ADD CONSTRAINT document_chunk_vectors_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id) ON DELETE CASCADE;


--
-- Name: document_chunk_vectors document_chunk_vectors_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunk_vectors
    ADD CONSTRAINT document_chunk_vectors_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_chunk_vectors document_chunk_vectors_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunk_vectors
    ADD CONSTRAINT document_chunk_vectors_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: document_chunks document_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_chunks document_chunks_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: document_processing_jobs document_processing_jobs_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs
    ADD CONSTRAINT document_processing_jobs_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: document_processing_jobs document_processing_jobs_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs
    ADD CONSTRAINT document_processing_jobs_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: document_processing_jobs document_processing_jobs_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_processing_jobs
    ADD CONSTRAINT document_processing_jobs_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: documents documents_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: documents documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: entities entities_canonical_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_canonical_entity_id_fkey FOREIGN KEY (canonical_entity_id) REFERENCES public.canonical_entities(id) ON DELETE CASCADE;


--
-- Name: entities entities_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id) ON DELETE CASCADE;


--
-- Name: entities entities_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: entities entities_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: chat_sessions fk_chat_sessions_document_id_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT fk_chat_sessions_document_id_documents FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: graph_edges graph_edges_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT graph_edges_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id) ON DELETE CASCADE;


--
-- Name: graph_edges graph_edges_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT graph_edges_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- Name: graph_edges graph_edges_source_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT graph_edges_source_node_id_fkey FOREIGN KEY (source_node_id) REFERENCES public.graph_nodes(id) ON DELETE CASCADE;


--
-- Name: graph_edges graph_edges_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT graph_edges_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: graph_edges graph_edges_target_node_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_edges
    ADD CONSTRAINT graph_edges_target_node_id_fkey FOREIGN KEY (target_node_id) REFERENCES public.graph_nodes(id) ON DELETE CASCADE;


--
-- Name: graph_nodes graph_nodes_canonical_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_nodes
    ADD CONSTRAINT graph_nodes_canonical_entity_id_fkey FOREIGN KEY (canonical_entity_id) REFERENCES public.canonical_entities(id) ON DELETE CASCADE;


--
-- Name: graph_nodes graph_nodes_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.graph_nodes
    ADD CONSTRAINT graph_nodes_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: spaces spaces_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spaces
    ADD CONSTRAINT spaces_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tracked_field_values tracked_field_values_resolved_from_correction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_resolved_from_correction_id_fkey FOREIGN KEY (resolved_from_correction_id) REFERENCES public.correction_records(id) ON DELETE SET NULL;


--
-- Name: tracked_field_values tracked_field_values_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: tracked_field_values tracked_field_values_tracked_field_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_field_values
    ADD CONSTRAINT tracked_field_values_tracked_field_id_fkey FOREIGN KEY (tracked_field_id) REFERENCES public.tracked_fields(id) ON DELETE CASCADE;


--
-- Name: tracked_fields tracked_fields_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_fields
    ADD CONSTRAINT tracked_fields_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tracked_fields tracked_fields_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracked_fields
    ADD CONSTRAINT tracked_fields_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE CASCADE;


--
-- Name: usage_events usage_events_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- Name: usage_events usage_events_space_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_space_id_fkey FOREIGN KEY (space_id) REFERENCES public.spaces(id) ON DELETE SET NULL;


--
-- Name: usage_events usage_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usage_events
    ADD CONSTRAINT usage_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_usage_snapshots user_usage_snapshots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage_snapshots
    ADD CONSTRAINT user_usage_snapshots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--

-- migrate:down
DROP TABLE IF EXISTS public.change_event_reads CASCADE;
DROP TABLE IF EXISTS public.change_events CASCADE;
DROP TABLE IF EXISTS public.tracked_field_values CASCADE;
DROP TABLE IF EXISTS public.correction_records CASCADE;
DROP TABLE IF EXISTS public.chat_messages CASCADE;
DROP TABLE IF EXISTS public.tracked_fields CASCADE;
DROP TABLE IF EXISTS public.graph_edges CASCADE;
DROP TABLE IF EXISTS public.graph_nodes CASCADE;
DROP TABLE IF EXISTS public.entities CASCADE;
DROP TABLE IF EXISTS public.canonical_entities CASCADE;
DROP TABLE IF EXISTS public.document_chunk_vectors CASCADE;
DROP TABLE IF EXISTS public.document_processing_jobs CASCADE;
DROP TABLE IF EXISTS public.user_usage_snapshots CASCADE;
DROP TABLE IF EXISTS public.usage_events CASCADE;
DROP TABLE IF EXISTS public.chat_sessions CASCADE;
DROP TABLE IF EXISTS public.document_chunks CASCADE;
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.spaces CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
