"""
Stage 6 — Query (full RAG pipeline)

retrieve() → format context → Claude generates answer

Auto-detects whether to use game-only search based on keywords in the question.
Responds in the same language as the question (PT or EN).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import Optional, List, Dict, Any
import anthropic

from .retriever import retrieve

# Keywords that signal a stats / match question → use game-only retrieval
_STATS_KEYWORDS = [
    "gol", "goal", "placar", "score", "resultado", "result",
    "ganhou", "perdeu", "won", "lost", "drew", "empat",
    "artilheiro", "scorer", "partida", "jogo", "game",
    "temporada", "season", "histórico", "history", "record",
    "assistência", "assist", "cartão", "card", "lesão", "injury",
    "quem marcou", "who scored", "quantos gols", "how many goals",
]

_SYSTEM = """Você é o Brazuka Scout — assistente oficial de estatísticas do BRAZUKA & RECEBA FC, um time recreativo brasileiro que joga às terças no Magnuson Park, Seattle.

Você responde perguntas sobre história do time, estatísticas de jogadores, resultados e momentos marcantes, com base no histórico do chat do WhatsApp e nos dados de partidas.

Regras:
- Responda no mesmo idioma da pergunta (português ou inglês)
- Seja direto mas com energia — você está falando com um companheiro de time
- Se o dado vier do chat, mencione a data aproximada
- Se não tiver certeza, diga — não invente estatísticas
- Use termos de futebol naturalmente (gols, partida, placar, etc.)
- Um toque de energia do futebol brasileiro nunca faz mal ⚽🇧🇷"""


def query(
    question: str,
    top_k: int = 5,
    game_only: Optional[bool] = None,
    verbose: bool = False,
) -> str:
    """
    Full RAG query: embed → retrieve → generate.

    Args:
        question  : natural language question
        top_k     : chunks to retrieve
        game_only : force game-only retrieval (auto-detected if None)
        verbose   : print retrieved chunks for debugging

    Returns:
        Generated answer as a string
    """
    # Auto-detect retrieval mode
    if game_only is None:
        q_lower = question.lower()
        game_only = any(kw in q_lower for kw in _STATS_KEYWORDS)

    if verbose:
        print(f"🔍 Question : {question}")
        print(f"   game_only: {game_only}")

    # ── Retrieve ──────────────────────────────────────────────────────────────
    chunks = retrieve(question, top_k=top_k, game_only=game_only)

    if not chunks:
        return "Não encontrei informações relevantes no histórico do grupo. 🤷"

    if verbose:
        print(f"\n📚 Retrieved {len(chunks)} chunks:")
        for i, c in enumerate(chunks, 1):
            meta = c.get("metadata") or {}
            label = meta.get("date") or meta.get("week_start") or "?"
            print(f"   [{i}] sim={c.get('similarity', 0):.3f} | {c.get('chunk_type')} | {label}")
        print()

    # ── Format context ────────────────────────────────────────────────────────
    context_parts: List[str] = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata") or {}
        sim = chunk.get("similarity", 0)

        if chunk.get("chunk_type") == "game":
            header = (
                f"[Fonte {i} | Jogo vs {meta.get('opponent', '?')} "
                f"em {meta.get('date', '?')} | sim={sim:.2f}]"
            )
        else:
            header = (
                f"[Fonte {i} | Chat geral — semana de {meta.get('week_start', '?')} "
                f"| sim={sim:.2f}]"
            )

        context_parts.append(f"{header}\n{chunk['content']}")

    context = "\n\n---\n\n".join(context_parts)

    # ── Generate ──────────────────────────────────────────────────────────────
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Contexto do chat do grupo:\n\n{context}\n\n---\n\nPergunta: {question}",
        }],
    )

    return response.content[0].text
