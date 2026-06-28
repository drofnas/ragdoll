# `apps/api/db`

Canonical DBmate home for `apps/api`.

- `migrations/` holds ordered SQL migrations applied by DBmate.
- `schema.sql` is the checked-in schema snapshot generated from those migrations.
- Supabase-managed schemas stay upstream-owned; these files cover only app-owned `public` objects.
