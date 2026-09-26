"""
Math guard étendu (lot 13) : équivalence démontrée seulement, ambiguïté ⇒ NEEDS_HUMAN_REVIEW,
temps borné sur entrées hostiles.
"""

import time

import pytest

from app.curriculum.verifiers.base import Verdict as V
from app.curriculum.verifiers.maths_etendu import (
    racine_simplifiee,
    verifier_angle,
    verifier_derivee,
    verifier_ensemble,
    verifier_limite,
    verifier_probabilite,
    verifier_suite,
    verifier_valeur_approchee,
)


@pytest.mark.parametrize("attendu,reponse,verdict", [
    ("x > 3", "]3 ; +inf[", V.VALID),
    ("x > 3", "3 < x", V.VALID),
    ("x > 3", "x >= 3", V.INVALID),                    # borne fermée à tort
    ("x > 3", "[3 ; +∞[", V.INVALID),
    ("-1 <= x < 2", "[-1;2[", V.VALID),
    ("-1 <= x < 2", "]-1;2[", V.INVALID),
    ("2x - 6 > 0", "x > 3", V.VALID),                   # inéquation résolue
    ("x^2 - 4 <= 0", "[-2 ; 2]", V.VALID),
    ("x^2 - 4 > 0", "]-inf;-2[ ∪ ]2;+inf[", V.VALID),
    ("x^2 - 4 > 0", "]2;+inf[", V.INVALID),             # une partie seulement
    ("x^2 + 1 < 0", "∅", V.VALID),
    ("x^2 + 1 > 0", "R", V.VALID),
    ("x > 3", "x > trois", V.NEEDS_HUMAN_REVIEW),
    ("x^3 - x > 0", "x > 1", V.NEEDS_HUMAN_REVIEW),      # degré 3 : hors périmètre ⇒ revue
    ("x > 3", "S = ]3 ; +∞[", V.VALID),
])
def test_ensembles(attendu, reponse, verdict):
    assert verifier_ensemble(attendu, reponse).verdict == verdict


@pytest.mark.parametrize("f,rep,verdict", [
    ("x^2", "2x", V.VALID),
    ("x^2", "f'(x) = 2*x", V.VALID),
    ("x^2", "x^2", V.INVALID),
    ("3x^2 + 2x - 5", "6x + 2", V.VALID),
    ("sin(x)", "cos(x)", V.VALID),
    ("exp(2x)", "2exp(2x)", V.VALID),
    ("exp(2x)", "exp(2x)", V.INVALID),
    ("1/x", "-1/x^2", V.VALID),
    ("x^2 + y", "2x", V.NEEDS_HUMAN_REVIEW),
])
def test_derivees(f, rep, verdict):
    assert verifier_derivee(f, rep).verdict == verdict


@pytest.mark.parametrize("expr,point,rep,verdict", [
    ("1/x", "+inf", "0", V.VALID),
    ("(2x+1)/(x-3)", "+inf", "2", V.VALID),
    ("x^2", "+inf", "+inf", V.VALID),
    ("x^2", "+inf", "-inf", V.INVALID),
    ("sin(x)/x", "0", "1", V.VALID),
    ("1/x", "0", "+inf", V.NEEDS_HUMAN_REVIEW),        # limite bilatérale inexistante ⇒ revue
    ("sin(x)", "+inf", "0", V.NEEDS_HUMAN_REVIEW),     # oscillante
    ("(2x+1)/(x-3)", "+inf", "3", V.INVALID),
])
def test_limites(expr, point, rep, verdict):
    assert verifier_limite(expr, point, rep).verdict == verdict


