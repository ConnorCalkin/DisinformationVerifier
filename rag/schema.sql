--schema to set up the postgres database for the RAG system


CREATE EXTENSION vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
    document_id uuid DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding VECTOR(1536) NOT NULL
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);