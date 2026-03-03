-- =============================================================================
-- init-db.sql
-- Bootstrap script executed once when the PostgreSQL container first starts.
-- Run by docker-compose via the postgres service's initdb entrypoint.
--
-- This script only handles infrastructure-level setup that must exist before
-- Alembic migrations run (extensions, schemas, roles).  Table DDL lives in
-- migrations/versions/ and is applied separately with: alembic upgrade head
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------

-- pgvector: vector similarity search (cosine, L2, inner-product)
CREATE EXTENSION IF NOT EXISTS vector;

-- pgcrypto: gen_random_uuid() used as a server-side default in tables
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Schemas
-- ---------------------------------------------------------------------------

-- Hub schema: shared resources visible across all spokes
--   (organizations, users, knowledge_base, …)
CREATE SCHEMA IF NOT EXISTS hub;

-- Spokes schema: domain-specific tables created by individual spoke services
CREATE SCHEMA IF NOT EXISTS spokes;

-- ---------------------------------------------------------------------------
-- Application role (least-privilege)
-- ---------------------------------------------------------------------------
-- The app connects as 'hub_app' so that FORCE ROW LEVEL SECURITY applies
-- to its connections without needing BYPASSRLS.
-- In docker-compose the superuser 'postgres' is used for convenience;
-- uncomment the block below when hardening for production.

-- DO $$
-- BEGIN
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hub_app') THEN
--     CREATE ROLE hub_app WITH LOGIN PASSWORD 'changeme';
--   END IF;
-- END $$;
--
-- GRANT CONNECT ON DATABASE hubdb TO hub_app;
-- GRANT USAGE ON SCHEMA hub, spokes TO hub_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA hub TO hub_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA spokes TO hub_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA hub
--   GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hub_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA spokes
--   GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hub_app;
