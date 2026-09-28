"""Tests de pedagogy.qa.level_lexicon (heuristique)."""

from __future__ import annotations

import pytest

from pedagogy.models import DifficultyBand, Level, Subject
from pedagogy.qa.level_lexicon import LEXICON, check_text_level, fold, is_too_simple

M, PC, SVT = Subject.MATHS, Subject.PHYSIQUE_CHIMIE, Subject.SVT


def terms(text, subject, level):
    return [t for t, _ in check_text_level(text, subject, level)]


@pytest.mark.parametrize("text,subject,too_low,ok_level,term", [
    ("Calculer la dérivée de f.", M, Level.SECONDE, Level.PREMIERE, "dérivée"),
    ("Utiliser le logarithme népérien.", M, Level.PREMIERE, Level.TERMINALE, "logarithme"),
    ("Calculer l'intégrale de f sur [0;1].", M, Level.PREMIERE, Level.TERMINALE, "intégrale"),
    ("Soit le vecteur AB.", M, Level.TROISIEME, Level.SECONDE, "vecteur"),
    ("Calculer le discriminant.", M, Level.SECONDE, Level.PREMIERE, "discriminant"),
    ("Étudier la fonction exponentielle.", M, Level.SECONDE, Level.PREMIERE, "exponentielle"),
    ("Calculer le cosinus de l'angle.", M, Level.CINQUIEME, Level.QUATRIEME, "cosinus"),
    ("Ranger ces nombres relatifs.", M, Level.SIXIEME, Level.CINQUIEME, "nombre relatif / négatif"),
    ("Calculer la quantité de matière en mol.", PC, Level.TROISIEME, Level.SECONDE, "mole / quantité de matière"),
    ("L'ADN porte l'information génétique.", SVT, Level.CINQUIEME, Level.QUATRIEME, "ADN / gène"),
    ("Décrire la mitose.", SVT, Level.QUATRIEME, Level.TROISIEME, "mitose / méiose"),
])
def test_term_min_level(text, subject, too_low, ok_level, term):
    assert term in terms(text, subject, too_low)
    assert term not in terms(text, subject, ok_level)


def test_accents_and_case_folded():
    assert "dérivée" in terms("LA DERIVEE de f", M, Level.SECONDE)


def test_subject_scope_avoids_false_positives():
    # « montage en dérivation » : vocabulaire de physique-chimie au collège.
    assert terms("Réaliser un montage en dérivation.", PC, Level.CINQUIEME) == []
    # « vecteur » d'une maladie en SVT.
    assert terms("Le moustique est un vecteur du paludisme.", SVT, Level.CINQUIEME) == []
    # « atmosphère primitive » en SVT.
    assert terms("L'atmosphère primitive de la Terre.", SVT, Level.QUATRIEME) == []
    # « molécule » ne déclenche pas « mole ».
    assert terms("Une molécule d'eau.", PC, Level.CINQUIEME) == []


def test_sorted_and_deterministic():
    text = "Le logarithme et la dérivée d'un vecteur"
    res = check_text_level(text, M, Level.SIXIEME)
    assert res == [("vecteur", Level.SECONDE), ("dérivée", Level.PREMIERE), ("logarithme", Level.TERMINALE)]
    assert res == check_text_level(text, M, Level.SIXIEME)


def test_no_hit_at_terminale():
    text = " ".join(e.term for e in LEXICON)
    assert check_text_level(text, M, Level.TERMINALE) == []


def test_lexicon_patterns_match_their_own_term():
    for e in LEXICON:
        subject = next(iter(sorted(e.subjects, key=lambda s: s.value))) if e.subjects else M
        assert check_text_level(e.term.split(" /")[0], subject, Level.SIXIEME) or e.min_level == Level.SIXIEME, e.term


def test_too_simple():
    assert is_too_simple("Calculer 3 + 4.", Level.SECONDE, DifficultyBand.DISCOVERY)
    assert is_too_simple("Combien font 7 × 8 ?", Level.TERMINALE, DifficultyBand.DISCOVERY)
    # négatifs : collège, autre bande, nombres à plusieurs chiffres, variable, pas d'opération
    assert not is_too_simple("Calculer 3 + 4.", Level.TROISIEME, DifficultyBand.DISCOVERY)
    assert not is_too_simple("Calculer 3 + 4.", Level.SECONDE, DifficultyBand.APPLICATION)
    assert not is_too_simple("Calculer 13 + 4.", Level.SECONDE, DifficultyBand.DISCOVERY)
    assert not is_too_simple("Résoudre x + 3 = 5.", Level.SECONDE, DifficultyBand.DISCOVERY)
    assert not is_too_simple("Calculer 3².", Level.SECONDE, DifficultyBand.DISCOVERY)
    assert not is_too_simple("Citer 3 organites.", Level.SECONDE, DifficultyBand.DISCOVERY)


def test_fold():
    assert fold("  Équation   DIFFÉRENTIELLE ") == "equation differentielle"
