"""
Mathématiques 4e et 3e (année scolaire 2026-2027) — programme du cycle 4 de 2020
(BO n°31 du 30 juillet 2020) découpé par année grâce aux repères annuels de progression
Éduscol (SRC-C4-REPERES-MATHS-2019).

  python -m pedagogy.ingest.maths_c4_2020
Écrit pedagogy/data/notions/MATHS/{4E,3E}.json (notions PROUVÉES, verbatim).

En 2026-2027, la 4e et la 3e suivent encore le programme 2020 (le programme 2026
s'applique en 4e en 2027-2028 et en 3e en 2028-2029).

MÉTHODE (attribution de l'année)
--------------------------------
Les repères annuels présentent chaque thème sous forme de tableau à trois colonnes
(5e | 4e | 3e ; en-tête explicite page 2). L'extraction linéaire de pypdf ne dit pas
à quelle colonne appartient un paragraphe : on relit donc chaque page avec les
coordonnées des fragments de texte (visitor pypdf) et on affecte chaque fragment à
une colonne selon son abscisse :
  - pages 2-3 (mise en page de la page d'en-tête) : 5e < 355 pt ≤ 4e < 565 pt ≤ 3e ;
  - pages 4-12 : 5e < 295 pt ≤ 4e < 530 pt ≤ 3e.
Deux contrôles de cohérence bloquants vérifient cette attribution sur le texte
officiel lui-même : « pas formalisés en 4e » doit tomber dans la colonne 4e (page 8)
et « configuration étudiée en quatrième » dans la colonne 3e (page 11).
Seules les colonnes 4e et 3e sont retenues (la 5e est hors périmètre).

Le texte d'une colonne est découpé en phrases ; chaque phrase est ensuite
relocalisée (sans tenir compte des espaces) dans l'extraction linéaire de la page et
c'est CE texte de la page qui devient l'extrait, prouvé verbatim par Builder.add.
Les phrases anaphoriques (« Ils… », « Celle-ci… », « Le lien est fait… ») sont
rattachées à la phrase précédente (texte contigu dans la même colonne). Les phrases
qui énoncent une limite ou une simple possibilité (« Aucune connaissance… »,
« … ne figure pas au programme », « Il est possible… », « Par exemple… ») ne sont
pas des notions : elles sont écartées et listées par excluded(). Une phrase retenue qui
contient « il est (cependant) possible » est marquée optional_in_program=True.

Le thème « Algorithmique et programmation » (page 13) est découpé en « niveaux »
et non en années (« Certains élèves sont capables de réaliser des activités de
troisième niveau dès le début du cycle »), et le programme 2020 (SRC-C4-2020,
thème E) ne donne aucune année : aucune notion AP n'est créée (pas de supposition).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pypdf import PdfReader

from pedagogy.ingest.core import Builder, Item, clean_line, link_sequential_prerequisites, report_rejections, \
    write_notion_file
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR, REPO_ROOT

SOURCE_ID = "SRC-C4-REPERES-MATHS-2019"
PROGRAM_VERSION = ("Programme du cycle 4 (BO n°31 du 30 juillet 2020) — repères annuels de progression Éduscol "
                   "(mathématiques, 2019)")
SCHOOL_YEAR = "2026-2027"
DIFFICULTY = {Level.QUATRIEME: 3, Level.TROISIEME: 3}
PAGES = range(2, 13)  # page 13 = algorithmique, découpée en niveaux et non en années

NC = ("Nombres et calculs", "NC")
OGDF = ("Organisation et gestion de données, fonctions", "OGDF")
GM = ("Grandeurs et mesures", "GM")
EG = ("Espace et géométrie", "EG")

# Titres de thèmes tels qu'imprimés dans le document → domaine du programme 2020.
THEMES: Dict[str, Tuple[str, str]] = {
    "Nombres décimaux relatifs": NC,
    "Fractions, nombres rationnels": NC,
    "Racine carrée": NC,
    "Puissances": NC,
    "Divisibilité, nombres premiers": NC,
    "Calcul littéral": NC,
    "Statistiques": OGDF,
    "Probabilités": OGDF,
    "Proportionnalité": OGDF,
    "Fonctions": OGDF,
    "Calculs sur des grandeurs mesurables": GM,
    "Effet des transformations sur des grandeurs géométriques": GM,
    "Représenter l’espace": EG,
    "Géométrie plane": EG,
    "Transformations": EG,
}
# Sous-titres (imprimés dans la colonne de gauche) : précisent le chapitre du thème courant.
SUBTHEMES: Dict[str, str] = {
    "Expressions littérales": "Calcul littéral",
    "Distributivité": "Calcul littéral",
    "Équations": "Calcul littéral",
    "Figures et configurations": "Géométrie plane",
}
PAGE_NOISE = {"(suite)", "> Repères annuels de progressio", "n pour le cycle 4"}

# Seuils d'abscisse (pt) : (début colonne 4e, début colonne 3e).
def column_bounds(page: int) -> Tuple[float, float]:
    return (355.0, 565.0) if page in (2, 3) else (295.0, 530.0)


CHAR_WIDTH = 4.3  # largeur moyenne d'un caractère (pt) pour détecter une ligne pleine largeur

ANAPHORA_RE = re.compile(r"^(Ils|Elles|Celle-ci|Celui-ci|Ceux-ci|Cela|Cette|Le lien est|Il est alors)\b")
EXCLUDE_RE = re.compile(
    r"^(Aucune?|Il est possible|Par exemple|Toutefois|La connaissance des formules générales|"
    r"Une progressivité)|ne figure(?:nt)? pas|n’est pas un attendu|ne sont pas formalisés"
)
# Les fragments PDF sont parfois accolés sans espace (« programme.Toutefois ») : \s* et non \s+.
# « il est (cependant) possible de… » à l'intérieur d'une phrase : contenu facultatif.
OPTIONAL_RE = re.compile(r"\bil est (?:cependant )?possible\b", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[a-zà-ÿ)»][.…])\s*(?=[A-ZÀ-ÖØ-Ý«])")


@dataclass
class Frag:
    x: float
    y: float
    text: str


def page_fragments(page_index: int) -> List[Frag]:
    from pedagogy.registry import load_registry

    src = load_registry().sources[SOURCE_ID]
    reader = PdfReader(str(REPO_ROOT / src.local_path))
    out: List[Frag] = []

    def visit(text, cm, tm, _fd, _fs):  # noqa: ANN001
        if text and text.strip():
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            out.append(Frag(x, y, text))

    reader.pages[page_index - 1].extract_text(visitor_text=visit)
    return out


def column_of(page: int, x: float) -> int:
    c4, c3 = column_bounds(page)
    return 0 if x < c4 else (1 if x < c3 else 2)


def header_rows(frags: List[Frag]) -> List[float]:
    """Ordonnées de la ligne d'en-tête « 5e 4e 3e » (chiffre suivi d'un « e » en exposant)."""
    ys = []
    for a, b in zip(frags, frags[1:]):
        if a.text.strip() in {"5", "4", "3"} and b.text.strip() == "e" and 0 < b.y - a.y < 8:
            ys.append(a.y)
    return ys


def full_width_rows(page: int, frags: List[Frag]) -> List[float]:
    """Ordonnées des lignes qui traversent plusieurs colonnes (texte valable pour tout le cycle)."""
    c4, _ = column_bounds(page)
    return [f.y for f in frags if f.x < 100 and f.x + CHAR_WIDTH * len(f.text.strip()) > c4 + 60]


def columns_by_chapter(page: int, chapter: Optional[str]) -> Tuple[Dict[Tuple[str, int], str], Optional[str], List[str]]:
    """Texte de chaque (chapitre, colonne) de la page, dans l'ordre du flux PDF."""
    frags = merge_titles(page_fragments(page))
    frags_body = [f for f in frags if f.text.strip() not in THEMES and f.text.strip() not in SUBTHEMES]
    skip_y = header_rows(frags_body) + full_width_rows(page, frags_body)
    full = full_width_rows(page, frags_body)
    skipped = [f.text.strip() for f in frags_body if any(abs(f.y - y) <= 6 for y in full)]
    theme = chapter.split(" — ")[0] if chapter else None
    texts: Dict[Tuple[str, int], str] = {}
    last_y: Dict[Tuple[str, int], float] = {}
    for f in frags:
        t = f.text.strip()
        if t in PAGE_NOISE or f.y > 520 or any(abs(f.y - y) <= 6 for y in skip_y):
            continue
        if t in THEMES:
            theme, chapter = t, t
            continue
        if t in SUBTHEMES and SUBTHEMES[t] == theme:
            chapter = f"{theme} — {t}"
            continue
        if chapter is None:
            continue
        key = (chapter, column_of(page, f.x))
        sep = "\n" if key in last_y and abs(last_y[key] - f.y) > 6 else ""
        texts[key] = texts.get(key, "") + sep + f.text
        last_y[key] = f.y
    return texts, chapter, skipped


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


