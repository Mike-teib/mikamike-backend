"""
Non-régression des bugs/failles corrigés au lot 2 (cf. CLOUD_AUDIT_MIKAMAIKE.md §4).
Chaque test échoue sur le code d'origine.
"""

import datetime as _dt

import jwt
import pytest

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal
from app.api.v1.parcours.curriculum_dataset import (
    NotionNode,
    obtenir_graphe_competences,
    valider_prerequis_resolus,
    CURRICULA_DATA,
)
from app.api.v1.rgpd.router import TABLES_ELEVE, _hmac


# --------------------------------------------------------------------------- #
# B1 — IDOR session
# --------------------------------------------------------------------------- #
def _save(client, sid, uid, data):
    return client.post("/api/v1/session/save-state", json={"session_id": sid, "user_id": uid, "state_data": data})


def test_b1_reconnect_session_autre_eleve_refuse(client):
    assert _save(client, "sess-a", "eleve-a", {"ardoise_draft": "brouillon-prive-a"}).status_code == 200
    r = client.post("/api/v1/session/reconnect", json={"session_id": "sess-a", "user_id": "eleve-b"})
    assert r.status_code == 403
    assert "brouillon-prive-a" not in r.text


def test_b1_save_state_session_autre_eleve_refuse(client):
    _save(client, "sess-a", "eleve-a", {"x": 1})
    r = _save(client, "sess-a", "eleve-b", {"x": 2})
    assert r.status_code == 403
    r = client.post("/api/v1/session/reconnect", json={"session_id": "sess-a", "user_id": "eleve-a"})
    assert r.json()["session_state"]["x"] == 1


def test_b1_heartbeat_session_autre_eleve_refuse(client):
    client.post("/api/v1/session/heartbeat", json={"session_id": "sess-h", "user_id": "eleve-a"})
    r = client.post("/api/v1/session/heartbeat", json={"session_id": "sess-h", "user_id": "eleve-b"})
    assert r.status_code == 403


def test_b1_etat_session_trop_volumineux_413(client):
    r = _save(client, "sess-big", "eleve-a", {"ardoise_draft": "A" * (2 * 1024 * 1024 + 10)})
    assert r.status_code == 413


# --------------------------------------------------------------------------- #
# B2 — Droit à l'oubli complet
# --------------------------------------------------------------------------- #
def test_b2_effacement_couvre_memoire_et_sessions(client):
    uid = "eleve-rgpd-complet"
    client.post("/api/v1/memory/schedule", json={"user_id": uid, "notion_id": "n1", "mastery_event": "SUCCESS"})
    _save(client, "sess-rgpd", uid, {"ardoise_draft": "trace"})

    exp = client.get(f"/api/v1/rgpd/export/{uid}")
    assert exp.status_code == 200, "mémoire + session suffisent : l'export ne doit pas être 404"
    body = exp.json()
    assert len(body["rappels_memoire"]) == 1
    assert body["sessions"][0]["etat_seance"]["ardoise_draft"] == "trace"

    r = client.delete(f"/api/v1/rgpd/effacer/{uid}")
    assert r.status_code == 200
    assert r.json()["rappels_memoire_supprimes"] == 1
    assert r.json()["sessions_supprimees"] == 1
    assert client.get(f"/api/v1/rgpd/export/{uid}").status_code == 404


def test_b2_registre_couvre_toute_table_eleve():
    """Toute table ayant une colonne eleve_hmac doit être purgée par /rgpd/effacer."""
    from app.db.registre import metadatas

    couvertes = {m.__tablename__ for m in TABLES_ELEVE}
    # Revue session 2 : toutes les metadata de la base élève (registre), pas une liste figée
    # qui laisserait échapper une nouvelle base déclarative.
    for md in metadatas("mika"):
        for table in md.tables.values():
            if "eleve_hmac" in table.c:
                assert table.name in couvertes, f"table élève non couverte par le RGPD : {table.name}"


# --------------------------------------------------------------------------- #
# B3/B4 — Référentiel : pas de repli silencieux vers Maths
# --------------------------------------------------------------------------- #
def test_b3_matiere_absente_du_niveau_404_et_pas_maths(client):
    r = client.post("/api/v1/parcours", json={"user_id": "u1", "level": "6e", "subject": "SVT"})
    assert r.status_code == 404
    assert r.json()["detail"] == "programme_indisponible"
    assert obtenir_graphe_competences("6e", "svt") == []


@pytest.mark.parametrize("level,subject", [("7e", "Maths"), ("5e", "sciences"), ("5e", "histoire")])
def test_b3_referentiel_inconnu_422(client, level, subject):
    r = client.post("/api/v1/parcours", json={"user_id": "u1", "level": level, "subject": subject})
    assert r.status_code == 422


def test_b3_get_parcours_matiere_inconnue_422(client):
    assert client.get("/api/v1/parcours/u1/5e/histoire").status_code == 422


def test_b4_prerequis_resolus_reel():
    toutes = [n for g in CURRICULA_DATA.values() for n in g]
    assert valider_prerequis_resolus(toutes) is True
    orpheline = NotionNode("x_01", "X", "5e", "Maths", ["n_existe_pas"])
    assert valider_prerequis_resolus([orpheline]) is False


