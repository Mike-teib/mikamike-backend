"""
R6 — Outils de détection d'équivalence symbolique (app/curriculum/equivalence.py) et audit
du catalogue historique en LECTURE SEULE. Tout cas ambigu ⇒ NEEDS_HUMAN_REVIEW.
"""

import copy
import json

import pytest

from app.api.v1.mikamike import catalogue
from app.curriculum.equivalence import (
    Constat,
    Decision,
    auditer_catalogue,
    classer,
    comparer_unites,
    forme_de_la_consigne,
    synthese,
)

D = Decision


@pytest.mark.parametrize("enonce,attendues,reponse,hist,decision", [
    # équations
    ("Résous : x + 4 = 7", ["x=3", "3"], "x = 3", True, D.ACCEPTER),
    ("Résous : x + 4 = 7", ["x=3", "3"], "3 = x", False, D.ACCEPTER),
    ("Résous : x + 4 = 7", ["x=3", "3"], "y = 3", False, D.REFUSER),
    ("Résous : x + 4 = 7", ["x=3", "3"], "x = 6/2", False, D.NEEDS_HUMAN_REVIEW),  # fond ok, forme non réduite
    ("Résous : x² = 4", ["x = 2 ou x = -2"], "x = -2 ou x = 2", False, D.ACCEPTER),
    ("Résous : x² = 4", ["x = 2 ou x = -2"], "x = 2", False, D.REFUSER),
    # fractions
    ("Simplifie : 4/8", ["1/2"], "1/2", True, D.ACCEPTER),
    ("Simplifie : 4/8", ["1/2"], "2/4", False, D.NEEDS_HUMAN_REVIEW),
    ("Simplifie : 4/8", ["1/2"], "0,5", True, D.NEEDS_HUMAN_REVIEW),  # décimal quand une fraction est demandée
    ("Simplifie : 4/8", ["1/2"], "2/3", False, D.REFUSER),
    ("Écris 7/10 sous forme décimale.", ["0,7"], "0.7", False, D.ACCEPTER),
    ("Écris 7/10 sous forme décimale.", ["0,7"], "7/10", False, D.NEEDS_HUMAN_REVIEW),
    ("Écris 7/10 sous forme décimale.", ["0,7"], "0,70", False, D.NEEDS_HUMAN_REVIEW),
    # puissances / expressions
    ("Réduis : x*x*3", ["3x^2"], "3x²", False, D.ACCEPTER),
    ("Réduis : x*x*3", ["3x^2"], "3*x**2", False, D.ACCEPTER),
    ("Réduis : x*x*3", ["3x^2"], "3x^3", False, D.REFUSER),
    ("Développe : (x+1)(x-1)", ["x^2 - 1"], "x²-1", False, D.ACCEPTER),
    ("Développe : (x+1)(x-1)", ["x^2 - 1"], "(x+1)(x-1)", False, D.NEEDS_HUMAN_REVIEW),
    ("Factorise : x^2 - 1", ["(x+1)(x-1)"], "(x-1)(x+1)", False, D.ACCEPTER),
    ("Calcule : 2 + 3 × 4", ["14"], "14", True, D.ACCEPTER),
    ("Calcule : 2 + 3 × 4", ["14"], "20", False, D.REFUSER),
    ("Calcule : 2^10", ["1024"], "2^10", False, D.NEEDS_HUMAN_REVIEW),
    # consigne sans forme connue : un équivalent jamais accepté ⇒ revue humaine
    ("Quelle est la moitié de 8 ?", ["4"], "8/2", False, D.NEEDS_HUMAN_REVIEW),
    # entrées indécidables / hostiles
    ("Calcule : 2 + 3 × 4", ["14"], "quatorze", False, D.NEEDS_HUMAN_REVIEW),
    ("Calcule : 2 + 3 × 4", ["14"], "9^(9^9)", False, D.NEEDS_HUMAN_REVIEW),
    # unités mathématiques
    ("Convertis 1 m en cm.", ["100 cm"], "100 cm", False, D.ACCEPTER),
    ("Convertis 1 m en cm.", ["100 cm"], "1 m", False, D.NEEDS_HUMAN_REVIEW),  # conversion : forme à trancher
    ("Convertis 1 m en cm.", ["100 cm"], "100 m", False, D.REFUSER),
    ("Aire du carré de côté 2 cm ?", ["4 cm²"], "4 cm2", False, D.ACCEPTER),
    ("Aire du carré de côté 2 cm ?", ["4 cm²"], "4 cm", False, D.REFUSER),  # dimension différente
    ("Aire du carré de côté 2 cm ?", ["4 cm²"], "4", False, D.NEEDS_HUMAN_REVIEW),  # unité omise
    ("Angle droit ?", ["90°"], "90 °", False, D.ACCEPTER),
])
def test_classer(enonce, attendues, reponse, hist, decision):
    assert classer(enonce, attendues, reponse, hist).decision == decision


