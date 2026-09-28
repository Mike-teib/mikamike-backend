"""
Mathématiques cycle 3 (CM1, CM2, 6e) — programme 2025 (SRC-C3-MATHS-NOUVEAU).

  python -m pedagogy.ingest.maths_c3_2025
Écrit pedagogy/data/notions/MATHS/{CM1,CM2,6E}.json (notions PROUVÉES, verbatim).

Mise en page (différente du cycle 2) : pas de colonne « Exemples de réussite » ; sous chaque
rubrique « Objectifs d’apprentissage » (gras), chaque ligne de tableau est un objectif, sans
tiret, commençant par une majuscule ; les retours à la ligne d’un même objectif commencent par
une minuscule (ou une formule). Le tableau se termine à la première ligne de titre (gras ou
italique : sous-rubrique, « Automatismes », « Prolongements possibles… », chapitre, année).
En 6e, seules les rubriques « Connaissances et capacités attendues / Objectifs d’apprentissage »
sont extraites ; les « Automatismes » (texte rédigé avec formules) ne le sont pas.

Le parseur `parse_objective_rows` est partagé avec maths_c4_2026 (même charte graphique).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from pypdf import PdfReader

from pedagogy.ingest.core import Builder, Item, clean_line, link_sequential_prerequisites, report_rejections, write_notion_file
from pedagogy.ingest.objectives import sommaire_entries
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry

SOURCE_ID = "SRC-C3-MATHS-NOUVEAU"
PROGRAM_VERSION = ("Programme de mathématiques du cycle 3 — BO n°16 du 17 avril 2025 "
                   "(arrêté du 10 avril 2025, NOR MENE2504620A)")
LEVELS = {
    "Cours moyen première année": Level.CM1,
    "Cours moyen deuxième année": Level.CM2,
    "Sixième": Level.SIXIEME,
}
DOMAINS = {
    "Nombres, calcul et résolution de problèmes": "NCRP",
    "Grandeurs et mesures": "GM",
    "Espace et géométrie": "EG",
    "Organisation et gestion de données et probabilités": "OGDP",
    "La proportionnalité": "PROP",
    "Initiation à la pensée informatique": "INFO",
}
DIFFICULTY = {Level.CM1: 2, Level.CM2: 2, Level.SIXIEME: 2}
TABLE_MARKER = "Objectifs d’apprentissage"
FIRST_BODY_PAGE = 5  # « Nombres, calcul et résolution de problèmes » (après les principes)

_SENTENCE_SPLIT = re.compile(r"(?<=\.)\s+(?=[A-ZÀÂÉÈÊÎÔÛÇ])")


def _key(s: str) -> str:
    """Clé de comparaison insensible aux espaces (le visiteur pypdf perd parfois des espaces)."""
    return re.sub(r"\s+", "", s.replace(" ", " ")).casefold()


def styled_heading_keys(source_id: str, root: Path = REPO_ROOT) -> Dict[int, Set[str]]:
    """Pour chaque page, clés des lignes composées uniquement en gras ou en italique (titres).

    Les formules (lettres isolées en italique comme « a », « b ») sont écartées."""
    src = load_registry().sources[source_id]
    reader = PdfReader(str(root / src.local_path))
    out: Dict[int, Set[str]] = {}
    for i, page in enumerate(reader.pages):
        rows: Dict[float, List[Tuple[str, str]]] = {}

        def visit(text, cm, tm, font_dict, font_size, rows=rows):  # noqa: ANN001
            if not text.strip():
                return
            font = str((font_dict or {}).get("/BaseFont", ""))
            rows.setdefault(round(tm[5], 1), []).append((font, text))

        page.extract_text(visitor_text=visit)
        keys: Set[str] = set()
        for frags in rows.values():
            if all(("Bold" in f or "Italic" in f) for f, _ in frags):
                txt = "".join(t for _, t in frags).strip()
                if len(_key(txt)) >= 3 and txt[0].isupper():
                    keys.add(_key(txt))
        out[i + 1] = keys
    return out


def parse_objective_rows(
    b: Builder,
    level_headings: Dict[str, Level],
    domains: Dict[str, str],
    chapters: Sequence[str],
    first_page: int,
    last_page: Optional[int] = None,
    keep_levels: Optional[Set[Level]] = None,
    difficulty_of: Optional[Dict[Level, int]] = None,
    row_needs_period: bool = False,
    split_sentences: bool = False,
) -> List[Tuple[int, str]]:
    """Ajoute chaque objectif (ligne du tableau « Objectifs d’apprentissage ») comme notion prouvée.

    - row_needs_period : une nouvelle ligne ne commence un nouvel objectif que si l’objectif en
      cours se termine par un point (cycle 4, dont les objectifs sont ponctués).
    - split_sentences : une ligne de tableau contenant plusieurs phrases donne plusieurs objectifs.
    Renvoie la liste des lignes orphelines (suite d’objectif sans début sur la page) pour contrôle.
    """
    headings = styled_heading_keys(b.source_id)
    chapter_keys = {_key(c): c for c in chapters}
    domain: Optional[Tuple[str, str]] = None
    level: Optional[Level] = None
    chapter = ""
    in_table = False
    cur: List[str] = []
    cur_page = 0
    orphans: List[Tuple[int, str]] = []

    def flush() -> None:
        nonlocal cur
        if cur and domain and level and (keep_levels is None or level in keep_levels):
            text = clean_line(" ".join(cur))
            parts = _SENTENCE_SPLIT.split(text) if split_sentences else [text]
            for part in parts:
                b.add(Item(level=level, domain=domain[0], domain_code=domain[1], chapter=chapter or domain[0],
                           excerpt=part, page=cur_page, kind="objectif",
                           difficulty=(difficulty_of or {}).get(level, 2),
                           # Cycle 3 : une ligne de tableau est un objectif complet, sans point
                           # final ; en 5e (phrases ponctuées) on garde la détection par ponctuation.
                           complete=None if split_sentences else True))
        cur = []

    last = last_page or max(b.lines)
    for p in range(first_page, last + 1):
        for raw in b.lines.get(p, []):
            s = clean_line(raw)
            if not s:
                continue
            k = _key(s)
            styled = k in headings.get(p, set())
            if s in domains and styled:
                flush(); domain = (s, domains[s]); level = None; chapter = ""; in_table = False; continue
            if s in level_headings:
                flush(); level = level_headings[s]; chapter = ""; in_table = False; continue
            if k in chapter_keys and styled:
                flush(); chapter = chapter_keys[k]; in_table = False; continue
            if s.startswith(TABLE_MARKER):
                flush(); in_table = True; continue
            if styled:  # sous-rubrique, « Automatismes », « Prolongements possibles… », etc.
                flush(); in_table = False; continue
            if not in_table:
                continue
            starts_new = s[0].isupper() and (not row_needs_period or not cur or cur[-1].endswith("."))
            if starts_new:
                flush(); cur = [s]; cur_page = p
            elif cur:
                cur.append(s)
            else:
                orphans.append((p, s))
        # un objectif ne franchit pas une page (preuve page par page) ; le tableau, si.
        flush()
    return orphans


def build() -> Builder:
    b = Builder(SOURCE_ID, Subject.MATHS, Course.COMMON, "2026-2027", PROGRAM_VERSION)
    som = sommaire_entries(b.lines)
    chapters = [x for x in som if x not in LEVELS and x not in DOMAINS and x != "Principes"]
    b.orphans = parse_objective_rows(b, LEVELS, DOMAINS, chapters, first_page=FIRST_BODY_PAGE,  # type: ignore[attr-defined]
                                     difficulty_of=DIFFICULTY)
    return b


def main() -> int:
    b = build()
    for level, notions in sorted(b.by_level().items(), key=lambda kv: kv[0].value):
        write_notion_file(DATA_DIR / "notions" / "MATHS" / f"{level.value}.json", Subject.MATHS, level,
                          Course.COMMON, link_sequential_prerequisites(notions), "pedagogy.ingest.maths_c3_2025")
    counts = {lv.value: len(ns) for lv, ns in b.by_level().items()}
    print(f"{len(b.notions)} notions prouvées {counts} ; {report_rejections(b.rejected)} ; "
          f"{len(b.orphans)} ligne(s) orpheline(s)")  # type: ignore[attr-defined]
    return 0 if not b.rejected and not b.orphans else 1  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
