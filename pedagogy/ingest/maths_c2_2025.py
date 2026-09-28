"""
Mathématiques cycle 2 (CP, CE1, CE2) — programme 2025 (SRC-C2-MATHS-2025).

  python -m pedagogy.ingest.maths_c2_2025
Écrit pedagogy/data/notions/MATHS/{CP,CE1,CE2}.json (notions PROUVÉES, verbatim).
"""

from __future__ import annotations

from pedagogy.ingest.core import Builder, link_sequential_prerequisites, report_rejections, write_notion_file
from pedagogy.ingest.objectives import parse_objectives, sommaire_entries
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR

SOURCE_ID = "SRC-C2-MATHS-2025"
LEVELS = {
    "Cours préparatoire": Level.CP,
    "Cours élémentaire première année": Level.CE1,
    "Cours élémentaire deuxième année": Level.CE2,
}
DOMAINS = {
    "Nombres, calcul et résolution de problèmes": "NCRP",
    "Grandeurs et mesures": "GM",
    "Espace et géométrie": "EG",
    "Organisation et gestion de données": "OGD",
}
DIFFICULTY = {Level.CP: 1, Level.CE1: 1, Level.CE2: 2}


def build() -> Builder:
    b = Builder(SOURCE_ID, Subject.MATHS, Course.COMMON, "2026-2027",
                "Programme de mathématiques du cycle 2 — BO n°41 du 31 octobre 2024 (en vigueur depuis 2025-2026)")
    som = sommaire_entries(b.lines)
    chapters = [x for x in som if x not in LEVELS and x not in DOMAINS and x != "Principes"]
    parse_objectives(b, LEVELS, DOMAINS, chapters, first_page=3, difficulty_of=DIFFICULTY)
    return b


def main() -> int:
    b = build()
    for level, notions in sorted(b.by_level().items(), key=lambda kv: kv[0].value):
        write_notion_file(DATA_DIR / "notions" / "MATHS" / f"{level.value}.json", Subject.MATHS, level,
                          Course.COMMON, link_sequential_prerequisites(notions), "pedagogy.ingest.maths_c2_2025")
    print(f"{len(b.notions)} notions prouvées ; {report_rejections(b.rejected)}")
    return 0 if not b.rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
