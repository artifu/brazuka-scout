"""
Stage 5 — Retriever

Embeds a query and runs a pgvector cosine-similarity search against
the `rag_chunks` table, with optional metadata filters.

Calls the `match_rag_chunks` SQL function defined in:
  migrations/create_rag_chunks.sql
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List, Optional, Dict, Any
from supabase import create_client

from .embedder import embed_query


def _client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
    return create_client(url, key)


def retrieve(
    query: str,
    top_k: int = 5,
    game_only: bool = False,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Args:
        query     : natural language question
        top_k     : number of chunks to return
        game_only : if True, only search game-related chunks
        category  : optional category filter (result | signup | banter | etc.)

    Returns:
        List of dicts with keys: id, content, chunk_type, game_related,
        category, metadata, similarity
    """
    query_embedding = embed_query(query)
    sb = _client()

    params: Dict[str, Any] = {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "game_only": game_only,
    }
    if category:
        params["filter_category"] = category

    result = sb.rpc("match_rag_chunks", params).execute()
    return result.data or []
