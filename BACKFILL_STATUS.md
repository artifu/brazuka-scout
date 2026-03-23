# Chat Backfill Status

Tracks which seasons have had their WhatsApp chat data parsed and saved to Supabase.
"Backfilled" = goals, assists, appearances, cards, and notable moments enriched from chat.

## ✅ Done — chat parsed & DB backfilled

| Season | season_id | Dates | Games | Script |
|---|---|---|---|---|
| Winter 2025-26 | 1 | Dec 2025 → | 10 | `save_all_remaining.py` |
| Winter I 2025 | 21 | Sep 2025 | 10 | `save_all_remaining.py` |
| Fall 2025 | 22 | Aug 2025 | 7 | (covered in all_remaining) |
| Summer 2025 | 23 | Jun 2025 | 6 | `save_summer2025.py` |
| Spring 2025 | 24 | Apr 2025 | 12 | `save_spring2025.py` |
| Winter II 2025 | 14 | Jan 2025 | 20 | `save_winter2_2025.py` |
| Winter I 2024 | 15 | Oct 2024 | 12 | `save_winter1_2024.py` |
| Fall 2024 | 16 | Aug–Sep 2024 | 6 | `save_fall2024.py` |
| Summer 2024 | 17 | Jul–Aug 2024 | 6 | `save_summer2024.py` |
| Spring 2024 | 25 | Apr–Jun 2024 | 12 | `save_spring2024.py` |
| Winter II 2024 | 26 | Jan–Apr 2024 | 12 | `save_winter2_2024.py` |
| Winter I 2023 | 27 | Oct–Dec 2023 | 11 | `save_winter1_2023.py` |
| Fall 2023 | 28 | Aug–Sep 2023 | 6 | `save_fall2023.py` |
| Summer 2023 | 29 | Jul–Aug 2023 | 6 | `save_summer2023.py` |
| Spring 2023 | 7 | Apr–Jun 2023 | 11 | `save_spring2023.py` |
| Winter II 2023 | 13 | Jan–Apr 2023 | 13 | `save_winter2_2023.py` |
| Winter I 2022 | 11 | Oct 2022–Jan 2023 | 12 | `save_winter1_2022.py` |
| Fall 2022 | 5 | Aug–Oct 2022 | 6 | `save_fall2022.py` |
| Summer 2022 | 9 | Jul–Aug 2022 | 6 | `save_summer2022.py` |
| Spring 2022 | 6 | Apr–Jul 2022 | 12 | `save_spring2022.py` |
| Winter II 2022 | 12 | Jan–Apr 2022 | 11+9dup | `save_winter2_2022.py` |
| Winter I 2021 | 10 | Oct–Dec 2021 | 11 | `save_winter1_2021.py` |
| Fall 2021 | 4 | Aug–Sep 2021 | 8 | `save_fall2021.py` |
| Summer 2021 | 8 | Jul–Aug 2021 | 6 | `save_summer2021.py` |

## ❌ Not done — need chat parsing

**(none — backfill complete!)**

**All historical seasons backfilled.** 🎉

## Notes

- The chat file is `_chat.txt` (~194k lines, Jun 2021 → present)
- For each season: read the relevant chat window, extract goals/assists/appearances/cards/moments, write a `save_<season>.py` script, run it
- Older seasons (2021–2022) will have less chat context and may need more inference
- There are duplicate season IDs for some names (e.g. two "Spring 2023" entries) — check `season_id` carefully
- Season 19 (Fall 2024, start Aug 22) appears to be a RECEBA FC team entry, not Brazuka Tuesday — skip or handle separately
