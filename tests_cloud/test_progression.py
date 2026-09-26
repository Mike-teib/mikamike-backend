"""
Adaptation élève (lot 18) : niveau calculé sur l'historique, jamais sur une seule réponse,
aide et compréhension finale ratée (D14) jamais comptées comme réussite autonome.
"""

import random

import pytest

from app.curriculum.pedagogie.progression import (
    MIN_OBSERVATIONS,
    ORDRE,
    Niveau,
    Tentative,
    diagnostiquer,
)

JOUR = 86400.0


def T(ok, aide=False, jour=0, k=0, comp=True):
    return Tentative(ok, aide, 1_900_000_000 + jour * JOUR + k * 60, comp)


def test_jamais_de_diagnostic_sur_une_reponse():
    for h in ([T(False)], [T(True)], [T(False), T(False, k=1)]):
        d = diagnostiquer(h)
        assert d.niveau == Niveau.NON_EVALUEE and d.prochaine_action == "observer_encore"


def test_maitrise_exige_reussites_autonomes_espacees():
    meme_jour = [T(True, k=i) for i in range(4)]
    d = diagnostiquer(meme_jour)
    assert d.niveau == Niveau.EN_COURS and "R4_retest_espace_requis" in d.raisons
    espace = [T(True, jour=0), T(True, jour=0, k=1), T(True, jour=2)]
    assert diagnostiquer(espace).niveau == Niveau.MAITRISEE


def test_reussites_aidees_jamais_maitrise():
    h = [T(True, aide=True, jour=j) for j in range(6)]
    d = diagnostiquer(h)
    assert d.niveau == Niveau.EN_COURS and "R2_reussites_aidees_non_comptees_comme_autonomes" in d.raisons


def test_d14_comprehension_ratee_n_est_pas_une_reussite():
    h = [T(True, jour=j, comp=False) for j in range(4)]
    assert diagnostiquer(h).niveau == Niveau.NON_ACQUISE


def test_non_acquise_et_fragile():
    assert diagnostiquer([T(False, k=i) for i in range(3)]).niveau == Niveau.NON_ACQUISE
    assert diagnostiquer([T(True), T(False, k=1), T(False, k=2), T(False, k=3)]).niveau == Niveau.FRAGILE
    h = [T(True, jour=0), T(True, jour=1), T(True, jour=2, k=1), T(False, jour=3), T(False, jour=3, k=1)]
    d = diagnostiquer(h)
    assert d.niveau == Niveau.FRAGILE


def test_une_erreur_apres_maitrise_ne_fait_pas_tout_perdre():
    h = [T(True, jour=j) for j in range(5)]
    assert diagnostiquer(h).niveau == Niveau.MAITRISEE
    d = diagnostiquer(h + [T(False, jour=6)])
    assert d.niveau in (Niveau.MAITRISEE, Niveau.EN_COURS)


def test_ordre_des_tentatives_par_horodatage():
    h = [T(True, jour=0), T(True, jour=1), T(True, jour=2), T(False, jour=3), T(False, jour=3, k=1)]
    assert diagnostiquer(list(reversed(h))) == diagnostiquer(h)


@pytest.mark.parametrize("graine", range(40))
def test_propriete_variation_bornee_a_un_cran(graine):
    rnd = random.Random(graine)
    h = [T(rnd.random() < 0.6, aide=rnd.random() < 0.3, jour=i // 3, k=i, comp=rnd.random() < 0.9)
         for i in range(rnd.randint(MIN_OBSERVATIONS, 25))]
    avant = diagnostiquer(h).niveau
    for ok in (True, False):
        apres = diagnostiquer(h + [T(ok, jour=40, k=999)]).niveau
        if avant in ORDRE and apres in ORDRE:
            assert abs(ORDRE.index(apres) - ORDRE.index(avant)) <= 1, (avant, apres)


def test_historique_long_borne():
    h = [T(i % 2 == 0, jour=i, k=i) for i in range(5000)]
    d = diagnostiquer(h)
    assert d.observations == 60 and d.niveau in ORDRE
