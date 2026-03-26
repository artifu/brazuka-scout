"""
Stage 4 — Indexer

Stores chunks + embeddings into the Supabase `rag_chunks` table (pgvector).
Requires the SQL migration to be applied first:
  migrations/create_rag_chunks.sql
"""
import os
import sys
import time
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List
from supabase import create_client

from .chunker import Chunk

TABLE = "rag_chunks"
UPSERT_BATCH_SIZE = 50


def _client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
    return create_client(url, key)


def index_chunks(chunks: List[Chunk]) -> int:
    """
    Upsert all embedded chunks into Supabase.
    Returns number of chunks successfully indexed.
    """
    ready = [c for c in chunks if c.embedding is not None]
    if not ready:
        print("⚠️  No chunks with embeddings — nothing to index.")
        return 0

    sb = _client()
    total = len(ready)
    indexed = 0
    print(f"📥 Indexing {total} chunks into Supabase '{TABLE}'…")

    for i in range(0, total, UPSERT_BATCH_SIZE):
        batch = ready[i : i + UPSERT_BATCH_SIZE]
        records = [
            {
                "id": str(uuid.uuid4()),
                "content": c.content,
                "embedding": c.embedding,
                "chunk_type": c.chunk_type,
                "game_related": c.game_related if c.game_related is not None else False,
                "category": c.category or "unknown",
                "metadata": c.metadata,
            }
            for c in batch
        ]
        # Reconnect each batch + retry to handle LibreSSL/HTTP2 flakiness on macOS
        for attempt in range(4):
            try:
                _client().table(TABLE).upsert(records).execute()
                break
            except Exception as e:
                if attempt == 3:
                    raise
                wait = 2 ** attempt
                print(f"\n   ⚠️  Batch error (attempt {attempt+1}/4): {e}. Retrying in {wait}s…")
                time.sleep(wait)
        indexed += len(batch)
        print(f"   {indexed}/{total} indexed…", end="\r")

    print()
    print(f"✅ Indexing done — {indexed} chunks stored in Supabase\n")
    return indexed


def clear_index() -> None:
    """Delete ALL rows from the index. Use with caution."""
    sb = _client()
    # Delete all rows by filtering on a column that's always non-null
    sb.table(TABLE).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print(f"🗑️  Cleared all rows from '{TABLE}'")


def get_index_stats() -> dict:
    """Return summary stats about the current index."""
    sb = _client()
    rows = sb.table(TABLE).select("chunk_type, game_related, category").execute().data

    type_counts: dict = {}
    category_counts: dict = {}
    for row in rows:
        t = row.get("chunk_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        cat = row.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "total": len(rows),
        "game_related": sum(1 for r in rows if r.get("game_related")),
        "by_type": type_counts,
        "by_category": category_counts,
    }
