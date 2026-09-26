"""Filet mathématique : préservation exacte des expressions + vérification symbolique."""

import pytest

from app.curriculum.math_guard import appliquer_sans_toucher_maths, proteger, restaurer, verifier_preservation
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.maths import equivalents, verifier_reponse

V, I, A, R = Verdict.VALID, Verdict.INVALID, Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW


# --------------------------------------------------------------------------- #
# Préservation dans les textes
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("source,sortie,code", [
    ("Utiliser 1/10 et 1/100", "Utiliser 0,1 et 1/100", "FRACTION_CONVERTIE:1/10"),
    ("Utiliser 1/100", "Utiliser 0.01", "FRACTION_CONVERTIE:1/100"),
    ("Utiliser 1/100", "Utiliser 1 100", "FRACTION_PERDUE:1/100"),
    ("Calculer x² + 1", "Calculer x2 + 1", "EXPOSANT_PERDU"),
    ("Écrire 10^-3 m", "Écrire 10-3 m", "EXPOSANT_PERDU"),
    ("Développer (a + b)(a - b)", "Développer a + b(a - b)", "PARENTHESES_MODIFIEES"),
    ("Calculer √2 × 3", "Calculer 2 × 3", "RACINE_PERDUE"),
    ("Si x ≤ 3 alors", "Si x < 3 alors", "SYMBOLE_MODIFIE"),
    ("a = b", "a b", "OPERATEUR_MODIFIE"),
    ("π r²", "� r²", "CARACTERE_CORROMPU"),
])
def test_alterations_detectees(source, sortie, code):
    assert code in verifier_preservation(source, sortie)


def test_texte_identique_sans_anomalie():
    t = "Calculer (a + b)² = a² + 2ab + b², puis 1/10 de 10^3 et √2 ≤ 2"
    assert verifier_preservation(t, t) == []


def test_transformation_sans_toucher_aux_maths():
    source = "Calculer   1/10   de (x+1)^2  et  x² ≤ 3"
    sortie = appliquer_sans_toucher_maths(source, lambda t: " ".join(t.split()).upper())
    assert "1/10" in sortie and "(x+1)^2" in sortie and "x² ≤ 3" in sortie
    assert verifier_preservation(source, sortie) == []


def test_jeton_altere_detecte():
    masque, expr = proteger("Calculer 1/10 de 20")
    assert expr
    with pytest.raises(ValueError):
        restaurer(masque.replace("⁣", ""), expr)


# --------------------------------------------------------------------------- #
# Vérification symbolique
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("attendue,reponse,verdict", [
    ("x=3", "3", V), ("x=3", "x = 6/2", V), ("x=3", "y=3", I), ("x=3", "4", I),
    ("1/2", "0,5", V), ("1/2", "0.5", V), ("3,5", "7/2", V),
    ("(x+1)^2", "x^2+2x+1", V), ("(x+1)^2", "x^2+1", I),
    ("a^2+2ab+b^2", "(a+b)²", V), ("5x", "3x+2x", V), ("sqrt(8)", "2√2", V),
    ("x=2 ou x=-2", "x=-2 ou x=2", V), ("x=2 ou x=-2", "x=2", I),
    ("1", "1/0", I), ("1", "ln(0)", I),
])
def test_verifier_reponse(attendue, reponse, verdict):
    assert verifier_reponse(attendue, reponse).verdict == verdict


@pytest.mark.parametrize("hostile", [
    "__import__('os')", "9^9^9", "2^99999", "x^(2^3)", "lambda", "eval(1)",
    "9" * 20, "1;2", "a" * 300, "[1]", "x=3=3",
])
def test_entrees_hostiles_jamais_valid(hostile):
    r = verifier_reponse("1", hostile)
    assert r.verdict in (I, R), r


def test_reponse_vide_invalide():
    assert verifier_reponse("x=3", "").verdict == I
    assert verifier_reponse("x=3", "   ").verdict == I


def test_lettres_sympy_sont_des_symboles_ordinaires():
    # E, I, N, S, O, Q ne doivent pas devenir e, i, fonctions SymPy…
    assert equivalents("E", "E").verdict == V
    assert verifier_reponse("1", "E").verdict == I
    assert verifier_reponse("-1", "I^2").verdict == I


@pytest.mark.parametrize("attendue,reponse,forme,verdict", [
    ("1/2", "2/4", "fraction_irreductible", I),
    ("1/2", "1/2", "fraction_irreductible", V),
    ("1/2", "0,5", "fraction_irreductible", I),
    ("1/2", "0,5", "decimal", V),
    ("3", "6/2", "entier", I),
    ("x^2+2x+1", "(x+1)^2", "developpee", I),
    ("x^2+2x+1", "x^2+2x+1", "developpee", V),
    ("x^2-1", "(x-1)(x+1)", "factorisee", V),
    ("x^2-1", "x^2-1", "factorisee", I),
])
def test_formes_requises(attendue, reponse, forme, verdict):
    assert verifier_reponse(attendue, reponse, forme).verdict == verdict
