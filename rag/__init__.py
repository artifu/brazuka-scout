"""
RAG Pipeline for Brazuka Scout.

Stages:
  1. chunker.py   — split WhatsApp chat into chunks (game windows + weekly general)
  2. classifier.py — label each chunk with Claude Haiku (game_related, category)
  3. embedder.py   — generate vector embeddings with Voyage AI
  4. indexer.py    — store chunks + embeddings in Supabase pgvector
  5. retriever.py  — similarity search with metadata filters
  6. query.py      — full RAG: retrieve + generate answer with Claude
"""
