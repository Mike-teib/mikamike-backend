"""
LOT 15 — Banc de progression multi-jours (rapport : PROGRESSION_BENCHMARK.md).

Deux niveaux de preuve, sur les MÊMES scénarios datés (jours 1, 2, 7, 30) :
  1. moteur pur : `app.curriculum.pedagogie.progression.diagnostiquer` ;
  2. API réelle : `/api/v1/exercices/soumettre`, avec un historique DATÉ injecté en base
     (les tentatives déjà journalisées sont re-datées avant chaque soumission, cf. `_anciennes`
     dans test_progression_api_s5.py) — le niveau renvoyé doit être identique au moteur pur.

Propriétés : au plus un cran par réponse (R7), MAITRISEE ⇒ réussites autonomes sur ≥ 2 jours
(R4), l'aide n'est jamais plus favorable (R8), pas de diagnostic avant 3 réponses (R1),
stabilité sur alternances régulières (borne justifiée dans `test_stabilite_*`).
Constats (comportement ACTUEL documenté, pas une règle inventée) : aucune décroissance
temporelle après une longue absence ; oscillation MAITRISEE ↔ EN_COURS à 2 réussites sur 3.
Défaut : `xfail(strict=True)` en fin de fichier.
"""

import datetime as _dt
import itertools
import random

import pytest
from sqlalchemy import select

from app.api.v1.mikamike import moteur
from app.api.v1.mikamike.store import SessionLocal, TentativeExercice
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.pedagogie.progression import FENETRE, ORDRE, Niveau, Tentative, diagnostiquer

JOUR = 86400.0
T0 = 1_900_000_000  # 2030-03-17 17:46:40 UTC : loin de minuit, les minutes ajoutées restent le même jour
EXO, COMP = "exo-maths-algebre-1", "equations_1er_degre"
BONNE, FAUSSE = "3", "x = 999"

S, F, SA, FA = (True, False), (False, False), (True, True), (False, True)  # (correcte, avec_aide)
NE, NA, FR, EC, MA = "NON_EVALUEE", "NON_ACQUISE", "FRAGILE", "EN_COURS", "MAITRISEE"

# scénario -> (séquence [(jour, (correcte, aide))], niveaux attendus, libellés historiques attendus)
SCENARIOS = {
    "S1_autonome_regulier": (
        [(1, S), (1, S), (2, S), (2, S), (7, S), (30, S)],
        [NE, NE, MA, MA, MA, MA],
        ["EN_COURS", "EN_COURS", "MAITRISE", "MAITRISE", "MAITRISE", "MAITRISE"]),
    "S2_aide_reguliere": (
        [(1, SA), (1, SA), (2, SA), (2, SA), (7, SA), (30, SA)],
        [NE, NE, EC, EC, EC, EC],
        ["ACQUIS_ASSISTE"] * 6),
    "S3_echecs": (
        [(1, F), (1, F), (1, F), (2, F), (2, F), (7, F), (30, F)],
        [NE, NE, NA, NA, NA, NA, NA],
        ["INCONNU", "INCONNU"] + ["A_REVOIR"] * 5),
    "S4_alternance": (
        [(1, S), (1, F), (2, S), (2, F), (7, S), (7, F), (30, S), (30, F)],
        [NE, NE, EC, EC, EC, EC, EC, EC],
        ["EN_COURS"] * 8),
    "S5_absence_apres_maitrise": (
        [(1, S), (1, S), (1, S), (2, S), (2, S), (30, F), (30, F), (30, S), (30, S)],
        [NE, NE, EC, MA, MA, EC, FR, EC, EC],
        ["EN_COURS", "EN_COURS", "ACQUIS_AUTONOME", "MAITRISE", "MAITRISE", "EN_COURS", "FRAGILE",
         "EN_COURS", "EN_COURS"]),
    "S6_retour_apres_echecs": (
        [(1, F), (1, F), (1, F), (2, F), (7, S), (7, S), (30, S), (30, S), (30, S)],
        [NE, NE, NA, NA, FR, FR, EC, MA, MA],
        ["INCONNU", "INCONNU", "A_REVOIR", "A_REVOIR", "FRAGILE", "FRAGILE", "EN_COURS", "MAITRISE",
         "MAITRISE"]),
    "S7_aide_puis_autonomie": (
        [(1, SA), (1, SA), (1, SA), (2, S), (2, S), (7, S), (30, S)],
        [NE, NE, EC, EC, EC, MA, MA],
        ["ACQUIS_ASSISTE", "ACQUIS_ASSISTE", "ACQUIS_ASSISTE", "EN_COURS", "EN_COURS", "MAITRISE",
         "MAITRISE"]),
    "S8_meme_jour": (
        [(1, S)] * 8,
        [NE, NE] + [EC] * 6,
        ["EN_COURS", "EN_COURS"] + ["ACQUIS_AUTONOME"] * 6),
    "S9_echecs_aides_puis_reussites_aidees": (
        [(1, FA), (1, FA), (1, FA), (2, FA), (7, SA), (30, SA)],
        [NE, NE, NA, NA, FR, FR],
        ["INCONNU", "INCONNU", "A_REVOIR", "A_REVOIR", "FRAGILE", "FRAGILE"]),
}


