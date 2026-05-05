-- ╔══════════════════════════════════════════════════════════════════════════════╗
-- ║ KOREV EVIDENCE — Postgres init script (P0 — Migration RDBMS)                ║
-- ║                                                                              ║
-- ║ Exécuté UNE SEULE FOIS au premier démarrage du conteneur Postgres            ║
-- ║ (cf. docker-entrypoint-initdb.d/, image pgvector/pgvector:pg16 — Postgres   ║
-- ║ 16 officiel + extension pgvector pré-installée par l'image upstream).        ║
-- ║                                                                              ║
-- ║ Objectif P0 : préparer le SGBD à recevoir les schémas applicatifs (P1+).    ║
-- ║ Ce script ne crée AUCUNE table métier — il pose seulement les fondations.   ║
-- ╚══════════════════════════════════════════════════════════════════════════════╝

-- Extensions requises
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid(), digest()
CREATE EXTENSION IF NOT EXISTS vector;       -- pgvector — embeddings FAISS → SQL (P3)
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- recherche texte trigram (legal_index migration P5)

-- Schémas logiques (cloisonnement par domaine)
CREATE SCHEMA IF NOT EXISTS identity;        -- users, organizations, memberships (P1)
CREATE SCHEMA IF NOT EXISTS chats;           -- contexts, messages (P2)
CREATE SCHEMA IF NOT EXISTS memory;          -- vector store (P3)
CREATE SCHEMA IF NOT EXISTS audit;           -- audit_reports métadonnées (P4)
CREATE SCHEMA IF NOT EXISTS legal;           -- legal_index FTS (P5)

-- Trace d'initialisation (utile pour les tests d'infra)
CREATE TABLE IF NOT EXISTS public.korev_init_marker (
    id            SERIAL PRIMARY KEY,
    applied_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    phase         TEXT        NOT NULL,
    extensions    TEXT[]      NOT NULL,
    schemas       TEXT[]      NOT NULL
);

INSERT INTO public.korev_init_marker (phase, extensions, schemas)
VALUES (
    'P0',
    ARRAY['pgcrypto', 'vector', 'pg_trgm'],
    ARRAY['identity', 'chats', 'memory', 'audit', 'legal']
);
