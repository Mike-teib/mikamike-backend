"""
Types de quiz (lot 10) : vrai/faux, réponse courte, classement, association.
Conception contrôlée (codes) et correction EXACTE (score partiel = information, jamais réussite).
"""

import pytest
from pydantic import ValidationError

from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.quiz_types import (
    QuestionAssociation,
    QuestionClassement,
    QuestionReponseCourte,
    QuestionVraiFaux,
    corriger,
    score_partiel,
    valider,
)
from app.curriculum.verifiers.base import Verdict as V


@pytest.fixture(scope="module")
def idx():
    return referentiel_fictif().index()


def _commun(idx, **k):
    n = idx.notions["notion:fictif:fractions-decimales"]
    base = dict(id="quiz:fictif:q1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                enonce="[FICTIF] Question de test ?", explication="Parce que 7/10 = 0,7.")
    base.update(k)
    return base


# --- vrai / faux -------------------------------------------------------------------------------
def test_vrai_faux(idx):
    q = QuestionVraiFaux(**_commun(idx, enonce="7/10 est égal à 0,7."), affirmation_vraie=True)
    assert valider(q, idx, autoriser_fictif=True) == []
    assert corriger(q, True).verdict == V.VALID
    assert corriger(q, False).verdict == V.INVALID
    assert corriger(q, "vrai").verdict == V.NEEDS_HUMAN_REVIEW   # jamais de coercition texte → booléen
    assert corriger(q, 1).verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("enonce,code", [
    ("Il n'est pas faux que 7/10 ne soit pas 0,7.", "DOUBLE_NEGATION"),
    ("Une fraction décimale est souvent inférieure à 1.", "AFFIRMATION_IMPRECISE"),
])
def test_vrai_faux_conception(idx, enonce, code):
    q = QuestionVraiFaux(**_commun(idx, enonce=enonce), affirmation_vraie=False)
    assert code in valider(q, idx, autoriser_fictif=True)


def test_vrai_faux_booleen_strict(idx):
    with pytest.raises(ValidationError):
        QuestionVraiFaux(**_commun(idx), affirmation_vraie="true")


# --- réponse courte ----------------------------------------------------------------------------
def test_reponse_courte(idx):
    q = QuestionReponseCourte(**_commun(idx, enonce="Écris 7/10 en décimal."), reponse_reference="0,7",
                              type_verification="maths_symbolique", parametres_verification={"forme_requise": "decimal"})
    assert valider(q, idx, autoriser_fictif=True) == []
    assert corriger(q, "0,7").verdict == V.VALID
    assert corriger(q, "0.70").verdict == V.VALID
    assert corriger(q, "0,07").verdict == V.INVALID
    assert corriger(q, 0.7).verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("surcharge,code", [
    ({"type_verification": "inconnu"}, "TYPE_VERIFICATION_INCONNU"),
    ({"reponse_reference": "zéro virgule sept"}, "REFERENCE_NON_VERIFIABLE"),
    ({"enonce": "Vérifie que 7/10 = 0,7"}, "FUITE_REPONSE"),
    ({"explication": ""}, "NON_EXPLICABLE"),
])
def test_reponse_courte_conception(idx, surcharge, code):
    k = dict(reponse_reference="0,7", type_verification="maths_symbolique")
    enonce = surcharge.pop("enonce", "Écris 7/10 en décimal.")
    explication = surcharge.pop("explication", "7 dixièmes.")
    k.update(surcharge)
    q = QuestionReponseCourte(**_commun(idx, enonce=enonce, explication=explication), **k)
    assert code in valider(q, idx, autoriser_fictif=True)


# --- classement --------------------------------------------------------------------------------
def _classement(idx, **k):
    base = dict(elements=("0,7", "1/2", "3/4", "0,05"), ordre_correct=(3, 1, 0, 2), valeurs=(0.7, 0.5, 0.75, 0.05))
    base.update(k)
    return QuestionClassement(**_commun(idx, enonce="Range dans l'ordre croissant."), **base)


def test_classement(idx):
    q = _classement(idx)
    assert valider(q, idx, autoriser_fictif=True) == []
    assert corriger(q, [3, 1, 0, 2]).verdict == V.VALID
    r = corriger(q, [3, 0, 1, 2])
    assert r.verdict == V.INVALID and score_partiel(r) == (5, 6)
    assert corriger(q, [3, 1, 0]).verdict == V.INVALID
    assert corriger(q, [3, 1, 0, 0]).verdict == V.INVALID
    assert corriger(q, ["3", 1, 0, 2]).verdict == V.NEEDS_HUMAN_REVIEW
    assert corriger(q, [True, 1, 0, 2]).verdict == V.NEEDS_HUMAN_REVIEW
    assert corriger(q, "3102").verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("k,code", [
    ({"ordre_correct": (0, 1, 2, 2)}, "ORDRE_NON_PERMUTATION"),
    ({"ordre_correct": (0, 1, 2, 3), "valeurs": None}, "ORDRE_DEJA_DONNE"),
    ({"ordre_correct": (1, 3, 0, 2)}, "ORDRE_CONTREDIT_LES_VALEURS"),
    ({"valeurs": (0.7, 0.5, 0.5, 0.05)}, "ORDRE_INDECIDABLE_EGALITE"),
    ({"valeurs": (0.7, 0.5)}, "VALEURS_INCOHERENTES"),
    ({"elements": ("0,7", "0,7", "3/4", "0,05")}, "ELEMENTS_DUPLIQUES"),
])
def test_classement_conception(idx, k, code):
    assert code in valider(_classement(idx, **k), idx, autoriser_fictif=True)


def test_classement_decroissant(idx):
    q = _classement(idx, ordre_correct=(2, 0, 1, 3), croissant=False)
    assert valider(q, idx, autoriser_fictif=True) == []


# --- association -------------------------------------------------------------------------------
def _assoc(idx, **k):
    base = dict(gauche=("1/2", "3/4", "7/10"), droite=("0,75", "0,5", "0,7", "0,07"), paires=((0, 1), (1, 0), (2, 2)))
    base.update(k)
    return QuestionAssociation(**_commun(idx, enonce="Relie chaque fraction à son écriture décimale."), **base)


def test_association(idx):
    q = _assoc(idx)
    assert valider(q, idx, autoriser_fictif=True) == []
    assert corriger(q, {0: 1, 1: 0, 2: 2}).verdict == V.VALID
    assert corriger(q, {"0": 1, "1": 0, "2": 2}).verdict == V.VALID     # clés JSON
    r = corriger(q, {0: 1, 1: 0, 2: 3})
    assert r.verdict == V.INVALID and score_partiel(r) == (2, 3)
    assert corriger(q, {0: 1, 1: 0}).verdict == V.INVALID
    assert corriger(q, {0: 1, 1: 0, 2: 9}).verdict == V.INVALID
    assert corriger(q, {0: "1", 1: 0, 2: 2}).verdict == V.NEEDS_HUMAN_REVIEW
    assert corriger(q, {"a": 1}).verdict == V.NEEDS_HUMAN_REVIEW
    assert corriger(q, [1, 0, 2]).verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("k,code", [
    ({"paires": ((0, 1), (1, 1), (2, 2))}, "DROITE_REUTILISEE"),
    ({"paires": ((0, 1), (2, 2))}, "GAUCHE_NON_ASSOCIE_EXACTEMENT_UNE_FOIS"),
    ({"paires": ((0, 1), (0, 0), (2, 2))}, "GAUCHE_NON_ASSOCIE_EXACTEMENT_UNE_FOIS"),
    ({"paires": ((0, 1), (1, 0), (2, 9))}, "PAIRE_HORS_BORNES"),
    ({"droite": ("0,75", "0,5")}, "DROITE_INSUFFISANTE"),
    ({"gauche": ("1/2", "1/2", "7/10")}, "ELEMENTS_DUPLIQUES"),
])
def test_association_conception(idx, k, code):
    assert code in valider(_assoc(idx, **k), idx, autoriser_fictif=True)


def test_association_droite_reutilisable(idx):
    q = _assoc(idx, paires=((0, 1), (1, 1), (2, 2)), droite_reutilisable=True)
    assert "DROITE_REUTILISEE" not in valider(q, idx, autoriser_fictif=True)


# --- verrous communs ---------------------------------------------------------------------------
def test_verrous_notion_communs(idx):
    q = QuestionVraiFaux(**_commun(idx, notion_id="notion:inexistante"), affirmation_vraie=True)
    assert valider(q, idx, autoriser_fictif=True) == ["NOTION_INCONNUE"]
    q = QuestionVraiFaux(**_commun(idx), affirmation_vraie=True)
    assert any(r.startswith("NOTION_NON_AUTORISEE") for r in valider(q, idx, autoriser_fictif=False))
    q = QuestionVraiFaux(**_commun(idx, niveau="tle"), affirmation_vraie=True)
    assert "NIVEAU_INCOHERENT" in valider(q, idx, autoriser_fictif=True)


def test_champs_inconnus_refuses(idx):
    with pytest.raises(ValidationError):
        QuestionVraiFaux(**_commun(idx), affirmation_vraie=True, bonus=1)
