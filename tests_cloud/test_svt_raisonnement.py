"""
SVT (lot 15) : raisonnement évalué sur réponses STRUCTURÉES et données fournies ; le texte libre
n'est jamais validé sur la seule présence d'un mot (négation ⇒ revue, jamais VALID).
Données entièrement FICTIVES (aucun contenu de programme officiel).
"""

import pytest

from app.curriculum.verifiers.base import Verdict as V
from app.curriculum.verifiers.svt_raisonnement import (
    occurrences,
    tendance,
    verifier_conclusion_experience,
    verifier_definition,
    verifier_exploitation_documents,
    verifier_extremum,
    verifier_lecture_valeur,
    verifier_lien,
    verifier_protocole,
    verifier_tendance,
)

COURBE = [(0, 2.0), (10, 4.0), (20, 8.0), (30, 12.0), (40, 11.0), (50, 6.0)]


# --- graphique ---------------------------------------------------------------------------------
@pytest.mark.parametrize("a,b,attendu", [(0, 30, "augmente"), (30, 50, "diminue"), (0, 50, "non_monotone")])
def test_tendance(a, b, attendu):
    assert tendance(COURBE, a, b) == attendu
    assert verifier_tendance(COURBE, a, b, attendu).verdict == V.VALID
    autre = "stable" if attendu != "stable" else "augmente"
    r = verifier_tendance(COURBE, a, b, autre)
    assert r.verdict == V.INVALID and f"tendance_incorrecte:{attendu}" in r.raisons


def test_tendance_stable_avec_seuil_et_cas_limites():
    plat = [(0, 5.0), (1, 5.1), (2, 4.95)]
    assert tendance(plat, 0, 2, seuil=0.2) == "stable"
    assert tendance(plat, 0, 2) == "non_monotone"
    assert verifier_tendance(COURBE, 0, 5, "augmente").verdict == V.NEEDS_HUMAN_REVIEW  # une seule mesure
    assert verifier_tendance(COURBE, 0, 30, "ça monte").verdict == V.NEEDS_HUMAN_REVIEW
    assert verifier_tendance([(0, 1)], 0, 1, "stable").verdict == V.NEEDS_HUMAN_REVIEW
    assert verifier_tendance([(0, 1), (0, 2)], 0, 1, "stable").verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("x,rep,verdict", [
    (20, "8", V.VALID), (15, "6", V.VALID), (15, "6,4", V.VALID), (15, "7", V.INVALID),
    (60, "5", V.NEEDS_HUMAN_REVIEW),  # extrapolation refusée
    (-1, "2", V.NEEDS_HUMAN_REVIEW), (20, "huit", V.NEEDS_HUMAN_REVIEW),
])
def test_lecture_valeur(x, rep, verdict):
    assert verifier_lecture_valeur(COURBE, x, rep, precision=0.5).verdict == verdict


def test_lecture_precision_invalide():
    assert verifier_lecture_valeur(COURBE, 20, "8", precision=0).verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("rep,verdict", [
    ({"type": "max", "x": 30, "y": 12}, V.VALID),
    ({"type": "max", "x": 40, "y": 12}, V.INVALID),
    ({"type": "max", "x": 30, "y": 11}, V.INVALID),
    ({"type": "min", "x": 0, "y": 2}, V.VALID),
    ({"type": "pic", "x": 30, "y": 12}, V.NEEDS_HUMAN_REVIEW),
    ({"type": "max"}, V.NEEDS_HUMAN_REVIEW),
])
def test_extremum(rep, verdict):
    assert verifier_extremum(COURBE, rep, precision_x=2, precision_y=0.5).verdict == verdict


def test_extremum_non_unique_revue():
    pts = [(0, 1), (1, 3), (2, 1), (3, 3)]
    assert verifier_extremum(pts, {"type": "max", "x": 1, "y": 3}, precision_x=0.1, precision_y=0.1).verdict \
        == V.NEEDS_HUMAN_REVIEW


# --- démarche expérimentale --------------------------------------------------------------------
PROTO = {"hypothese": "La lumière influence la croissance fictive.", "variables_testees": ["lumière"],
         "variables_controlees": ["température", "eau"], "temoin": True, "mesure": "taille en cm",
         "repetitions": 3}


def test_protocole_rigoureux():
    assert verifier_protocole(PROTO, variable_attendue="lumiere").verdict == V.VALID


