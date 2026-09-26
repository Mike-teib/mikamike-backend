"""Tests du validateur de qualité du texte des notions (Phase 7)."""

import pytest

from app.curriculum.model import StatutTexte
from app.curriculum.text_quality import analyser_texte, reparer_sans_perte

S = StatutTexte


@pytest.mark.parametrize("texte", [
    "Comparer, ranger et encadrer des fractions.",
    "Théorème de Pythagore",
    "Résoudre une équation du type ax + b = c",
    "Utiliser les fractions 1/10 et 1/100",
    "Connaître la relation a² + b² = c² dans un triangle rectangle",
    "Fonction f : x ↦ ax + b",
    "Écrire un nombre en notation scientifique : a × 10^n",
    "Mesurer le pH d'une solution",
    "Suites : démontrer une propriété par récurrence",
    "Chaîne d'énergie et chaîne d'information...",
    "Programmer en JavaScript un algorithme simple",
])
def test_textes_sains_exacts(texte):
    r = analyser_texte(texte)
    assert r.statut == S.TEXT_EXACT, r.anomalies


def test_ligatures_et_espaces_recuperes_sans_toucher_aux_maths():
    r = analyser_texte("Simpliﬁer  la fraction 1/100­")
    assert r.statut == S.TEXT_RECOVERED
    assert r.texte_normalise == "Simplifier la fraction 1/100"


@pytest.mark.parametrize("texte,attendu", [
    ("Comparer des fractions et", S.TEXT_TRUNCATED),
    ("Résoudre une équation du premier degré avec", S.TEXT_TRUNCATED),
    ("Calculer l'aire d'un disque de", S.TEXT_TRUNCATED),
    ("Identifier les grandeurs,", S.TEXT_TRUNCATED),
    ("et utiliser le théorème de Thalès", S.TEXT_FRAGMENTED),
    ("x", S.TEXT_FRAGMENTED),
    ("Calculer (a + b)² = a² + 2ab + b² ) ", S.FORMULA_CORRUPTED),
    ("Résoudre x + 3 =", S.FORMULA_CORRUPTED),
    ("Calculer � x", S.FORMULA_CORRUPTED),
    ("Calculer  la puissance", S.FORMULA_CORRUPTED),
    ("Fractions     Attendus de fin de cycle     Comparer", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions Connaissances et compétences associées utiliser", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions eduscol.education.fr", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions Ministère de l'Éducation nationale page 12", S.COLUMN_CONTAMINATION),
    ("Comparer des fractionsLes nombres décimaux", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions.Utiliser les décimaux", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions ,, ranger", S.AMBIGUOUS),
    ("Comparer les deux fractions les deux fractions données", S.AMBIGUOUS),
])
def test_textes_suspects(texte, attendu):
    r = analyser_texte(texte)
    assert r.statut == attendu, (r.statut, r.anomalies)


def test_absent_de_la_source():
    r = analyser_texte("Comparer des fractions", extrait_source="Utiliser les nombres décimaux.")
    assert r.statut == S.SOURCE_NOT_EVIDENCED
    r2 = analyser_texte("Comparer des fractions", extrait_source="… Comparer  des fractions. …")
    assert r2.statut == S.TEXT_EXACT


def test_reparation_ne_change_pas_les_expressions():
    for expr in ["1/10", "10^-3", "(a+b)^2", "√2", "x² − 4 = 0", "3,5 × 10^4"]:
        assert reparer_sans_perte(expr) == expr