THEME_KEYS = {_compact(k): k for k in list(THEMES) + list(SUBTHEMES)}


def merge_titles(frags: List[Frag]) -> List[Frag]:
    """Un titre peut être imprimé en plusieurs fragments (« Calcul » + « littéral ») :
    on fusionne jusqu'à 4 fragments consécutifs de même ordonnée s'ils forment un titre connu."""
    out: List[Frag] = []
    i = 0
    while i < len(frags):
        for n in (4, 3, 2):
            group = frags[i:i + n]
            if len(group) == n and all(abs(g.y - group[0].y) < 1 for g in group):
                joined = _compact("".join(g.text for g in group))
                if joined in THEME_KEYS:
                    out.append(Frag(group[0].x, group[0].y, THEME_KEYS[joined]))
                    i += n
                    break
        else:
            f = frags[i]
            key = _compact(f.text)
            out.append(Frag(f.x, f.y, THEME_KEYS[key]) if key in THEME_KEYS else f)
            i += 1
    return out


def split_sentences(text: str) -> List[str]:
    # Un débris de formule voisine (chiffres isolés) peut précéder la phrase : une phrase
    # commence à sa première majuscule.
    parts = [re.sub(r"^[^A-Za-zÀ-ÿ«]+(?=[A-ZÀ-ÖØ-Ý«])", "", clean_line(p))
             for p in SENTENCE_SPLIT_RE.split(clean_line(text)) if clean_line(p)]
    merged: List[str] = []
    for p in parts:
        if merged and ANAPHORA_RE.match(unicodedata.normalize("NFKC", p)):
            merged[-1] = f"{merged[-1]} {p}"
        else:
            merged.append(p)
    return merged