@pytest.mark.parametrize("modif,raison", [
    ({"variables_testees": ["lumière", "eau"]}, "une_seule_variable_doit_varier"),
    ({"variables_testees": ["eau"], "variables_controlees": ["température"]}, "variable_testee_incorrecte"),
    ({"variables_controlees": ["lumière", "eau"]}, "variable_testee_aussi_controlee"),
    ({"variables_controlees": []}, "aucune_variable_controlee"),
    ({"temoin": False}, "temoin_absent"),
    ({"temoin": "oui"}, "temoin_absent"),
    ({"repetitions": 1}, "repetitions_insuffisantes"),
    ({"repetitions": True}, "repetitions_insuffisantes"),
    ({"hypothese": "  "}, "hypothese_absente"),
    ({"mesure": ""}, "mesure_absente"),
])
def test_protocole_defauts(modif, raison):
    r = verifier_protocole(dict(PROTO, **modif), variable_attendue="lumière")
    assert r.verdict == V.INVALID and raison in r.raisons, r


def test_protocole_incomplet():
    assert verifier_protocole({"hypothese": "x"}, variable_attendue="lumière").verdict == V.INVALID


@pytest.mark.parametrize("res,concl,verdict", [
    ({"ecart_significatif": True, "sens": "hausse", "repetitions": 3, "hypothese_predit": "hausse"}, "validee", V.VALID),
    ({"ecart_significatif": True, "sens": "hausse", "repetitions": 3, "hypothese_predit": "baisse"}, "invalidee", V.VALID),
    ({"ecart_significatif": True, "sens": "hausse", "repetitions": 3, "hypothese_predit": "baisse"}, "validee", V.INVALID),
    ({"ecart_significatif": False, "sens": None, "repetitions": 3, "hypothese_predit": "hausse"}, "validee", V.INVALID),
    ({"ecart_significatif": False, "sens": None, "repetitions": 3, "hypothese_predit": "hausse"}, "non_conclusive", V.VALID),
    ({"ecart_significatif": True, "sens": "hausse", "repetitions": 1, "hypothese_predit": "hausse"}, "validee", V.INVALID),
    ({"ecart_significatif": True, "sens": "hausse", "repetitions": 1, "hypothese_predit": "hausse"}, "non_conclusive", V.VALID),
    ({"ecart_significatif": True}, "validee", V.NEEDS_HUMAN_REVIEW),
])
def test_conclusion_experience(res, concl, verdict):
    assert verifier_conclusion_experience(res, {"hypothese": concl}).verdict == verdict


# --- corrélation / causalité -------------------------------------------------------------------
@pytest.mark.parametrize("etude,rep,verdict", [
    ("observationnelle", {"lien": "correlation"}, V.VALID),
    ("observationnelle", {"lien": "causalite"}, V.INVALID),
    ("observationnelle", {"lien": "correlation", "justification": "Le facteur A provoque la maladie B."},
     V.NEEDS_HUMAN_REVIEW),
    ("observationnelle", {"lien": "correlation", "justification": "A est corrélé à B ; A pourrait provoquer B."},
     V.VALID),
    ("observationnelle", {"lien": "correlation", "justification": "Rien ne montre que A provoque B."}, V.VALID),
    ("experimentale_controlee", {"lien": "causalite"}, V.VALID),
    ("experimentale_controlee", {"lien": "correlation"}, V.INVALID),
    ("sondage", {"lien": "correlation"}, V.NEEDS_HUMAN_REVIEW),
    ("observationnelle", {"lien": "peut-être"}, V.NEEDS_HUMAN_REVIEW),
    ("observationnelle", "correlation", V.NEEDS_HUMAN_REVIEW),
])
def test_correlation_causalite(etude, rep, verdict):
    assert verifier_lien(etude, rep).verdict == verdict


# --- documents ---------------------------------------------------------------------------------
INFOS = {"i1": "doc1", "i2": "doc1", "i3": "doc2", "i4": "doc3"}


