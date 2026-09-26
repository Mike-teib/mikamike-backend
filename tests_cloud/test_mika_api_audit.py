"""
Audit du contrat réel `mika-tutorat/1` (session 3) : idempotence, propriété, concurrence réelle
(threads), rejeu, jeton expiré, mauvaise notion, plan invalide, non-divulgation, aide monotone,
prérequis, état corrompu, double soumission, bornes. Contenu FICTIF uniquement.
"""

import datetime as _dt
import json
import threading

import pytest

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal
from app.api.v1.tutorat import contenu, service
from app.api.v1.tutorat.store import TutoratRequete, TutoratSession
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.pedagogie.tuteur import PlanGuidage, TuteurMika
from tests_cloud.test_mika_api import A, B, EXO, PLAN, PREREQ, REP, URL, _exercice, _op, _start, api  # noqa: F401

CLES_ETAT = {"tentatives", "indices_donnes", "questions_posees", "methodes_donnees", "niveau_aide", "avec_aide",
             "resolu", "termine", "attend_comprehension", "comprehension_verifiee", "niveau_estime",
             "prerequis_manquant", "messages"}


def _servir(ex, plan):
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [ex], {ex.id: plan},
                                                       autoriser_fictif=True))


# --------------------------------------------------------------------------- #
# Forme exacte de la réponse (aucun champ interne)
# --------------------------------------------------------------------------- #
def test_contrat_champs_exacts(api):
    out = _start(api).json()
    assert set(out) == {"contract_version", "tutorat_id", "version", "exercice_id", "derniere_action", "etat",
                        "reponse", "rejeu"}
    assert set(out["etat"]) == CLES_ETAT
    assert set(out["reponse"]) == {"action", "message", "difficulte_proposee", "exercice_id", "notion_cible"}
    g = api.get(f"{URL}/{out['tutorat_id']}", params={"student_id": A}).json()
    assert set(g) == {"contract_version", "tutorat_id", "version", "exercice_id", "derniere_action", "etat"}


# --------------------------------------------------------------------------- #
# Non-divulgation : ni la réponse, ni la clé de compréhension, ni les aides FUTURES
# --------------------------------------------------------------------------- #
def test_aides_futures_jamais_divulguees(api):
    ex = _exercice()
    futures = list(PLAN.questions_intermediaires) + list(ex.indices) + list(PLAN.methodes_alternatives)
    t = _start(api).json()
    donnees = 0
    for i in range(6):
        brut = json.dumps(t, ensure_ascii=False)
        assert PLAN.reponse_comprehension not in brut and "reponse_attendue" not in brut
        if t["reponse"]["action"] != "CORRECTION_COMMENTEE":
            assert PLAN.correction_commentee not in brut
            for aide in futures[donnees:]:
                assert aide not in brut, (i, aide)
        t = _op(api, "help", t, f"h{i}").json()
        donnees += 1
    assert t["reponse"]["action"] == "CORRECTION_COMMENTEE"


def test_aide_monotone_et_compteurs_croissants(api):
    t = _start(api).json()
    prec = t["etat"]
    for i, (op, kw) in enumerate([("answer", {"reponse": "5"}), ("help", {}), ("answer", {"reponse": ""}),
                                  ("answer", {"reponse": "7,10"}), ("help", {}), ("answer", {"reponse": ""})]):
        r = _op(api, op, t, f"m{i}", **kw)
        if r.status_code == 409:
            break
        t = r.json()
        e = t["etat"]
        for k in ("niveau_aide", "indices_donnes", "questions_posees", "methodes_donnees", "tentatives"):
            assert e[k] >= prec[k], k
        assert e["avec_aide"] >= prec["avec_aide"]
        prec = e


# --------------------------------------------------------------------------- #
# Idempotence / rejeu
# --------------------------------------------------------------------------- #
def test_rejeu_d_une_ancienne_requete_apres_d_autres_transitions(api):
    t = _start(api).json()
    r1 = _op(api, "answer", t, "a1", reponse="5").json()
    t2 = _op(api, "help", r1, "h1").json()
    rejeu = _op(api, "answer", t, "a1", reponse="5").json()  # renvoyée tardivement (réseau)
    assert rejeu == {**r1, "rejeu": True}
    assert api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A}).json()["version"] == t2["version"]


