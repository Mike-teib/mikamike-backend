"""
Oracle récurrence renforcé (lot 12) : Mika identifie l'ÉTAPE qui bloque et pose UNE question
qui ne donne pas la réponse. Fonction auxiliaire : correspondance avec la relation de récurrence.
"""

import pytest

from app.curriculum.pedagogie.recurrence import (
    ETAPE_DE,
    QUESTIONS_GUIDAGE,
    analyser_redaction,
    diagnostiquer_redaction,
    verifier_fonction_auxiliaire,
    verifier_heredite_fonction_auxiliaire,
)
from app.curriculum.verifiers.base import Verdict

OK = {
    "propriete": "Soit P(n) : « u(n) = 2^n ».",
    "initialisation": "Pour n = 0 : u0 = 1 et 2^0 = 1, donc P(0) est vraie.",
    "hypothese": "Supposons P(n) vraie pour un certain entier n ≥ 0.",
    "heredite": "Montrons P(n+1). D'après l'hypothèse de récurrence, u(n+1) = 2u(n) = 2×2^n = 2^(n+1).",
    "conclusion": "Par récurrence, P(n) est vraie pour tout entier n ≥ 0.",
}


def test_redaction_complete():
    r = analyser_redaction(OK, 0, exiger_propriete=True)
    assert r["complete"] and r["etape_bloquante"] is None and r["question"] is None
    assert r["etapes_valides"] == ["propriete", "initialisation", "hypothese", "heredite", "conclusion"]


@pytest.mark.parametrize("section,texte,confusion,etape", [
    ("initialisation", "", "INIT_ABSENTE", "initialisation"),
    ("initialisation", "Pour n = 1 : u1 = 2 = 2^1 donc P(1) est vraie.", "INIT_MAUVAIS_RANG", "initialisation"),
    ("hypothese", "", "HYP_ABSENTE", "hypothese"),
    ("hypothese", "Supposons P(n) vraie.", "HYP_SANS_RANG", "hypothese"),
    ("hypothese", "Supposons P(n) vraie pour tout n.", "HYP_POUR_TOUT_N", "hypothese"),
    ("heredite", "D'après l'hypothèse de récurrence, P(n+1) implique P(n), donc c'est vrai.",
     "HER_IMPLICATION_INVERSEE", "heredite"),
    ("heredite", "Si P(n+1) est vraie alors P(n) aussi, d'après l'hypothèse de récurrence.",
     "HER_IMPLICATION_INVERSEE", "heredite"),
    ("heredite", "Montrons P(n+1). u(n+1) = 2u(n) = 2^(n+1).", "HER_SANS_HYPOTHESE", "heredite"),
    ("conclusion", "Il existe un entier n tel que P(n) est vraie.", "CONCL_QUANTIFICATEUR_EXISTENTIEL", "conclusion"),
    ("conclusion", "Donc P(n+1) est vraie.", "CONCL_P_N_PLUS_1_SEULEMENT", "conclusion"),
    ("propriete", "", "PROP_NON_DEFINIE", "propriete"),
])
def test_etape_bloquante_identifiee(section, texte, confusion, etape):
    r = analyser_redaction(dict(OK, **{section: texte}), 0, exiger_propriete=True)
    assert confusion in r["confusions"], r
    assert r["etape_bloquante"] == etape
    assert r["question"] == QUESTIONS_GUIDAGE[r["confusions"][0]]
    assert r["question"].endswith("?") and "2^(n+1)" not in r["question"] and "2^n" not in r["question"]


def test_eleve_bloque_des_le_debut():
    r = analyser_redaction({}, 0, exiger_propriete=True)
    assert r["etape_bloquante"] == "propriete" and r["etapes_valides"] == []
    r = analyser_redaction({}, 0)
    assert r["etape_bloquante"] == "initialisation"


def test_eleve_partiellement_correct():
    redac = dict(OK, heredite="Montrons P(n+1). u(n+1) = 2u(n) = 2^(n+1).")
    r = analyser_redaction(redac, 0, exiger_propriete=True)
    assert r["etape_bloquante"] == "heredite"
    assert r["etapes_valides"] == ["propriete", "initialisation", "hypothese", "conclusion"]


def test_une_seule_question_dans_l_ordre_de_la_demonstration():
    redac = dict(OK, initialisation="Pour n = 1 : P(1) est vraie.", conclusion="Donc P(n+1) est vraie.")
    r = analyser_redaction(redac, 0)
    assert r["etape_bloquante"] == "initialisation" and r["confusions"][-1] == "CONCL_P_N_PLUS_1_SEULEMENT"


def test_propriete_definie_dans_la_redaction_suffit():
    redac = {k: v for k, v in OK.items() if k != "propriete"}
    redac["initialisation"] = "Notons P(n) la propriété u(n) = 2^n. Pour n = 0 : P(0) est vraie."
    assert "PROP_NON_DEFINIE" not in diagnostiquer_redaction(redac, 0, exiger_propriete=True)


def test_implication_dans_le_bon_sens_non_signalee():
    redac = dict(OK, heredite="Montrons P(n+1). D'après l'hypothèse de récurrence, P(n) implique P(n+1).")
    assert "HER_IMPLICATION_INVERSEE" not in diagnostiquer_redaction(redac, 0)


def test_tables_coherentes():
    assert set(ETAPE_DE) == set(QUESTIONS_GUIDAGE)
    assert all(q.endswith("?") for q in QUESTIONS_GUIDAGE.values())


@pytest.mark.parametrize("f,g,verdict", [
    ("sqrt(x+2)", "sqrt(2+x)", Verdict.VALID),
    ("x/2+1", "(x+2)/2", Verdict.VALID),
    ("x/2+1", "x/2", Verdict.INVALID),
    ("x/2+1", "2x+1", Verdict.INVALID),
    ("x/2+1", "x/2+1+y", Verdict.NEEDS_HUMAN_REVIEW),
    ("x/2+1", "9^(9^9)", Verdict.NEEDS_HUMAN_REVIEW),
])
def test_fonction_auxiliaire_correspond_a_la_recurrence(f, g, verdict):
    assert verifier_fonction_auxiliaire(f, g).verdict == verdict


def test_fonction_auxiliaire_puis_stabilite():
    # u(n+1) = sqrt(u(n) + 2), 0 ≤ u(n) ≤ 2 : f croissante et [0, 2] stable ⇒ hérédité démontrée.
    assert verifier_fonction_auxiliaire("sqrt(x+2)", "sqrt(x+2)").verdict == Verdict.VALID
    assert verifier_heredite_fonction_auxiliaire("sqrt(x+2)", "0", "2").verdict == Verdict.VALID
    assert verifier_heredite_fonction_auxiliaire("sqrt(x+2)", "0", "1").verdict == Verdict.INVALID  # f(1) > 1
