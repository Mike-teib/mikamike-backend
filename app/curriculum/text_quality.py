"""
text_quality.py — Contrôle qualité du TEXTE d'une notion extraite (PDF, BO…).

Détecte : troncature, fin manquante, fragments, colonnes mélangées, en-têtes /
pieds de page parasites, formule cassée, ponctuation anormale, texte trop court,
répétition, concaténation suspecte.

Principe de prudence : on ne corrige que ce qui est SANS AMBIGUÏTÉ (ligatures,
espaces multiples, trait d'union conditionnel…) ⇒ TEXT_RECOVERED. Tout le reste
est signalé et bloque l'usage du texte comme source d'exercice.
Aucune transformation ne touche aux expressions mathématiques (fractions,
exposants, parenthèses) : cf. math_guard.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, NamedTuple, Optional

from app.curriculum.model import StatutTexte

# --- Réparations sûres (réversibles, sans perte d'information) --------------- #
_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
_INVISIBLES = {"­": "", "​": "", "‌": "", "‍": "", "﻿": ""}

# --- Motifs de contamination de mise en page ---------------------------------- #
# En-têtes de colonnes typiques des programmes (tableaux à 2-3 colonnes).
ENTETES_COLONNES = (
    "attendus de fin de cycle",
    "connaissances et compétences associées",
    "exemples de situations, d'activités et de ressources pour l'élève",
    "exemples de situations",
    "repères de progressivité",
    "capacités attendues",
    "contenus",
    "démonstrations",
    "algorithmique et programmation",
)
_HEADER_FOOTER = re.compile(
    r"(bulletin officiel|\bb\.?o\.?\s+n[°o]|eduscol\.education\.fr|education\.gouv\.fr|"
    r"minist[èe]re de l[’']?[ée]ducation|©|\bpage\s+\d+\s*(/|sur)\s*\d+|\bpage\s+\d+\b|"
    r"retrouvez [ée]duscol|www\.)",
    re.IGNORECASE,
)
_ESPACES_COLONNES = re.compile(r"\S {3,}\S")
_CONCAT = re.compile(r"[a-zàâçéèêëîïôûùüÿœ]{3,}[A-ZÀÂÇÉÈÊËÎÏÔÛÙÜŸŒ][a-zàâçéèêëîïôûùüÿœ]{2,}")
_POINT_COLLE = re.compile(r"[a-zàâçéèêëîïôûùü]{2,}\.[A-ZÀÂÇÉÈÊËÎÏÔÛÙÜ][a-zàâçéèêëîïôûùü]")
_PONCT_ANORMALE = re.compile(r"(,,|;;|::|(?<!\.)\.\.(?!\.)|\s[,.](?!\d)|[!?]{3,}|\(\s*\))")
# Noms propres en « CamelCase » légitimes (ne sont pas des concaténations d'extraction).
_CAMEL_LEGITIMES = frozenset({"javascript", "powerpoint", "libreoffice", "openoffice", "youtube"})

# Mots après lesquels une phrase ne peut pas se terminer (fin coupée).
_MOTS_NON_TERMINAUX = frozenset(
    "le la les l un une des du de d à au aux en et ou où pour par avec sur sous dans "
    "que qui dont ne se sa son ses leur leurs ce cette ces mais car donc or ni entre "
    "vers chez sans selon lorsque puis comme".split()
)
_DEBUT_CONTINUATION = frozenset("et ou mais donc car puis ainsi alors que qui dont".split())
_OPERATEURS_FIN = ("+", "-", "×", "*", "/", "=", "÷", "^", "<", ">", "≤", "≥", "(", "[", "{", "√")

# Caractères de police symbole non convertis (zone d'usage privé) / remplacement.
_CAR_CORROMPUS = re.compile("[�-]")

MIN_CARACTERES = 4
MIN_MOTS = 1


class RapportTexte(NamedTuple):
    statut: StatutTexte
    anomalies: List[str]
    texte_normalise: str


def reparer_sans_perte(texte: str) -> str:
    """Réparations sûres uniquement : ligatures, caractères invisibles, espaces."""
    t = unicodedata.normalize("NFC", texte)
    for a, b in {**_LIGATURES, **_INVISIBLES}.items():
        t = t.replace(a, b)
    t = t.replace(" ", " ").replace(" ", " ")
    return " ".join(t.split())


def _parentheses_equilibrees(t: str) -> bool:
    pile = []
    paires = {")": "(", "]": "[", "}": "{"}
    for c in t:
        if c in "([{":
            pile.append(c)
        elif c in paires:
            if not pile or pile.pop() != paires[c]:
                return False
    return not pile


def _repetition(mots: List[str]) -> bool:
    """Séquence de ≥ 3 mots répétée immédiatement (ex. « les fractions les fractions »)."""
    n = len(mots)
    for taille in range(3, n // 2 + 1):
        for i in range(0, n - 2 * taille + 1):
            if [m.lower() for m in mots[i:i + taille]] == [m.lower() for m in mots[i + taille:i + 2 * taille]]:
                return True
    return False


def analyser_texte(texte: str, *, extrait_source: Optional[str] = None) -> RapportTexte:
    """
    Analyse le texte d'une notion et renvoie un statut unique + la liste des anomalies.

    `extrait_source` : si fourni, le texte (normalisé) doit y figurer, sinon
    SOURCE_NOT_EVIDENCED.
    """
    brut = texte or ""
    anomalies: List[str] = []

    # Anomalies détectées sur le texte BRUT (avant réparation), liées à la mise en page.
    for ligne in brut.splitlines() or [brut]:
        if len(_ESPACES_COLONNES.findall(ligne)) >= 2:
            anomalies.append("colonnes_melangees_espacement")
            break

    t = reparer_sans_perte(brut)
    repare = t != " ".join(unicodedata.normalize("NFC", brut).split())
    bas = t.casefold()
    mots = t.split()

    if len(t) < MIN_CARACTERES or len(mots) < MIN_MOTS:
        anomalies.append("texte_trop_court")

    if _CAR_CORROMPUS.search(t):
        anomalies.append("caractere_corrompu")
    if not _parentheses_equilibrees(t):
        anomalies.append("parentheses_desequilibrees")
    if t.endswith(_OPERATEURS_FIN) or re.search(r"(^|\s)[=×÷*/^](\s*[=×÷*/^])", t):
        anomalies.append("operateur_orphelin")

    if any(h in bas for h in ENTETES_COLONNES) and len(mots) > 4:
        # Un titre de colonne au milieu d'un texte de notion = colonnes fusionnées.
        if not any(bas == h for h in ENTETES_COLONNES):
            anomalies.append("entete_colonne_dans_texte")
    if _HEADER_FOOTER.search(t):
        anomalies.append("entete_pied_de_page_parasite")
    concat = [
        w for w in mots
        if _CONCAT.search(w) and re.sub(r"\W", "", w).casefold() not in _CAMEL_LEGITIMES
    ]
    if concat or _POINT_COLLE.search(t):
        anomalies.append("concatenation_suspecte")

    dernier = re.sub(r"[^\wàâçéèêëîïôûùüÿœ']", "", mots[-1].casefold()) if mots else ""
    if t.endswith((",", ";", ":", "'", "’", "-", "–")) or dernier.rstrip("'’") in _MOTS_NON_TERMINAUX \
            or dernier.endswith(("'", "’")):
        anomalies.append("fin_tronquee")
    if mots and t[0].islower() and mots[0].casefold() in _DEBUT_CONTINUATION:
        anomalies.append("debut_fragment")
    if _PONCT_ANORMALE.search(t):
        anomalies.append("ponctuation_anormale")
    if _repetition(mots):
        anomalies.append("repetition")

    if extrait_source is not None:
        if reparer_sans_perte(extrait_source).casefold().find(bas) < 0:
            anomalies.append("absent_de_la_source")

    statut = _statut(anomalies, repare)
    return RapportTexte(statut, anomalies, t)


def _statut(anomalies: List[str], repare: bool) -> StatutTexte:
    a = set(anomalies)
    if a & {"caractere_corrompu", "parentheses_desequilibrees", "operateur_orphelin"}:
        return StatutTexte.FORMULA_CORRUPTED
    if a & {"colonnes_melangees_espacement", "entete_colonne_dans_texte",
            "entete_pied_de_page_parasite", "concatenation_suspecte"}:
        return StatutTexte.COLUMN_CONTAMINATION
    if "absent_de_la_source" in a:
        return StatutTexte.SOURCE_NOT_EVIDENCED
    if "fin_tronquee" in a:
        return StatutTexte.TEXT_TRUNCATED
    if a & {"debut_fragment", "texte_trop_court"}:
        return StatutTexte.TEXT_FRAGMENTED
    if a & {"ponctuation_anormale", "repetition"}:
        return StatutTexte.AMBIGUOUS
    return StatutTexte.TEXT_RECOVERED if repare else StatutTexte.TEXT_EXACT
