"""
staging_synthetique.py — Jeu de données SYNTHÉTIQUE complet pour l'environnement de staging.

⚠ 100 % FICTIF. Aucune donnée réelle d'élève (mineur), aucun extrait réel de programme officiel :
  - chaque texte est préfixé « [SYNTHÉTIQUE] » ;
  - chaque source est `fictive=True`, son URL pointe vers le domaine réservé `example.invalid`,
    son « PDF » est un fichier synthétique de quelques lignes (jamais un document officiel) ;
  - les comptes parents ont des adresses `@example.com` (domaine réservé), les élèves sont des
    pseudo-identifiants `eleve-synth-XXX` ; aucun prénom, seulement des libellés « Élève 001 ».
En mode normal (`autoriser_fictif=False`), l'intégrité refuse tout le lot
(SOURCE_FICTIVE_HORS_TEST) : ce jeu ne peut jamais passer pour un contenu de production.

Tout est DÉTERMINISTE (fonctions pures, graine explicite, pas d'horloge ni de hasard global) :
deux générations avec la même graine produisent les mêmes octets et le même SHA de manifest.

Couverture : les 5 matières de `Matiere`, plusieurs niveaux chacune (conformes à
NIVEAUX_PAR_MATIERE / CYCLE_DU_NIVEAU), 2 chapitres par niveau, 3 notions par chapitre (prérequis
chaînés, sans cycle), 2 exercices par notion, 1 QCM (`QuestionQuiz`) par notion, 1 vrai/faux
(`QuestionVraiFaux`) par chapitre et 1 classement (`QuestionClassement`) par chapitre de
mathématiques ; 6 familles (parents) pour 9 élèves ; historiques de tentatives datés sur
plusieurs jours, avec et sans aide, couvrant les 5 niveaux du moteur de progression.

`ecrire_lot_staging(d)` écrit DEUX dossiers séparés. `d/contenu/` = lot d'import v2 PUBLIABLE
(cf. IMPORT_CONTRACT.md), SANS aucune donnée utilisateur :
  sources/<prog>.pdf           source_document          / source_pdf
  structures/<prog>.json       structure_document       / structure_pdf      (chapitrage PROUVÉ)
  SHA256_SOURCE.txt            manifest_sha256          / manifest_sha256
  referentiel.json             referentiel              / referentiel
  mapping.jsonl                mapping_notion_chapitre  / mapping_chapitre_notion
  exercices.jsonl              index_contenus           / index_exercices   {"kind": "exercice", "data": …}
  quiz.jsonl                   index_contenus           / index_quiz        {"kind": "quiz", "data": …}
  quiz_complementaires.jsonl   opaque                   / rapport  (vrai/faux, classement : l'index de
                                                                    contenus n'accepte que QuestionQuiz)
`d/utilisateurs/` = données « utilisateurs » FICTIVES, JAMAIS dans un lot de contenu :
  familles.json, progression.jsonl, UTILISATEURS_MANIFEST.json
  ({format: "mika-staging-utilisateurs/1", fichiers: [{chemin, sha256, taille}], sha_lot_contenu}).
"""

from __future__ import annotations

import datetime as _dt
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from app.curriculum import dedup
from app.curriculum.exercices import Exercice
from app.curriculum.ids import sha256_octets, sha256_texte
from app.curriculum.importers import ecrire_manifest_v2
from app.curriculum.model import (
    CYCLE_DU_NIVEAU,
    NIVEAUX_PAR_MATIERE,
    Chapitre,
    Cycle,
    Domaine,
    Matiere,
    Niveau,
    Notion,
    Preuve,
    Programme,
    Referentiel,
    SourceOfficielle,
    StatutPreuve,
    StatutTexte,
    Theme,
)
from app.curriculum.pedagogie.progression import Niveau as NiveauProgression
from app.curriculum.pedagogie.progression import Tentative, diagnostiquer
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.quiz_types import QuestionClassement, QuestionVraiFaux

MARQUE = "[SYNTHÉTIQUE]"
GRAINE_DEFAUT = "mikamike-staging-v1"
LOT_ID = "staging-synthetique-v1"
DATE_LOT = "2026-09-01"
RENTREE = 2025
DOMAINE_EMAIL = "example.com"
URL_BASE = "https://example.invalid/staging"
PAGES_PAR_CHAPITRE = 3
DOSSIER_CONTENU = "contenu"
DOSSIER_UTILISATEURS = "utilisateurs"
NOM_MANIFEST_UTILISATEURS = "UTILISATEURS_MANIFEST.json"
FORMAT_UTILISATEURS = "mika-staging-utilisateurs/1"
FICHIERS_UTILISATEURS = ("familles.json", "progression.jsonl")
# Début des historiques (UTC, fixe : jamais l'horloge).
DEBUT_HISTORIQUES = _dt.datetime(2026, 9, 7, 16, 0, tzinfo=_dt.timezone.utc)

_LIBELLE_NIVEAU = {
    Niveau.CM1: "CM1", Niveau.CM2: "CM2", Niveau.SIXIEME: "6e", Niveau.CINQUIEME: "5e",
    Niveau.QUATRIEME: "4e", Niveau.TROISIEME: "3e", Niveau.SECONDE: "2de", Niveau.PREMIERE: "1re",
    Niveau.TERMINALE: "Tle",
}

