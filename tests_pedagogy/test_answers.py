"""checks.answers : check_answer par AnswerKind ; jamais VALID par défaut."""

import pytest

from pedagogy.checks.answers import (
    answer_texts,
    check_answer,
    check_answer_detailed,
    normalize_answer_text,
    parse_choice,
    parse_matching,
    parse_ordering,
    render_expected,
    text_contains_answer,
)
from pedagogy.checks.verdict import Verdict
from pedagogy.models import AnswerKind, ExpectedAnswer

V, I, A, R = Verdict.VALID, Verdict.INVALID, Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW


def E(kind, value, **kw):
    return ExpectedAnswer(kind=kind, value=value, **kw)


CASES = [
    # MATH_EXPR
    (E("MATH_EXPR", "3/4"), "0,75", V),
    (E("MATH_EXPR", "3/4"), "6/8", V),
    (E("MATH_EXPR", "3/4", required_form="fraction_irreductible"), "6/8", I),
    (E("MATH_EXPR", "x = 3"), "x=6/2", V),
    (E("MATH_EXPR", "x = 3"), "y=3", I),
    (E("MATH_EXPR", 2.5), "5/2", V),
    (E("MATH_EXPR", "3/4"), "__import__('os')", R),
    # QUANTITY
    (E("QUANTITY", 20, unit="m/s"), "72 km/h", V),
    (E("QUANTITY", 20, unit="m/s"), "20", I),
    (E("QUANTITY", 20, unit="m/s"), "20 m", I),
    (E("QUANTITY", "2,50", unit="kg", significant_figures=3), "2,5 kg", I),
    (E("QUANTITY", "2,50", unit="kg", significant_figures=3), "2,50 kg", V),
    (E("QUANTITY", 300000000, unit="m/s", required_form="notation_scientifique"), "3,0 × 10^8 m/s", V),
    (E("QUANTITY", 300000000, unit="m/s", required_form="notation_scientifique"), "300000000 m/s", I),
    (E("QUANTITY", 20, unit="m/s", required_form="unite_imposee"), "72 km/h", I),
    (E("QUANTITY", 20, unit="m/s", required_form="forme_inventee"), "20 m/s", R),
    (E("QUANTITY", 100, unit="m", tolerance_relative=0.05), "104 m", V),
    (E("QUANTITY", 100, unit="m", tolerance_relative=0.05), "106 m", I),
    (E("QUANTITY", 7), "7", V),  # pH, sans dimension
    # EXACT_TEXT
    (E("EXACT_TEXT", "Dioxygène"), "  dioxygène. ", V),
    (E("EXACT_TEXT", "noyau"), "le noyau", V),
    (E("EXACT_TEXT", ["dioxygène", "O2"]), "o2", V),
    (E("EXACT_TEXT", "dioxygène"), "dioxyde de carbone", I),
    (E("EXACT_TEXT", "l’eau"), "L'eau", V),
    # CHOICE
    (E("CHOICE", 2), "2", V),
    (E("CHOICE", 2), "C", V),
    (E("CHOICE", 2), "1", I),
    (E("CHOICE", [0, 2]), "A et C", V),
    (E("CHOICE", [0, 2]), "0", I),
    (E("CHOICE", 2), "la réponse deux", I),
    (E("CHOICE", True), "1", R),
    (E("CHOICE", "n'importe"), "1", R),
    # BOOLEAN
    (E("BOOLEAN", True), "Vrai", V),
    (E("BOOLEAN", "faux"), "false", V),
    (E("BOOLEAN", False), "oui", I),
    (E("BOOLEAN", False), "peut-être", I),
    (E("BOOLEAN", "parfois"), "vrai", R),
    # ORDERING
    (E("ORDERING", ["mm", "cm", "m"]), "mm < cm < m", V),
    (E("ORDERING", ["mm", "cm", "m"]), "mm ; cm ; m", V),
    (E("ORDERING", ["mm", "cm", "m"]), '["mm", "cm", "m"]', V),
    (E("ORDERING", ["mm", "cm", "m"]), "cm ; mm ; m", I),
    (E("ORDERING", ["0,5", "1,5"]), "0,5 ; 1,5", V),
    (E("ORDERING", ["x"]), "x", R),
    # MATCHING
    (E("MATCHING", {"cœur": "pomper le sang", "poumons": "échanges gazeux"}),
     "poumons → échanges gazeux ; cœur → pomper le sang", V),
    (E("MATCHING", {"a": "1", "b": "2"}), '{"a": "1", "b": "2"}', V),
    (E("MATCHING", [["a", "1"], ["b", "2"]]), "a: 1 ; b: 2", V),
    (E("MATCHING", {"a": "1", "b": "2"}), "a -> 2 ; b -> 1", I),
    (E("MATCHING", {"a": "1", "b": "2"}), "a -> 1", I),
    (E("MATCHING", "pas une association"), "a -> 1", R),
    # RUBRIC : toujours revue humaine
    (E("RUBRIC", "Faux, contre-exemple", rubric=("répond faux",)), "Faux, contre-exemple", R),
    (E("RUBRIC", "x", rubric=("c",)), "", R),
]


