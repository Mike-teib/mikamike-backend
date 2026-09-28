"""
Sciences et technologie à l'école et en 6e — année scolaire 2026-2027.

  python -m pedagogy.ingest.sciences_ecole
Écrit pedagogy/data/notions/ST/{CP,CE1,CE2,CM1,CM2,6E}.json (notions PROUVÉES, verbatim).

Sources et calendrier d'application retenus pour 2026-2027 (cf. notes du registre) :
  - SRC-C2-ST-2026 (programme 2026, cycle 2)      → CP, CE1, CE2 ;
  - SRC-C3-ST-2026 (programme 2026, cycle 3)      → CM1 uniquement (CM2 et 6e en 2027-2028) ;
  - SRC-C3-2020   (programme 2020, cycle 3, ST)   → CM2 et 6E.

Programmes 2026 : tableau « Objectifs d'apprentissage | Propositions de démarches et
d'activités ». Une notion par objectif (puce « - » commençant par un infinitif) ; les
propositions d'activités (« - L'élève… », « - À partir… ») sont ignorées.

Programme 2020 : tableaux « Connaissances et compétences associées | Exemples de
situations… ». Une notion par puce « - » de la colonne des connaissances, plus les
« Attendus de fin de cycle » (kind « attendu », rattachés à la 6e, fin du cycle 3).
L'année (CM2 ou 6E) n'est attribuée que d'après les « Repères de progressivité »
(table YEAR_2020, justification citée) ; à défaut, la notion va en 6E et figure dans
la liste explicite `unspecified_2020` (« attribution cycle non précisée »).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from pedagogy.ingest.core import Builder, Item, clean_line, found_on_page, link_sequential_prerequisites, \
    report_rejections, write_notion_file
from pedagogy.ingest.objectives import sommaire_entries
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR
from pedagogy.sources import normalize_for_match

SCHOOL_YEAR = "2026-2027"
GENERATED_BY = "pedagogy.ingest.sciences_ecole"
TABLE_MARKER = "Objectifs d’apprentissage"
DIFFICULTY = {Level.CP: 1, Level.CE1: 1, Level.CE2: 1, Level.CM1: 2, Level.CM2: 2, Level.SIXIEME: 2}

# --------------------------------------------------------------------------------------
# Programmes 2026 (cycle 2 et cycle 3)
# --------------------------------------------------------------------------------------

C2_SOURCE = "SRC-C2-ST-2026"
C3_SOURCE = "SRC-C3-ST-2026"
C2_LEVELS = {
    "Cours préparatoire": Level.CP,
    "Cours élémentaire première année": Level.CE1,
    "Cours élémentaire deuxième année": Level.CE2,
}
C3_LEVELS = {
    "Cours moyen première année": Level.CM1,
    "Cours moyen deuxième année": Level.CM2,
    "Sixième": Level.SIXIEME,
}
C2_DOMAINS = {
    "La matière, les mesures, l’électricité": "MAT",
    "Les êtres vivants dans leur environnement": "VIV",
    "Le corps humain et la santé": "CORPS",
    "Les objets techniques au cœur de la société": "TEC",
}
C3_DOMAINS = {
    "La matière, les mouvements et les signaux": "MAT",
    "Les êtres vivants dans leur environnement": "VIV",
    "Le corps humain et la santé": "CORPS",
    "Les objets techniques au cœur de la société": "TEC",
}

# Premier mot d'un objectif : un infinitif (éventuellement pronominal).
_INFINITIVE = re.compile(r"^(?:(?:S’|S'|Se )[a-zà-ÿ]+|[A-ZÀ-Ý][a-zà-ÿ]+)(?:er|ir|re|oir)\b")
_NOT_VERBS = {"Entre", "Contre", "Outre", "Autre", "Notre", "Votre", "Pour", "Sur", "Par", "Lors", "Hiver"}
_INLINE_BULLET = re.compile(r"(?<=[.;:)])\s+-\s+(?=\S)")
_SUBHEAD_MAX = 70


def _is_objective(text: str) -> bool:
    first = text.split(" ", 1)[0]
    return bool(_INFINITIVE.match(text)) and first not in _NOT_VERBS


def _join(parts: Sequence[str], st, page: int) -> str:
    """Recolle des lignes consécutives. Un trait d'union en fin de ligne est conservé
    (« physico-chimiques ») si l'extrait reste prouvable, sinon traité comme une césure,
    conformément à normalize_for_match."""
    text = ""
    for p in parts:
        p = clean_line(p)
        if not text:
            text = p
        elif text.endswith("-"):
            # Trait d'union conservé. Si la page ne le contient pas (normalize_for_match le
            # traite comme une césure), l'extrait sera refusé par Builder.add : on préfère
            # perdre la notion plutôt que stocker un libellé altéré (« grainesgermination »).
            text = text + p
        else:
            text = f"{text} {p}"
    return clean_line(text)


def _is_subheading(s: str) -> bool:
    return (len(s) <= _SUBHEAD_MAX and not s.startswith(("-", "−", "")) and s[:1].isupper()
            and not s.endswith((".", ";", ":", ",")) and "?" not in s)


def parse_objectives_2026(b: Builder, level_headings: Dict[str, Level], domains: Dict[str, str],
                          chapters: Sequence[str], first_page: int, keep: Sequence[Level]) -> List[str]:
    """Ajoute chaque objectif d'apprentissage (niveaux `keep`) ; renvoie les avertissements."""
    chapter_set = set(chapters)
    warnings: List[str] = []
    domain: Optional[Tuple[str, str]] = None
    level: Optional[Level] = None
    chapter = ""
    sub = ""
    in_table = False
    mode: Optional[str] = None  # "obj" | "act" | None
    cur: List[str] = []
    cur_page = 0

    def flush() -> None:
        nonlocal cur
        if cur and domain and level and level in keep:
            text = _join(cur, b.st, cur_page)
            text = re.sub(r"^-\s+", "", text)
            if not text.endswith("."):
                warnings.append(f"p{cur_page} {level.value} objectif sans point final : {text[:80]!r}")
            chap = f"{chapter or domain[0]} — {sub}" if sub else (chapter or domain[0])
            b.add(Item(level=level, domain=domain[0], domain_code=domain[1], chapter=chap, excerpt=text,
                       page=cur_page, kind="objectif", difficulty=DIFFICULTY[level]))
        cur = []

    for p in range(first_page, max(b.lines) + 1):
        page_lines = [clean_line(x) for x in b.lines.get(p, [])]
        page_lines = [x for x in page_lines if x]
        for i, s in enumerate(page_lines):
            nxt = page_lines[i + 1] if i + 1 < len(page_lines) else ""
            prev = page_lines[i - 1] if i else ""
            if s in domains:
                flush(); domain = (s, domains[s]); level = None; chapter = sub = ""; in_table = False; mode = None
                continue
            if s in level_headings:
                flush(); level = level_headings[s]; chapter = sub = ""; in_table = False; mode = None
                continue
            if s in chapter_set:
                flush(); chapter = s; sub = ""; in_table = False; mode = None
                continue
            if s.startswith(TABLE_MARKER):
                flush(); in_table = True; mode = None
                continue
            if level and _is_subheading(s) and nxt.startswith(TABLE_MARKER):
                flush(); sub = s; in_table = False; mode = None
                continue
            if not in_table:
                continue
            if (_is_subheading(s) and (mode != "obj" or not cur)
                    and (prev.startswith(TABLE_MARKER)
                         or (nxt.startswith("- ") and _is_objective(nxt[2:]) and mode != "obj"))):
                flush(); sub = s; mode = None
                continue
            if s.startswith("- "):
                for seg in _INLINE_BULLET.split(s[2:]):
                    flush()
                    if _is_objective(seg):
                        mode = "obj"; cur = [seg]; cur_page = p
                    else:
                        mode = "act"
                continue
            if mode == "obj":
                cur.append(s)
        # un objectif ne franchit pas une page (preuve page par page)
        flush()
        mode = None
    return warnings