def _rang(n) -> int:
    n = Niveau(n)
    return -1 if n == Niveau.NON_EVALUEE else ORDRE.index(n)


def _histoire(seq, t0=T0):
    return [Tentative(ok, aide, t0 + d * JOUR + i * 60) for i, (d, (ok, aide)) in enumerate(seq)]


def _jour_par_jour(seq):
    """Niveau et libellé historique après CHAQUE réponse (moteur pur)."""
    h, niveaux, libelles = [], [], []
    for t in _histoire(seq):
        h.append(t)
        d = diagnostiquer(h)
        niveaux.append(d.niveau.value)
        libelles.append(moteur.etat_compatible(d, h).value)
    return niveaux, libelles


def _jours_autonomes_reussis(h):
    return {_dt.datetime.fromtimestamp(t.horodatage, _dt.timezone.utc).date()
            for t in h if t.correcte and not t.avec_aide and t.comprehension_finale}


# =========================================================================== #
# 1. Moteur pur : scénarios datés
# =========================================================================== #
@pytest.mark.parametrize("nom", sorted(SCENARIOS))
def test_scenario_moteur(nom):
    seq, niveaux, libelles = SCENARIOS[nom]
    assert _jour_par_jour(seq) == (niveaux, libelles)
    h = _histoire(seq)
    for k in range(1, len(h) + 1):
        n = diagnostiquer(h[:k]).niveau
        if k < 3:
            assert n == Niveau.NON_EVALUEE                      # R1
        if n == Niveau.MAITRISEE:
            assert len(_jours_autonomes_reussis(h[:k])) >= 2     # R4


def _aleatoires(nb, graine0=1000):
    for g in range(graine0, graine0 + nb):
        rnd = random.Random(g)
        p_ok = rnd.choice((0.2, 0.5, 0.67, 0.8, 0.95))
        p_aide = rnd.choice((0.0, 0.2, 0.5))
        jour, seq = 1, []
        for _ in range(rnd.randint(3, 18)):
            if rnd.random() < 0.3:
                jour = rnd.choice((jour, jour + 1, jour + 6, jour + 29))
            seq.append((jour, (rnd.random() < p_ok, rnd.random() < p_aide)))
        yield seq


def test_propriete_un_cran_par_reponse_et_maitrise_espacee():
    """300 historiques multi-jours (graines fixes) : ≤ 1 cran entre deux réponses successives,
    MAITRISEE seulement avec des réussites autonomes sur ≥ 2 jours, rien avant 3 réponses."""
    vus = set()
    for seq in _aleatoires(300):
        h, prec = _histoire(seq), None
        for k in range(1, len(h) + 1):
            n = diagnostiquer(h[:k]).niveau
            vus.add(n)
            if k < 3:
                assert n == Niveau.NON_EVALUEE
            if n == Niveau.MAITRISEE:
                assert len(_jours_autonomes_reussis(h[:k])) >= 2, seq[:k]
            if prec is not None and prec != Niveau.NON_EVALUEE:
                assert abs(_rang(n) - _rang(prec)) <= 1, (seq[:k], prec, n)
            prec = n
    assert vus == set(Niveau)  # tous les niveaux sont atteints par le banc


def test_propriete_aide_jamais_plus_favorable_multi_jours():
    """Marquer UNE tentative « avec aide » (n'importe laquelle) ne fait jamais monter le niveau
    final ; tout marquer « avec aide » ne donne jamais MAITRISEE."""
    for seq in _aleatoires(200, graine0=5000):
        h = _histoire(seq)
        base = _rang(diagnostiquer(h).niveau)
        for i, t in enumerate(h):
            if not t.avec_aide:
                h2 = h[:i] + [t._replace(avec_aide=True)] + h[i + 1:]
                assert _rang(diagnostiquer(h2).niveau) <= base, (seq, i)
        tout_aide = [t._replace(avec_aide=True) for t in h]
        assert diagnostiquer(tout_aide).niveau != Niveau.MAITRISEE


