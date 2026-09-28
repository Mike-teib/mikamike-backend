"""
Mathématiques lycée général — programmes en vigueur en 2026-2027.

  python -m pedagogy.ingest.maths_lycee

Écrit dans pedagogy/data/notions/MATHS/ :
  2NDE.json                         SRC-2NDE-MATHS-2026      (COMMON)
  1RE_SPECIALITE.json               SRC-1RE-MATHS-SPE-2026   (SPECIALITE)
  1RE_MATHS_SPECIFIQUES_1RE.json    SRC-1RE-MATHS-ES-2026    (MATHS_SPECIFIQUES_1RE)
  TLE_SPECIALITE.json               SRC-TLE-MATHS-SPE-2019   (SPECIALITE)
  TLE_MATHS_COMPLEMENTAIRES.json    SRC-TLE-MATHS-COMP-2019  (MATHS_COMPLEMENTAIRES)
  TLE_MATHS_EXPERTES.json           SRC-TLE-MATHS-EXP-2019   (MATHS_EXPERTES)

Mise en page des programmes : parties (domaines) → sections (chapitres) → rubriques
« Contenus », « Capacités attendues », « Démonstrations », « Exemples d'algorithme »,
« Approfondissements possibles »… chacune suivie d'une liste à puces (« − », « - », « • »
ou le glyphe privé « » des PDF 2019).

Granularité : une notion par puce de « Contenus » (contenu), « Capacités attendues »
(capacite), « Démonstrations » (demonstration) ; les puces « Approfondissements possibles »
et « Problèmes possibles » sont marquées optional_in_program=True, de même que les
« Démonstrations possibles » (mathématiques complémentaires). Les « Exemples d'algorithme »,
les paragraphes de commentaire (objectifs, histoire des mathématiques, descriptifs…) et les
thèmes d'étude des mathématiques complémentaires sont ignorés. Les automatismes (listés en
puces dans les programmes 2026) sont repris avec le domaine et le chapitre « Automatismes ».

Chaque notion passe par Builder.add : l'extrait doit figurer verbatim à la page déclarée du
PDF officiel (SHA-256 vérifié). Une notion ne chevauche jamais deux pages. Les formules
illisibles à l'extraction (police Symbol des PDF 2019, fractions éclatées sur plusieurs
lignes) sont tronquées à la dernière frontière de phrase lisible ; si rien de lisible ne
reste, la puce est ignorée et signalée (jamais réécrite).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from pedagogy.ingest.core import (
    Builder,
    Item,
    clean_line,
    link_sequential_prerequisites,
    report_rejections,
    write_notion_file,
)
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR

SCHOOL_YEAR = "2026-2027"
GENERATED_BY = "pedagogy.ingest.maths_lycee"

AUTO_DOMAIN = ("Automatismes", "AUTO")
# Les identifiants de notions ne portent pas l'enseignement : pour éviter qu'un même libellé
# (automatismes, analyse…) produise le même ID dans deux enseignements du même niveau, les
# enseignements autres que la spécialité préfixent leurs codes de domaine.
COURSE_CODE_PREFIX = {Course.MATHS_SPECIFIQUES_1RE: "E", Course.MATHS_COMPLEMENTAIRES: "C"}

# ---------------------------------------------------------------- rubriques
# mode -> (kind, optional)
MODES: Dict[str, Tuple[str, bool]] = {
    "contenu": ("contenu", False),
    "capacite": ("capacite", False),
    "demonstration": ("demonstration", False),
    "demonstration_possible": ("demonstration", True),
    "approfondissement": ("approfondissement", True),
}


def key(s: str) -> str:
    """Clé de comparaison des intitulés : apostrophes unifiées, sans espaces (les PDF 2019
    insèrent des espaces parasites dans les mots), casse ignorée."""
    s = unicodedata.normalize("NFKC", s).replace("’", "'").replace("‘", "'")
    s = s.replace("\uf0b7", "")  # puce des intitulés de section des PDF 2019
    return re.sub(r"\s+", "", s).casefold()


SECTION_HEADERS: Dict[str, Optional[str]] = {
    key("Contenus"): "contenu",
    key("Capacités attendues"): "capacite",
    key("Capacité attendue"): "capacite",
    key("Capacités"): "capacite",
    key("Démonstration"): "demonstration",
    key("Démonstrations"): "demonstration",
    key("Démonstration possible"): "demonstration_possible",
    key("Démonstrations possibles"): "demonstration_possible",
    key("Approfondissement possible"): "approfondissement",
    key("Approfondissements possibles"): "approfondissement",
    key("Problèmes possibles"): "approfondissement",
    # Tableau « Situations et problèmes | Contenus mathématiques » (maths intégrées à l'ES) :
    # seules les puces (colonne des contenus) sont reprises.
    key("Situations et problèmes Contenus mathématiques"): "contenu",
    # rubriques ignorées
    key("Exemple d'algorithme"): None,
    key("Exemples d'algorithme"): None,
    key("Exemples d'algorithmes"): None,
    key("Objectifs"): None,
    key("Histoire des mathématiques"): None,
    key("Commentaires"): None,
    key("Descriptif"): None,
    key("Contenus associés"): None,
}

# Puces : « − », « - », « – », « • » et le glyphe privé U+F02D des PDF 2019 (Symbol).
# (Détection locale : les lignes sont déjà nettoyées, la puce doit être suivie d'un espace.)
BULLET_RE = re.compile("^\\s*[-\u2212\u2013\u2022\uf02d]\\s+")


def is_bullet(s: str) -> bool:
    return bool(BULLET_RE.match(s)) and any(ch.isalnum() for ch in BULLET_RE.sub("", s, count=1))


def strip_bullet(s: str) -> str:
    return clean_line(BULLET_RE.sub("", s, count=1))


PUA_RE = re.compile("[-]")  # glyphes de la police Symbol (formules illisibles)


# ---------------------------------------------------------------- spécification
@dataclass(frozen=True)
class Head:
    """Intitulé attendu, dans l'ordre du document. kind : D (domaine), C (chapitre),
    A (sous-thème d'automatismes : puces = capacités), I (chapitre à puces directes = capacités)."""

    kind: str
    text: str
    code: str = ""


@dataclass(frozen=True)
class Spec:
    source_id: str
    level: Level
    course: Course
    filename: str
    difficulty: int
    program_version: str
    start_marker: str           # le parcours commence après la n-ième occurrence de cette ligne
    start_occurrence: int
    outline: Tuple[Head, ...]
    # Largeur (caractères) d'une ligne pleine : une puce terminée par « . » ou « ; » sur une ligne
    # plus courte est close. 0 : jamais (PDF 2019, où aucun commentaire ne suit une liste sans
    # intitulé, alors que des puces reprennent à la ligne après un point).
    wrap_width: int


def D(text: str, code: str) -> Head:
    return Head("D", text, code)


def C(text: str) -> Head:
    return Head("C", text)


def A(text: str) -> Head:
    return Head("A", text)


def I(text: str) -> Head:  # noqa: E743 — lisibilité des plans ci-dessous
    return Head("I", text)


AUTOS_2NDE = ("Calcul numérique et algébrique", "Proportions et pourcentages", "Évolutions et variations",
              "Fonctions et représentations", "Géométrie", "Statistiques", "Probabilités")
AUTOS_1RE = ("Évolutions et variations", "Calcul numérique et algébrique", "Fonctions et représentations",
             "Statistiques", "Probabilités")

SPECS: Tuple[Spec, ...] = (
    Spec("SRC-2NDE-MATHS-2026", Level.SECONDE, Course.COMMON, "2NDE.json", 3,
         "Programme de mathématiques de seconde générale et technologique — BO n°14 de 2026 (rentrée 2026)",
         "Programme", 2, (
             D("Vocabulaire ensembliste et logique", "LOG"),
             D("Algorithmique et programmation", "ALGO"),
             C("Variables et instructions élémentaires"), C("Notion de fonction"),
             D(*AUTO_DOMAIN), *(A(t) for t in AUTOS_2NDE),
             D("Nombres et calculs, algèbre", "NCA"), C("Arithmétique"), C("Nombres réels"), C("Algèbre"),
             D("Géométrie", "GEO"), C("Vecteurs et problèmes de géométrie"), C("Droites du plan"),
             D("Fonctions", "FON"), C("Représentation algébrique et graphique des fonctions"),
             C("Variations et extrémums d’une fonction"),
             D("Statistiques et probabilités", "SP"), C("Information chiffrée et statistique descriptive"),
             C("Croisement de deux variables qualitatives"), C("Probabilités"),
         ), 110),
    Spec("SRC-1RE-MATHS-SPE-2026", Level.PREMIERE, Course.SPECIALITE, "1RE_SPECIALITE.json", 4,
         "Programme de spécialité de mathématiques de première générale — BO n°14 de 2026 (rentrée 2026)",
         "Programme", 2, (
             D("Vocabulaire ensembliste et logique", "LOG"),
             D("Algorithmique et programmation", "ALGO"), I("Notion de liste"),
             D(*AUTO_DOMAIN), *(A(t) for t in AUTOS_1RE),
             D("Algèbre", "ALG"), C("Suites numériques, modèles discrets"),
             C("Équations, fonctions polynômes du second degré"),
             D("Analyse", "AN"), C("Dérivation"), C("Variations et courbes représentatives des fonctions"),
             C("Fonction exponentielle"), C("Trigonométrie"),
             D("Géométrie", "GEO"), C("Calcul vectoriel et produit scalaire"), C("Géométrie repérée"),
             D("Probabilités et statistiques", "PS"), C("Probabilités conditionnelles et indépendance"),
             C("Variables aléatoires réelles"), I("Expérimentations"),
         ), 110),
    Spec("SRC-1RE-MATHS-ES-2026", Level.PREMIERE, Course.MATHS_SPECIFIQUES_1RE, "1RE_MATHS_SPECIFIQUES_1RE.json", 4,
         "Programme de mathématiques intégré à l'enseignement scientifique de première générale — "
         "BO n°14 de 2026 (rentrée 2026)",
         "Contenus d'enseignement", 2, (
             D(*AUTO_DOMAIN), *(A(t) for t in AUTOS_1RE),
             D("Analyse de l'information chiffrée", "AIC"),
             D("Phénomènes aléatoires", "ALEA"),
             D("Phénomènes d'évolution, modélisation par des fonctions", "EVOL"),
             C("Variation linéaire"), C("Modélisation quadratique"), C("Variation exponentielle"),
         ), 110),
    Spec("SRC-TLE-MATHS-SPE-2019", Level.TERMINALE, Course.SPECIALITE, "TLE_SPECIALITE.json", 4,
         "Programme de spécialité de mathématiques de terminale générale — BO spécial n°8 du 25 juillet 2019 "
         "(en vigueur jusqu'en 2026-2027)",
         "Programme", 2, (
             D("Algèbre et géométrie", "AG"), C("Combinatoire et dénombrement"),
             C("Manipulation des vecteurs, des droites et des plans de l’espace"),
             C("Orthogonalité et distances dans l’espace"),
             C("Représentations paramétriques et équations cartésiennes"),
             D("Analyse", "AN"), C("Suites"), C("Limites des fonctions"), C("Compléments sur la dérivation"),
             C("Continuité des fonctions d’une variable réelle"), C("Fonction logarithme"),
             C("Fonctions sinus et cosinus"), C("Primitives, équations différentielles"), C("Calcul intégral"),
             D("Probabilités", "PROBA"), C("Succession d’épreuves indépendantes, schéma de Bernoulli"),
             C("Sommes de variables aléatoires"), C("Concentration, loi des grands nombres"),
             D("Algorithmique et programmation", "ALGO"), C("Notion de liste"),
             D("Vocabulaire ensembliste et logique", "LOG"),
         ), 0),
    Spec("SRC-TLE-MATHS-COMP-2019", Level.TERMINALE, Course.MATHS_COMPLEMENTAIRES, "TLE_MATHS_COMPLEMENTAIRES.json", 4,
         "Programme de l'option mathématiques complémentaires de terminale générale — BO spécial n°8 du "
         "25 juillet 2019 (en vigueur jusqu'en 2026-2027)",
         "Contenus", 2, (
             D("Analyse", "AN"), C("Suites numériques, modèles discrets"),
             C("Fonctions : continuité, dérivabilité, limites, représentation graphique"),
             C("Primitives et équations différentielles"), C("Fonctions convexes"), C("Intégration"),
             D("Probabilités et statistique", "PS"), C("Lois discrètes"), C("Lois à densité"),
             C("Statistique à deux variables quantitatives"),
             D("Algorithmique et programmation", "ALGO"),
             D("Vocabulaire ensembliste et logique", "LOG"),
         ), 0),
    Spec("SRC-TLE-MATHS-EXP-2019", Level.TERMINALE, Course.MATHS_EXPERTES, "TLE_MATHS_EXPERTES.json", 5,
         "Programme de l'option mathématiques expertes de terminale générale — BO spécial n°8 du 25 juillet 2019",
         "Programme", 2, (
             D("Nombres complexes", "CPLX"), C("Nombres complexes : point de vue algébrique"),
             C("Nombres complexes : point de vue géométrique"), C("Nombres complexes et trigonométrie"),
             C("Équations polynomiales"), C("Utilisation des nombres complexes en géométrie"),
             D("Arithmétique", "ARITH"),
             D("Graphes et matrices", "GM"),
         ), 0),
)
SPEC_BY_SOURCE = {s.source_id: s for s in SPECS}


# ---------------------------------------------------------------- extraction d'une puce
def _letters(s: str) -> int:
    return sum(ch.isalpha() for ch in s)


def _is_debris(line: str) -> bool:
    """Fragment de formule éclatée (numérateur, exposant…) : presque aucune lettre."""
    return _letters(line) <= 4


_BOUNDARY_RES = (re.compile(r"^(.*[.;])(?=\s|$)"), re.compile(r"^(.*\S\s?:)(?=\s|$)"))
MIN_LEN = 12
FALLBACK_MIN_LEN = 30
_DANGLING = {"à", "au", "aux", "de", "des", "du", "d", "en", "et", "la", "le", "les", "l", "ou", "par", "pour",
             "sur", "un", "une", "=", "×"}
_HYPHEN_BREAK = re.compile(r"\w-$")


def build_excerpt(lines: Sequence[str]) -> Tuple[Optional[str], Optional[str]]:
    """Texte verbatim d'une puce (lignes déjà nettoyées, puce retirée).

    Renvoie (extrait, remarque). La puce est coupée :
      - avant un glyphe de formule illisible (police Symbol, zone privée Unicode) ;
      - avant une formule éclatée sur plusieurs lignes (≥ 3 fragments quasi sans lettres) ;
      - avant un mot coupé par un trait d'union en fin de ligne (« moyenne-/écart type ») :
        la normalisation de la preuve recolle ces mots, l'extrait joint par une espace ne
        serait plus retrouvé verbatim.
    Après la coupe, on recule jusqu'à la dernière fin de phrase (« . », « ; ») ou « : ».
    À défaut (formule éclatée ou césure seulement), le début lisible est gardé s'il est assez
    long et ne se termine pas sur un mot-outil. Extrait None si rien de lisible ne subsiste."""
    cuts: List[Tuple[int, int, str]] = []
    for i, ln in enumerate(lines):
        m = PUA_RE.search(ln)
        if m:
            cuts.append((i, m.start(), "0pua"))
            break
    debris = [i for i, ln in enumerate(lines) if i and _is_debris(ln)]
    if len(debris) >= 3:
        cuts.append((debris[0], 0, "debris"))
    for i, ln in enumerate(lines[:-1]):
        if _HYPHEN_BREAK.search(ln) and re.match(r"\w", lines[i + 1]):
            tok = ln.rsplit(" ", 1)
            cuts.append((i, len(tok[0]) + 1 if len(tok) == 2 else 0, "cesure"))
            break
    if not cuts:
        return clean_line(" ".join(lines)), None
    i, pos, why = min(cuts)  # à position égale, « 0pua » l'emporte (pas de repli permissif)
    why = why.lstrip("0")
    text = clean_line(" ".join(list(lines[:i]) + [lines[i][:pos]]))
    for rx in _BOUNDARY_RES:
        m = rx.match(text)
        if m and len(m.group(1)) >= MIN_LEN:
            return m.group(1), f"tronque_{why}"
    if why != "pua":
        t = text.rstrip(" ,(")
        last = re.split(r"[\s’']", t)[-1].casefold() if t else ""
        if len(t) >= FALLBACK_MIN_LEN and last not in _DANGLING:
            return t, f"tronque_{why}"
    return None, f"illisible_{why}"


# ---------------------------------------------------------------- parcours d'un programme
@dataclass
class Parsed:
    items: List[Item] = field(default_factory=list)
    skipped: List[Tuple[int, str, str]] = field(default_factory=list)     # (page, raison, texte)
    truncated: List[Tuple[int, str, str]] = field(default_factory=list)   # (page, extrait, brut)
    page_breaks: List[Tuple[int, str, str]] = field(default_factory=list)  # (page, extrait, suite perdue)
    closures: List[Tuple[int, int, str]] = field(default_factory=list)     # (page, largeur, ligne suivante)
    garbled: List[Tuple[int, str]] = field(default_factory=list)           # (page, extrait) formule aplatie


def parse(spec: Spec, lines: Dict[int, List[str]]) -> Parsed:
    out = Parsed()
    outline = list(spec.outline)
    ptr = 0
    started = False
    seen_start = 0
    domain: Optional[Tuple[str, str]] = None
    chapter = ""
    mode: Optional[str] = None
    cur: List[str] = []
    cur_page = 0
    last_raw_len = 0

    def flush() -> None:
        nonlocal cur
        if cur and domain and mode:
            kind, optional = MODES[mode]
            excerpt, note = build_excerpt(cur)
            raw = clean_line(" ".join(cur))
            if excerpt is None:
                out.skipped.append((cur_page, note or "", raw))
            else:
                if note:
                    out.truncated.append((cur_page, excerpt, raw))
                elif any(_is_debris(ln) for ln in cur[1:]):
                    out.garbled.append((cur_page, excerpt))
                out.items.append(Item(level=spec.level, domain=domain[0],
                                      domain_code=COURSE_CODE_PREFIX.get(spec.course, "") + domain[1],
                                      chapter=chapter or domain[0], excerpt=excerpt, page=cur_page, kind=kind,
                                      difficulty=spec.difficulty, optional=optional))
        cur = []

    for p in sorted(lines):
        carried = bool(cur)
        flush()  # une notion ne chevauche jamais deux pages
        first_content = True
        for raw in lines[p]:
            s = clean_line(raw)
            if not s or s.startswith("©"):
                continue
            k = key(s)
            if not started:
                if k == key(spec.start_marker):
                    seen_start += 1
                    started = seen_start >= spec.start_occurrence
                continue
            if first_content:
                first_content = False
                prev = out.items[-1] if out.items else None
                if carried and prev and not is_bullet(s) and k not in SECTION_HEADERS \
                        and not (ptr < len(outline) and k == key(outline[ptr].text)) \
                        and (s[:1].islower() or not prev.excerpt.endswith((".", ";"))):
                    out.page_breaks.append((p - 1, prev.excerpt, s))
            # intitulés du plan (dans l'ordre du document)
            if ptr < len(outline) and k == key(outline[ptr].text):
                flush()
                h = outline[ptr]
                ptr += 1
                if h.kind == "D":
                    domain, chapter, mode = (h.text, h.code), "", None
                elif h.kind == "C":
                    chapter, mode = h.text, None
                elif h.kind == "A":
                    domain, chapter, mode = AUTO_DOMAIN, "Automatismes", "capacite"
                elif h.kind == "I":
                    chapter, mode = h.text, "capacite"
                continue
            if k in SECTION_HEADERS:
                flush()
                mode = SECTION_HEADERS[k]
                continue
            if mode is None:
                continue
            if is_bullet(s):
                body = strip_bullet(s)
                if s.lstrip().startswith("•") and cur:
                    cur.append(s)  # sous-puce : fait partie de la puce parente
                else:
                    flush()
                    cur, cur_page = [body], p
                last_raw_len = len(raw.rstrip())
                continue
            if not cur:
                continue  # sous-titre ou paragraphe hors puce
            ended = cur[-1].rstrip().endswith((".", ";"))
            subtitle = s[:1].isupper() and not s.endswith((".", ";", ",", ":")) and len(s) < 60
            if ended and not s[:1].islower() and (last_raw_len < spec.wrap_width or subtitle):
                out.closures.append((p, last_raw_len, s))
                flush()  # la puce était terminée : la ligne est un sous-titre ou un commentaire
                continue
            cur.append(s)
            last_raw_len = len(raw.rstrip())
    flush()
    if not started or ptr != len(outline):
        missing = outline[ptr].text if ptr < len(outline) else "(début)"
        raise RuntimeError(f"{spec.source_id}: plan non reconnu, intitulé attendu introuvable : {missing!r}")
    return out


# ---------------------------------------------------------------- construction
def build(spec: Spec) -> Tuple[Builder, Parsed]:
    b = Builder(spec.source_id, Subject.MATHS, spec.course, SCHOOL_YEAR, spec.program_version)
    parsed = parse(spec, b.lines)
    for it in parsed.items:
        b.add(it)
    return b, parsed


def build_all() -> List[Tuple[Spec, Builder, Parsed]]:
    return [(spec, *build(spec)) for spec in SPECS]


def main() -> int:
    total_rejected = 0
    for spec, b, parsed in build_all():
        notions = link_sequential_prerequisites(b.notions)
        write_notion_file(DATA_DIR / "notions" / "MATHS" / spec.filename, Subject.MATHS, spec.level, spec.course,
                          notions, GENERATED_BY)
        total_rejected += len(b.rejected)
        print(f"{spec.source_id} -> {spec.filename}: {len(notions)} notions prouvées ; "
              f"{report_rejections(b.rejected)}")
        for page, why, raw in parsed.skipped:
            print(f"  ignoré p{page} ({why}) : {raw[:100]!r}")
        for page, exc, raw in parsed.truncated:
            print(f"  tronqué p{page} : {exc[:70]!r} <- {raw[:100]!r}")
        for page, exc in parsed.garbled:
            print(f"  formule aplatie p{page} (à relire) : {exc[:100]!r}")
        for page, exc, lost in parsed.page_breaks:
            print(f"  coupure de page p{page} : {exc[:60]!r} / suite non reprise {lost[:60]!r}")
    return 0 if not total_rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