def test_requete_id_reutilise_pour_une_autre_action(api):
    t = _start(api).json()
    _op(api, "answer", t, "x1", reponse="5")
    r = _op(api, "help", {**t, "version": 2}, "x1")
    assert r.status_code == 409 and r.json()["detail"] == "requete_id_reutilise_avec_un_autre_contenu"


def test_rejeu_du_start_apres_fin_du_tutorat(api):
    t = _start(api).json()
    _op(api, "answer", t, "a1", reponse=REP)
    r = _start(api)
    assert r.status_code == 200 and r.json()["rejeu"] and r.json()["version"] == 1


def test_double_soumission_sequentielle(api):
    t = _start(api).json()
    a = _op(api, "help", t, "dbl")
    b = _op(api, "help", t, "dbl")
    assert (a.status_code, b.status_code) == (200, 200) and b.json()["rejeu"] and not a.json()["rejeu"]
    db = SessionLocal()
    try:
        assert db.query(TutoratRequete).filter_by(requete_id="dbl").count() == 1
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Concurrence réelle (threads, sessions SQL distinctes)
# --------------------------------------------------------------------------- #
def _en_parallele(n, fn):
    barriere, res = threading.Barrier(n), [None] * n

    def run(i):
        barriere.wait()
        try:
            res[i] = ("ok", fn(i))
        except Exception as exc:  # HTTPException attendue
            res[i] = ("err", getattr(exc, "status_code", None), getattr(exc, "detail", str(exc)))

    ths = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for th in ths:
        th.start()
    for th in ths:
        th.join(30)
    return res


def test_concurrence_requetes_differentes_une_seule_transition(api):
    t = _start(api).json()

    def help_(i):
        db = SessionLocal()
        try:
            return service.transition(db, hmac_eleve(A), t["tutorat_id"], f"c{i}", 1, "help", {},
                                      lambda tu, e: tu.demander_aide(e))
        finally:
            db.close()

    res = _en_parallele(6, help_)
    ok = [r for r in res if r[0] == "ok"]
    ko = [r for r in res if r[0] == "err"]
    assert len(ok) == 1 and all(r[1] == 409 for r in ko), res
    g = api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A}).json()
    assert g["version"] == 2 and g["etat"]["questions_posees"] == 1  # une seule aide consommée


def test_concurrence_meme_start_un_seul_tutorat(api):
    def start(_i):
        db = SessionLocal()
        try:
            return service.demarrer(db, hmac_eleve(A), EXO, "start-concurrent")
        finally:
            db.close()

    res = _en_parallele(6, start)
    assert all(r[0] == "ok" for r in res), res
    codes = sorted(r[1][0] for r in res)
    assert codes.count(201) == 1 and set(codes) <= {200, 201}
    assert len({r[1][1]["tutorat_id"] for r in res}) == 1
    db = SessionLocal()
    try:
        assert db.query(TutoratSession).count() == 1
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Propriété, jetons
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op,kw", [("answer", {"reponse": REP}), ("help", {}), ("comprehension", {"reponse": "0,9"})])
def test_autre_eleve_404_sur_toutes_les_operations(api, op, kw):
    t = _start(api, A).json()
    r = _op(api, op, t, "intrus", eleve=B, **kw)
    assert r.status_code == 404 and r.json()["detail"] == "tutorat_inconnu"
    # Aucun effet : A n'a pas changé de version.
    assert api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A}).json()["version"] == 1


def test_jeton_expire_ferme_le_tutorat(api, monkeypatch):
    from app.core import auth
    from paiement_comptes import liens
    from paiement_comptes.database import SessionLocal as BillingSession
    from paiement_comptes.models_billing import Compte

    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    bdb = BillingSession()
    c = Compte(email="p-exp@example.com", mot_de_passe_hash="x", role="parent")
    bdb.add(c)
    bdb.commit()
    liens.lier(bdb, c.id, hmac_eleve(A), "parent")
    cid = c.id
    bdb.close()
    passe = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=3)
    vieux, _ = auth.emettre_jeton_eleve(A, compte_id=cid, maintenant=passe)
    r = api.post(f"{URL}/start", json={"student_pseudo_id": A, "requete_id": "e", "exercice_id": EXO},
                 headers={"Authorization": f"Bearer {vieux}"})
    assert r.status_code == 401 and r.json()["detail"] == "jeton_expire"
    frais, _ = auth.emettre_jeton_eleve(A, compte_id=cid)
    r = api.post(f"{URL}/start", json={"student_pseudo_id": B, "requete_id": "e", "exercice_id": EXO},
                 headers={"Authorization": f"Bearer {frais}"})
    assert r.status_code == 403  # jeton de A, corps au nom de B


