-- Runs once, only when the Postgres data directory is first created.
-- Migrations (Alembic) should also ensure these exist, so CI and production
-- don't depend on this file — but for local dev it removes a manual step.

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector: embeddings + `<=>` cosine operator
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- lets EXCLUDE constraints mix `=` and range `&&`
