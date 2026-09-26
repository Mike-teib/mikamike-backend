"""
Session 5 — garde de publication : aucun contenu n'atteint READY_FOR_PUBLICATION sans source
PROVEN, texte sain, chapitre prouvé, notion prouvée, structure valide et tests verts ; PUBLISHED
reste un état séparé (décision humaine liée à l'empreinte, jamais automatique).
"""

import dataclasses
import itertools

import pytest

from app.curriculum.publication import (
    EtatPublication as E,
    PublicationRefusee,
    RegistrePublication,
    catalogue_publie,
    evaluer,
)
from app.curriculum.structure import Anomalie
from tests_cloud.test_publication import EXO, QUIZ, _ref_modifiee, res_prod  # noqa: F401

# Chaque altération casse UNE condition ; la raison attendue est indiquée.
ALTERATIONS = {
    "SOURCE_NON_PROUVEE": lambda r: dataclasses.replace(r, documents={}),
    "NOTION_NON_PROUVEE": lambda r: dataclasses.replace(r, integrite=r.integrite._replace(generables=frozenset())),
    "TEXTE_NON_SAIN": lambda r: dataclasses.replace(r, exercices=[r.exercices[0].model_copy(
        update={"enonce": "Écris 7/10 sous la forme des"})]),
    "CHAPITRE_NON_PROUVE": lambda r: dataclasses.replace(r, rattachements={**r.rattachements,
                                                                           r.exercices[0].notion_id: "DECLARE"}),
    "STRUCTURE_INVALIDE": lambda r: dataclasses.replace(r, anomalies=[Anomalie("TEST", r.exercices[0].notion_id, "")]),
    "TESTS_ROUGES": lambda r: dataclasses.replace(r, exercices=[r.exercices[0].model_copy(
        update={"erreurs_frequentes": {"0,70": "zéro inutile"}})]),
    "PLAN_MANQUANT": lambda r: dataclasses.replace(r, plans={}),
}


def test_temoin_contenus_prets(res_prod):
    ev = evaluer(res_prod)
    assert ev[EXO].etat == E.READY_FOR_PUBLICATION and ev[QUIZ].etat == E.READY_FOR_PUBLICATION


def test_tests_rouges_erreur_frequente_en_fait_correcte(res_prod, tmp_path):
    r = ALTERATIONS["TESTS_ROUGES"](res_prod)
    ev = evaluer(r)[EXO]
    assert ev.etat == E.BLOQUE and ev.raisons == ("TESTS_ROUGES",)
    with pytest.raises(PublicationRefusee, match="TESTS_ROUGES"):
        RegistrePublication(tmp_path / "d").publier(r, EXO, "operateur.mike")


@pytest.mark.parametrize("modif,attendu", [
    ({"choix": ("3/7", "6/14", "1/7")}, "VALIDATION_ECHOUEE"),        # deux bonnes réponses
    ({"index_correct": 1}, "VALIDATION_ECHOUEE"),                     # la clé désigne un distracteur
    ({"niveau": "5e"}, "VALIDATION_ECHOUEE"),                          # niveau ≠ notion
])
def test_quiz_invalide_bloque_a_la_publication(res_prod, modif, attendu, tmp_path):
    """Avant la session 5 : un quiz altéré APRÈS l'import restait READY (validation non rejouée)."""
    r = dataclasses.replace(res_prod, quiz=[res_prod.quiz[0].model_copy(update=modif)])
    ev = evaluer(r)[QUIZ]
    assert ev.etat == E.BLOQUE and attendu in ev.raisons, ev
    with pytest.raises(PublicationRefusee):
        RegistrePublication(tmp_path / "d").publier(r, QUIZ, "operateur.mike")


@pytest.mark.parametrize("a,b", list(itertools.combinations(sorted(ALTERATIONS), 2)))
def test_combinaisons_toutes_bloquees_toutes_raisons_listees(res_prod, a, b):
    r = ALTERATIONS[b](ALTERATIONS[a](res_prod))
    ev = evaluer(r)[EXO]
    assert ev.etat == E.BLOQUE
    assert {a, b} <= set(ev.raisons), ev.raisons


def test_ready_n_est_jamais_published_sans_decision_humaine(res_prod, tmp_path):
    reg = RegistrePublication(tmp_path / "d")
    assert all(e.etat != E.PUBLISHED for e in evaluer(res_prod, reg.publies()).values())
    assert catalogue_publie(res_prod, reg).exercices == {}
    reg.publier(res_prod, EXO, "operateur.mike")
    ev = evaluer(res_prod, reg.publies())
    assert ev[EXO].etat == E.PUBLISHED and ev[QUIZ].etat == E.READY_FOR_PUBLICATION


@pytest.mark.parametrize("cle", sorted(ALTERATIONS))
def test_publie_puis_condition_perdue_retire_du_catalogue(res_prod, tmp_path, cle):
    reg = RegistrePublication(tmp_path / "d")
    reg.publier(res_prod, EXO, "operateur.mike")
    r = ALTERATIONS[cle](res_prod)
    assert evaluer(r, reg.publies())[EXO].etat == E.BLOQUE
    assert EXO not in catalogue_publie(r, reg).exercices


def test_texte_de_notion_non_sain_bloque(res_prod):
    r = dataclasses.replace(res_prod, referentiel=_ref_modifiee(
        res_prod, {"texte": "[FICTIF] Utiliser l'écriture fractionnaire des"}))
    assert "TEXTE_NON_SAIN" in evaluer(r)[EXO].raisons