# --------------------------------------------------------------------------- #
# Contenu : mauvaise notion, plan invalide (jamais servi, 404 sans raison interne)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("ex_kw,plan_kw", [
    ({"notion_id": "notion:fictif:inexistante"}, {}),                                # notion inconnue
    ({}, {"questions_intermediaires": ("La réponse est 0,7.",)}),                    # plan qui divulgue
    ({"indices": ()}, {"questions_intermediaires": (), "methodes_alternatives": ()}),  # aucune aide
    ({}, {"questions_intermediaires": ("Même aide.", "Même aide.")}),                # aides répétées
    ({}, {"question_comprehension": "Et 9/10 ? (c'est 0,9)"}),                      # question qui donne sa clé
    ({}, {"reponse_comprehension": ""}),                                             # compréhension non vérifiable
])
def test_contenu_invalide_jamais_servi(client, ex_kw, plan_kw):
    try:
        _servir(_exercice(**ex_kw), PLAN.model_copy(update=plan_kw))
        r = _start(client)
        assert r.status_code == 404 and r.json()["detail"] == "exercice_indisponible"
    finally:
        contenu.definir_catalogue(None)


def test_plan_invalide_refuse_par_le_moteur():
    with pytest.raises(ValueError, match="plan_de_guidage_invalide"):
        TuteurMika(_exercice(), PLAN.model_copy(update={"methodes_alternatives": ("Réponse : 0,7",)}))


# --------------------------------------------------------------------------- #
# Prérequis
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("etat,action", [("FRAGILE", "REMEDIER_PREREQUIS"), ("EN_COURS", "REMEDIER_PREREQUIS"),
                                         ("ACQUIS_ASSISTE", "REMEDIER_PREREQUIS"), ("MAITRISE", "PRESENTER_EXERCICE"),
                                         ("ACQUIS_AUTONOME", "PRESENTER_EXERCICE")])
def test_prerequis_selon_etat(api, etat, action):
    db = SessionLocal()
    try:
        crud.upsert_etat(db, hmac_eleve("eleve-pre"), PREREQ, etat)
    finally:
        db.close()
    out = _start(api, eleve="eleve-pre").json()
    assert out["reponse"]["action"] == action
    assert out["etat"]["termine"] is (action == "REMEDIER_PREREQUIS")


# --------------------------------------------------------------------------- #
# État corrompu (JSON illisible, clé inconnue) et fin de tutorat
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("brut", ["{pas du json", json.dumps({"exercice_id": EXO, "inconnue": 1}), "[]",
                                  json.dumps({"tentatives": 1})])
def test_etat_illisible_erreur_controlee(api, brut):
    from fastapi.testclient import TestClient

    from main import app

    t = _start(api).json()
    db = SessionLocal()
    db.get(TutoratSession, t["tutorat_id"]).etat_json = brut
    db.commit()
    db.close()
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A})
    assert r.status_code == 500 and r.json() == {"detail": "etat_tutorat_illisible"}


@pytest.mark.parametrize("op,kw", [("answer", {"reponse": REP}), ("help", {}), ("comprehension", {"reponse": "x"})])
def test_operations_refusees_apres_la_fin(api, op, kw):
    t = _start(api).json()
    fin = _op(api, "answer", t, "fin", reponse=REP).json()
    assert fin["etat"]["termine"]
    r = _op(api, op, fin, "apres", **kw)
    assert r.status_code == 409 and r.json()["detail"] == "tutorat_termine"


# --------------------------------------------------------------------------- #
# Bornes de validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("modif", [{"version": 0}, {"version": 10_001}, {"tutorat_id": "Z" * 32},
                                   {"tutorat_id": "a" * 31}, {"reponse": "x" * 501}, {"requete_id": ""}])
def test_bornes(api, modif):
    t = _start(api).json()
    corps = {"student_pseudo_id": A, "requete_id": "b", "tutorat_id": t["tutorat_id"], "version": 1,
             "reponse": "5", **modif}
    assert api.post(f"{URL}/answer", json=corps).status_code == 422


def test_plan_guidage_strict():
    with pytest.raises(Exception):
        PlanGuidage(correction_commentee="x", champ_inconnu=1)
