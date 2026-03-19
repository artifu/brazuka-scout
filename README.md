# Brazuka Scout 🏆

A football stats tracker powered by WhatsApp chat history + Claude AI.

Automatically extracts match results, goal scorers, player availability, and funny moments from your group chat.

## Features
- Parse WhatsApp chat exports
- AI-powered event extraction (goals, results, cards, highlights)
- SQLite database for historical stats
- CLI to query player stats, head-to-head records, and more

## Setup
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
python main.py import chat.txt
python main.py stats
```