@pytest.mark.parametrize("expected,student,verdict", CASES)
def test_check_answer(expected, student, verdict):
    assert check_answer(expected, student) == verdict


@pytest.mark.parametrize("expected", [c[0] for c in CASES if c[0].kind != AnswerKind.RUBRIC and c[2] != R])
def test_auto_controle_attendu_se_valide(expected):
    assert check_answer(expected, render_expected(expected)) == V


def test_reponse_vide_ou_absente():
    for kind, value in (("MATH_EXPR", "1"), ("EXACT_TEXT", "a"), ("CHOICE", 0), ("BOOLEAN", True)):
        assert check_answer(E(kind, value), "") == I
        assert check_answer(E(kind, value), None) == I


def test_reponse_trop_longue():
    assert check_answer(E("EXACT_TEXT", "a"), "a" * 5000) == R


def test_jamais_valid_par_defaut():
    # Attendus malformés : jamais VALID
    for exp in (E("MATH_EXPR", None), E("QUANTITY", None), E("EXACT_TEXT", ""), E("CHOICE", None),
                E("ORDERING", None), E("MATCHING", None)):
        assert check_answer(exp, "1") != V


def test_resultat_detaille():
    r = check_answer_detailed(E("QUANTITY", 20, unit="m/s"), "20")
    assert r.verdict == I and "unite_manquante" in r.reasons


def test_parseurs():
    assert parse_choice("B, D") == (1, 3)
    assert parse_choice([2, 0]) == (0, 2)
    assert parse_choice([True]) is None
    assert parse_ordering("a → b → c") == ["a", "b", "c"]
    assert parse_matching("x = 1\ny = 2") == {"x": "1", "y": "2"}
    assert parse_matching("x = 1 ; x = 2") is None
    assert normalize_answer_text("  L’Eau  ") == "l'eau"


def test_textes_de_reponse_et_fuite():
    assert answer_texts(E("MATH_EXPR", "x = 2 ou x = -2")) == ["2", "-2"]
    assert answer_texts(E("QUANTITY", 0.7, unit="m")) == ["0.7"]
    assert answer_texts(E("CHOICE", 1)) == []
    assert not text_contains_answer("la valeur 0,75 est", "0,7")
    assert not text_contains_answer("la valeur 10,7 est", "0,7")
    assert not text_contains_answer("la valeur 0,7", "0,7", min_length=4)
    assert text_contains_answer("la valeur 0,7.", "0.7")
    assert text_contains_answer("on trouve 3/2 !", "3/2")
    assert not text_contains_answer("on trouve 13/2", "3/2")
    assert not text_contains_answer("on trouve 3/25", "3/2")


# --- Séparateur de milliers à la française -----------------------------------------
@pytest.mark.parametrize("student", ["1 200", "1200", "1 200", "1 200"])
def test_thousands_separator_accepted(student):
    from pedagogy.models import AnswerKind, ExpectedAnswer
    assert check_answer(ExpectedAnswer(kind=AnswerKind.MATH_EXPR, value="1200"), student) == Verdict.VALID


@pytest.mark.parametrize("student", ["1 20", "12 00", "10 00"])
def test_badly_grouped_numbers_not_accepted(student):
    from pedagogy.models import AnswerKind, ExpectedAnswer
    assert check_answer(ExpectedAnswer(kind=AnswerKind.MATH_EXPR, value="1200"), student) != Verdict.VALID


def test_ten_thousand_is_not_a_product():
    from pedagogy.models import AnswerKind, ExpectedAnswer
    assert check_answer(ExpectedAnswer(kind=AnswerKind.MATH_EXPR, value="10000"), "10 000") == Verdict.VALID
    assert check_answer(ExpectedAnswer(kind=AnswerKind.MATH_EXPR, value="0"), "10 000") != Verdict.VALID