def test_faux_positif_historique_detecte():
    # Un correcteur de chaînes laxiste qui accepterait « 41 » pour 14 est signalé.
    ligne = classer("Calcule : 2 + 3 × 4", ["14"], "41", True)
    assert ligne.decision == D.REFUSER and ligne.constat == Constat.FAUX_POSITIF_HISTORIQUE


def test_faux_negatif_historique_detecte():
    ligne = classer("Réduis : 3x + 2x", ["5x"], "5*x", False)
    assert ligne.decision == D.ACCEPTER and ligne.constat == Constat.FAUX_NEGATIF_HISTORIQUE


def test_ambigu_jamais_automatique():
    for rep in ("x", "", "1/0", "sin(", "14 km/h", "√"):
        ligne = classer("Calcule : 2 + 3 × 4", ["14"], rep, False)
        assert ligne.decision in (D.NEEDS_HUMAN_REVIEW, D.REFUSER), rep
        assert ligne.decision != D.ACCEPTER


def test_comparer_unites_sans_unite():
    assert comparer_unites("3", "3") is None


@pytest.mark.parametrize("enonce,forme", [("Simplifie : 4/8", "fraction_irreductible"),
                                          ("Réduis : 3x + 2x", "developpee"),
                                          ("Factorise x²-1", "factorisee"),
                                          ("Écris 7/10 sous forme décimale.", "decimal"),
                                          ("Résous : x + 4 = 7", "valeur_simplifiee"),
                                          ("Combien de côtés ?", None)])
def test_forme_de_la_consigne(enonce, forme):
    assert forme_de_la_consigne(enonce) == forme


def test_audit_catalogue_historique_lecture_seule_et_constats():
    avant = copy.deepcopy(catalogue.EXERCICES)
    rapports = auditer_catalogue(catalogue.EXERCICES, catalogue.est_correct)
    assert catalogue.EXERCICES == avant  # aucune donnée officielle modifiée
    s = synthese(rapports)
    assert s["exercices"] == len(catalogue.EXERCICES)
    assert "constat:FAUX_POSITIF_HISTORIQUE" not in s  # aucun non-équivalent accepté aujourd'hui
    par_id = {r.exercice_id: r for r in rapports}
    frac = {ligne.reponse.strip(): ligne for ligne in par_id["exo-maths-fractions-1"].lignes}
    # Constat réel : « 0.5 » est ACCEPTÉ aujourd'hui pour « Simplifie : 4/8 » alors qu'une
    # fraction irréductible est demandée ⇒ décision humaine (D5), pas une correction automatique.
    assert frac["0.5"].historique_accepte and frac["0.5"].decision == D.NEEDS_HUMAN_REVIEW
    assert frac["2/4"].decision == D.NEEDS_HUMAN_REVIEW
    lit = {ligne.reponse.strip(): ligne for ligne in par_id["exo-maths-calcul-litteral-1"].lignes}
    assert lit["5*x"].constat == Constat.FAUX_NEGATIF_HISTORIQUE
    alg = {ligne.reponse.strip(): ligne for ligne in par_id["exo-maths-algebre-1"].lignes}
    assert alg["3 = x"].decision == D.ACCEPTER and not alg["3 = x"].historique_accepte


def test_outil_rapport_deterministe(tmp_path):
    from tools.audit_equivalence import main

    assert main(["--sortie", str(tmp_path / "a")]) == 0
    assert main(["--sortie", str(tmp_path / "b")]) == 0
    for f in ("equivalence.json", "equivalence.md"):
        assert (tmp_path / "a" / f).read_bytes() == (tmp_path / "b" / f).read_bytes()
    data = json.loads((tmp_path / "a" / "equivalence.json").read_text("utf-8"))
    assert data["synthese"]["exercices"] == 4
