"""
Mathématiques cycle 4 — programme 2026 (SRC-C4-MATHS-2026), niveau 5e uniquement.

  python -m pedagogy.ingest.maths_c4_2026
Écrit pedagogy/data/notions/MATHS/5E.json (notions PROUVÉES, verbatim).

Le programme est organisé par domaine puis par année (« Cinquième », « Quatrième »,
« Troisième ») : en 2026-2027 seule la 5e suit ce programme, on n’extrait donc que les
tableaux « Objectifs d’apprentissage » placés sous « Cinquième ». Les objectifs sont des
phrases terminées par un point ; une ligne de tableau contenant deux phrases donne deux
objectifs. Les rubriques « Automatismes » et « Prolongements possibles » ne sont pas extraites.
"""

from __future__ import annotations

from pedagogy.ingest.core import Builder, link_sequential_prerequisites, report_rejections, write_notion_file
from pedagogy.ingest.maths_c3_2025 import parse_objective_rows
from pedagogy.ingest.objectives import sommaire_entries
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR

SOURCE_ID = "SRC-C4-MATHS-2026"
PROGRAM_VERSION = "Programme de mathématiques du cycle 4 — BO n°10 de 2026, annexe 2 (NOR MENE2602912A) — 5e en 2026-2027"
LEVELS = {
    "Cinquième": Level.CINQUIEME,
    "Quatrième": Level.QUATRIEME,
    "Troisième": Level.TROISIEME,
}
KEEP_LEVELS = {Level.CINQUIEME}
DOMAINS = {
    "Nombres et calculs": "NC",
    "Espace et géométrie": "EG",
    "Organisation et gestion de données et probabilités": "OGDP",
    "Proportionnalité, fonctions": "PROPF",
    "La pensée informatique": "INFO",
}
DIFFICULTY = {Level.CINQUIEME: 3}
FIRST_BODY_PAGE = 6  # « Nombres et calculs » (après les principes)


def build() -> Builder:
    b = Builder(SOURCE_ID, Subject.MATHS, Course.COMMON, "2026-2027", PROGRAM_VERSION)
    som = sommaire_entries(b.lines)
    chapters = [x for x in som if x not in LEVELS and x not in DOMAINS and x != "Principes"]
    b.orphans = parse_objective_rows(  # type: ignore[attr-defined]
        b, LEVELS, DOMAINS, chapters, first_page=FIRST_BODY_PAGE, keep_levels=KEEP_LEVELS,
        difficulty_of=DIFFICULTY, row_needs_period=True, split_sentences=True)
    return b


def main() -> int:
    b = build()
    for level, notions in sorted(b.by_level().items(), key=lambda kv: kv[0].value):
        write_notion_file(DATA_DIR / "notions" / "MATHS" / f"{level.value}.json", Subject.MATHS, level,
                          Course.COMMON, link_sequential_prerequisites(notions), "pedagogy.ingest.maths_c4_2026")
    print(f"{len(b.notions)} notions prouvées ; {report_rejections(b.rejected)} ; "
          f"{len(b.orphans)} ligne(s) orpheline(s)")  # type: ignore[attr-defined]
    return 0 if not b.rejected and not b.orphans else 1  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