# --------------------------------------------------------------------------------------
# Programme 2020 (cycle 3, sciences et technologie) → CM2 et 6E
# --------------------------------------------------------------------------------------

C3_2020_SOURCE = "SRC-C3-2020"
C3_2020_DOMAINS = {
    "Matière, mouvement, énergie, information": "MAT",
    "Le vivant, sa diversité et les fonctions qui le caractérisent": "VIV",
    "Matériaux et objets techniques": "TEC",
    "La planète Terre. Les êtres vivants dans leur environnement": "TER",
}

# Attribution d'année : (début du libellé officiel) → (niveau, justification tirée des
# « Repères de progressivité » du même thème, page indiquée). Tout libellé absent de cette
# table est rattaché à la 6E ET listé comme « attribution cycle non précisée ».
_CM = Level.CM2
_6E = Level.SIXIEME
YEAR_2020: Dict[str, Tuple[Level, str]] = {
    # Thème 1 — repères p81-82
    "Diversité de la matière": (_CM, "p81 « L’observation macroscopique de la matière sous une grande variété de formes et d’états, leur caractérisation et leurs usages relèvent des classes de CM1 et CM2 »"),
    "L’état physique d’un échantillon": (_CM, "p81 « L’observation macroscopique de la matière sous une grande variété de formes et d’états […] relèvent des classes de CM1 et CM2 »"),
    "Quelques propriétés de la matière solide": (_CM, "p81 « Des expériences simples sur les propriétés de la matière seront réalisées avec des réponses principalement « binaires » » (phrase rattachée à « CM1-CM2 »)"),
    "La matière qui nous entoure": (_CM, "p81 « Des exemples de mélanges solides […], liquides […] ou gazeux (air) seront présentés en CM1-CM2 »"),
    "Réaliser des mélanges peut provoquer": (_6E, "p81 « la classe de sixième permet d’approfondir : saturation d’une solution en sel […] On insistera en particulier sur la notion de mélange de constituants pouvant conduire à une transformation chimique »"),
    "Mouvement d’un objet (trajectoire": (_CM, "p82 « L’observation et la caractérisation de mouvements variés permettent d’introduire la vitesse et ses unités […] (CM1-CM2) »"),
    "Exemples de mouvements simples": (_CM, "p82 « L’observation et la caractérisation de mouvements variés […] (CM1-CM2) »"),
    "Mouvements dont la valeur de la vitesse": (_6E, "p82 « l’étude des mouvements à valeur de vitesse variable sera poursuivie en 6e »"),
    "Exemples de ressources en énergie": (_CM, "p82 « les différentes sources d’énergie sont abordés en CM1-CM2 »"),
    "Ressources renouvelables et non": (_CM, "p82 « les différentes sources d’énergie sont abordés en CM1-CM2 »"),
    "Exemples de convertisseurs": (_CM, "p82 « Des premières transformations d’énergie peuvent aussi être présentées en CM1-CM2 ; les objets techniques en charge de convertir les formes d’énergie sont identifiés »"),
    "Distinction entre signal et information": (_CM, "p82 « En CM1 et CM2 l’observation de communications entre élèves, puis de systèmes techniques simples permettra de progressivement distinguer la notion de signal »"),
    "Transmission d’une information par un": (_CM, "p82 « En CM1 et CM2 […] la notion de signal, comme grandeur physique, transportant une certaine quantité d’information »"),
    # Thème 2 — repères p84
    "Caractère commun, hérédité et relation": (_CM, "p84 « La mise en évidence des liens de parenté entre les êtres vivants peut être abordée dès le CM »"),
    "La cellule, une structure commune": (_6E, "p84 « La structure cellulaire doit en revanche être réservée à la classe de sixième »"),
    "Apports alimentaires : qualité et": (_CM, "p84 « Toutes les fonctions de nutrition ont vocation à être étudiées dès l’école élémentaire »"),
    "Origine des aliments consommés": (_CM, "p84 « Toutes les fonctions de nutrition ont vocation à être étudiées dès l’école élémentaire »"),
    "Apports discontinus de nourriture": (_CM, "p84 « Toutes les fonctions de nutrition ont vocation à être étudiées dès l’école élémentaire »"),
    "Organes de stockage": (_CM, "p84 « Toutes les fonctions de nutrition ont vocation à être étudiées dès l’école élémentaire »"),
    "Quelques techniques permettant d’éviter": (_6E, "p84 « Le rôle des microorganismes relève de la classe de sixième »"),
    # Thème 3 — repères p86
    "Besoin, fonction d'usage et d'estime": (_CM, "p86 « En CM1 et CM2 […] L’objet technique est à aborder en termes de description, de fonctions, de constitution »"),
    "Fonction technique, solutions techniques": (_CM, "p86 « En CM1 et CM2 […] L’objet technique est à aborder en termes de description, de fonctions, de constitution »"),
    "Représentation du fonctionnement d’un": (_CM, "p86 « En CM1 et CM2 […] L’objet technique est à aborder en termes de description, de fonctions, de constitution »"),
    "Comparaison de solutions techniques": (_CM, "p86 « En CM1 et CM2 […] L’objet technique est à aborder en termes de description, de fonctions, de constitution »"),
    "Caractéristiques et propriétés (aptitude": (_CM, "p86 « En CM1 et CM2, les matériaux utilisés sont comparés selon leurs caractéristiques dont leurs propriétés de recyclage en fin de vie »"),
    "Impact environnemental": (_6E, "p86 « En classe de sixième, des modifications de matériaux peuvent être imaginées par les élèves afin de prendre en compte leurs impacts environnementaux »"),
    "Recherche d’idées (schémas, croquis": (_6E, "p86 « La recherche de solutions en réponse à un problème posé dans un contexte de la vie courante est favorisée » (paragraphe « En classe de sixième »)"),
    "Modélisation du réel (maquette": (_6E, "p86 « la représentation partielle ou complète d’un objet […] sollicite les outils numériques courants » (paragraphe « En classe de sixième »)"),
    "Le stockage des données, notions": (_6E, "p86 « Les élèves sont progressivement mis en activité au sein d’une structure informatique en réseau sollicitant le stockage des données partagées » (paragraphe « En classe de sixième ») ; p82 « En classe de sixième, l’algorithme en lecture… »"),
    "Usage des moyens numériques dans un": (_6E, "p86 « au sein d’une structure informatique en réseau » (paragraphe « En classe de sixième »)"),
    # Thème 4 — repères p88
    "Les mouvements de la Terre sur elle-même": (_CM, "p88 « La description précise des mouvements est liée au thème (1) : CM2 et 6e » (première classe citée : CM2 ; pas de doublon)"),
    "Paysages, géologie locale": (_CM, "p88 « La mise en relation des paysages ou des phénomènes géologiques avec la nature du sous-sol et l’activité interne de la Terre peut être étudiée dès le CM »"),
    "Phénomènes géologiques traduisant": (_CM, "p88 « La mise en relation des paysages ou des phénomènes géologiques […] peut être étudiée dès le CM » (les explications géologiques relèvent de la 6e)"),
}