# --------------------------------------------------------------------------- #
# Plan de couverture : matière → (code court, libellé, niveaux couverts)
# --------------------------------------------------------------------------- #
PLAN: Tuple[Tuple[Matiere, str, str, Tuple[Niveau, ...]], ...] = (
    (Matiere.MATHEMATIQUES, "maths", "Mathématiques",
     (Niveau.CM2, Niveau.SIXIEME, Niveau.CINQUIEME, Niveau.TROISIEME, Niveau.SECONDE, Niveau.TERMINALE)),
    (Matiere.PHYSIQUE_CHIMIE, "pc", "Physique-chimie",
     (Niveau.CINQUIEME, Niveau.TROISIEME, Niveau.SECONDE, Niveau.PREMIERE)),
    (Matiere.SVT, "svt", "SVT", (Niveau.QUATRIEME, Niveau.SECONDE, Niveau.TERMINALE)),
    (Matiere.SCIENCES_ET_TECHNOLOGIE, "st", "Sciences et technologie", (Niveau.CM1, Niveau.CM2, Niveau.SIXIEME)),
    (Matiere.ENSEIGNEMENT_SCIENTIFIQUE, "es", "Enseignement scientifique", (Niveau.PREMIERE, Niveau.TERMINALE)),
)
CODE_MATIERE = {m: code for m, code, _, _ in PLAN}
CHAPITRES_PAR_NIVEAU = 2
NOTIONS_PAR_CHAPITRE = 3

# Chapitres génériques (INVENTÉS, formulations neutres ; aucun intitulé officiel).
_CHAPITRES: Dict[Matiere, Tuple[Tuple[str, Tuple[str, str, str]], ...]] = {
    Matiere.MATHEMATIQUES: (
        ("Calcul numérique", ("effectuer un calcul avec des nombres entiers",
                              "utiliser les priorités opératoires dans un calcul",
                              "vérifier un résultat par un calcul inverse")),
        ("Équations", ("traduire un énoncé par une égalité", "tester si un nombre est solution d'une équation",
                       "résoudre une équation du premier degré")),
        ("Grandeurs et mesures", ("calculer le périmètre d'un polygone", "calculer l'aire d'un rectangle",
                                  "convertir des unités de longueur")),
        ("Organisation de données", ("lire un tableau de valeurs", "calculer une moyenne simple",
                                     "comparer deux séries de valeurs")),
    ),
    Matiere.PHYSIQUE_CHIMIE: (
        ("Constitution de la matière", ("distinguer un corps pur d'un mélange", "décrire un changement d'état",
                                        "identifier une espèce chimique par un test")),
        ("Mouvement et vitesse", ("décrire un mouvement par rapport à un référentiel",
                                  "calculer une vitesse moyenne", "exploiter une relation entre distance et durée")),
        ("Circuits électriques", ("schématiser un circuit électrique simple", "mesurer une tension électrique",
                                  "exploiter la relation entre tension et intensité")),
        ("Énergie et conversions", ("identifier une forme d'énergie", "décrire une chaîne énergétique",
                                    "calculer une énergie à partir d'une puissance")),
    ),
    Matiere.SVT: (
        ("Organisation du vivant", ("décrire l'organisation d'une cellule", "distinguer plusieurs types de cellules",
                                    "relier un organe à sa fonction")),
        ("Nutrition des organismes", ("décrire les besoins nutritifs d'un végétal",
                                      "expliquer le rôle de la digestion", "relier respiration et énergie")),
        ("Hérédité", ("localiser l'information génétique", "décrire la transmission des caractères",
                      "expliquer la diversité des individus")),
        ("Planète Terre", ("décrire la structure interne du globe", "relier séisme et mouvement des plaques",
                           "décrire le cycle de l'eau")),
    ),
    Matiere.SCIENCES_ET_TECHNOLOGIE: (
        ("États de la matière", ("reconnaître les trois états de l'eau", "décrire une fusion et une solidification",
                                 "mesurer une masse avec une balance")),
        ("Objets techniques", ("identifier la fonction d'un objet", "décrire le fonctionnement d'un mécanisme",
                               "choisir un matériau adapté")),
        ("Le vivant et son milieu", ("classer des êtres vivants", "décrire le développement d'un végétal",
                                     "relier un animal à son milieu")),
        ("Énergie au quotidien", ("identifier une source d'énergie", "distinguer énergie renouvelable et fossile",
                                  "calculer le périmètre d'une surface rectangulaire")),
    ),
    Matiere.ENSEIGNEMENT_SCIENTIFIQUE: (
        ("Matière et rayonnement", ("relier composition et propriétés d'un matériau",
                                    "exploiter un spectre lumineux", "estimer une énergie rayonnée")),
        ("Modèles et données", ("exploiter une série de mesures", "calculer un taux d'évolution",
                                "comparer un modèle à des données")),
        ("Vivant et environnement", ("décrire un écosystème", "relier biodiversité et évolution",
                                     "exploiter un indicateur de biodiversité")),
        ("Signaux et information", ("décrire un signal périodique", "calculer une fréquence simple",
                                    "relier un codage numérique à une quantité d'information")),
    ),
}
# Disciplines « indiquées par la source » (fictive) pour chaque chapitre d'ES (cf. IMPORT_CONTRACT §10).
_DISCIPLINES_ES = (
    (Matiere.PHYSIQUE_CHIMIE, Matiere.SVT),
    (Matiere.MATHEMATIQUES, Matiere.PHYSIQUE_CHIMIE),
    (Matiere.SVT,),
    (Matiere.MATHEMATIQUES, Matiere.PHYSIQUE_CHIMIE),
)

