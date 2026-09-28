"""
ingest/objectives.py — Programmes au format « Objectifs d'apprentissage | Exemples de réussite »
(mathématiques cycle 2 et cycle 3 2025, cycle 4 2026).

Mise en page : tableau à deux colonnes. Les objectifs (colonne gauche, étroite) commencent
par « - » ; les exemples de réussite (colonne droite, large) suivent. Les rubriques
(domaine, année, chapitre) sont des lignes courtes égales aux entrées du sommaire.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from pedagogy.ingest.core import Builder, Item, clean_line
from pedagogy.models import Level

NARROW = 42  # largeur maximale (caractères) d'une ligne de la colonne « objectifs »


def sommaire_entries(lines: Dict[int, List[str]], stop_marker: str = "Principes", max_pages: int = 4) -> List[str]:
    """Entrées du sommaire (après « Sommaire », jusqu'à la 2e occurrence du marqueur de début du texte)."""
    out: List[str] = []
    started = False
    for p in range(1, max_pages + 1):
        for raw in lines.get(p, []):
            s = clean_line(raw)
            if not s:
                continue
            if not started:
                started = s.lower() == "sommaire"
                continue
            if s == stop_marker and len(out) > 3:
                return out
            out.append(s)
    return out


def parse_objectives(
    b: Builder,
    level_headings: Dict[str, Level],
    domains: Dict[str, str],
    chapters: Sequence[str],
    first_page: int,
    last_page: Optional[int] = None,
    difficulty_of: Optional[Dict[Level, int]] = None,
    table_marker: str = "Objectifs d’apprentissage",
) -> None:
    """Parcourt les pages et ajoute chaque objectif comme notion prouvée."""
    chapter_set = set(chapters)
    domain: Optional[Tuple[str, str]] = None
    level: Optional[Level] = None
    chapter = ""
    in_table = False
    cur: List[str] = []
    cur_page = 0

    def flush() -> None:
        nonlocal cur
        if cur and domain and level:
            text = clean_line(" ".join(cur))
            if not re.match(r"^-?\s*[A-Za-zÀ-ÖØ-öø-ÿ«]", text):
                cur = []  # légende de figure ou tableau de nombres : pas un objectif
                return
            b.add(Item(level=level, domain=domain[0], domain_code=domain[1], chapter=chapter or domain[0],
                       excerpt=text.lstrip("- ").strip(), page=cur_page, kind="objectif",
                       difficulty=(difficulty_of or {}).get(level, 2)))
        cur = []

    last = last_page or max(b.lines)
    for p in range(first_page, last + 1):
        for raw in b.lines.get(p, []):
            s = clean_line(raw)
            if not s:
                continue
            if s in domains:
                flush(); domain = (s, domains[s]); in_table = False; chapter = ""; continue
            if s in level_headings:
                flush(); level = level_headings[s]; in_table = False; chapter = ""; continue
            if s in chapter_set and len(s) <= 90:
                flush(); chapter = s; in_table = False; continue
            if s.startswith(table_marker):
                flush(); in_table = True; continue
            if not in_table:
                continue
            if s.startswith("- ") and len(s) <= NARROW + 2:
                flush(); cur = [s]; cur_page = p
                if s.endswith("."):
                    flush()
                continue
            if cur:
                if len(s) <= NARROW and not s.startswith(("L’élève", "L'élève", "Par exemple")):
                    cur.append(s)
                    if s.endswith("."):
                        flush()
                else:
                    flush()
        # un objectif ne franchit pas une page (preuve page par page)
        flush()
