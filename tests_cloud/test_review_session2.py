"""
Revue contradictoire de la PR #4 (session cloud 3) — un test par finding (CLOUD_REVIEW_SESSION2.md).

Chaque test a été rejoué sur le head de la PR #4 (db03ff4) : il y ÉCHOUE (sauf témoins
positifs signalés). Acteurs et contenus FICTIFS, secrets de test, bases SQLite jetables.
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.v1.mikamike.store import SessionLocal, TentativeExercice
from app.api.v1.rgpd import router as rgpd
from app.api.v1.tutorat import service
from app.api.v1.tutorat.store import TutoratSession
from app.core.pseudonymisation import hmac_eleve
from paiement_comptes import crud_billing, liens
from paiement_comptes.database import SessionLocal as BillingSession
from paiement_comptes.router_comptes import creer_token
from tests_cloud.test_auth import enforce, monde  # noqa: F401  (fixtures)
from tests_cloud.test_mika_api import A, EXO, _op, _start, api  # noqa: F401  (fixture)

RACINE = Path(__file__).resolve().parents[1]
MDP = "motdepasse-de-test-1"


@pytest.fixture()
def bcrypt_rapide(monkeypatch):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    getattr(crud_billing, "_LEURRE", []).clear()
    yield
    getattr(crud_billing, "_LEURRE", []).clear()


@pytest.fixture()
def parent_lie(client, monkeypatch, bcrypt_rapide):
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    db = BillingSession()
    p = crud_billing.creer_compte(db, email="parent-s3@example.com", mot_de_passe=MDP, role="parent")
    liens.lier(db, p.id, hmac_eleve("eleve-s3"), "parent")
    tok, pid = creer_token(p), p.id
    db.close()
    r = client.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": "eleve-s3"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    return client, tok, r.json()["token"], pid


def _schedule(client, jeton):
    return client.post("/api/v1/memory/schedule", headers={"Authorization": f"Bearer {jeton}"},
                       json={"user_id": "eleve-s3", "notion_id": "n1", "mastery_event": "SUCCESS"})


# --------------------------------------------------------------------------- #
# S3-01 (P1) — le jeton élève survivait à l'effacement RGPD / au retrait du lien / à la
# désactivation du compte émetteur
# --------------------------------------------------------------------------- #
def test_s3_01_temoin_jeton_eleve_valide(parent_lie):
    client, _, je, _ = parent_lie
    assert _schedule(client, je).status_code == 200


def test_s3_01_jeton_eleve_refuse_apres_effacement_rgpd(parent_lie):
    client, tok, je, _ = parent_lie
    assert _schedule(client, je).status_code == 200
    assert client.delete("/api/v1/rgpd/effacer/eleve-s3", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    r = _schedule(client, je)
    assert r.status_code == 401 and r.json()["detail"] == "jeton_revoque"
    # Rien n'a été recréé pour l'élève effacé.
    db = SessionLocal()
    try:
        for modele in rgpd.TABLES_ELEVE:
            assert db.query(modele).filter(modele.eleve_hmac == hmac_eleve("eleve-s3")).count() == 0
    finally:
        db.close()


def test_s3_01_jeton_eleve_refuse_si_compte_desactive(parent_lie):
    client, _, je, pid = parent_lie
    db = BillingSession()
    crud_billing.get_compte(db, pid).actif = False
    db.commit()
    db.close()
    assert _schedule(client, je).status_code == 401
    assert client.get("/api/v1/rgpd/export/eleve-s3", headers={"Authorization": f"Bearer {je}"}).status_code == 401


def test_s3_01_jeton_eleve_sans_cid_refuse(parent_lie):
    import jwt as pyjwt

    from app.core import auth

    client, _, je, _ = parent_lie
    claims = pyjwt.decode(je, options={"verify_signature": False})
    del claims["cid"]
    forge = pyjwt.encode(claims, auth._cle_eleve(), algorithm="HS256")
    assert _schedule(client, forge).status_code == 401


def test_s3_01_stream_verifie_aussi_le_lien(parent_lie):
    client, tok, je, _ = parent_lie
    client.delete("/api/v1/rgpd/effacer/eleve-s3", headers={"Authorization": f"Bearer {tok}"})
    assert client.get("/api/v1/session/stream?session_id=s1",
                      headers={"Authorization": f"Bearer {je}"}).status_code == 401


# --------------------------------------------------------------------------- #
# S3-02 / S3-03 (P1) — migrations : URL avec `%`, migration interrompue non reprenable
# --------------------------------------------------------------------------- #
def _sous_processus(tmp_path, code, mika_url):
    import os

    env = {**os.environ, "MIKA_DB_URL": mika_url, "BILLING_DB_URL": f"sqlite:///{tmp_path / 'b.db'}"}
    r = subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=RACINE, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_s3_02_url_avec_pourcent(tmp_path):
    d = tmp_path / "a%20b"
    d.mkdir()
    out = _sous_processus(tmp_path, """
        import json
        from app.db import migrations as m
        m.upgrade("mika")
        print(json.dumps({"courante": m.courante("mika"), "head": m.head("mika")}))
    """, f"sqlite:///{d / 'm.db'}")
    assert out["courante"] == out["head"]


def test_s3_03_migration_interrompue_atomique_et_reprenable(tmp_path):
    out = _sous_processus(tmp_path, """
        import json
        from sqlalchemy import inspect
        from alembic.operations import Operations
        from app.db import migrations as m
        from app.db.registre import engines
        m.upgrade("mika", "m0002_index_tentatives")
        orig = Operations.create_table
        def coupure(self, nom, *a, **k):
            if nom == "mika_tutorat_requetes":
                raise RuntimeError("coupure simulee")
            return orig(self, nom, *a, **k)
        Operations.create_table = coupure
        try:
            m.upgrade("mika")
        except RuntimeError:
            pass
        Operations.create_table = orig
        apres_coupure = sorted(inspect(engines()["mika"]).get_table_names())
        version_coupure = m.courante("mika")
        m.upgrade("mika")
        print(json.dumps({"tables": apres_coupure, "version": version_coupure,
                          "reprise": m.courante("mika"), "head": m.head("mika")}))
    """, f"sqlite:///{tmp_path / 'm.db'}")
    assert out["version"] == "m0002_index_tentatives"
    assert "mika_tutorat_sessions" not in out["tables"]  # rien de la révision coupée ne subsiste
    assert out["reprise"] == out["head"]


# --------------------------------------------------------------------------- #
# S3-04 (P2) — double soumission concurrente : 409 au lieu du rejeu
# --------------------------------------------------------------------------- #
def test_s3_04_double_soumission_concurrente_rejouee(api, monkeypatch):
    t = _start(api).json()
    orig = service.transition
    premiere = {}

    def course(db, eleve_hmac, tutorat_id, requete_id, version, operation, corps, appliquer):
        def appliquer_en_course(tu, e):
            if not premiere:  # la même requête (double clic) aboutit pendant celle-ci
                premiere["r"] = orig(SessionLocal(), eleve_hmac, tutorat_id, requete_id, version,
                                     operation, corps, appliquer)
            return appliquer(tu, e)
        return orig(db, eleve_hmac, tutorat_id, requete_id, version, operation, corps, appliquer_en_course)

    monkeypatch.setattr(service, "transition", course)
    r = _op(api, "help", t, "r-double")
    assert r.status_code == 200, r.text
    assert r.json()["rejeu"] is True and r.json()["version"] == premiere["r"]["version"] == 2


# --------------------------------------------------------------------------- #
# S3-05 (P2) — état persisté corrompu : servi tel quel (GET) / 500 non maîtrisée
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("champ,valeur", [("tentatives", "x"), ("messages", "abc"), ("avec_aide", 1),
                                          ("tentatives", -1), ("prerequis_manquant", 3)])
def test_s3_05_etat_corrompu_refuse_proprement(api, champ, valeur):
    t = _start(api).json()
    db = SessionLocal()
    s = db.get(TutoratSession, t["tutorat_id"])
    d = json.loads(s.etat_json)
    d[champ] = valeur
    s.etat_json = json.dumps(d)
    db.commit()
    db.close()
    from main import app

    c = TestClient(app, raise_server_exceptions=False)
    r = c.get(f"/api/v1/mika/session/{t['tutorat_id']}", params={"student_id": A})
    assert r.status_code == 500 and r.json()["detail"] == "etat_tutorat_illisible"
    r = c.post("/api/v1/mika/session/answer", json={"student_pseudo_id": A, "requete_id": "rz",
                                                     "tutorat_id": t["tutorat_id"], "version": 1, "reponse": "5"})
    assert r.status_code == 500 and r.json()["detail"] == "etat_tutorat_illisible"


# --------------------------------------------------------------------------- #
# S3-06 (P2) — compréhension infirmée comptée comme réussite (« Bravo », est_correct)
# --------------------------------------------------------------------------- #
def test_s3_06_comprehension_ratee_n_est_pas_une_reussite(api):
    t = _start(api).json()
    t = _op(api, "help", t, "r1").json()
    t = _op(api, "answer", t, "r2", reponse="0,7").json()
    assert t["reponse"]["action"] == "VERIFIER_COMPREHENSION"
    t = _op(api, "comprehension", t, "r3", reponse="12").json()
    assert t["etat"]["comprehension_verifiee"] is False and t["etat"]["niveau_estime"] == "FRAGILE"
    # Épuise la suite : jusqu'à la fin, jamais « Bravo » ni tentative correcte.
    i = 0
    while not t["etat"]["termine"]:
        op, kw = ("comprehension", {"reponse": "12"}) if t["etat"]["attend_comprehension"] else ("answer", {"reponse": "0,7"})
        t = _op(api, op, t, f"s{i}", **kw).json()
        assert "Bravo" not in t["reponse"]["message"]
        assert t["etat"]["niveau_estime"] == "FRAGILE"
        i += 1
        assert i < 20
    db = SessionLocal()
    try:
        assert [x.est_correct for x in db.query(TentativeExercice).all()] == [False]
    finally:
        db.close()


def test_s3_06_temoin_comprehension_reussie_reste_bravo(api):
    t = _start(api).json()
    t = _op(api, "help", t, "r1").json()
    t = _op(api, "answer", t, "r2", reponse="0,7").json()
    t = _op(api, "comprehension", t, "r3", reponse="0,9").json()
    assert t["reponse"]["action"] == "CONSOLIDATION" and "Bravo" in t["reponse"]["message"]


# --------------------------------------------------------------------------- #
# S3-07 (P2) — oracle de timing à la connexion (e-mail inconnu : pas de bcrypt)
# --------------------------------------------------------------------------- #
def test_s3_07_connexion_temps_constant(client, bcrypt_rapide, monkeypatch):
    db = BillingSession()
    crud_billing.creer_compte(db, email="connu@example.com", mot_de_passe=MDP)
    appels = []
    orig = crud_billing.verifier_mot_de_passe
    monkeypatch.setattr(crud_billing, "verifier_mot_de_passe", lambda m, h: appels.append(1) or orig(m, h))
    for email in ("connu@example.com", "inconnu@example.com"):
        assert crud_billing.authentifier(db, email, "mauvais-mot-de-passe") is None
    compte = crud_billing.get_compte_par_email(db, "connu@example.com")
    compte.actif = False
    db.commit()
    assert crud_billing.authentifier(db, "connu@example.com", MDP) is None  # désactivé
    db.close()
    assert len(appels) == 3  # un hash vérifié dans CHAQUE cas


# --------------------------------------------------------------------------- #
# S3-08 (P2) — inscription concurrente du même e-mail : IntegrityError ⇒ 500
# --------------------------------------------------------------------------- #
def test_s3_08_inscription_concurrente(client, bcrypt_rapide, monkeypatch):
    db = BillingSession()
    crud_billing.creer_compte(db, email="double@example.com", mot_de_passe=MDP)
    # L'autre requête a passé le contrôle « e-mail libre » avant notre commit.
    monkeypatch.setattr(crud_billing, "get_compte_par_email", lambda db, e: None)
    with pytest.raises(ValueError, match="email_deja_utilise"):
        crud_billing.creer_compte(BillingSession(), email="double@example.com", mot_de_passe=MDP)
    db.close()


# --------------------------------------------------------------------------- #
# S3-09 (P2) — export RGPD incomplet (journal du tuteur, liens compte ↔ élève)
# --------------------------------------------------------------------------- #
def test_s3_09_export_couvre_toute_table_eleve(api):
    t = _start(api).json()
    _op(api, "help", t, "r1")
    out = api.get(f"/api/v1/rgpd/export/{A}").json()
    for modele in rgpd.TABLES_ELEVE:
        assert modele.__tablename__ in rgpd.CLES_EXPORT, modele.__tablename__
        assert rgpd.CLES_EXPORT[modele.__tablename__] in out
    assert {q["requete_id"] for q in out["requetes_tutorat_mika"]} == {"r-start", "r1"}
    assert "liens_comptes" in out and "@" not in json.dumps(out["liens_comptes"])


# --------------------------------------------------------------------------- #
# S3-10 (P2) — identifiants de 128 caractères persistés dans des colonnes String(64)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,corps", [
    ("/api/v1/session/heartbeat", {"session_id": "s" * 65, "user_id": "e1"}),
    ("/api/v1/memory/schedule", {"user_id": "e1", "notion_id": "n" * 65, "mastery_event": "SUCCESS"}),
    ("/api/v1/escalier/etape", {"student_pseudo_id": "e1", "competence_objectif": "c" * 65,
                                "exercice_id": "x", "reponse_eleve": "1"}),
])
def test_s3_10_identifiant_plus_long_que_la_colonne_refuse(client, url, corps):
    assert client.post(url, json=corps).status_code == 422


def test_s3_10_longueurs_api_compatibles_avec_colonnes():
    from typing import get_args

    from app.api.v1.escalier.router import EscalierEtapeIn
    from app.api.v1.memory.router import MemoryScheduleRequest
    from app.api.v1.memory.spaced_repetition import TacheRappelMemoire
    from app.api.v1.mikamike.store import TentativeExercice as T
    from app.api.v1.session.router import SessionHeartbeatIn, SessionReconnectIn, SessionSaveStateIn
    from app.api.v1.session.session_manager import MikaSessionState

    def max_len(modele, champ):
        info = modele.model_fields[champ]
        for m in list(info.metadata) + [x for a in get_args(info.annotation) for x in getattr(a, "__metadata__", ())]:
            if getattr(m, "max_length", None):
                return m.max_length
        return None

    paires = [
        (SessionHeartbeatIn, "session_id", MikaSessionState.session_id),
        (SessionSaveStateIn, "session_id", MikaSessionState.session_id),
        (SessionReconnectIn, "session_id", MikaSessionState.session_id),
        (MemoryScheduleRequest, "notion_id", TacheRappelMemoire.notion_id),
        (EscalierEtapeIn, "competence_objectif", T.competence),
        (EscalierEtapeIn, "exercice_id", T.exercice_id),
    ]
    for modele, champ, colonne in paires:
        assert max_len(modele, champ) <= colonne.type.length, (modele.__name__, champ)


def test_s3_10_catalogue_refuse_identifiant_trop_long():
    from app.api.v1.tutorat import contenu
    from app.curriculum.fixtures import referentiel_fictif
    from tests_cloud.test_mika_api import PLAN, _exercice

    long_id = "exo:fictif:" + "x" * 60
    cat = contenu.CatalogueTutorat(referentiel_fictif(), [_exercice(id=long_id)], {long_id: PLAN},
                                   autoriser_fictif=True)
    with pytest.raises(contenu.ContenuIndisponible) as e:
        cat.obtenir(long_id)
    assert "identifiant_trop_long" in e.value.raisons


# --------------------------------------------------------------------------- #
# S3-11 (P2) — mutation_check mutait l'ARBRE DE TRAVAIL (bug laissé en place si arrêt brutal)
# --------------------------------------------------------------------------- #
def test_s3_11_mutation_sur_copie_jetable(monkeypatch, tmp_path):
    from tools import mutation_check

    f = tmp_path / "m.py"
    f.write_text("A = 1\n", "utf-8")
    vus = []

    def suite(*_a):
        vus.append(f.read_text("utf-8"))  # le dépôt réel n'est JAMAIS muté, même pendant l'exécution
        if len(vus) > 1:
            raise KeyboardInterrupt  # arrêt brutal pendant le mutant
        return 0

    monkeypatch.setattr(mutation_check, "RACINE", tmp_path)
    monkeypatch.setattr(mutation_check, "MUTANTS", [mutation_check.Mutant("m", "m.py", "A = 1", "A = 2")])
    monkeypatch.setattr(mutation_check, "executer_suite", suite)
    with pytest.raises(KeyboardInterrupt):
        mutation_check.main([])
    assert vus == ["A = 1\n", "A = 1\n"] and f.read_text("utf-8") == "A = 1\n"


def test_s3_11_mutants_session3_applicables():
    from tools import mutation_check

    for m in mutation_check.MUTANTS:
        assert (RACINE / m.fichier).read_text("utf-8").count(m.avant) == 1, m.nom


# --------------------------------------------------------------------------- #
# S3-12 (P2) — faux positifs possibles : les tests négatifs de test_auth.py forgent des
# claims sans témoin positif ; ce témoin prouve que les MÊMES claims, non altérés, passent
# (sinon un 401 pouvait venir d'une autre cause que la modification testée).
# --------------------------------------------------------------------------- #
def test_s3_12_temoin_claims_forges_valides_acceptes(monde):
    import jwt as pyjwt

    from tests_cloud.test_auth import _cle_eleve, _eleve_claims, _soumettre

    client, _ = monde
    assert _soumettre(client, "eleve-a-001", pyjwt.encode(_eleve_claims(), _cle_eleve(), algorithm="HS256")).status_code == 200