# Réservoirs de questions à réponse textuelle (SVT, sciences et technologie). Faits scolaires
# génériques, formulés pour ce jeu ; jamais recopiés d'un programme.
_ITEMS_SVT = (
    ("Quel organite de la cellule contient l'information génétique ?", "noyau",
     "Le noyau contient l'information génétique de la cellule.", "membrane"),
    ("Quel organe assure les échanges gazeux respiratoires chez l'être humain ?", "poumon",
     "Les poumons assurent les échanges gazeux.", "estomac"),
    ("Quel pigment permet aux végétaux verts de capter la lumière ?", "chlorophylle",
     "La chlorophylle capte l'énergie lumineuse.", "hémoglobine"),
    ("Quelle molécule porte l'information génétique ?", "adn",
     "L'ADN porte l'information génétique.", "glucose"),
    ("Quelle enveloppe délimite la cellule ?", "membrane",
     "La membrane délimite la cellule.", "noyau"),
    ("Quelle couche du globe se situe sous la croûte ?", "manteau",
     "Le manteau se situe sous la croûte terrestre.", "atmosphère"),
)
_POOL_SVT = ("noyau", "poumon", "chlorophylle", "adn", "membrane", "manteau", "estomac", "glucose")
_ITEMS_ST = (
    ("Quel est l'état de l'eau dans un glaçon ?", "solide"),
    ("Quel est l'état de l'eau dans la vapeur qui sort d'une casserole ?", "gazeux"),
    ("Quel instrument mesure une masse ?", "balance"),
    ("Quel instrument mesure une température ?", "thermomètre"),
    ("Quelle source d'énergie renouvelable utilise une éolienne ?", "vent"),
    ("Quelle partie d'un végétal absorbe l'eau du sol ?", "racine"),
)
_POOL_ST = ("solide", "liquide", "gazeux", "balance", "thermomètre", "règle", "vent", "racine", "feuille", "tige")

_VF: Dict[Matiere, Tuple[Tuple[str, bool], ...]] = {
    Matiere.SVT: (("La cellule est l'unité de base de tout être vivant.", True),
                  ("Le sang circule uniquement dans les artères.", False),
                  ("Les végétaux verts fabriquent leur matière organique grâce à la lumière.", True),
                  ("Le noyau se trouve à l'extérieur de la membrane cellulaire.", False)),
    Matiere.SCIENCES_ET_TECHNOLOGIE: (("L'eau gèle à 0 °C sous la pression atmosphérique normale.", True),
                                      ("Une balance sert à mesurer une longueur.", False),
                                      ("Le vent est une source d'énergie renouvelable.", True),
                                      ("Un glaçon est de l'eau à l'état gazeux.", False)),
}


# --------------------------------------------------------------------------- #
# Référentiel
# --------------------------------------------------------------------------- #
def _cycle_programme(niveaux: Sequence[Niveau]) -> Dict[Cycle, List[Niveau]]:
    par_cycle: Dict[Cycle, List[Niveau]] = defaultdict(list)
    for n in niveaux:
        par_cycle[CYCLE_DU_NIVEAU[n]].append(n)
    return par_cycle


def pdf_source(programme_id: str, n_pages: int) -> bytes:
    """Octets d'un « PDF » SYNTHÉTIQUE (jamais un document officiel ; seulement haché à l'import)."""
    corps = "".join(f"% {MARQUE} {programme_id} feuillet {p}\n" for p in range(1, n_pages + 1))
    return f"%PDF-1.4\n{corps}%%EOF\n".encode("utf-8")


def _slug_programme(prog_id: str) -> str:
    return prog_id.split(":", 1)[1].replace(":", "-")


def _texte_notion(libelle: str, niveau: Niveau, phrase: str) -> str:
    return f"{MARQUE} {libelle} {_LIBELLE_NIVEAU[niveau]} : {phrase}."


def referentiel_staging(graine: str = GRAINE_DEFAUT) -> Referentiel:
    """Référentiel complet, déterministe. La graine n'influe que sur les contenus (nombres)."""
    del graine  # structure fixe ; conservé pour une signature homogène
    sources, programmes, domaines, themes, chapitres, notions = [], [], [], [], [], []
    for matiere, code, libelle, niveaux in PLAN:
        admis = NIVEAUX_PAR_MATIERE[matiere]
        if any(n not in admis for n in niveaux):  # garde de conception
            raise ValueError(f"niveau_hors_matiere:{code}")
        catalogue = _CHAPITRES[matiere]
        for cycle, niv_cycle in sorted(_cycle_programme(niveaux).items(), key=lambda kv: kv[0].value):
            prog_id = f"prog:synth:{code}:{cycle.value}:{RENTREE}"
            n_chap = len(niv_cycle) * CHAPITRES_PAR_NIVEAU
            pdf = pdf_source(prog_id, 1 + n_chap * PAGES_PAR_CHAPITRE)
            src_id = f"src:synth:{code}:{cycle.value}"
            url = f"{URL_BASE}/{_slug_programme(prog_id)}.pdf"
            sources.append(SourceOfficielle(
                id=src_id, titre=f"{MARQUE} Document source fictif {libelle} {cycle.value}",
                editeur="MikaMike — jeu de données de staging", url=url, reference="STAGING_SYNTHETIQUE",
                date_publication=DATE_LOT, sha256_document=sha256_octets(pdf), fictive=True))
            programmes.append(Programme(
                id=prog_id, source_id=src_id, matiere=matiere, niveaux=tuple(niv_cycle),
                titre=f"{MARQUE} {libelle} {cycle.value}", rentree_debut=RENTREE))
            dom_id = f"dom:synth:{code}:{cycle.value}"
            domaines.append(Domaine(id=dom_id, programme_id=prog_id, titre=f"{MARQUE} {libelle}", ordre=1))
            k_prog = 0  # rang du chapitre dans le document du programme (pages)
            for niveau in niv_cycle:
                niv = niveau.value
                th_id = f"theme:synth:{code}:{niv}"
                themes.append(Theme(id=th_id, programme_id=prog_id, domaine_id=dom_id,
                                    titre=f"{MARQUE} {libelle} {_LIBELLE_NIVEAU[niveau]}",
                                    ordre=niveaux.index(niveau) + 1))
                precedente = None
                for c in range(1, CHAPITRES_PAR_NIVEAU + 1):
                    i_cat = (niveaux.index(niveau) * CHAPITRES_PAR_NIVEAU + c - 1) % len(catalogue)
                    titre_chap, phrases = catalogue[i_cat]
                    chap_id = f"chap:synth:{code}:{niv}:c{c}"
                    chapitres.append(Chapitre(id=chap_id, programme_id=prog_id, theme_id=th_id, niveau=niveau,
                                              titre=f"{MARQUE} {titre_chap}", ordre=c))
                    page0 = 2 + PAGES_PAR_CHAPITRE * k_prog
                    disciplines = _DISCIPLINES_ES[i_cat] if matiere == Matiere.ENSEIGNEMENT_SCIENTIFIQUE else ()
                    for j, phrase in enumerate(phrases, start=1):
                        texte = _texte_notion(libelle, niveau, phrase)
                        extrait = f"{texte} {MARQUE} Paragraphe fictif rédigé pour le jeu de staging."
                        nid = f"notion:synth:{code}:{niv}:c{c}:n{j}"
                        notions.append(Notion(
                            id=nid, programme_id=prog_id, chapitre_id=chap_id, niveau=niveau, matiere=matiere,
                            texte=texte, statut_texte=StatutTexte.TEXT_EXACT,
                            preuve=Preuve(
                                source_id=src_id, document=f"sources/{_slug_programme(prog_id)}.pdf", url=url,
                                page=page0 + j - 1, section=f"{MARQUE} {titre_chap}", extrait=extrait,
                                sha256_extrait=sha256_texte(extrait), statut=StatutPreuve.PROVEN,
                                date_verification=DATE_LOT,
                                disciplines_indiquees=tuple(disciplines) if disciplines else None),
                            # Prérequis chaînés : notion précédente (même niveau), jamais de cycle.
                            prerequis=(precedente,) if precedente else (),
                            disciplines_mobilisees=tuple(disciplines)))
                        precedente = nid
                    k_prog += 1
    return Referentiel(sources=tuple(sources), programmes=tuple(programmes), domaines=tuple(domaines),
                       themes=tuple(themes), chapitres=tuple(chapitres), notions=tuple(notions))


