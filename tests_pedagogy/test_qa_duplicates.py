"""Tests de pedagogy.qa.duplicates."""

from __future__ import annotations

from pedagogy.issues import Severity
from pedagogy.qa.duplicates import (
    find_exercise_duplicates,
    find_quiz_duplicates,
    jaccard,
    mask_numbers,
    normalize_text,
    trigrams,
)

try:
    from tests_pedagogy.qa_fixtures import exercise, quiz
except ImportError:  # pragma: no cover
    from qa_fixtures import exercise, quiz

N1 = "MATHS.6E.NC.fractions-simples"
N2 = "MATHS.6E.NC.aires"
T = "Un jardin rectangulaire mesure {} m de longueur et {} m de largeur. Calculer son aire en metres carres puis son perimetre."


def by_code(issues, code):
    return [i for i in issues if i.code == code]


def test_normalization_helpers():
    assert normalize_text("  Calculer   L'ÉQUATION : 3,5 + 2 ! ") == "calculer l equation 3_5 + 2"
    assert mask_numbers(normalize_text("Calculer 3,5 + 12")) == "calculer # + #"
    assert jaccard(trigrams("abc"), trigrams("abc")) == 1.0
    assert jaccard(set(), set()) == 1.0


def test_exact_duplicate_even_across_notions():
    a = exercise("EX.a.1", N1, "Calculer la somme de 3/4 et 1/4.")
    b = exercise("EX.a.2", N2, "calculer  la somme de 3/4 et 1/4 !")
    issues = find_exercise_duplicates([b, a])
    hits = by_code(issues, "EXERCISE_DUPLICATE_EXACT")
    assert [(i.object_id, i.detail) for i in hits] == [("EX.a.2", "identique_a:EX.a.1")]
    assert hits[0].severity == Severity.ERROR
    assert not by_code(issues, "EXERCISE_TOO_SIMILAR")
    assert not by_code(issues, "EXERCISE_DUPLICATE_TEMPLATE")


def test_template_duplicate_same_notion_only():
    a = exercise("EX.t.1", N1, T.format(4, 7))
    b = exercise("EX.t.2", N1, T.format(5, 9))
    c = exercise("EX.t.3", N2, T.format(6, 2))
    issues = find_exercise_duplicates([a, b, c])
    tpl = by_code(issues, "EXERCISE_DUPLICATE_TEMPLATE")
    assert [i.object_id for i in tpl] == ["EX.t.2"]
    assert tpl[0].severity == Severity.WARNING
    # c (autre notion) n'est pas un doublon de gabarit, mais reste très proche textuellement
    sim = by_code(issues, "EXERCISE_TOO_SIMILAR")
    assert {i.object_id for i in sim} == {"EX.t.3"}
    assert all(i.severity == Severity.WARNING for i in sim)


def test_too_similar_threshold_and_scope():
    a = exercise("EX.s.1", N1, "Ranger dans l'ordre croissant les fractions un demi, un tiers et un quart.")
    b = exercise("EX.s.2", N1, "Ranger dans l'ordre décroissant les fractions un demi, un tiers et un quart.")
    c = exercise("EX.s.3", N1, "Tracer un triangle équilatéral de côté donné avec un compas.")
    d = exercise("EX.s.4", "MATHS.5E.NC.fractions", "Ranger dans l'ordre croissant les fractions un demi, un tiers et un quart.",
                 level="5E")
    issues = find_exercise_duplicates([a, b, c, d])
    sim = by_code(issues, "EXERCISE_TOO_SIMILAR")
    assert [(i.object_id, i.detail.split(":")[1]) for i in sim] == [("EX.s.2", "EX.s.1")]
    # d est identique à a mais d'un autre niveau : doublon exact quand même
    assert [i.object_id for i in by_code(issues, "EXERCISE_DUPLICATE_EXACT")] == ["EX.s.4"]


def test_distinct_items_no_issue():
    a = exercise("EX.d.1", N1, "Calculer l'aire d'un disque de rayon donné.")
    b = exercise("EX.d.2", N1, "Donner la définition d'un nombre premier.")
    assert find_exercise_duplicates([a, b]) == []
    assert find_exercise_duplicates([]) == []


def test_quiz_duplicates_include_choices():
    q1 = quiz("QZ.q.1", N1, "Quelle fraction est égale à 1/2 ?", choices=("2/4", "1/3", "3/4"))
    q2 = quiz("QZ.q.2", N1, "Quelle fraction est égale à 1/2 ?", choices=("3/4", "2/4", "1/3"))  # mêmes choix, ordre différent
    q3 = quiz("QZ.q.3", N1, "Quelle fraction est égale à 1/2 ?", choices=("5/10", "1/5", "2/3"))
    issues = find_quiz_duplicates([q1, q2, q3])
    assert [i.object_id for i in by_code(issues, "QUIZ_DUPLICATE_EXACT")] == ["QZ.q.2"]
    assert [i.object_id for i in by_code(issues, "QUIZ_DUPLICATE_TEMPLATE")] == ["QZ.q.3"]
    assert all(i.code.startswith("QUIZ_") for i in issues)


def test_deterministic():
    items = [exercise(f"EX.r.{k}", N1, f"Un rectangle mesure {k} cm sur 3 cm. Calculer son aire.") for k in range(1, 5)]
    assert find_exercise_duplicates(items) == find_exercise_duplicates(list(reversed(items)))
