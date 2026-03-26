"""
Stage 2 — Classifier

Sends each chunk (first 500 chars) to Claude Haiku in batches.
Adds two fields to each Chunk:
  - game_related (bool)  : does this chunk contain football match content?
  - category     (str)   : result | signup | injury | banter | logistics | off_topic
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List
import anthropic

from .chunker import Chunk


CATEGORIES = ["result", "signup", "injury", "banter", "logistics", "off_topic"]

_SYSTEM = """Você é um classificador de mensagens do WhatsApp de um time de futebol recreativo brasileiro chamado Brazuka, que joga às terças no Magnuson Park, Seattle.

Para cada chunk de mensagens, retorne:
- game_related: true se o chunk contém conteúdo relevante de futebol (resultados, gols, escalação, lesões, disponibilidade de jogadores)
- category: uma das opções abaixo
    result     — mensagens pós-jogo com placar, gols, resultado
    signup     — listas de confirmação de presença pré-jogo
    injury     — lesão ou condição física de jogador
    banter     — zoações, comemorações, momentos engraçados
    logistics  — horário, campo, pagamento, admin
    off_topic  — assuntos não relacionados ao futebol (churrasco, memes, vida pessoal, etc.)

Retorne SOMENTE um array JSON com um objeto por chunk, nesta ordem e formato exatos:
[
  {"game_related": true, "category": "result"},
  {"game_related": false, "category": "off_topic"}
]"""


def classify_chunks(chunks: List[Chunk], batch_size: int = 10) -> List[Chunk]:
    """
    Classify all chunks using Claude Haiku.
    Modifies chunks in-place (sets .game_related and .category).
    Returns the same list for chaining.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    total = len(chunks)
    print(f"🤖 Classifying {total} chunks (batches of {batch_size})…")

    for batch_start in range(0, total, batch_size):
        batch = chunks[batch_start : batch_start + batch_size]

        # Build prompt — first 500 chars per chunk is enough to classify
        user_text = f"Classifique estes {len(batch)} chunks:\n"
        for j, chunk in enumerate(batch, 1):
            preview = chunk.content[:500].replace("\n", " ")
            user_text += f"\nChunk {j}:\n{preview}\n"

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user_text}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            results = json.loads(raw)

            for j, classification in enumerate(results):
                if j < len(batch):
                    batch[j].game_related = bool(classification.get("game_related", False))
                    batch[j].category = classification.get("category", "off_topic")

        except Exception as exc:
            print(f"   ⚠️  Batch {batch_start // batch_size + 1} classification error: {exc}")
            # Graceful fallback: game chunks → result, general → off_topic
            for chunk in batch:
                chunk.game_related = chunk.chunk_type == "game"
                chunk.category = "result" if chunk.chunk_type == "game" else "off_topic"

        done = min(batch_start + batch_size, total)
        print(f"   {done}/{total} classified…", end="\r")

    print()  # newline after \r
    game_related = sum(1 for c in chunks if c.game_related)
    print(f"✅ Classification done — {game_related}/{total} chunks are game-related\n")
    return chunks