# --------------------------------------------------------------------------- #
# Contenus : exercices et quiz
# --------------------------------------------------------------------------- #
def _fuite(enonce: str, reponse: str) -> bool:
    nb = dedup.normaliser(reponse)
    return len(nb) >= 2 and nb in dedup.normaliser(enonce)


def _rng(graine: str, *cles: str) -> random.Random:
    return random.Random(":".join((graine, *cles)))  # graine str ⇒ déterministe (sha512)


def _entete(n: Notion) -> str:
    return f"{MARQUE} {n.texte[len(MARQUE) + 1:].rstrip('.')} —"


def _gabarits_exercice(n: Notion, rng: random.Random, k: int) -> Tuple[str, str, str, Dict[str, Any],
                                                                     Dict[str, str], Tuple[str, ...]]:
    """(énoncé, réponse, type, paramètres, erreurs fréquentes, indices) pour l'exercice k (1 ou 2)."""
    m = n.matiere
    if m == Matiere.MATHEMATIQUES or (m == Matiere.ENSEIGNEMENT_SCIENTIFIQUE and k == 1) \
            or (m == Matiere.SCIENCES_ET_TECHNOLOGIE and k == 1):
        if k == 1 and m == Matiere.MATHEMATIQUES:
            a, b, c = rng.randint(2, 9), rng.randint(2, 9), rng.randint(2, 30)
            rep = a * b + c
            err = {str(a * (b + c)): "priorités opératoires non respectées", str(rep + 1): "erreur de calcul"}
            if a * (b + c) == rep:
                err.pop(str(rep))
            return (f"Calcule {a} × {b} + {c}.", str(rep), "maths_symbolique", {}, err,
                    ("La multiplication est prioritaire.", f"Commence par calculer {a} × {b}."))
        if m == Matiere.MATHEMATIQUES:
            a, s, b = rng.randint(2, 9), rng.randint(2, 12), rng.randint(1, 20)
            return (f"Résous l'équation {a}x + {b} = {a * s + b}.", f"x = {s}", "maths_symbolique", {},
                    {f"x = {s + 1}": "erreur de calcul", f"x = {a * s + 2 * b}": "terme constant mal déplacé"},
                    ("Isole le terme en x.", f"Soustrais {b} aux deux membres."))
        if m == Matiere.SCIENCES_ET_TECHNOLOGIE:
            a, b = rng.randint(3, 20), rng.randint(3, 20)
            p = 2 * (a + b)
            return (f"Un jardin rectangulaire mesure {a} m sur {b} m. Calcule son périmètre en mètres "
                    f"(nombre seul).", str(p), "maths_symbolique", {},
                    {str(a * b): "confusion entre aire et périmètre", str(a + b): "demi-périmètre"},
                    ("Le périmètre est le tour de la figure.", "Additionne les quatre côtés."))
        # ES, exercice 1 : taux d'évolution (pourcentage entier)
        p0 = rng.choice((200, 400, 500, 800))
        t = rng.choice((5, 10, 20, 25))
        p1 = p0 + p0 * t // 100
        return (f"Une grandeur passe de {p0} à {p1}. Calcule son taux d'évolution en pourcentage "
                f"(nombre seul).", str(t), "maths_symbolique", {},
                {str(p1 - p0): "variation absolue au lieu du taux", str(t + 1): "erreur de calcul"},
                ("Calcule d'abord la variation.", "Divise la variation par la valeur de départ."))
    if m in (Matiere.PHYSIQUE_CHIMIE, Matiere.ENSEIGNEMENT_SCIENTIFIQUE):
        if k == 1:
            t, v = rng.randint(2, 9), rng.randint(2, 15)
            d = t * v
            return (f"Un mobile parcourt {d} m en {t} s. Calcule sa vitesse moyenne.", f"{v} m/s",
                    "physique_grandeur", {}, {f"{d * t} m/s": "multiplication au lieu d'une division",
                                              f"{v} m": "unité incohérente"},
                    ("La vitesse est une distance divisée par une durée.", "Divise la distance par la durée."))
        if m == Matiere.PHYSIQUE_CHIMIE:
            r, i = rng.randint(2, 20) * 10, rng.randint(2, 9)
            return (f"Un dipôle ohmique de résistance {r} Ω est parcouru par un courant d'intensité {i} A. "
                    f"Calcule la tension à ses bornes.", f"{r * i} V", "physique_grandeur", {},
                    {f"{r + i} V": "addition au lieu d'un produit"},
                    ("Utilise la relation U = R × I.", "Multiplie la résistance par l'intensité."))
        p, t = rng.randint(2, 20) * 5, rng.randint(2, 12) * 10
        return (f"Un appareil de puissance {p} W fonctionne pendant {t} s. Calcule l'énergie reçue.",
                f"{p * t} J", "physique_grandeur", {}, {f"{p + t} J": "addition au lieu d'un produit"},
                ("E = P × t.", "Multiplie la puissance par la durée."))
    if m == Matiere.SVT:
        q, terme, phrase, faux = _ITEMS_SVT[rng.randrange(len(_ITEMS_SVT))]
        if k == 1:
            return (f"{q} Réponds par une phrase.", phrase, "svt_vocabulaire",
                    {"termes_requis": [terme], "termes_errones": [faux]},
                    {f"La réponse est : {faux}.": "confusion de vocabulaire"},
                    ("Pense à l'échelle de la cellule ou de l'organe.", "Utilise le mot scientifique exact."))
        return (f"{q} Réponds par un seul mot.", terme, "texte_exact", {},
                {faux: "confusion de vocabulaire"}, ("Un seul mot est attendu.",))
    # Sciences et technologie, exercice 2
    q, mot = _ITEMS_ST[rng.randrange(len(_ITEMS_ST))]
    faux = next(x for x in _POOL_ST if x != mot)
    return (f"{q} Réponds par un seul mot.", mot, "texte_exact", {}, {faux: "confusion"},
            ("Observe la situation décrite.",))


