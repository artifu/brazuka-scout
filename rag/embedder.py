"""
Stage 3 — Embedder

Generates vector embeddings for each chunk using Voyage AI (voyage-3-lite).
  - Documents are embedded with input_type="document"
  - Queries are embedded with input_type="query" (see embed_query())

Requires:
  pip install voyageai
  export VOYAGE_API_KEY=your_key   # free tier: 50M tokens/month at voyageai.com
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
from typing import List
from .chunker import Chunk

VOYAGE_MODEL = "voyage-3-lite"   # 512-dim, fast, cheap — ideal for this use case
EMBED_BATCH_SIZE = 128            # Voyage AI max batch size
_RATE_LIMIT_DELAY = 21            # seconds between batches on free tier (3 RPM)


def _get_client():
    try:
        import voyageai
    except ImportError:
        raise ImportError(
            "voyageai not installed.\n"
            "Run: pip install voyageai\n"
            "Then get a free API key at https://www.voyageai.com and set VOYAGE_API_KEY"
        )
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise ValueError(
            "VOYAGE_API_KEY not set.\n"
            "Get a free key at https://www.voyageai.com and: export VOYAGE_API_KEY=your_key"
        )
    return voyageai.Client(api_key=api_key)


def embed_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """
    Generate embeddings for all chunks.
    Modifies chunks in-place (sets .embedding).
    Returns the same list for chaining.
    """
    client = _get_client()
    total = len(chunks)
    print(f"🔢 Generating embeddings for {total} chunks (model: {VOYAGE_MODEL})…")

    for i in range(0, total, EMBED_BATCH_SIZE):
        if i > 0:
            print(f"   ⏳ Rate limit pause ({_RATE_LIMIT_DELAY}s)…", end="\r")
            time.sleep(_RATE_LIMIT_DELAY)

        batch = chunks[i : i + EMBED_BATCH_SIZE]
        texts = [c.content[:16_000] for c in batch]  # voyage-3-lite context limit

        result = client.embed(texts, model=VOYAGE_MODEL, input_type="document")

        for j, embedding in enumerate(result.embeddings):
            batch[j].embedding = embedding

        done = min(i + EMBED_BATCH_SIZE, total)
        print(f"   {done}/{total} embedded…", end="\r")

    print()
    print(f"✅ Embedding done — {total} chunks embedded\n")
    return chunks


def embed_query(query: str) -> List[float]:
    """
    Embed a single query string for retrieval.
    Uses input_type="query" (asymmetric embedding — different from documents).
    """
    client = _get_client()
    result = client.embed([query], model=VOYAGE_MODEL, input_type="query")
    return result.embeddings[0]
