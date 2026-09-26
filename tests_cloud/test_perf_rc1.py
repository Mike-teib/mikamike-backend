"""
Session 5 — performance des lots restants (release candidate).

Critère principal : le NOMBRE DE REQUÊTES SQL par appel HTTP ne dépend pas du volume (historique
de l'élève, nombre d'élèves, de séances, de liens) — détecte les requêtes répétitives (N+1) et
les chargements globaux. Critère secondaire : durées RELATIVES (robustes à la machine de CI) pour
le moteur de progression, le backlog et une migration sur base volumineuse.
Données FICTIVES, bases jetables.
"""

import datetime as dt
import time
from contextlib import contextmanager

import pytest
from sqlalchemy import event, insert

from app.api.v1.mikamike.store import SessionLocal, TentativeExercice
from app.api.v1.session.session_manager import MikaSessionState
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.pedagogie.progression import HISTORIQUE_MAX, Tentative, diagnostiquer
from app.db.registre import engines

T0 = dt.datetime(2030, 1, 1)
EXO, COMP = "exo-maths-algebre-1", "equations_1er_degre"


@contextmanager
def compteur():
    """Compte les requêtes SQL émises sur les DEUX bases pendant le bloc."""
    n = {"total": 0, "mika_tentatives": 0}

    def ecoute(conn, cursor, statement, *a):
        n["total"] += 1
        if "mika_tentatives" in statement:
            n["mika_tentatives"] += 1

    engs = list(engines().values())
    for e in engs:
        event.listen(e, "before_cursor_execute", ecoute)
    try:
        yield n
    finally:
        for e in engs:
            event.remove(e, "before_cursor_execute", ecoute)


def _historique(eleve, n, competence=COMP, autres_eleves=0):
    lignes = [{"eleve_hmac": hmac_eleve(eleve), "exercice_id": EXO, "matiere": "maths", "niveau": "4e",
               "competence": competence, "est_correct": i % 3 != 0, "avec_aide": i % 5 == 0,
               "ts": T0 + dt.timedelta(hours=i)} for i in range(n)]
    lignes += [{"eleve_hmac": f"{e:016x}", "exercice_id": EXO, "matiere": "maths", "niveau": "4e",
                "competence": competence, "est_correct": True, "avec_aide": False, "ts": T0}
               for e in range(autres_eleves)]
    with SessionLocal() as db:
        if lignes:
            db.execute(insert(TentativeExercice), lignes)
        db.commit()


def _requetes(client, methode, url, **kw):
    with compteur() as n:
        r = client.request(methode, url, **kw)
    assert r.status_code < 300, r.text
    return n


# --------------------------------------------------------------------------- #
# Soumission / escalier : moteur sur historique (lecture BORNÉE, requêtes constantes)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url,corps", [
    ("/api/v1/exercices/soumettre", {"exercice_id": EXO, "reponse": "3"}),
    ("/api/v1/escalier/etape", {"competence_objectif": COMP, "exercice_id": EXO, "reponse_eleve": "3"}),
])
def test_soumission_requetes_independantes_de_l_historique(client, url, corps):
    mesures = {}
    for n_hist, autres in ((5, 0), (2000, 3000)):
        eleve = f"eleve-perf-{n_hist}"
        _historique(eleve, n_hist, autres_eleves=autres)
        mesures[n_hist] = _requetes(client, "POST", url, json={**corps, "student_pseudo_id": eleve})
    assert mesures[5]["total"] == mesures[2000]["total"], mesures


def test_prochaine_etape_requetes_constantes(client):
    for eleve, n in (("pe-a", 3), ("pe-b", 1500)):
        _historique(eleve, n)
    a = _requetes(client, "GET", "/api/v1/parcours/prochaine-etape", params={"student_id": "pe-a"})
    b = _requetes(client, "GET", "/api/v1/parcours/prochaine-etape", params={"student_id": "pe-b"})
    assert a["total"] == b["total"]


# --------------------------------------------------------------------------- #
# Séances : coût indépendant du nombre de séances des AUTRES élèves
# --------------------------------------------------------------------------- #
def test_seances_requetes_independantes_du_nombre_de_seances(client):
    def cycle(eleve):
        sid = client.post("/api/v1/session/nouvelle", json={"user_id": eleve}).json()["session_id"]
        out = []
        for chemin, corps in (("heartbeat", {}), ("save-state", {"state_data": {"ardoise": "x"}}), ("reconnect", {})):
            out.append(_requetes(client, "POST", f"/api/v1/session/{chemin}",
                                 json={"session_id": sid, "user_id": eleve, **corps})["total"])
        return out

    petit = cycle("seance-a")
    with SessionLocal() as db:
        db.execute(insert(MikaSessionState), [
            {"session_id": f"autre-{i:05d}", "eleve_hmac": f"{i:016x}", "is_active": True,
             "last_activity_ts": T0, "created_at": T0, "state_json": "{}"} for i in range(5000)])
        db.commit()
    assert cycle("seance-b") == petit