@pytest.mark.parametrize("nature,u0,r,n0,formule,verdict", [
    ("arithmetique", "5", "3", 0, "u(n) = 5 + 3n", V.VALID),
    ("arithmetique", "5", "3", 1, "5 + 3(n-1)", V.VALID),
    ("arithmetique", "5", "3", 0, "5 + 3(n-1)", V.INVALID),     # mauvais rang
    ("geometrique", "2", "3", 0, "2*3^n", V.VALID),
    ("geometrique", "2", "3", 0, "3*2^n", V.INVALID),
    ("geometrique", "2", "1/2", 0, "2*(1/2)^n", V.VALID),
])
def test_suites(nature, u0, r, n0, formule, verdict):
    assert verifier_suite(nature, u0, r, n0, formule).verdict == verdict


@pytest.mark.parametrize("att,rep,verdict", [
    ("1/4", "0,25", V.VALID), ("1/4", "2/8", V.VALID), ("1/4", "1/3", V.INVALID),
    ("1/4", "4/3", V.INVALID), ("1/4", "-0,25", V.INVALID), ("1/4", "25 %", V.NEEDS_HUMAN_REVIEW),
])
def test_probabilites(att, rep, verdict):
    r = verifier_probabilite(att, rep)
    assert r.verdict == verdict
    if rep in ("4/3", "-0,25"):
        assert "hors_intervalle_probabilite" in r.raisons


@pytest.mark.parametrize("att,rep,unite,verdict", [
    ("90°", "90°", "deg", V.VALID), ("90°", "90", "deg", V.VALID), ("90°", "pi/2", "deg", V.NEEDS_HUMAN_REVIEW),
    ("pi/2", "pi/2", "rad", V.VALID), ("pi/2", "90°", "rad", V.NEEDS_HUMAN_REVIEW), ("pi/2", "pi/3", "rad", V.INVALID),
    ("60°", "pi/3", "rad", V.VALID),
])
def test_angles(att, rep, unite, verdict):
    assert verifier_angle(att, rep, unite).verdict == verdict


@pytest.mark.parametrize("exacte,rep,d,verdict", [
    ("sqrt(3)/2", "0,87", 2, V.VALID), ("sqrt(3)/2", "0,86", 2, V.INVALID),   # troncature ≠ arrondi
    ("sqrt(3)/2", "0,866", 2, V.INVALID), ("sqrt(3)/2", "sqrt(3)/2", 2, V.VALID),
    ("pi", "3,14", 2, V.VALID), ("pi", "3,1416", 4, V.VALID), ("2/3", "0,67", 2, V.VALID),
    ("2/3", "0,66", 2, V.INVALID), ("10", "10,0", 1, V.VALID),
    ("1/4", "0,250", 2, V.INVALID), ("1/2", "0,5", 2, V.INVALID),  # valeur juste, mauvais nombre de décimales
    ("-5/2", "-3", 0, V.VALID), ("-5/2", "-2", 0, V.INVALID), ("-sqrt(3)/2", "-0,87", 2, V.VALID),
])
def test_valeurs_approchees(exacte, rep, d, verdict):
    assert verifier_valeur_approchee(exacte, rep, d).verdict == verdict


@pytest.mark.parametrize("expr,ok", [("2sqrt(2)", True), ("sqrt(8)", False), ("3sqrt(5)", True), ("sqrt(12)", False),
                                     ("sqrt(2)+sqrt(18)", False)])
def test_racines(expr, ok):
    assert racine_simplifiee(expr) is ok


@pytest.mark.parametrize("appel", [
    lambda: verifier_derivee("9^(9^9)", "0"),
    lambda: verifier_derivee("(x+1)^60*(x-1)^60", "0"),
    lambda: verifier_limite("exp(exp(exp(x)))", "+inf", "+inf"),
    lambda: verifier_ensemble("x > 3", "]" + "1" * 300 + ";2["),
    lambda: verifier_limite("tan(x)^60/x", "0", "0"),
])
def test_entrees_hostiles_bornees(appel):
    t = time.perf_counter()
    r = appel()
    assert time.perf_counter() - t < 3 and r.verdict in (V.NEEDS_HUMAN_REVIEW, V.INVALID)