# Intitulés de sous-parties dont le libellé diffère de l'attendu correspondant.
EXTRA_HEADINGS_2020 = (
    "Mettre en évidence l’interdépendance des différents êtres vivants dans un réseau trophique",
)


def _year_2020(text: str) -> Tuple[Level, Optional[str]]:
    for prefix, (lvl, why) in YEAR_2020.items():
        if normalize_for_match(text).startswith(normalize_for_match(prefix)):
            return lvl, why
    return Level.SIXIEME, None


@dataclass
class Report2020:
    decisions: List[Tuple[str, str, str]] = field(default_factory=list)  # (notion_id, niveau, justification)
    unspecified: List[str] = field(default_factory=list)                   # notion_id rattachés à la 6E par défaut
    attendus: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _ended(text: str) -> bool:
    return text.rstrip().endswith((".", ";", "…"))


def parse_2020(b: Builder, first_page: int = 79, last_page: int = 88) -> Report2020:
    rep = Report2020()
    domain: Optional[Tuple[str, str]] = None
    attendus: List[str] = []           # attendus du thème courant (titres de chapitre)
    chapter = ""
    state: Optional[str] = None        # "attendus" | "table" | None
    cur: List[str] = []
    cur_page = 0

    def chapter_of(line: str) -> Optional[str]:
        n = normalize_for_match(line)
        if len(n) < 20:
            return None
        for a in list(attendus) + list(EXTRA_HEADINGS_2020):
            if normalize_for_match(a).startswith(n):
                return a
        return None

    def flush() -> None:
        nonlocal cur
        if not cur or not domain:
            cur = []
            return
        text = re.sub(r"^-\s+", "", _join(cur, b.st, cur_page))
        if not _ended(text):
            rep.warnings.append(f"p{cur_page} puce sans ponctuation finale : {text[:80]!r}")
        if state == "attendus":
            attendus.append(text.rstrip(" ."))
            rep.attendus.append(text)
            b.add(Item(level=Level.SIXIEME, domain=domain[0], domain_code=domain[1], chapter=domain[0],
                       excerpt=text, page=cur_page, kind="attendu", difficulty=DIFFICULTY[Level.SIXIEME]))
        else:
            lvl, why = _year_2020(text)
            added = b.add(Item(level=lvl, domain=domain[0], domain_code=domain[1], chapter=chapter or domain[0],
                               excerpt=text, page=cur_page, kind="connaissance", difficulty=DIFFICULTY[lvl]))
            if added is not None and why is None:
                rep.unspecified.append(added.notion_id)
            elif added is not None:
                rep.decisions.append((added.notion_id, lvl.value, why))
        cur = []

    for p in range(first_page, last_page + 1):
        for raw in b.lines.get(p, []):
            s = clean_line(raw)
            if not s or s.startswith("©"):
                continue
            if s in C3_2020_DOMAINS:
                flush(); domain = (s, C3_2020_DOMAINS[s]); attendus = []; chapter = ""; state = None
                continue
            if domain is None:
                continue
            if s.startswith("Attendus de fin de cycle"):
                flush(); state = "attendus"
                continue
            if s.startswith("Connaissances et compétence"):
                flush(); state = "table"
                continue
            if s.startswith("Repères de progressivité"):
                flush(); state = None
                continue
            if state is None:
                continue
            if state == "table":
                ch = chapter_of(s)
                if ch and not s.startswith("- "):
                    flush(); chapter = ch
                    continue
            if s.startswith("- "):
                flush(); cur = [s]; cur_page = p
                continue
            if cur and not _ended(_join(cur, b.st, cur_page)):
                cur.append(s)
            else:
                flush()
        flush()  # une puce ne franchit pas une page
    return rep


