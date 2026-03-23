#!/usr/bin/env python3
"""Seed the players table in Supabase with canonical names and aliases."""
import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lwfbvoewpzutowasyyoz.supabase.co")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

PLAYERS = [
    {"canonical_name": "Arthur Mendes",   "aliases": ["arthur", "art", "arthur bom", "arthur good", "arthur mendes"]},
    {"canonical_name": "Arthur Koefender","aliases": ["koefender", "arthur koefender"]},
    {"canonical_name": "Rafael Franco",   "aliases": ["rato", "rat", "r@", "rafa", "rafael", "rafael franco", "rafael rato", "rafa rato"]},
    {"canonical_name": "Kuster",          "aliases": ["kuster", "küster", "guilherme", "guilherme kuster", "guilherme küster"]},
    {"canonical_name": "Luigi Tedesco",   "aliases": ["luigi", "luigi messi", "luigi tedesco"]},
    {"canonical_name": "Daniel Tedesco",  "aliases": ["dandan", "daniel", "messi", "lionel", "daniel tedesco"]},
    {"canonical_name": "Pablo",           "aliases": ["pablo", "pabl"]},
    {"canonical_name": "Sergio Filho",    "aliases": ["sergio", "sergio filho"]},
    {"canonical_name": "Pedro Nakamura",  "aliases": ["pedro", "pedro nakamura"]},
    {"canonical_name": "Marcelo D",       "aliases": ["marcelo", "marcelo d", "marcelo dichtchekenian"]},
    {"canonical_name": "Marcelo Mazzafera","aliases": ["mazza", "mazzafera", "marcelo mazza", "marcelo mazzafera"]},
    {"canonical_name": "Caio Scofield",   "aliases": ["caio", "caio scofield", "scofa", "scofield"]},
    {"canonical_name": "Ranieri Filho",   "aliases": ["ranieri", "rani", "ranieri filho"]},
    {"canonical_name": "Lucas Claro",     "aliases": ["lucas", "lucas claro"]},
    {"canonical_name": "Roberto Bandarra","aliases": ["roberto", "roberto b", "roberto bandarra"]},
    {"canonical_name": "Bobby Axe",       "aliases": ["roberto m", "roberto machado", "bobby axe", "bobby"]},
    {"canonical_name": "Ademario Nunes",  "aliases": ["ademario", "nunes", "ademario nunes"]},
    {"canonical_name": "Joao Barros",     "aliases": ["joao", "joao barros", "jb", "joao b", "jonny muds", "johnny muds"]},
    {"canonical_name": "Joao Pinto",      "aliases": ["joao pinto", "joao c", "joao c. pinto", "pintola", "pinto"]},
    {"canonical_name": "Cleiton Castro",  "aliases": ["cleiton castro", "castro", "cleito", "cleiton", "cleiton goes", "cleiton góes", "goes", "góes", "cleiton do cavaco", "cavaco"]},
    {"canonical_name": "Cleiton Moura",   "aliases": ["cleiton moura", "moura"]},
    {"canonical_name": "Victor Ozorio",   "aliases": ["victor", "victor ozorio"]},
    {"canonical_name": "Adelmo",          "aliases": ["adelmo"]},
    {"canonical_name": "Allan",           "aliases": ["allan"]},
    {"canonical_name": "Alexis",          "aliases": ["alexis"]},
    {"canonical_name": "Rafa Mattos",     "aliases": ["rafa mattos", "mattos"]},
    {"canonical_name": "Matheus Waterfall","aliases": ["matheus", "cachoeira", "matheus cachoeira", "matheus waterfall", "waterfall"]},
    {"canonical_name": "Federico",        "aliases": ["federico", "fede", "federico del bono"]},
    {"canonical_name": "Rodrigo",         "aliases": ["rodrigo", "rodrigo accioly"]},
    {"canonical_name": "Mauricio",        "aliases": ["mauricio", "mauricio steinbruch"]},
    {"canonical_name": "Lucas Guilherme", "aliases": ["lucas guilherme"]},  # injured, rarely plays
    {"canonical_name": "Gustavo Bittencourt", "aliases": ["gus", "gustavo", "gustavo bittencourt"]},
    {"canonical_name": "Darley Tomaz",        "aliases": ["darley", "darley tomaz"]},
    {"canonical_name": "Chase TenBrook",      "aliases": ["chase", "chase tenbrook"]},
    {"canonical_name": "Amaral",              "aliases": ["amaral"]},
    {"canonical_name": "Tamir Guy",           "aliases": ["tamir", "tamir guy"]},
    {"canonical_name": "Flavio Magalhaes",    "aliases": ["flavio", "flavio magalhaes"]},
    {"canonical_name": "Aleme",               "aliases": ["aleme"]},
    {"canonical_name": "Ednaldo",             "aliases": ["ednaldo"]},
    {"canonical_name": "Sebastiao",           "aliases": ["sebastiao", "sebastião"]},
    {"canonical_name": "Pedro Koefender",     "aliases": ["pedro k", "pedro koefender"]},
    {"canonical_name": "Jordan",              "aliases": ["jordan", "de bruyne", "debruyne"]},
    # Receba FC regulars
    {"canonical_name": "Leonel",              "aliases": ["leonel"]},
    {"canonical_name": "Maik",               "aliases": ["maik"]},
    {"canonical_name": "Reese",              "aliases": ["reese"]},
    {"canonical_name": "Kenneth",            "aliases": ["kenneth"]},
    {"canonical_name": "Wesley",             "aliases": ["wesley"]},
]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Clear and re-seed
sb.table("players").delete().neq("id", 0).execute()
resp = sb.table("players").insert(PLAYERS).execute()
print(f"Seeded {len(resp.data)} players.")
for p in resp.data:
    print(f"  [{p['id']}] {p['canonical_name']}")