# --------------------------------------------------------------------------- #
# Export RGPD : requêtes constantes (lignes proportionnelles à l'élève, pas N+1)
# --------------------------------------------------------------------------- #
def test_export_rgpd_sans_n_plus_1(client):
    _historique("rgpd-a", 3)
    _historique("rgpd-b", 800)
    for i in range(30):
        client.post("/api/v1/session/nouvelle", json={"user_id": "rgpd-b"})
    client.post("/api/v1/session/nouvelle", json={"user_id": "rgpd-a"})
    a = _requetes(client, "GET", "/api/v1/rgpd/export/rgpd-a")
    b = _requetes(client, "GET", "/api/v1/rgpd/export/rgpd-b")
    assert a["total"] == b["total"]


# --------------------------------------------------------------------------- #
# Dashboard d'un parent multi-enfants (enforce) : coût par enfant constant
# --------------------------------------------------------------------------- #
def test_dashboard_parent_multi_enfants_constant(client, monkeypatch):
    import bcrypt

    from paiement_comptes import crud_billing
    from paiement_comptes.database import SessionLocal as Billing
    from paiement_comptes.liens import LienCompteEleve

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    client.post("/api/v1/comptes/inscription", json={"email": "multi@example.com", "mot_de_passe": "motdepasse-multi-1"})
    jeton = client.post("/api/v1/comptes/connexion", json={"email": "multi@example.com",
                                                          "mot_de_passe": "motdepasse-multi-1"}).json()["token"]
    with Billing() as b:
        cid = crud_billing.get_compte_par_email(b, "multi@example.com").id
        for k in range(60):
            b.add(LienCompteEleve(compte_id=cid, eleve_hmac=hmac_eleve(f"enfant-{k}"), relation="parent"))
        b.commit()
    _historique("enfant-0", 5)
    _historique("enfant-59", 900)
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    h = {"Authorization": f"Bearer {jeton}"}
    a = _requetes(client, "GET", "/api/v1/parents/dashboard/enfant-0", headers=h)
    b = _requetes(client, "GET", "/api/v1/parents/dashboard/enfant-59", headers=h)
    assert a["total"] == b["total"] and a["total"] <= 8


# --------------------------------------------------------------------------- #
# Moteur de progression : coût borné quel que soit l'historique (O(HISTORIQUE_MAX²) au pire)
# --------------------------------------------------------------------------- #
def test_diagnostic_borne_par_historique_max():
    def mesure(n):
        h = [Tentative(i % 3 != 0, i % 5 == 0, 1_900_000_000 + i * 3600) for i in range(n)]
        t = time.perf_counter()
        for _ in range(20):
            diagnostiquer(h)
        return time.perf_counter() - t

    mesure(10)
    base, grand = mesure(HISTORIQUE_MAX), mesure(50_000)
    # 50 000 réponses coûtent comme 60 (+ tri) : jamais quadratique en la taille brute.
    assert grand < base * 40 + 0.5


# --------------------------------------------------------------------------- #
# Backlog : croissance ~linéaire
# --------------------------------------------------------------------------- #
def test_backlog_croissance_lineaire():
    from app.curriculum.backlog import calculer_backlog
    from app.curriculum.harnais_import import notion_synthetique, referentiel_structure

    def mesure(n):
        ref = referentiel_structure("0" * 64, 4)
        ref = ref.model_copy(update={"notions": tuple(notion_synthetique(i) for i in range(n))})
        t = time.perf_counter()
        calculer_backlog(ref)
        return time.perf_counter() - t

    mesure(50)
    petit, grand = min(mesure(500) for _ in range(3)), min(mesure(4000) for _ in range(3))
    assert grand < petit * 8 * 3 + 0.2  # ×8 données ⇒ bien moins que ×64 (quadratique)


# --------------------------------------------------------------------------- #
# Migrations sur base volumineuse : instructions indépendantes du volume (aucun traitement
# ligne à ligne), durée bornée
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n_lignes", [1_000, 100_000])
def test_migration_sur_grosse_base(tmp_path, n_lignes):
    from tests_cloud.test_migrations_validation import _py

    out = _py(tmp_path, f"""
        import time
        from sqlalchemy import event
        m.upgrade("mika", "m0001_baseline")
        m.upgrade("billing")
        with engines()["mika"].begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO mika_tentatives (eleve_hmac, exercice_id, matiere, niveau, competence, est_correct, "
                "avec_aide, ts) VALUES (?, 'exo', 'maths', '5e', ?, 1, 0, '2026-01-01 00:00:00')",
                [(f"{{i % 997:016x}}", f"c{{i % 13}}") for i in range({n_lignes})])
        n = {{"stmts": 0}}
        def compte(*a):
            n["stmts"] += 1
        event.listen(engines()["mika"], "before_cursor_execute", compte)
        t = time.perf_counter()
        m.upgrade("mika")
        duree = time.perf_counter() - t
        print(json.dumps({{"stmts": n["stmts"], "duree": duree, "rev": m.courante("mika")}}))
    """)
    assert out["rev"] == "m0003_tutorat" and out["duree"] < 30
    _STMTS[n_lignes] = out["stmts"]
    if len(_STMTS) == 2:
        assert _STMTS[1_000] == _STMTS[100_000], _STMTS


_STMTS = {}
