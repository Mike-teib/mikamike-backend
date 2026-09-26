"""
quiz_types.py — Types de questions complémentaires au QCM (lot 10, session 4).

  vrai_faux       affirmation + valeur de vérité + explication ;
  reponse_courte  réponse saisie, corrigée par le vérificateur déterministe (dispatch) ;
  classement      remettre des éléments dans l'ordre ; si des valeurs sont fournies, l'ordre
                  déclaré DOIT en découler (et aucune égalité : sinon ordre indécidable) ;
  association     relier chaque élément de gauche à UN élément de droite (distracteurs admis
                  à droite) ; relation bijective par défaut.

Chaque type : contrôles de conception (codes, comme quiz.py) + correction d'une réponse d'élève.
Une réponse n'est VALID que si elle est EXACTE (pas de score partiel déguisé en réussite ;
le score partiel est renvoyé dans les raisons pour l'adaptation, jamais comme verdict).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.curriculum import dedup
from app.curriculum.model import ID_CANONIQUE, IndexReferentiel, Matiere, Niveau
from app.curriculum.quiz import verrous_notion
from app.curriculum.verifiers.base import Resultat, Verdict, invalide, revue, valide
from app.curriculum.verifiers.dispatch import TYPES_VERIFICATION, verifier

_DOUBLE_NEGATION = re.compile(r"\b(ne|n)\b[^.]*\bpas\b[^.]*\b(non|ne|n|pas|jamais|aucun)\b", re.I)
_FLOU = re.compile(r"\b(souvent|parfois|généralement|en général|la plupart|environ|à peu près)\b", re.I)


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_CANONIQUE)
    notion_id: str = Field(pattern=ID_CANONIQUE)
    matiere: Matiere
    niveau: Niveau
    enonce: str = Field(min_length=3, max_length=2000)
    explication: str = Field(default="", max_length=2000)


class QuestionVraiFaux(_Base):
    type: Literal["vrai_faux"] = "vrai_faux"
    affirmation_vraie: StrictBool


class QuestionReponseCourte(_Base):
    type: Literal["reponse_courte"] = "reponse_courte"
    reponse_reference: str = Field(min_length=1, max_length=500)
    type_verification: str
    parametres_verification: Dict[str, Any] = Field(default_factory=dict)


class QuestionClassement(_Base):
    type: Literal["classement"] = "classement"
    elements: Tuple[str, ...] = Field(min_length=3, max_length=8)
    ordre_correct: Tuple[int, ...]
    valeurs: Optional[Tuple[float, ...]] = None     # si fournies : l'ordre doit en découler
    croissant: StrictBool = True


class QuestionAssociation(_Base):
    type: Literal["association"] = "association"
    gauche: Tuple[str, ...] = Field(min_length=2, max_length=8)
    droite: Tuple[str, ...] = Field(min_length=2, max_length=10)
    paires: Tuple[Tuple[int, int], ...]
    droite_reutilisable: StrictBool = False


Question = Union[QuestionVraiFaux, QuestionReponseCourte, QuestionClassement, QuestionAssociation]


# --------------------------------------------------------------------------- #
# Contrôles de conception
# --------------------------------------------------------------------------- #
def _doublons(textes: Sequence[str]) -> bool:
    n = [dedup.normaliser(t) for t in textes]
    return len(set(n)) != len(n) or any(not x for x in n)


def valider(q: Question, idx: IndexReferentiel, *, autoriser_fictif: bool = False) -> List[str]:
    raisons = verrous_notion(q, idx, autoriser_fictif=autoriser_fictif)
    if raisons == ["NOTION_INCONNUE"]:
        return raisons
    if not q.explication.strip():
        raisons.append("NON_EXPLICABLE")

    if isinstance(q, QuestionVraiFaux):
        if _DOUBLE_NEGATION.search(q.enonce):
            raisons.append("DOUBLE_NEGATION")
        if _FLOU.search(q.enonce):
            raisons.append("AFFIRMATION_IMPRECISE")  # « souvent » : ni vrai ni faux démontrable

    elif isinstance(q, QuestionReponseCourte):
        if q.type_verification not in TYPES_VERIFICATION:
            raisons.append("TYPE_VERIFICATION_INCONNU")
        elif verifier(q.type_verification, q.reponse_reference, q.reponse_reference,
                      q.parametres_verification).verdict != Verdict.VALID:
            raisons.append("REFERENCE_NON_VERIFIABLE")
        nb = dedup.normaliser(q.reponse_reference)
        if len(nb) >= 2 and nb in dedup.normaliser(q.enonce):
            raisons.append("FUITE_REPONSE")

    elif isinstance(q, QuestionClassement):
        n = len(q.elements)
        if _doublons(q.elements):
            raisons.append("ELEMENTS_DUPLIQUES")
        if sorted(q.ordre_correct) != list(range(n)):
            raisons.append("ORDRE_NON_PERMUTATION")
        elif q.ordre_correct == tuple(range(n)):
            raisons.append("ORDRE_DEJA_DONNE")  # les éléments sont présentés déjà classés
        if q.valeurs is not None:
            if len(q.valeurs) != n:
                raisons.append("VALEURS_INCOHERENTES")
            elif len(set(q.valeurs)) != n:
                raisons.append("ORDRE_INDECIDABLE_EGALITE")
            elif sorted(q.ordre_correct) == list(range(n)):
                attendu = sorted(range(n), key=lambda i: q.valeurs[i], reverse=not q.croissant)
                if list(q.ordre_correct) != attendu:
                    raisons.append("ORDRE_CONTREDIT_LES_VALEURS")

    elif isinstance(q, QuestionAssociation):
        if _doublons(q.gauche) or _doublons(q.droite):
            raisons.append("ELEMENTS_DUPLIQUES")
        gs = [g for g, _ in q.paires]
        ds = [d for _, d in q.paires]
        if any(not (0 <= g < len(q.gauche)) for g in gs) or any(not (0 <= d < len(q.droite)) for d in ds):
            raisons.append("PAIRE_HORS_BORNES")
        elif sorted(gs) != list(range(len(q.gauche))):
            raisons.append("GAUCHE_NON_ASSOCIE_EXACTEMENT_UNE_FOIS")
        elif not q.droite_reutilisable and len(set(ds)) != len(ds):
            raisons.append("DROITE_REUTILISEE")
        if len(q.droite) < len(q.gauche) and not q.droite_reutilisable:
            raisons.append("DROITE_INSUFFISANTE")
    return sorted(set(raisons))


# --------------------------------------------------------------------------- #
# Correction d'une réponse d'élève
# --------------------------------------------------------------------------- #
def corriger(q: Question, reponse: Any) -> Resultat:
    if isinstance(q, QuestionVraiFaux):
        if not isinstance(reponse, bool):
            return revue("reponse_non_booleenne")
        return valide("reponse_correcte") if reponse is q.affirmation_vraie else invalide("reponse_incorrecte")

    if isinstance(q, QuestionReponseCourte):
        if not isinstance(reponse, str):
            return revue("reponse_non_textuelle")
        return verifier(q.type_verification, q.reponse_reference, reponse, q.parametres_verification)

    if isinstance(q, QuestionClassement):
        n = len(q.elements)
        if not isinstance(reponse, (list, tuple)) or any(type(i) is not int for i in reponse):
            return revue("reponse_structuree_invalide")
        if sorted(reponse) != list(range(n)):
            return invalide("reponse_non_permutation")
        if tuple(reponse) == q.ordre_correct:
            return valide("ordre_correct")
        rang = {e: k for k, e in enumerate(q.ordre_correct)}
        paires = [(a, b) for i, a in enumerate(reponse) for b in reponse[i + 1:]]
        bien = sum(rang[a] < rang[b] for a, b in paires)
        return invalide("ordre_incorrect", f"paires_bien_ordonnees:{bien}/{len(paires)}")

    if isinstance(q, QuestionAssociation):
        if not isinstance(reponse, Mapping):
            return revue("reponse_structuree_invalide")
        try:
            rep = {int(k): v for k, v in reponse.items()}
        except (TypeError, ValueError):
            return revue("reponse_structuree_invalide")
        if any(type(v) is not int for v in rep.values()):
            return revue("reponse_structuree_invalide")
        attendu = dict(q.paires)
        if set(rep) != set(attendu):
            return invalide("association_incomplete")
        if any(not (0 <= v < len(q.droite)) for v in rep.values()):
            return invalide("association_hors_bornes")
        justes = sum(rep[g] == d for g, d in attendu.items())
        if justes == len(attendu):
            return valide("associations_correctes")
        return invalide("associations_incorrectes", f"associations_justes:{justes}/{len(attendu)}")

    return revue("type_question_inconnu")


def raisons_bloquantes(q: Question, idx: IndexReferentiel, *, autoriser_fictif: bool = False) -> Tuple[str, ...]:
    return tuple(valider(q, idx, autoriser_fictif=autoriser_fictif))


def score_partiel(r: Resultat) -> Optional[Tuple[int, int]]:
    """Extrait « a/b » des raisons (paires ou associations justes) — information d'adaptation."""
    for raison in r.raisons:
        m = re.search(r":(\d+)/(\d+)$", raison)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


__all__ = ["QuestionVraiFaux", "QuestionReponseCourte", "QuestionClassement", "QuestionAssociation",
           "Question", "valider", "corriger", "score_partiel", "raisons_bloquantes"]

