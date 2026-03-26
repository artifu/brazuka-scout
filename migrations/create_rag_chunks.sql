-- ============================================================
-- Brazuka Scout — RAG Pipeline: pgvector setup
-- Run this once in the Supabase SQL editor before indexing.
-- ============================================================

-- 1. Enable pgvector (usually already enabled in Supabase)
create extension if not exists vector;

-- 2. Main chunks table
--    embedding is 512-dim (voyage-3-lite default)
create table if not exists rag_chunks (
    id           uuid primary key default gen_random_uuid(),
    content      text        not null,
    embedding    vector(512),                          -- voyage-3-lite
    chunk_type   text        not null check (chunk_type in ('game', 'general')),
    game_related boolean     not null default false,
    category     text        not null default 'unknown',
    metadata     jsonb       not null default '{}',
    created_at   timestamptz not null default now()
);

comment on table  rag_chunks                is 'Chunks of WhatsApp chat history, embedded for RAG retrieval';
comment on column rag_chunks.chunk_type     is 'game = game window | general = weekly non-game messages';
comment on column rag_chunks.game_related   is 'True if Claude Haiku classified the chunk as football-related';
comment on column rag_chunks.category       is 'result | signup | injury | banter | logistics | off_topic';
comment on column rag_chunks.metadata       is 'Varies by type: {date, opponent, home_or_away} or {week_start}';

-- 3. Indexes
--    IVFFlat for ANN search — lists = sqrt(expected_rows), tune as needed
create index if not exists rag_chunks_embedding_idx
    on rag_chunks using ivfflat (embedding vector_cosine_ops)
    with (lists = 50);

create index if not exists rag_chunks_chunk_type_idx    on rag_chunks (chunk_type);
create index if not exists rag_chunks_game_related_idx  on rag_chunks (game_related);
create index if not exists rag_chunks_category_idx      on rag_chunks (category);

-- 4. Similarity search function
--    Called by retriever.py via supabase.rpc("match_rag_chunks", {...})
--
--    Parameters:
--      query_embedding  — embedded query vector (512-dim)
--      match_count      — how many results to return (default 5)
--      game_only        — if true, restrict to game_related = true rows
--      filter_category  — optional category filter (null = no filter)
create or replace function match_rag_chunks(
    query_embedding  vector(512),
    match_count      int     default 5,
    game_only        boolean default false,
    filter_category  text    default null
)
returns table (
    id           uuid,
    content      text,
    chunk_type   text,
    game_related boolean,
    category     text,
    metadata     jsonb,
    similarity   float
)
language sql stable
as $$
    select
        id,
        content,
        chunk_type,
        game_related,
        category,
        metadata,
        1 - (embedding <=> query_embedding) as similarity
    from rag_chunks
    where
        (not game_only or game_related = true)
        and (filter_category is null or category = filter_category)
        and embedding is not null
    order by embedding <=> query_embedding
    limit match_count;
$$;