# --------------------------------------------------------------------------- #
# B5 — JWT dont `sub` n'est pas un id de compte
# --------------------------------------------------------------------------- #
def test_b5_token_sub_non_entier_401(client):
    from paiement_comptes.router_comptes import _JWT_ALGO, _JWT_SECRET

    now = int(_dt.datetime.now(_dt.timezone.utc).timestamp())
    tok = jwt.encode({"sub": "eleve-pseudo", "exp": now + 60}, _JWT_SECRET, algorithm=_JWT_ALGO)
    r = client.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_b5_token_alg_none_refuse(client):
    tok = jwt.encode({"sub": "1"}, key=None, algorithm="none")
    r = client.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# B6 — Pas de fuite du message d'exception Stripe
# --------------------------------------------------------------------------- #
def test_b6_erreur_stripe_non_divulguee(client, monkeypatch):
    import paiement_comptes.router_paiement as rp

    class _FakeSession:
        @staticmethod
        def create(**_kw):
            raise RuntimeError("detail-interne-confidentiel")

    class _FakeStripe:
        class checkout:  # noqa: N801
            Session = _FakeSession

    monkeypatch.setattr(rp, "stripe", _FakeStripe)
    monkeypatch.setattr(rp, "_STRIPE_SECRET", "configure-pour-le-test")
    monkeypatch.setattr(rp, "_PRICE_ID", "prix-fictif")

    tok = client.post(
        "/api/v1/comptes/inscription",
        json={"email": "parent@example.com", "mot_de_passe": "MotDePasse#2026"},
    ).json()["token"]
    r = client.post("/api/v1/paiement/checkout", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 502
    assert "confidentiel" not in r.text


# --------------------------------------------------------------------------- #
# B7 — Entrées mémoire bornées / explicites
# --------------------------------------------------------------------------- #
def test_b7_evenement_inconnu_422(client):
    r = client.post("/api/v1/memory/schedule", json={"user_id": "u", "notion_id": "n", "mastery_event": "PEUT-ETRE"})
    assert r.status_code == 422


@pytest.mark.parametrize("scores,seuil", [([1.5], 0.7), ([-0.1], 0.7), ([0.5], 3.0)])
def test_b7_scores_hors_bornes_422(client, scores, seuil):
    r = client.post("/api/v1/memory/detect-fragile", json={"scores": scores, "seuil_fragilite": seuil})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# B8 — Un succès AVEC aide ne compte pas dans la série vers MAITRISE
# --------------------------------------------------------------------------- #
def test_b8_succes_aide_casse_la_serie(client):
    def soumettre(aide):
        return client.post("/api/v1/exercices/soumettre", json={
            "exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "eleve-serie",
            "reponse": "3", "avec_aide": aide,
        }).json()["etat_maitrise"]

    assert soumettre(False) == "EN_COURS"
    assert soumettre(False) == "ACQUIS_AUTONOME"
    assert soumettre(True) == "ACQUIS_ASSISTE"
    # Seule la tentative courante est autonome : pas de MAITRISE.
    assert soumettre(False) == "ACQUIS_AUTONOME"
    assert soumettre(False) == "MAITRISE"


# --------------------------------------------------------------------------- #
# B9 — L'échec est imputé à la compétence réellement tentée
# --------------------------------------------------------------------------- #
def test_b9_escalier_echec_impute_a_la_competence_tentee(client):
    r = client.post("/api/v1/escalier/etape", json={
        "student_pseudo_id": "eleve-b9", "competence_objectif": "equations_1er_degre",
        "exercice_id": "exo-maths-algebre-1", "reponse_eleve": "x = 999",
    })
    assert r.status_code == 200
    lacune = r.json()["remediation"]["competence_lacune"]
    db = SessionLocal()
    try:
        etats = crud.get_etats(db, _hmac("eleve-b9"))
    finally:
        db.close()
    assert etats == {"equations_1er_degre": "FRAGILE"}
    assert lacune not in etats


def test_b9_escalier_meme_semantique_que_soumettre(client):
    def etape():
        return client.post("/api/v1/escalier/etape", json={
            "student_pseudo_id": "eleve-b9s", "competence_objectif": "equations_1er_degre",
            "exercice_id": "exo-maths-algebre-1", "reponse_eleve": "3",
        }).json()["etat_maitrise"]

    assert [etape(), etape(), etape()] == ["EN_COURS", "ACQUIS_AUTONOME", "MAITRISE"]


# --------------------------------------------------------------------------- #
# B10 — État corrompu en base : pas de 500
# --------------------------------------------------------------------------- #
def test_b10_prochaine_etape_etat_corrompu(client):
    db = SessionLocal()
    try:
        crud.upsert_etat(db, _hmac("eleve-b10"), "equations_1er_degre", "ETAT_INVENTE")
    finally:
        db.close()
    r = client.get("/api/v1/parcours/prochaine-etape", params={"student_id": "eleve-b10"})
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Validation des identifiants : aucune PII possible dans un pseudo-id
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pseudo", ["Jean Dupont", "parent@example.com", "x" * 200, "", "../etc"])
def test_identifiant_pii_ou_invalide_422(client, pseudo):
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-maths-algebre-1", "student_pseudo_id": pseudo, "reponse": "3",
    })
    assert r.status_code == 422


def test_reponse_trop_longue_422(client):
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "eleve-x", "reponse": "3" * 501,
    })
    assert r.status_code == 422


def test_reponse_vide_non_acceptee(client):
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "eleve-x", "reponse": "",
    })
    assert r.status_code == 200
    assert r.json()["est_correct"] is False