def exercices_staging(ref: Referentiel, graine: str = GRAINE_DEFAUT) -> List[Exercice]:
    out: List[Exercice] = []
    for n in ref.notions:
        for k in (1, 2):
            rng = _rng(graine, n.id, f"e{k}")
            for _ in range(50):
                corps, rep, typ, params, err, indices = _gabarits_exercice(n, rng, k)
                enonce = f"{_entete(n)} {corps}"
                if not _fuite(enonce, rep):
                    break
            else:  # pragma: no cover - garde de conception
                raise RuntimeError(f"fuite_irreductible:{n.id}")
            out.append(Exercice(
                id=f"exo:{n.id.split(':', 1)[1]}:e{k}", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                programme_id=n.programme_id, chapitre_id=n.chapitre_id, difficulte=min(5, k + (1 if n.niveau in (
                    Niveau.PREMIERE, Niveau.TERMINALE) else 0)),
                objectif_pedagogique=f"{MARQUE} Savoir {n.texte.split(' : ', 1)[1].rstrip('.')}",
                prerequis=n.prerequis, enonce=enonce, reponse_attendue=rep, type_verification=typ,
                parametres_verification=params, indices=indices, erreurs_frequentes=err,
                source_sha256_extrait=n.preuve.sha256_extrait))
    return out


def _qcm(n: Notion, rng: random.Random) -> Tuple[str, List[str], str, str, str]:
    """(énoncé, choix, bonne réponse, type de vérification, explication)."""
    m = n.matiere
    if m in (Matiere.MATHEMATIQUES, Matiere.ENSEIGNEMENT_SCIENTIFIQUE):
        a, b = rng.randint(11, 49), rng.randint(11, 49)
        s = a + b
        return (f"Combien vaut {a} + {b} ?", [str(s), str(s + 1), str(s + 10), str(s - 10)], str(s),
                "maths_symbolique", "On additionne les unités puis les dizaines.")
    if m == Matiere.PHYSIQUE_CHIMIE:
        t, v = rng.randint(2, 9), rng.randint(3, 15)
        return (f"Un objet parcourt {t * v} m en {t} s. Quelle est sa vitesse moyenne ?",
                [f"{v} m/s", f"{v + 2} m/s", f"{v * 2 + 1} m/s", f"{t * v * t} m/s"], f"{v} m/s",
                "physique_grandeur", "La vitesse moyenne est la distance divisée par la durée.")
    if m == Matiere.SVT:
        q, terme, _phrase, _faux = _ITEMS_SVT[rng.randrange(len(_ITEMS_SVT))]
        autres = [x for x in _POOL_SVT if x != terme]
        rng.shuffle(autres)
        return (q, [terme, *autres[:3]], terme, "texte_exact", f"La réponse attendue est « {terme} ».")
    q, mot = _ITEMS_ST[rng.randrange(len(_ITEMS_ST))]
    autres = [x for x in _POOL_ST if x != mot]
    rng.shuffle(autres)
    return (q, [mot, *autres[:3]], mot, "texte_exact", f"La réponse attendue est « {mot} ».")


