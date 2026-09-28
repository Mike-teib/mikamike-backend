"""checks.maths : équivalence symbolique sécurisée ; entrées hostiles jamais VALID, temps borné."""

import time

import pytest

from pedagogy.checks.maths import (
    check_math_answer,
    equivalent,
    find_equivalent_in_text,
    math_candidates,
    normalize_math,
    MathInputRejected,
)
from pedagogy.checks.verdict import Verdict

V, I, A, R = Verdict.VALID, Verdict.INVALID, Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("expected,answer,verdict", [
    ("x=3", "3", V), ("x=3", "x = 6/2", V), ("x=3", "y=3", I), ("x=3", "4", I),
    ("1/2", "0,5", V), ("1/2", "0.5", V), ("3,5", "7/2", V), (0.1, "1/10", V), (3, "6/2", V),
    ("(x+1)^2", "x^2+2x+1", V), ("(x+1)^2", "x^2+1", I),
    ("a^2+2ab+b^2", "(a+b)²", V), ("5x", "3x+2x", V), ("sqrt(8)", "2√2", V),
    ("x=2 ou x=-2", "x=-2 ou x=2", V), ("x=2 ou x=-2", "x=2", I),
    ("1", "1/0", I), ("1", "ln(0)", I), ("3/4", "", I),
    ("3/4", "\\frac{3}{4}", V), ("3/4", "$\\dfrac{6}{8}$", V), ("x^2", "x^{2}", V),
])
def test_check_math_answer(expected, answer, verdict):
    assert check_math_answer(expected, answer).verdict == verdict


@pytest.mark.parametrize("expected,answer,form,verdict", [
    ("3/4", "3/4", "fraction_irreductible", V),
    ("3/4", "6/8", "fraction_irreductible", I),
    ("3/4", "0,75", "fraction_irreductible", I),
    ("4", "8/2", "entier", I), ("4", "4", "entier", V),
    ("0,75", "3/4", "decimal", I), ("0,75", "0,75", "decimal", V),
    ("x^2+2x+1", "(x+1)^2", "developpee", I), ("x^2+2x+1", "x^2+2x+1", "developpee", V),
    ("(x+1)^2", "x^2+2x+1", "factorisee", I), ("(x+1)^2", "(x+1)^2", "factorisee", V),
    ("3*x+15", "3(x+5)", "factorisee", V),
    ("(x+1)*(x-2)", "(x+1)(x-2)", "factorisee", V),
    ("3*x+15", "3x+15", "factorisee", I),
    ("exp(x)", "e^x", "factorisee", I),
    ("3/4", "3/4", "forme_inventee", R),
])
def test_formes_requises(expected, answer, form, verdict):
    assert check_math_answer(expected, answer, form).verdict == verdict


@pytest.mark.parametrize("hostile", [
    "__import__('os').system('ls')",
    "eval('1')",
    "x.n()",
    "(1).evalf()",
    "lambda: 1",
    "9^9^9",
    "10^(59)^(59)",
    "9^(59*59*59*59)",
    "2^1000",
    "(x+y+z+1)^60",
    "exp(exp(exp(59)))",
    "sin(x)^59",
    "1" * 300,
    "12345678901234567890",
    "x" * 250,
    "Symbol('a')",
    "open",
    "globals",
    "1,2,3",
    "x = = 3",
    "((((((((((",
    "√",
    "π²²²",
])
def test_entrees_hostiles_jamais_valid_et_bornees(hostile):
    t = time.perf_counter()
    r1 = check_math_answer("2", hostile)
    r2 = equivalent("2", hostile)
    r3 = check_math_answer(hostile, "2")  # attendue hostile : revue, jamais VALID
    assert time.perf_counter() - t < 3
    assert r1.verdict != V and r2.verdict != V and r3.verdict != V


def test_attendue_non_analysable_donne_revue():
    assert check_math_answer("trois demis", "3/2").verdict == R
    assert check_math_answer(True, "1").verdict == R


def test_normalisation_refuse_attributs():
    with pytest.raises(MathInputRejected):
        normalize_math("x.subs")


def test_equivalence_non_prouvee_nest_pas_valid():
    r = equivalent("sin(x)^2+cos(x)^2", "1")
    assert r.verdict in (V, A)  # prouvée par simplify ; jamais VALID sur simple test numérique
    assert equivalent("x", "x+10^-15").verdict != V


def test_candidats_et_recherche_dans_texte():
    assert "3/2" in math_candidates("On simplifie par 6 : 18/12 = 3/2.")
    assert find_equivalent_in_text("3/2", "On simplifie : 18/12 = 3/2.")
    assert find_equivalent_in_text("x = 3", "On divise par 2 : x = 6/2 = 3.")
    assert find_equivalent_in_text("x=2 ou x=-2", "donc x = 2 ou x = -2.")
    assert not find_equivalent_in_text("3/2", "2/3 × 9/4 = 5/4.")  # le membre de gauche est ignoré
    assert find_equivalent_in_text("x^2+2x+1", "$= x^2 + 2x + 1$")