@pytest.mark.parametrize("prel,verdict,raison", [
    ({"doc1": ["i1"], "doc2": ["i3"]}, V.VALID, None),
    ({"doc1": ["i1", "i2"], "doc2": ["i3"], "doc3": ["i4"]}, V.VALID, None),
    ({"doc1": ["i1", "i3"]}, V.INVALID, "information_mal_attribuee:i3"),
    ({"doc1": ["i1"]}, V.INVALID, "information_cle_manquante:i3"),
    ({"doc1": ["i1"], "doc2": ["i3", "i9"]}, V.NEEDS_HUMAN_REVIEW, None),
])
def test_exploitation_documents(prel, verdict, raison):
    r = verifier_exploitation_documents(prel, INFOS, ["i1", "i3"])
    assert r.verdict == verdict
    if raison:
        assert raison in r.raisons


def test_mise_en_relation_obligatoire():
    r = verifier_exploitation_documents({"doc1": ["i1", "i2"]}, INFOS, ["i1", "i2"])
    assert r.verdict == V.INVALID and "mise_en_relation_insuffisante" in r.raisons
    assert verifier_exploitation_documents({"doc1": ["i1", "i2"]}, INFOS, ["i1", "i2"], documents_min=1).verdict \
        == V.VALID
    assert verifier_exploitation_documents({}, INFOS, ["i9"]).verdict == V.NEEDS_HUMAN_REVIEW


# --- définitions (non purement lexicales) ------------------------------------------------------
ESSENTIELS = [["transformation", "conversion"], ["énergie lumineuse", "lumière"], ["matière organique"]]


@pytest.mark.parametrize("rep,verdict,raison", [
    ("La synthèse fictive est la conversion, grâce à la lumière, de matière minérale en matière organique.",
     V.VALID, None),
    ("C'est une transformation utilisant l'énergie lumineuse pour produire de la matière organique.", V.VALID, None),
    ("C'est une transformation utilisant la lumière.", V.INVALID, "element_manquant:matière organique"),
    ("C'est une transformation qui produit de la matière organique sans lumière.", V.NEEDS_HUMAN_REVIEW, None),
    ("La synthèse fictive est une synthèse fictive de matière organique par la lumière.", V.INVALID,
     "definition_circulaire"),
    ("C'est une respiration qui produit de la matière organique à la lumière.", V.INVALID, "confusion:respiration"),
    ("", V.INVALID, "reponse_vide"),
])
def test_definition(rep, verdict, raison):
    r = verifier_definition("synthèse fictive", rep, ESSENTIELS, confusions=["respiration"])
    assert r.verdict == verdict, r
    if raison:
        assert raison in r.raisons


def test_confusion_niee_n_est_pas_une_erreur():
    rep = "Ce n'est pas une respiration : c'est une transformation par la lumière produisant de la matière organique."
    assert verifier_definition("synthèse fictive", rep, ESSENTIELS, confusions=["respiration"]).verdict == V.VALID


def test_negation_detectee_par_proposition():
    assert occurrences("La mitose n'a pas lieu ici, mais la méiose oui.", "mitose") == (0, 1)
    assert occurrences("La mitose n'a pas lieu ici, mais la méiose oui.", "méiose") == (1, 0)
    assert occurrences("Sans ADN, pas de cellule.", "adn") == (0, 1)


def test_vocabulaire_terme_seulement_nie_part_en_revue():
    from app.curriculum.verifiers.svt import verifier_vocabulaire

    assert verifier_vocabulaire("Ce n'est pas la mitose.", ["mitose"]).verdict == V.NEEDS_HUMAN_REVIEW
    assert verifier_vocabulaire("Ce n'est pas la méiose, c'est la mitose.", ["mitose"]).verdict == V.VALID
    assert verifier_vocabulaire("Les mitoses se succèdent.", ["mitose"]).verdict == V.VALID


def test_dispatch_svt_definition():
    from app.curriculum.verifiers.dispatch import verifier

    p = {"terme_defini": "synthèse fictive", "elements_essentiels": ESSENTIELS, "confusions": ["respiration"]}
    modele = "La synthèse fictive est la transformation, par la lumière, de matière minérale en matière organique."
    assert verifier("svt_definition", modele, modele, dict(p)).verdict == V.VALID
    assert verifier("svt_definition", modele, "C'est une respiration.", dict(p)).verdict == V.INVALID
    assert verifier("svt_definition", modele, modele, {}).verdict == V.NEEDS_HUMAN_REVIEW
    assert verifier("svt_definition", modele, modele, dict(p, inconnu=1)).verdict == V.NEEDS_HUMAN_REVIEW