def quiz_staging(ref: Referentiel, graine: str = GRAINE_DEFAUT) -> List[QuestionQuiz]:
    """Un QCM (`QuestionQuiz`) par notion."""
    out: List[QuestionQuiz] = []
    for n in ref.notions:
        rng = _rng(graine, n.id, "qcm")
        for _ in range(50):
            corps, choix, bonne, typ, expl = _qcm(n, rng)
            enonce = f"{_entete(n)} {corps}"
            if not _fuite(enonce, bonne):
                break
        ordre = list(range(len(choix)))
        rng.shuffle(ordre)
        melanges = [choix[i] for i in ordre]
        out.append(QuestionQuiz(
            id=f"quiz:{n.id.split(':', 1)[1]}:q1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
            enonce=enonce, choix=tuple(melanges), index_correct=melanges.index(bonne), reponse_reference=bonne,
            type_verification=typ, explication=f"{MARQUE} {expl}"))
    return out


def quiz_complementaires_staging(ref: Referentiel, graine: str = GRAINE_DEFAUT) -> List[Any]:
    """Types de `quiz_types.py` : un vrai/faux par chapitre, un classement par chapitre de maths."""
    out: List[Any] = []
    premiere = {}
    for n in ref.notions:
        premiere.setdefault(n.chapitre_id, n)
    for i, chap in enumerate(ref.chapitres):
        n = premiere[chap.id]
        rng = _rng(graine, chap.id, "vf")
        base = chap.id.split(":", 1)[1]
        if n.matiere in _VF:
            aff, vrai = _VF[n.matiere][i % len(_VF[n.matiere])]
            expl = "Fait scientifique général rappelé pour l'entraînement."
        else:
            a, b = rng.randint(11, 49), rng.randint(11, 49)
            vrai = i % 2 == 0
            aff = f"La somme {a} + {b} est égale à {a + b if vrai else a + b + 1}."
            expl = f"{a} + {b} = {a + b}."
        out.append(QuestionVraiFaux(id=f"quiz:{base}:vf", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                                    enonce=f"{MARQUE} Vrai ou faux ? {aff}", affirmation_vraie=vrai,
                                    explication=f"{MARQUE} {expl}"))
        if n.matiere == Matiere.MATHEMATIQUES:
            valeurs = rng.sample(range(10, 100), 4)
            ordre = tuple(sorted(range(4), key=lambda k: valeurs[k]))
            if ordre == tuple(range(4)):
                valeurs = list(reversed(valeurs))
                ordre = tuple(sorted(range(4), key=lambda k: valeurs[k]))
            out.append(QuestionClassement(
                id=f"quiz:{base}:cl", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                enonce=f"{MARQUE} Range ces nombres dans l'ordre croissant.",
                elements=tuple(str(v) for v in valeurs), ordre_correct=ordre,
                valeurs=tuple(float(v) for v in valeurs), croissant=True,
                explication=f"{MARQUE} On compare d'abord les dizaines."))
    return out


# --------------------------------------------------------------------------- #
# Familles et historiques de progression (FICTIFS)
# --------------------------------------------------------------------------- #
_NIVEAUX_ELEVES = (Niveau.CM2, Niveau.SIXIEME, Niveau.CINQUIEME, Niveau.TROISIEME, Niveau.QUATRIEME,
                   Niveau.SECONDE, Niveau.PREMIERE, Niveau.TERMINALE, Niveau.CM1)
# parent → enfants (indices 1..9). Parent 001 a 2 enfants ; l'élève 003 a 2 parents (002 et 003).
_FAMILLES = ((1, (1, 2)), (2, (3,)), (3, (3, 4)), (4, (5,)), (5, (6, 7)), (6, (8, 9)))


def pseudo_eleve(i: int) -> str:
    return f"eleve-synth-{i:03d}"


def email_parent(i: int) -> str:
    return f"parent-synth-{i:03d}@{DOMAINE_EMAIL}"


def familles_staging() -> Dict[str, Any]:
    eleves = [{"pseudo_id": pseudo_eleve(i), "libelle": f"Élève {i:03d}",
               "niveau": _NIVEAUX_ELEVES[i - 1].value} for i in range(1, len(_NIVEAUX_ELEVES) + 1)]
    parents = [{"id": f"parent-synth-{p:03d}", "email": email_parent(p), "libelle": f"Parent {p:03d}",
                "role": "parent", "enfants": [pseudo_eleve(e) for e in enfants]} for p, enfants in _FAMILLES]
    return {"marque": MARQUE, "parents": parents, "eleves": eleves}


# Profils d'historique : (jour, correcte, avec_aide) → niveau attendu du moteur (vérifié à la génération).
PROFILS: Dict[str, Tuple[Tuple[int, bool, bool], ...]] = {
    NiveauProgression.MAITRISEE.value: ((0, True, False), (0, True, False), (1, True, False), (2, True, False)),
    NiveauProgression.EN_COURS.value: ((0, False, False), (0, True, True), (1, True, False), (1, True, False)),
    NiveauProgression.FRAGILE.value: ((0, True, False), (0, False, False), (1, False, False), (1, False, True)),
    NiveauProgression.NON_ACQUISE.value: ((0, False, False), (0, False, True), (1, False, False), (2, False, False)),
    NiveauProgression.NON_EVALUEE.value: ((0, True, True), (1, False, False)),
}
_ORDRE_PROFILS = tuple(PROFILS)
COMPETENCES_PAR_ELEVE = 5


def _ts(jour_eleve: int, jour: int, rang: int) -> _dt.datetime:
    return DEBUT_HISTORIQUES + _dt.timedelta(days=jour_eleve + jour, minutes=7 * rang)