# =========================================================================== #
# 2. Stabilité (anti-oscillation)
# =========================================================================== #
def _niveaux_periodiques(motif, par_jour, n=24):
    h, out = [], []
    for i in range(n):
        ok, aide = motif[i % len(motif)]
        h.append(Tentative(ok, aide, T0 + (i // par_jour) * JOUR + i * 60))
        out.append(diagnostiquer(h).niveau)
    return out


def _changements(niveaux, depuis):
    return [i for i in range(max(depuis, 1), len(niveaux)) if niveaux[i] != niveaux[i - 1]]


@pytest.mark.parametrize("par_jour", [1, 2, 3, 100])
@pytest.mark.parametrize("motif", [(S, F), (F, S)])
def test_stabilite_alternance_reguliere(motif, par_jour):
    """Borne : AUCUN changement de niveau une fois la fenêtre remplie (FENETRE = 6 réponses).
    Justification : en alternance stricte, la fenêtre de 6 contient toujours 3 réussites (≥ la
    moitié : pas R6), jamais deux échecs autonomes consécutifs (pas R6), et 2 réussites sur les
    4 dernières autonomes (pas R4) : EN_COURS est un point fixe. Pendant le remplissage de la
    fenêtre, au plus 3 changements (F,S,F,S… démarre à FRAGILE)."""
    niv = _niveaux_periodiques(motif, par_jour)
    assert _changements(niv, FENETRE) == []
    assert niv[-1] == Niveau.EN_COURS
    assert len(_changements(niv, 3)) <= 3


def test_stabilite_motifs_periodiques_courts():
    """Tous les motifs périodiques de période 2 à 4 (réussite/échec × aide/sans aide), à 1, 3 ou
    100 réponses par jour : après la fenêtre, jamais 3 réponses consécutives qui changent chacune
    le niveau (un niveau qui bascule à CHAQUE réponse serait illisible pour l'élève et le
    parent). Borne 2 atteinte (constat ci-dessous : motif S,S,F)."""
    opts = (S, F, SA, FA)
    pire = 0
    for p in (2, 3, 4):
        for motif in itertools.product(opts, repeat=p):
            for par_jour in (1, 3, 100):
                niv = _niveaux_periodiques(motif, par_jour)
                serie = 0
                for i in range(FENETRE + 1, len(niv)):
                    serie = serie + 1 if niv[i] != niv[i - 1] else 0
                    assert serie <= 2, (motif, par_jour, [n.value for n in niv])
                    pire = max(pire, serie)
    assert pire == 2


def test_constat_oscillation_deux_reussites_sur_trois():
    """CONSTAT (comportement actuel) : un élève à 2 réussites autonomes sur 3, sur plusieurs
    jours, est MAITRISEE 2 réponses sur 3 ; chaque échec retire la maîtrise, la réussite
    suivante la rend (2 changements par période de 3, indéfiniment). Voir recommandation R-2."""
    niv = _niveaux_periodiques((S, S, F), par_jour=3)
    fin = [n.value for n in niv[FENETRE:FENETRE + 6]]
    assert fin == [MA, MA, EC, MA, MA, EC]
    assert len(_changements(niv, FENETRE)) == 12


# =========================================================================== #
# 3. Longue absence, espacement (constats)
# =========================================================================== #
def test_constat_aucune_decroissance_temporelle():
    """CONSTAT : le moteur n'a PAS de décroissance temporelle. Le niveau ne dépend que de
    l'ordre des réponses et des JOURS distincts : une absence de 1, 30 ou 365 jours avant le
    retour donne exactement les mêmes niveaux (et le niveau stocké reste MAITRISEE pendant
    toute l'absence, puisqu'il n'est recalculé qu'à la réponse suivante)."""
    avant = [(1, S), (1, S), (1, S), (2, S), (2, S)]
    assert diagnostiquer(_histoire(avant)).niveau == Niveau.MAITRISEE
    for retour in ([F], [F, F], [S], [F, F, S, S]):
        resultats = set()
        for absence in (1, 30, 365):
            seq = avant + [(2 + absence, r) for r in retour]
            resultats.add(tuple(_jour_par_jour(seq)[0]))
        assert len(resultats) == 1, retour
    # Retour après 28 jours : le premier échec ne retire qu'un cran (R7), pas de retest imposé.
    niv = _jour_par_jour(avant + [(30, F)])[0]
    assert niv[-2:] == [MA, EC]


def test_constat_espacement_compte_une_reussite_ancienne():
    """CONSTAT : l'espacement R4 compte toute réussite autonome de l'historique borné (60
    tentatives) : une réussite unique il y a 29 jours + 3 réussites aujourd'hui = MAITRISEE,
    même après des échecs entre-temps."""
    seq = [(1, S), (5, F), (5, F), (30, S), (30, S), (30, S)]
    assert _jour_par_jour(seq)[0][-1] == MA


# =========================================================================== #
# 4. API réelle /exercices/soumettre avec historique daté
# =========================================================================== #
def _redater(eleve, jours, maintenant):
    """Re-date les tentatives déjà journalisées : la k-ième reçoit maintenant − (jour courant −
    jour_k) jours (− quelques ms pour garder l'ordre), comme si elles dataient de leur jour."""
    db = SessionLocal()
    try:
        lignes = db.execute(select(TentativeExercice).where(
            TentativeExercice.eleve_hmac == hmac_eleve(eleve), TentativeExercice.competence == COMP)
            .order_by(TentativeExercice.id)).scalars().all()
        courant, n = jours[len(lignes)], len(lignes)
        for k, ligne in enumerate(lignes):
            ligne.ts = maintenant - _dt.timedelta(days=courant - jours[k], milliseconds=n - k)
        db.commit()
    finally:
        db.close()


def _jouer_api(client, eleve, seq):
    jours = [d for d, _ in seq]
    niveaux, libelles = [], []
    for d, (ok, aide) in seq:
        _redater(eleve, jours, _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None))
        r = client.post("/api/v1/exercices/soumettre", json={
            "exercice_id": EXO, "student_pseudo_id": eleve, "reponse": BONNE if ok else FAUSSE,
            "avec_aide": aide})
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["est_correct"] is ok
        niveaux.append(out["progression"]["niveau"])
        libelles.append(out["etat_maitrise"])
    return niveaux, libelles


def test_scenarios_via_api_identiques_au_moteur(client):
    """Tous les scénarios datés rejoués via l'API : niveaux ET libellés historiques identiques
    au moteur pur, jour par jour (aucun écart d'une réponse, aucun double comptage)."""
    obtenus = {}
    for nom, (seq, niveaux, libelles) in SCENARIOS.items():
        obtenus[nom] = _jouer_api(client, f"eleve-jours-{nom[:2]}", seq)
        assert obtenus[nom] == (niveaux, libelles), nom
    # Aide jamais plus favorable, réponse par réponse (même calendrier, aide vs autonomie).
    for aide, auto in (("S2_aide_reguliere", "S1_autonome_regulier"),):
        for a, b in zip(obtenus[aide][0], obtenus[auto][0]):
            assert _rang(a) <= _rang(b)
    solides = {"ACQUIS_AUTONOME", "MAITRISE"}
    assert not solides & set(obtenus["S2_aide_reguliere"][1])
    assert not solides & set(obtenus["S9_echecs_aides_puis_reussites_aidees"][1])
    assert "MAITRISE" not in obtenus["S8_meme_jour"][1]


def test_retour_apres_longue_absence_via_api(client):
    """Via l'API : maîtrise acquise J1–J2, absence de 28 jours ; le retour (J30) part du niveau
    MAITRISEE (aucune décroissance) et un échec ne retire qu'un cran."""
    seq = [(1, S), (1, S), (1, S), (2, S), (2, S), (30, F)]
    niveaux, libelles = _jouer_api(client, "eleve-jours-absence", seq)
    assert niveaux[-2:] == [MA, EC] and libelles[-2:] == ["MAITRISE", "EN_COURS"]


# =========================================================================== #
# Défaut trouvé (xfail strict : deviendra rouge une fois corrigé)
# =========================================================================== #
@pytest.mark.xfail(strict=True, reason=(
    "PROG-01 : les « jours distincts » de R4 sont des dates UTC. Trois réussites en 3 minutes "
    "de part et d'autre de minuit UTC (20 h aux Antilles, 1 h/2 h à Paris) donnent MAITRISEE : "
    "le « retest espacé » n'est pas garanti."))
def test_defaut_maitrise_en_trois_minutes_autour_de_minuit_utc():
    minuit = _dt.datetime(2030, 3, 18, tzinfo=_dt.timezone.utc).timestamp()
    h = [Tentative(True, False, minuit - 120), Tentative(True, False, minuit - 60),
         Tentative(True, False, minuit + 60)]
    assert diagnostiquer(h).niveau != Niveau.MAITRISEE
