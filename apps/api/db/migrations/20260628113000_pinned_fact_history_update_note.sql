-- migrate:up

ALTER TABLE public.pinned_fact_history
    ADD COLUMN update_note text;

-- migrate:down

ALTER TABLE public.pinned_fact_history
    DROP COLUMN update_note;