def historiques_staging(ref: Referentiel, familles: Dict[str, Any] | None = None,
                        graine: str = GRAINE_DEFAUT) -> List[Dict[str, Any]]:
    """Tentatives datées (UTC, ISO 8601) : une ligne par tentative, triées (élève, compétence, date)."""
    familles = familles or familles_staging()
    par_niveau: Dict[str, List[Notion]] = defaultdict(list)
    for n in ref.notions:
        par_niveau[n.niveau.value].append(n)
    lignes: List[Dict[str, Any]] = []
    for i, e in enumerate(familles["eleves"]):
        rng = _rng(graine, e["pseudo_id"], "historique")
        candidates = par_niveau[e["niveau"]]
        # Une notion par chapitre (1re notion), toutes matières du niveau confondues.
        choisies = [n for n in candidates if n.id.endswith(":n1")][:COMPETENCES_PAR_ELEVE]
        decalage = rng.randint(0, 3)
        for k, n in enumerate(choisies):
            profil = _ORDRE_PROFILS[(i + k) % len(_ORDRE_PROFILS)]
            for r, (jour, ok, aide) in enumerate(PROFILS[profil]):
                exo = f"exo:{n.id.split(':', 1)[1]}:e{1 + r % 2}"
                lignes.append({
                    "pseudo_id": e["pseudo_id"], "exercice_id": exo, "competence": n.id,
                    "matiere": n.matiere.value, "niveau": n.niveau.value, "est_correct": ok, "avec_aide": aide,
                    "ts": _ts(decalage, jour, 10 * k + r).isoformat(), "profil": profil})
    _controler_profils(lignes)
    return lignes


def tentatives_par_competence(lignes: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Tentative]]:
    out: Dict[Tuple[str, str], List[Tentative]] = defaultdict(list)
    for li in lignes:
        ts = _dt.datetime.fromisoformat(li["ts"]).timestamp()
        out[(li["pseudo_id"], li["competence"])].append(Tentative(li["est_correct"], li["avec_aide"], ts))
    return dict(out)


def _controler_profils(lignes: List[Dict[str, Any]]) -> None:
    attendu = {(li["pseudo_id"], li["competence"]): li["profil"] for li in lignes}
    for cle, h in tentatives_par_competence(lignes).items():
        obtenu = diagnostiquer(h).niveau.value
        if obtenu != attendu[cle]:  # garde de conception : le profil doit produire le niveau annoncé
            raise AssertionError(f"profil_incoherent:{cle}:{attendu[cle]}≠{obtenu}")


# --------------------------------------------------------------------------- #
# Écriture du lot d'import v2
# --------------------------------------------------------------------------- #
def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _ecrire_jsonl(chemin: Path, objets: Iterable[Any]) -> None:
    chemin.write_text("".join(_json(o) + "\n" for o in objets), encoding="utf-8")


CLES_STATS = ("chapitres", "notions", "exercices", "qcm", "quiz_autres")


def statistiques(ref: Referentiel, exercices: Sequence[Exercice], quiz: Sequence[QuestionQuiz],
                 complementaires: Sequence[Any] = ()) -> Dict[str, Dict[str, Dict[str, int]]]:
    """{matière: {niveau: {chapitres, notions, exercices, qcm, quiz_autres}}}."""
    stats: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for c in ref.chapitres:
        m = next(p.matiere for p in ref.programmes if p.id == c.programme_id)
        stats[m.value][c.niveau.value]["chapitres"] += 1
    for n in ref.notions:
        stats[n.matiere.value][n.niveau.value]["notions"] += 1
    for e in exercices:
        stats[e.matiere.value][e.niveau.value]["exercices"] += 1
    for q in quiz:
        stats[q.matiere.value][q.niveau.value]["qcm"] += 1
    for q in complementaires:
        stats[q.matiere.value][q.niveau.value]["quiz_autres"] += 1
    out: Dict[str, Dict[str, Dict[str, int]]] = {}
    for m, par_niv in stats.items():
        out[m] = {niv: {k: c[k] for k in CLES_STATS} for niv, c in par_niv.items()}
    return out


class LotStaging(NamedTuple):
    sha_contenu: str        # SHA du manifest v2 de `contenu/` (à épingler pour l'import)
    sha_utilisateurs: str   # SHA de `utilisateurs/UTILISATEURS_MANIFEST.json`


