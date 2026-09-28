"""
Physique-chimie et SVT, cycle 4 (5e, 4e, 3e) — programme consolidé 2020 (SRC-C4-2020,
BO n°31 du 30 juillet 2020, annexe 3), pour l'année scolaire 2026-2027.

  python -m pedagogy.ingest.sciences_c4_2020
Écrit pedagogy/data/notions/PC/{5E,4E,3E}.json et pedagogy/data/notions/SVT/{5E,4E,3E}.json
(notions PROUVÉES, libellés recopiés verbatim, review_status=NOT_REVIEWED).

Extraction
----------
Le PDF met en page des tableaux à deux colonnes (« Connaissances et compétences associées » |
« Exemples de situations, d'activités… ») dont les lignes s'entremêlent à l'extraction. On
déclare donc, page par page, des SEGMENTS de la colonne de gauche délimités par le début de
leur première ligne et le début de la première ligne qui ne leur appartient plus. Dans un
segment, chaque tiret « - » ouvre une connaissance (kind « connaissance »), chaque phrase sans
tiret une compétence (kind « capacite ») ; les « Attendus de fin de cycle » donnent des items
de kind « attendu ». Le texte des items vient TOUJOURS du PDF (jamais saisi à la main) et chaque
item est prouvé verbatim sur sa page par Builder.add (SHA-256 + recherche exacte). Sont écartés
avant promotion (et listés dans le rapport) : les items coupés par une césure de fin de ligne
(« micro-/organismes » : le texte extrait perd le trait d'union, la preuve verbatim est
impossible sans altérer le libellé), les items contenant un glyphe de police « Symbol » extrait
hors Unicode standard (« ρ » lu U+F072) et les items à cheval sur deux pages.

Attribution à une classe (règle MikaMike)
-----------------------------------------
Le programme fixe des attendus de FIN DE CYCLE ; aucune répartition annuelle officielle n'est
disponible dans le dépôt. On attribue une notion à la 5e, 4e ou 3e :
  1. EXPLICITE quand les « Repères de progressivité » le disent (« dès la classe de 5e »,
     « à partir de la classe de 4e », « réservée à la classe de 3e », « objectif de fin de
     cycle »…) ; la citation est vérifiée verbatim sur la page du repère ;
  2. sinon (attribution MikaMike À VALIDER) : les attendus de fin de cycle vont en 3e ; les
     autres items suivent l'ordre donné par le repère de leur thème s'il est clair
     (« on passe progressivement de … à … » : début → 5e, fin → 3e) ; à défaut, 4e.
Chaque attribution est tracée dans ATTRIBUTIONS (affichée par main()).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from pedagogy.ingest.core import Builder, Item, clean_line, link_sequential_prerequisites, report_rejections, \
    write_notion_file
from pedagogy.models import Course, Level, Subject
from pedagogy.registry import DATA_DIR
from pedagogy.sources import normalize_for_match

SOURCE_ID = "SRC-C4-2020"
SCHOOL_YEAR = "2026-2027"
PROGRAM_VERSION = "Programme du cycle 4 — BO n°31 du 30 juillet 2020 (version consolidée)"
GENERATED_BY = "pedagogy.ingest.sciences_c4_2020"
DIFFICULTY = {Level.CINQUIEME: 2, Level.QUATRIEME: 3, Level.TROISIEME: 3}
ATTENDUS = "Attendus de fin de cycle"

DOMAINS: Dict[str, Tuple[Subject, str]] = {
    "MAT": (Subject.PHYSIQUE_CHIMIE, "Organisation et transformations de la matière"),
    "MVT": (Subject.PHYSIQUE_CHIMIE, "Mouvement et interactions"),
    "NRJ": (Subject.PHYSIQUE_CHIMIE, "L’énergie, ses transferts et ses conversions"),
    "SIG": (Subject.PHYSIQUE_CHIMIE, "Des signaux pour observer et communiquer"),
    "TER": (Subject.SVT, "La planète Terre, l’environnement et l’action humaine"),
    "VIV": (Subject.SVT, "Le vivant et son évolution"),
    "CORPS": (Subject.SVT, "Le corps humain et la santé"),
}


@dataclass(frozen=True)
class Segment:
    """Plage de lignes d'une page appartenant à la colonne « connaissances et compétences »
    (ou à la liste des attendus). ``stop`` = début de la première ligne exclue (None : fin de page).
    ``breaks`` = débuts de ligne qui ouvrent forcément un nouvel item."""

    page: int
    domain_code: str
    chapter: str
    start: str
    stop: Optional[str]
    breaks: Tuple[str, ...] = ()


# Rubriques du tableau (PC) ; pour les SVT, rubriques des « Repères de progressivité ».
C_CONST = "Décrire la constitution et les états de la matière"
C_TRANSF = "Décrire et expliquer des transformations chimiques"
C_PROPR = "Propriétés de quelques transformations chimiques"
C_UNIV = "Décrire l’organisation de la matière dans l’Univers"
C_MOUV = "Caractériser un mouvement"
C_FORCE = "Modéliser une action exercée sur un objet par une force caractérisée par une direction, un sens et une valeur"
C_ENERG = ("Identifier les sources, les transferts, les conversions et les formes d’énergie — "
           "Utiliser la conservation de l’énergie")
C_ELEC = "Réaliser des circuits électriques simples et exploiter les lois de l’électricité"
C_LUM = "Signaux lumineux"
C_SON = "Signaux sonores"
C_GEO = "Les phénomènes géologiques liés au fonctionnement de la Terre / éléments de climatologie et de météorologie"
C_RESS = "Ressources naturelles, écosystèmes et activités humaines"
C_NUTR = "La nutrition des organismes"
C_DYN = "La dynamique des populations"
C_GEN = "La diversité génétique des individus"
C_EVOL = "La classification du vivant et l’évolution des êtres vivants"
C_NERV = "Activités musculaire, nerveuse et cardiovasculaire ; activité cérébrale"
C_ALIM = "Alimentation et digestion"
C_MICR = "Relations avec le monde microbien"
C_REPR = "Reproduction et sexualité"
CONNAISSANCES = "Connaissances et compétences"

SEGMENTS: Tuple[Segment, ...] = (
    # ---------------- Physique-chimie ----------------
    Segment(97, "MAT", ATTENDUS, "- Décrire la constitution et les états", CONNAISSANCES),
    Segment(97, "MAT", C_CONST, "Caractériser les différents états de la matière", "On mettra en œuvre des expériences"),
    Segment(98, "MAT", C_CONST, "Concevoir et réaliser des expériences pour", "Ces études sont l’occasion"),
    Segment(98, "MAT", C_TRANSF, "Mettre en œuvre des tests caractéristiques", "Cette partie prendra appui"),
    Segment(98, "MAT", C_PROPR, "Identifier le caractère acide ou basique", "Ces différentes transformations chimiques"),
    Segment(99, "MAT", C_PROPR, "- Ions H+ et OH-.", "de serre, acidification des océans"),
    Segment(99, "MAT", C_UNIV, "Décrire la structure de l’Univers et du système", "Ce thème fait prendre conscience"),
    Segment(100, "MVT", ATTENDUS, "- Caractériser un mouvement.", CONNAISSANCES),
    Segment(100, "MVT", C_MOUV, "Caractériser le mouvement d’un objet.", "L’ensemble des notions de cette partie"),
    Segment(100, "MVT", C_FORCE, "Identifier les actions mises en jeu", "L’étude mécanique d’un système"),
    Segment(101, "NRJ", ATTENDUS, "- Identifier les sources, les transferts", CONNAISSANCES),
    Segment(101, "NRJ", C_ENERG, "Identifier les différentes formes d’énergie.", "Les supports d’enseignement gagnent"),
    Segment(102, "NRJ", C_ENERG, "Associer l’émission et l’absorption", "L’étude privilégie des situations"),
    Segment(102, "NRJ", C_ELEC, "Élaborer et mettre en œuvre un protocole", "Les exemples de circuits électriques"),
    Segment(103, "SIG", ATTENDUS, "- Caractériser différents types de signaux", CONNAISSANCES),
    Segment(103, "SIG", C_LUM, "Distinguer une source primaire", "L’exploitation de la propagation"),
    Segment(103, "SIG", C_SON, "Décrire les conditions de propagation d’un son.", "Les exemples abordés privilégient"),
    # ---------------- SVT ----------------
    Segment(108, "TER", ATTENDUS, "- Explorer et expliquer certains phénomènes géologiques", CONNAISSANCES),
    Segment(108, "TER", C_GEO, "Expliquer quelques phénomènes", "Les exemples locaux ou régionaux"),
    Segment(108, "TER", C_GEO, "Expliquer quelques phénomènes", None),
    Segment(109, "TER", C_GEO, "- Les phénomènes naturels : risques", "biotechnologies, des solutions"),
    Segment(109, "TER", C_RESS, "Caractériser quelques-uns des principaux", "Repères de progressivité"),
    Segment(110, "VIV", ATTENDUS, "- Expliquer l’organisation et le fonctionnement du monde vivant", CONNAISSANCES),
    Segment(110, "VIV", C_NUTR, "Relier les besoins en nutriments", "Ce thème se prête notamment"),
    Segment(110, "VIV", C_DYN, "Relier des éléments de biologie de la", "On privilégie des observations"),
    Segment(111, "VIV", C_EVOL, "Relier l’étude des relations de parenté", "certains organismes vivants."),
    Segment(111, "VIV", C_EVOL, "Utiliser des connaissances pour évaluer", "Ce thème se prête à l’étude"),
    Segment(111, "VIV", C_EVOL, "Montrer que certains événements majeurs", "Expliquer sur quoi reposent"),
    Segment(111, "VIV", C_GEN, "Expliquer sur quoi reposent", "Mettre en évidence des faits d’évolution"),
    Segment(111, "VIV", C_EVOL, "Mettre en évidence des faits d’évolution", "Repères de progressivité"),
    Segment(112, "CORPS", ATTENDUS, "- Expliquer quelques processus biologiques", CONNAISSANCES),
    Segment(112, "CORPS", C_NERV, "Expliquer comment le système nerveux", "Ce thème se prête :",
            breaks=("Mettre en évidence le rôle du cerveau",)),
    Segment(112, "CORPS", C_ALIM, "Expliquer le devenir des aliments", "Relier le monde microbien"),
    Segment(112, "CORPS", C_MICR, "Relier le monde microbien", None),
    Segment(113, "CORPS", C_MICR, "- Réactions immunitaires.", "changement climatique."),
    Segment(113, "CORPS", C_REPR, "Relier le fonctionnement des appareils", "Repères de progressivité"),
)


@dataclass(frozen=True)
class Rule:
    """Attribution d'une classe à des items (repérés par le début de leur libellé officiel).
    ``quote`` : extrait du repère de progressivité (vérifié verbatim sur ``page``)."""

    level: Level
    explicit: bool
    page: int
    quote: str
    prefixes: Tuple[str, ...]


L5, L4, L3 = Level.CINQUIEME, Level.QUATRIEME, Level.TROISIEME
RULES: Tuple[Rule, ...] = (
    # --- Organisation et transformations de la matière (repères p. 99-100)
    Rule(L5, True, 99, "Dès la classe de 5 e, les activités proposées permettent de consolider", (
        "Caractériser les différents états de la matière", "Proposer et mettre en œuvre un protocole expérimental pour étudier",
        "Caractériser les différents changements d’état", "Espèce chimique", "Corps pur et mélange",
        "Changements d’états de la matière", "Conservation de la masse, variation du volume")),
    Rule(L5, True, 99, "transformations chimiques peut être développée à partir de la classe de 5e", (
        "Interpréter les changements d’état au niveau microscopique",
        "Interpréter une transformation chimique comme une redistribution", "Notions de molécules, atomes, ions")),
    Rule(L4, True, 99, "masse volumique se fait progressivement à partir de la classe de 4e", (
        "Proposer et mettre en œuvre un protocole expérimental pour déterminer une masse volumique",
        "Exploiter des mesures de masse volumique")),
    Rule(L5, True, 99, "Les notions de miscibilité et de solubilité peuvent être introduites expérimentalement dès le "
                       "début du cycle", ("Solubilité.", "Miscibilité.", "Estimer expérimentalement une valeur de solubilité")),
    Rule(L5, False, 99, "Les notions de miscibilité et de solubilité peuvent être introduites expérimentalement dès le "
                        "début du cycle", ("Concevoir et réaliser des expériences pour caractériser des mélanges",)),
    Rule(L5, True, 99, "introduire expérimentalement des exemples de transformations chimiques dès la classe de 5 e", (
        "Mettre en œuvre des tests caractéristiques", "Identifier expérimentalement une transformation chimique",
        "Distinguer transformation chimique et mélange")),
    Rule(L4, True, 99, "de réaction pour modéliser les transformations peut être initiée en classe de 4 e", (
        "Utiliser une équation de réaction chimique fournie",)),
    Rule(L4, True, 100, "Le tableau périodique est considéré à partir de la classe de 4e", (
        "Associer leurs symboles aux éléments",)),
    Rule(L3, True, 100, "structure interne du noyau peut être réservée à la classe de 3 e", ("Constituants de l’atome",)),
    # --- Mouvement et interactions (p. 101)
    Rule(L5, True, 101, "Le concept de vitesse est réinvesti et approfondi dès le début du cycle 4 en introduisant les "
                        "caractéristiques direction et sens", ("Vitesse : direction, sens et valeur",)),
    Rule(L5, False, 101, "Le concept de vitesse est réinvesti et approfondi dès le début du cycle 4",
         ("Caractériser le mouvement d’un objet",)),
    Rule(L5, True, 101, "de contact ou à distance peut être abordée de manière descriptive dès le début du cycle 4", (
        "Action de contact et action à distance",)),
    Rule(L4, True, 101, "si possible dès la classe de 4 e, ces interactions sont modélisées par la", (
        "Identifier les actions mises en jeu", "Force : direction, sens et valeur")),
    Rule(L3, True, 101, "En fin de cycle 4, un élève sait exploiter l'expression de la force de gravitation universelle", (
        "Exploiter l’expression littérale scalaire", "Force de pesanteur et son expression P=mg")),
    # --- L'énergie (p. 102-103)
    Rule(L5, True, 102, "La classe de 5 e est l'occasion de revenir sur les attendus du cycle 3 concernant les sources et "
                        "les conversions", ("Sources.", "Conversion d’une forme d’énergie en une autre")),
    Rule(L3, True, 102, "La pleine maîtrise de la relation entre puissance et énergie est un objectif de fin de cycle", (
        "Utiliser la relation liant puissance, énergie et durée",)),
    Rule(L3, False, 102, "La pleine maîtrise de la relation entre puissance et énergie est un objectif de fin de cycle", (
        "Notion de puissance",)),
    Rule(L3, True, 102, "L'expression littérale de l'énergie cinétique peut être réservée à la classe de 3 e", (
        "Énergies cinétique",)),
    Rule(L3, True, 102, "maîtrise de la notion de conservation de l'énergie est également un objectif de fin de cycle", (
        "Conservation de l’énergie.",)),
    Rule(L3, False, 102, "maîtrise de la notion de conservation de l'énergie est également un objectif de fin de cycle", (
        "Établir un bilan énergétique",)),
    Rule(L5, True, 103, "Dès la classe de 5e, la mise en œuvre de circuits simples", (
        "Élaborer et mettre en œuvre un protocole expérimental simple",)),
    Rule(L5, False, 103, "Dès la classe de 5e, la mise en œuvre de circuits simples", (
        "Dipôles en série, dipôles en dérivation",)),
    Rule(L4, True, 103, "les différentes lois de l'électricité peuvent être abordées sans", (
        "Exploiter les lois de l’électricité", "L’intensité du courant électrique est la même",
        "Loi d’additivité des tensions", "Loi d’additivité des intensités", "Relation tension-courant")),
    Rule(L3, True, 103, "Les aspects énergétiques peuvent être réservés à la classe de 3e", (
        "Conduire un calcul de consommation d’énergie", "Puissance électrique P= U.I",
        "Relation liant l’énergie, la puissance électrique")),
    # --- Signaux (p. 103)
    Rule(L3, True, 103, "La maîtrise de la notion de fréquence est un objectif de fin de cycle", ("Notion de fréquence",)),
    # --- SVT : la planète Terre (p. 109-110)
    Rule(L5, False, 109, "L'exploration peut débuter au niveau local ou au niveau régional", (
        "Caractériser quelques-uns des principaux enjeux", "L’exploitation de quelques ressources naturelles",
        "Expliquer les choix en matière de gestion")),
    Rule(L3, False, 110, "le contexte global du fonctionnement de la planète Terre travaillé plutôt en fin de cycle", (
        "Expliquer comment une activité humaine peut modifier",)),
    # --- SVT : le vivant (p. 111)
    Rule(L5, False, 111, "on passe progressivement de l'organisation fonctionnelle à l'échelle des organismes", (
        "Relier les besoins en nutriments", "Nutrition et organisation fonctionnelle",
        "Relier les besoins des cellules d’une plante")),
    Rule(L5, False, 111, "de l'étude de la diversité des modes de reproduction et des modalités de rencontre des gamètes", (
        "Relier des éléments de biologie de la reproduction", "Reproductions sexuée et asexuée")),
    Rule(L4, False, 111, "à la transmission du patrimoine génétique", ("Gamètes et patrimoine génétique",)),
    Rule(L3, False, 111, "au maintien des espèces et à la dynamique des populations", ("Dynamique des populations et",)),
    Rule(L5, False, 111, "du constat de la diversité des êtres vivants et de leurs interactions", (
        "Diversité et dynamique du monde vivant",)),
    Rule(L3, False, 111, "aux mécanismes à l'origine de cette diversité", (
        "Expliquer les mécanismes à l’origine de la diversité", "ADN, mutations, brassage",
        "Expliquer comment les phénotypes")),
    Rule(L3, False, 111, "Dès que les élèves ont les bases génétiques et paléontologiques suffisantes", (
        "Mettre en évidence des faits d’évolution", "Apparition et disparition d’espèces", "Maintien des formes aptes")),
    # --- SVT : le corps humain (p. 113)
    Rule(L5, True, 113, "permet dès le début du cycle de découvrir l'organisation fonctionnelle du système", (
        "Expliquer comment le système nerveux", "Rythmes cardiaque et respiratoire")),
    Rule(L4, True, 113, "le fonctionnement cérébral ne seront développés qu'à partir de la 4e", (
        "Mettre en évidence le rôle du cerveau", "Message nerveux", "Relier quelques comportements",
        "Activité cérébrale")),
    Rule(L3, False, 113, "moléculaires à la classe de 3 e", (
        "Expliquer le devenir des aliments", "Système digestif, digestion")),
    Rule(L3, True, 113, "l'explication globale est atteinte en classe de 3e", ("Réactions immunitaires",)),
)


@dataclass(frozen=True)
class Parsed:
    seg: Segment
    kind: str
    text: str
    skip_reason: Optional[str] = None


@dataclass(frozen=True)
class Attribution:
    subject: Subject
    level: Level
    domain_code: str
    excerpt: str
    page: int
    explicit: bool
    justification: str


def _is_dash(line: str) -> bool:
    return line.startswith("- ") or line == "-"


def _find(lines: Sequence[str], prefix: str, frm: int) -> int:
    for i in range(frm, len(lines)):
        if lines[i].startswith(prefix):
            return i
    raise ValueError(f"marqueur_introuvable:{prefix!r}")


def parse_segments(page_lines: Dict[int, List[str]]) -> List[Parsed]:
    """Découpe chaque segment en items (texte du PDF, lignes jointes par une espace)."""
    out: List[Parsed] = []
    pos: Dict[int, int] = {}
    for seg in SEGMENTS:
        lines = [clean_line(x) for x in page_lines[seg.page]]
        a = _find(lines, seg.start, pos.get(seg.page, 0))
        b = _find(lines, seg.stop, a + 1) if seg.stop else len(lines)
        pos[seg.page] = b
        items: List[List] = []  # [kind, text, hyphen_break]
        for ln in lines[a:b]:
            if not ln:
                continue
            dash = _is_dash(ln)
            body = ln[2:].strip() if dash else ln
            cur = items[-1] if items else None
            if dash and body[:1].islower() and cur is not None:
                cur[1] += " " + ln  # sous-tiret (« - la nutrition des organismes ; »)
                continue
            opens = dash or cur is None or cur[1].endswith(".") or any(ln.startswith(k) for k in seg.breaks)
            if opens:
                kind = "attendu" if seg.chapter == ATTENDUS else ("connaissance" if dash else "capacite")
                items.append([kind, body, False])
                continue
            if re.search(r"\w-$", cur[1]):
                cur[2] = True          # césure de fin de ligne : le PDF extrait perd le trait d'union
                cur[1] += ln
            else:
                cur[1] += " " + ln
        for n, (kind, text, hyph) in enumerate(items):
            reason = None
            if hyph:
                reason = "cesure_fin_de_ligne_non_prouvable"
            elif re.search("[\ue000-\uf8ff]", text):
                reason = "glyphe_police_symbol_non_unicode"  # ex. « ρ » extrait en U+F072
            elif seg.stop is None and n == len(items) - 1 and not text.endswith("."):
                reason = "item_a_cheval_sur_deux_pages"
            out.append(Parsed(seg, kind, clean_line(text), reason))
    return out


def attribute(p: Parsed) -> Tuple[Level, bool, str]:
    for r in RULES:
        if any(p.text.startswith(x) for x in r.prefixes):
            tag = "explicite" if r.explicit else "MikaMike"
            return r.level, r.explicit, f"{tag} — repère p.{r.page} : « {r.quote} »"
    if p.kind == "attendu":
        return L3, False, "MikaMike — attendu de fin de cycle → 3e"
    return L4, False, "MikaMike — aucun repère de classe explicite → 4e par défaut"


def check_rules(b: Builder) -> List[str]:
    """Citations des repères introuvables à leur page (doit être vide)."""
    return [f"p{r.page}: {r.quote}" for r in RULES
            if normalize_for_match(r.quote) not in b.st.pages.get(r.page, "")]


def build() -> Tuple[Dict[Subject, Builder], List[Attribution], List[Parsed], List[str]]:
    builders = {s: Builder(SOURCE_ID, s, Course.COMMON, SCHOOL_YEAR, PROGRAM_VERSION)
                for s in (Subject.PHYSIQUE_CHIMIE, Subject.SVT)}
    first = builders[Subject.PHYSIQUE_CHIMIE]
    parsed = parse_segments(first.lines)
    attributions: List[Attribution] = []
    skipped: List[Parsed] = []
    used_prefixes = set()
    for p in parsed:
        if p.skip_reason:
            skipped.append(p)
            continue
        subject, domain = DOMAINS[p.seg.domain_code]
        level, explicit, why = attribute(p)
        for r in RULES:
            used_prefixes.update(x for x in r.prefixes if p.text.startswith(x))
        it = Item(level=level, domain=domain, domain_code=p.seg.domain_code, chapter=p.seg.chapter,
                  excerpt=p.text, page=p.seg.page, kind=p.kind, difficulty=DIFFICULTY[level])
        if builders[subject].add(it) is not None:
            attributions.append(Attribution(subject, level, p.seg.domain_code, p.text, p.seg.page, explicit, why))
    problems = check_rules(first)
    problems += [f"préfixe_de_regle_inutilise: {x}" for r in RULES for x in r.prefixes if x not in used_prefixes]
    return builders, attributions, skipped, problems


SUBJECT_DIR = {Subject.PHYSIQUE_CHIMIE: "PC", Subject.SVT: "SVT"}


def main() -> int:
    builders, attributions, skipped, problems = build()
    for subject, b in builders.items():
        for level, notions in sorted(b.by_level().items(), key=lambda kv: kv[0].value):
            write_notion_file(DATA_DIR / "notions" / SUBJECT_DIR[subject] / f"{level.value}.json", subject, level,
                              Course.COMMON, link_sequential_prerequisites(notions), GENERATED_BY)
        counts = {lv.value: len(ns) for lv, ns in sorted(b.by_level().items(), key=lambda kv: kv[0].value)}
        print(f"{SUBJECT_DIR[subject]} : {len(b.notions)} notions prouvées {counts} ; {report_rejections(b.rejected)}")
    print(f"\n{len(skipped)} item(s) écarté(s) avant promotion :")
    for p in skipped:
        print(f"  p{p.seg.page} {p.seg.domain_code} {p.skip_reason}: {p.text[:110]!r}")
    print("\nAttributions :")
    for a in attributions:
        print(f"  [{'EXPL' if a.explicit else 'MIKA'}] {SUBJECT_DIR[a.subject]} {a.level.value} {a.domain_code} "
              f"p{a.page} {a.excerpt[:80]!r} — {a.justification}")
    for pb in problems:
        print(f"PROBLÈME : {pb}")
    rejected = any(b.rejected for b in builders.values())
    return 1 if rejected or problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
