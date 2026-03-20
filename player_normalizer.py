"""
Maps raw player name strings (from chat/AI extraction) to canonical player IDs.
Loads the players table from Supabase and builds a lookup index from aliases.
"""
import os
from typing import Optional
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lwfbvoewpzutowasyyoz.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx3ZmJ2b2V3cHp1dG93YXN5eW96Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzk1ODA0MCwiZXhwIjoyMDg5NTM0MDQwfQ.YJDp0wQYczXqfH1inJ3gIl3_4wqay8XzIdgKQKt8cU4")


class PlayerNormalizer:
    def __init__(self):
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        players = sb.table("players").select("*").execute().data
        # Build alias → player dict
        self._index: dict[str, dict] = {}
        for p in players:
            for alias in p["aliases"]:
                self._index[alias.lower().strip()] = p
            # Also index canonical name itself
            self._index[p["canonical_name"].lower().strip()] = p
        self._players = {p["id"]: p for p in players}

    def resolve(self, raw_name: str) -> Optional[dict]:
        """Return player dict if found, else None."""
        return self._index.get(raw_name.lower().strip())

    def resolve_id(self, raw_name: str) -> Optional[int]:
        """Return player_id if found, else None."""
        p = self.resolve(raw_name)
        return p["id"] if p else None

    def resolve_or_flag(self, raw_name: str) -> tuple[Optional[int], str]:
        """Return (player_id, canonical_name). If not found, returns (None, raw_name) so caller can flag it."""
        p = self.resolve(raw_name)
        if p:
            return p["id"], p["canonical_name"]
        return None, raw_name


if __name__ == "__main__":
    n = PlayerNormalizer()
    test_names = ["rato", "rat", "Rato", "arthur", "arthur bom", "arthur ruim",
                  "luigi", "dandan", "messi", "lionel", "kuster", "küster",
                  "r@", "lucas", "Unknown Player"]
    print("Alias resolution test:")
    for name in test_names:
        pid, canonical = n.resolve_or_flag(name)
        status = f"→ [{pid}] {canonical}" if pid else f"⚠️  NOT FOUND: '{name}'"
        print(f"  {name!r:20} {status}")