def ecrire_lot_staging(dossier: Path, graine: str = GRAINE_DEFAUT) -> LotStaging:
    """Écrit, dans `dossier` (vide ou inexistant), deux sous-dossiers SÉPARÉS :
      - `contenu/`      : lot d'import v2 PUBLIABLE (aucune donnée utilisateur) ;
      - `utilisateurs/` : familles + progression FICTIVES, jamais dans un lot de contenu.
    Renvoie les deux SHA (contenu à épingler hors bande, utilisateurs)."""
    racine = Path(dossier)
    if racine.exists() and any(racine.iterdir()):
        raise FileExistsError(f"dossier_non_vide:{racine}")
    dossier = racine / DOSSIER_CONTENU
    (dossier / "sources").mkdir(parents=True, exist_ok=True)
    (dossier / "structures").mkdir(exist_ok=True)

    ref = referentiel_staging(graine)
    exercices = exercices_staging(ref, graine)
    quiz = quiz_staging(ref, graine)
    complementaires = quiz_complementaires_staging(ref, graine)
    familles = familles_staging()
    historiques = historiques_staging(ref, familles, graine)

    fichiers: Dict[str, Tuple[str, str]] = {}
    lignes_sha: List[str] = []
    mapping: List[Dict[str, Any]] = []
    notions_par_chap: Dict[str, List[Notion]] = defaultdict(list)
    for n in ref.notions:
        notions_par_chap[n.chapitre_id].append(n)
    for prog in ref.programmes:
        slug = _slug_programme(prog.id)
        chaps = [c for c in ref.chapitres if c.programme_id == prog.id]
        pdf = pdf_source(prog.id, 1 + len(chaps) * PAGES_PAR_CHAPITRE)
        src = next(s for s in ref.sources if s.id == prog.source_id)
        assert sha256_octets(pdf) == src.sha256_document
        chemin_pdf = f"sources/{slug}.pdf"
        (dossier / chemin_pdf).write_bytes(pdf)
        fichiers[chemin_pdf] = ("source_document", "source_pdf")
        lignes_sha.append(f"{src.sha256_document}  {chemin_pdf}")
        structure = {"sha256_document": src.sha256_document, "sommaire_pages": [1], "chapitres": []}
        for k, c in enumerate(chaps):
            debut = 2 + PAGES_PAR_CHAPITRE * k
            structure["chapitres"].append({"chapitre_id": c.id, "page_debut": debut,
                                           "page_fin": debut + PAGES_PAR_CHAPITRE - 1})
            for n in notions_par_chap[c.id]:
                mapping.append({"notion_id": n.id, "chapitre_id": c.id, "preuves": [{
                    "type": "section_pdf", "sha256_document": src.sha256_document, "page": n.preuve.page,
                    "bbox": [50, 100, 500, 140]}]})
        chemin_st = f"structures/{slug}.json"
        (dossier / chemin_st).write_text(_json(structure) + "\n", encoding="utf-8")
        fichiers[chemin_st] = ("structure_document", "structure_pdf")
    (dossier / "SHA256_SOURCE.txt").write_text("\n".join(lignes_sha) + "\n", encoding="utf-8")
    fichiers["SHA256_SOURCE.txt"] = ("manifest_sha256", "manifest_sha256")

    (dossier / "referentiel.json").write_text(_json(ref.model_dump(mode="json")) + "\n", encoding="utf-8")
    fichiers["referentiel.json"] = ("referentiel", "referentiel")
    _ecrire_jsonl(dossier / "mapping.jsonl", mapping)
    fichiers["mapping.jsonl"] = ("mapping_notion_chapitre", "mapping_chapitre_notion")
    _ecrire_jsonl(dossier / "exercices.jsonl",
                  ({"kind": "exercice", "data": e.model_dump(mode="json")} for e in exercices))
    fichiers["exercices.jsonl"] = ("index_contenus", "index_exercices")
    _ecrire_jsonl(dossier / "quiz.jsonl", ({"kind": "quiz", "data": q.model_dump(mode="json")} for q in quiz))
    fichiers["quiz.jsonl"] = ("index_contenus", "index_quiz")
    _ecrire_jsonl(dossier / "quiz_complementaires.jsonl",
                  ({"type": q.type, "data": q.model_dump(mode="json")} for q in complementaires))
    fichiers["quiz_complementaires.jsonl"] = ("opaque", "rapport")
    sha_contenu = ecrire_manifest_v2(dossier, fichiers, lot_id=LOT_ID,
                                     producteur=f"{MARQUE} jeu de staging MikaMike", date=DATE_LOT, trier=True)

    util = racine / DOSSIER_UTILISATEURS
    util.mkdir()
    (util / "familles.json").write_text(_json(familles) + "\n", encoding="utf-8")
    _ecrire_jsonl(util / "progression.jsonl", historiques)
    entrees = [{"chemin": nom, "sha256": sha256_octets((util / nom).read_bytes()),
                "taille": (util / nom).stat().st_size} for nom in FICHIERS_UTILISATEURS]
    brut = (json.dumps({"format": FORMAT_UTILISATEURS, "fichiers": entrees, "sha_lot_contenu": sha_contenu},
                       ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (util / NOM_MANIFEST_UTILISATEURS).write_bytes(brut)
    return LotStaging(sha_contenu, sha256_octets(brut))


def verifier_utilisateurs(dossier_utilisateurs: Path, sha_manifest: Optional[str] = None) -> Dict[str, Any]:
    """Contrôle les empreintes de `utilisateurs/` (manifeste, fichiers listés, aucun fichier en
    trop). Lève ValueError si altéré. Renvoie le manifeste."""
    d = Path(dossier_utilisateurs)
    brut = (d / NOM_MANIFEST_UTILISATEURS).read_bytes()
    if sha_manifest is not None and sha256_octets(brut) != sha_manifest:
        raise ValueError("manifeste_utilisateurs_different")
    m = json.loads(brut.decode("utf-8"))
    if m.get("format") != FORMAT_UTILISATEURS or not isinstance(m.get("fichiers"), list):
        raise ValueError("manifeste_utilisateurs_invalide")
    listes = {f["chemin"] for f in m["fichiers"]}
    if listes != set(FICHIERS_UTILISATEURS):
        raise ValueError("manifeste_utilisateurs_incomplet")
    presents = {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()} - {NOM_MANIFEST_UTILISATEURS}
    if presents != listes:
        raise ValueError("fichiers_utilisateurs_non_listes:" + ",".join(sorted(presents - listes)))
    for f in m["fichiers"]:
        chemin = d / f["chemin"]
        if chemin.stat().st_size != f["taille"] or sha256_octets(chemin.read_bytes()) != f["sha256"]:
            raise ValueError(f"fichier_utilisateurs_altere:{f['chemin']}")
    return m




def lire_quiz_complementaires(chemin: Path) -> List[Any]:
    from pydantic import TypeAdapter

    from app.curriculum.quiz_types import Question

    ta = TypeAdapter(Question)
    return [ta.validate_python(json.loads(li)["data"]) for li in chemin.read_text("utf-8").splitlines() if li.strip()]


__all__ = ["referentiel_staging", "exercices_staging", "quiz_staging", "quiz_complementaires_staging",
           "familles_staging", "historiques_staging", "ecrire_lot_staging", "LotStaging", "verifier_utilisateurs", "statistiques",
           "tentatives_par_competence", "lire_quiz_complementaires", "MARQUE", "PROFILS", "GRAINE_DEFAUT"]