def locate_in_page(raw_page: str, sentence: str) -> Optional[str]:
    """Retrouve la phrase dans l'extraction linéaire de la page (espaces ignorés) et renvoie
    le texte de la page lui-même : l'extrait n'est jamais recomposé à la main."""
    compact, index = [], []
    for i, ch in enumerate(raw_page):
        if not ch.isspace():
            compact.append(ch)
            index.append(i)
    hay = "".join(compact)
    needle = re.sub(r"\s+", "", sentence)
    pos = hay.find(needle)
    if pos < 0 or not needle:
        return None
    return clean_line(raw_page[index[pos]:index[pos + len(needle) - 1] + 1])


_EXCLUDED: List[Tuple[int, str, str]] = []
_UNATTRIBUTED: List[Tuple[int, str]] = []


def excluded() -> List[Tuple[int, str, str]]:
    return list(_EXCLUDED)


def unattributed() -> List[Tuple[int, str]]:
    return list(_UNATTRIBUTED)


def build() -> Builder:
    _EXCLUDED.clear()
    _UNATTRIBUTED.clear()
    b = Builder(SOURCE_ID, Subject.MATHS, Course.COMMON, SCHOOL_YEAR, PROGRAM_VERSION)
    chapter: Optional[str] = None
    per_page: Dict[int, Dict[Tuple[str, int], str]] = {}
    for page in PAGES:
        texts, chapter, skipped = columns_by_chapter(page, chapter)
        per_page[page] = texts
        if skipped:
            _UNATTRIBUTED.append((page, clean_line(" ".join(skipped))))

    # Contrôles de cohérence de l'attribution des colonnes (bloquants).
    col8 = {c: clean_line(t) for (_, c), t in per_page[8].items() if "formalisés en 4" in clean_line(t)}
    col11 = {c: clean_line(t) for (_, c), t in per_page[11].items() if "étudiée en quatrième" in clean_line(t)}
    if set(col8) != {1} or set(col11) != {2}:
        raise RuntimeError(f"attribution_colonnes_incoherente: p8={set(col8)} p11={set(col11)}")

    for page, texts in per_page.items():
        raw = "\n".join(b.lines[page])
        for (chap, col), text in texts.items():
            if col == 0:
                continue  # colonne 5e : hors périmètre
            level = Level.QUATRIEME if col == 1 else Level.TROISIEME
            domain, code = THEMES[chap.split(" — ")[0]]
            for sentence in split_sentences(text):
                if EXCLUDE_RE.search(unicodedata.normalize("NFKC", sentence)):
                    _EXCLUDED.append((page, level.value, sentence))
                    continue
                excerpt = locate_in_page(raw, sentence) or sentence
                b.add(Item(level=level, domain=domain, domain_code=code, chapter=chap, excerpt=excerpt,
                           page=page, kind="repere_annuel", difficulty=DIFFICULTY[level],
                           optional=bool(OPTIONAL_RE.search(sentence))))
    return b


def main() -> int:
    b = build()
    for level in (Level.QUATRIEME, Level.TROISIEME):
        notions = b.by_level().get(level, [])
        write_notion_file(DATA_DIR / "notions" / "MATHS" / f"{level.value}.json", Subject.MATHS, level,
                          Course.COMMON, link_sequential_prerequisites(notions), "pedagogy.ingest.maths_c4_2020")
        print(f"{level.value}: {len(notions)} notions prouvées")
    print(report_rejections(b.rejected))
    print(f"{len(_EXCLUDED)} phrase(s) écartée(s) (limites / possibilités) :")
    for page, lv, s in _EXCLUDED:
        print(f"  p{page} {lv}: {s[:110]!r}")
    for page, s in _UNATTRIBUTED:
        print(f"  p{page} ligne pleine largeur non attribuée : {s[:110]!r}")
    return 0 if not b.rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