# --------------------------------------------------------------------------------------
# Construction et écriture
# --------------------------------------------------------------------------------------

@dataclass
class Build:
    builders: List[Builder]
    warnings: List[str]
    report_2020: Report2020

    @property
    def notions(self):
        return [n for bl in self.builders for n in bl.notions]

    @property
    def rejected(self):
        return [r for bl in self.builders for r in bl.rejected]


def _chapters(b: Builder, levels: Dict[str, Level], domains: Dict[str, str]) -> List[str]:
    som = sommaire_entries(b.lines)
    return [x for x in som if x not in levels and x not in domains and x != "Principes"
            and not x.startswith(("Contribution", "L’égalité", "Organisation du programme"))]


def build() -> Build:
    warnings: List[str] = []
    c2 = Builder(C2_SOURCE, Subject.SCIENCES_TECHNOLOGIE, Course.COMMON, SCHOOL_YEAR,
                 "Programme de sciences et technologie du cycle 2 — BO 2026, annexe 1 (NOR MENE2611650A)")
    warnings += parse_objectives_2026(c2, C2_LEVELS, C2_DOMAINS, _chapters(c2, C2_LEVELS, C2_DOMAINS),
                                      first_page=2, keep=list(C2_LEVELS.values()))
    c3 = Builder(C3_SOURCE, Subject.SCIENCES_TECHNOLOGIE, Course.COMMON, SCHOOL_YEAR,
                 "Programme de sciences et technologie du cycle 3 — BO 2026, annexe 2 (NOR MENE2611650A) ; "
                 "appliqué au CM1 en 2026-2027")
    warnings += parse_objectives_2026(c3, C3_LEVELS, C3_DOMAINS, _chapters(c3, C3_LEVELS, C3_DOMAINS),
                                      first_page=2, keep=[Level.CM1])
    old = Builder(C3_2020_SOURCE, Subject.SCIENCES_TECHNOLOGIE, Course.COMMON, SCHOOL_YEAR,
                  "Programme du cycle 3 — sciences et technologie — BO n°31 du 30 juillet 2020 (version consolidée) ; "
                  "appliqué au CM2 et en 6e en 2026-2027")
    rep = parse_2020(old)
    warnings += rep.warnings
    return Build([c2, c3, old], warnings, rep)


LEVELS_OUT = (Level.CP, Level.CE1, Level.CE2, Level.CM1, Level.CM2, Level.SIXIEME)


def by_level(res: Build) -> Dict[Level, list]:
    out: Dict[Level, list] = {lvl: [] for lvl in LEVELS_OUT}
    for n in res.notions:
        out[n.level].append(n)
    return out


def main() -> int:
    res = build()
    for level, notions in by_level(res).items():
        write_notion_file(DATA_DIR / "notions" / "ST" / f"{level.value}.json", Subject.SCIENCES_TECHNOLOGIE, level,
                          Course.COMMON, link_sequential_prerequisites(notions), GENERATED_BY)
        print(f"{level.value}: {len(notions)} notions")
    print(f"{len(res.notions)} notions prouvées ; {report_rejections(res.rejected)}")
    for w in res.warnings:
        print("AVERTISSEMENT", w)
    print(f"Attribution cycle non précisée (→ 6E) : {len(res.report_2020.unspecified)}")
    for u in res.report_2020.unspecified:
        print("  ", u)
    print(f"Attributions justifiées par les repères de progressivité : {len(res.report_2020.decisions)}")
    for nid, lvl, why in res.report_2020.decisions:
        print(f"   {lvl} {nid} ← {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
