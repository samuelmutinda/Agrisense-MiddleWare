-- =============================================================================
-- PostgreSQL init script – runs ONCE on first docker-compose up
-- Creates additional databases required by the stack.
-- The default "agrisense" DB is already created by POSTGRES_DB env var.
-- =============================================================================

-- Database for ChirpStack Network Server
CREATE DATABASE chirpstack_ns WITH OWNER agrisense;

-- Extensions needed by ChirpStack
\c chirpstack_ns
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS hstore;

-- Switch back to the agrisense database and enable useful extensions
\c agrisense
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
