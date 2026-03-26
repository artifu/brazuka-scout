#!/usr/bin/env python3
"""
Brazuka Scout — RAG Pipeline CLI

Commands:
  index   Parse chat → classify → embed → store in Supabase pgvector
  query   Ask a natural language question against the indexed data
  stats   Show index statistics

Usage examples:
  python rag_cli.py index                                   # full pipeline
  python rag_cli.py index --game-only                       # only game chunks
  python rag_cli.py index --no-classify                     # skip AI classifier
  python rag_cli.py index --clear                           # wipe index first

  python rag_cli.py query "quem é nosso artilheiro histórico?"
  python rag_cli.py query "quando foi a última vez que ganhamos da Newbeebee?"
  python rag_cli.py query "who scored the most goals this season?" --verbose

  python rag_cli.py stats
"""
import argparse
import os
import sys

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass  # env vars must be set manually — that's fine


def cmd_index(args: argparse.Namespace) -> None:
    from rag.chunker import create_chunks
    from rag.classifier import classify_chunks
    from rag.embedder import embed_chunks
    from rag.indexer import index_chunks, clear_index

    chat_file = args.chat_file
    if not os.path.exists(chat_file):
        print(f"❌ Chat file not found: {chat_file}")
        sys.exit(1)

    print("=" * 60)
    print("  BRAZUKA SCOUT — RAG INDEX PIPELINE")
    print("=" * 60)
    print()

    # ── Step 1: Chunk ─────────────────────────────────────────────
    print("[1/4] Chunking chat messages…")
    chunks = create_chunks(chat_file, game_only=args.game_only)

    # ── Step 2: Classify ──────────────────────────────────────────
    if not args.no_classify:
        print("[2/4] Classifying chunks with Claude Haiku…")
        chunks = classify_chunks(chunks)

        if args.game_only:
            before = len(chunks)
            chunks = [c for c in chunks if c.game_related]
            removed = before - len(chunks)
            if removed:
                print(f"   🔽 Filtered out {removed} non-game-related chunks\n")
    else:
        print("[2/4] Skipping classification (--no-classify)\n")
        for chunk in chunks:
            chunk.game_related = chunk.chunk_type == "game"
            chunk.category = "result" if chunk.chunk_type == "game" else "general"

    # ── Step 3: Embed ─────────────────────────────────────────────
    print("[3/4] Generating embeddings with Voyage AI…")
    chunks = embed_chunks(chunks)

    # ── Step 4: Index ─────────────────────────────────────────────
    print("[4/4] Storing in Supabase pgvector…")
    if args.clear:
        print("   Clearing existing index first…")
        clear_index()
        print()

    count = index_chunks(chunks)

    print("=" * 60)
    print(f"  ✅ Done! {count} chunks indexed.")
    print("=" * 60)


def cmd_query(args: argparse.Namespace) -> None:
    from rag.query import query

    question = " ".join(args.question)
    game_only = True if args.game_only else None  # None = auto-detect

    print()
    answer = query(
        question,
        top_k=args.top_k,
        game_only=game_only,
        verbose=args.verbose,
    )

    print("─" * 60)
    print(answer)
    print("─" * 60)


def cmd_stats(args: argparse.Namespace) -> None:
    from rag.indexer import get_index_stats

    stats = get_index_stats()

    print("\n📊 RAG Index Stats")
    print("─" * 40)
    print(f"  Total chunks  : {stats['total']}")
    print(f"  Game-related  : {stats['game_related']}")
    print(f"\n  By type:")
    for k, v in stats.get("by_type", {}).items():
        print(f"    {k:<12} {v}")
    print(f"\n  By category:")
    for k, v in sorted(stats.get("by_category", {}).items(), key=lambda x: -x[1]):
        print(f"    {k:<12} {v}")
    print()


# ── Argument parser ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Brazuka Scout RAG Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    # index
    p_index = sub.add_parser("index", help="Parse + classify + embed + store in Supabase")
    p_index.add_argument(
        "--chat-file", default="_chat.txt",
        help="Path to WhatsApp chat export (default: _chat.txt)",
    )
    p_index.add_argument(
        "--game-only", action="store_true",
        help="Only index game chunks (skip general weekly chunks)",
    )
    p_index.add_argument(
        "--no-classify", action="store_true",
        help="Skip the AI classifier step (faster, less accurate filtering)",
    )
    p_index.add_argument(
        "--clear", action="store_true",
        help="Wipe the existing index before indexing",
    )

    # query
    p_query = sub.add_parser("query", help="Ask a natural language question")
    p_query.add_argument("question", nargs="+", help="Question to ask (can be PT or EN)")
    p_query.add_argument(
        "--top-k", type=int, default=5,
        help="Number of chunks to retrieve (default: 5)",
    )
    p_query.add_argument(
        "--game-only", action="store_true",
        help="Force search only in game chunks",
    )
    p_query.add_argument(
        "--verbose", action="store_true",
        help="Show retrieved chunks + similarity scores",
    )

    # stats
    sub.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
