"""
Observabilité (lot 25) : journaux structurés sans données sensibles, request_id, erreurs
internes sans fuite. Aucun secret réel (secrets de test), comptes FICTIFS.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core import observabilite
from paiement_comptes import crud_billing, liens
from paiement_comptes.database import SessionLocal as BillingSession
from app.core.pseudonymisation import hmac_eleve

MDP = "motdepasse-obs-00001"


@pytest.fixture()
def journaux(caplog):
    caplog.set_level(logging.INFO, logger="mikamike.http")

    def lignes():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "mikamike.http"]
    return caplog, lignes


def test_une_ligne_par_requete_avec_gabarit_de_route(client, journaux):
    caplog, lignes = journaux
    client.get("/api/v1/rgpd/export/eleve-secret-42")
    ligne = lignes()[-1]
    assert set(ligne) >= {"event", "request_id", "method", "route", "status", "duration_ms", "error_code"}
    assert ligne["route"] == "/api/v1/rgpd/export/{student_pseudo_id}"
    assert "eleve-secret-42" not in caplog.text


def test_aucune_donnee_sensible_dans_les_journaux(client, journaux, monkeypatch):
    import bcrypt

    caplog, lignes = journaux
    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    r = client.post("/api/v1/comptes/inscription", json={"email": "obs@example.com", "mot_de_passe": MDP})
    jeton = r.json()["token"]
    db = BillingSession()
    compte = crud_billing.get_compte_par_email(db, "obs@example.com")
    compte.email_verifie = True
    db.commit()
    code, _ = liens.creer_invitation(db, "eleve-obs", hmac_eleve("eleve-obs"), emis_par="operateur")
    db.close()
    h = {"Authorization": f"Bearer {jeton}"}
    client.post("/api/v1/liens/accepter", json={"code": code, "confirmation": True}, headers=h)
    client.post("/api/v1/comptes/connexion", json={"email": "obs@example.com", "mot_de_passe": "mauvais-mdp-0"})
    client.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": "jeton-secret-xyz"})
    texte = caplog.text
    for secret in (MDP, jeton, code, "obs@example.com", "eleve-obs", "jeton-secret-xyz", "Bearer", "mauvais-mdp-0"):
        assert secret not in texte, secret
    codes = [x["error_code"] for x in lignes()]
    assert "identifiants_invalides" in codes and "jeton_invalide_ou_expire" in codes


def test_request_id_repris_si_sur_remplace_sinon(client, journaux):
    _, lignes = journaux
    r = client.get("/health", headers={"X-Request-ID": "abc-123-def-456"})
    assert r.headers["x-request-id"] == "abc-123-def-456" and lignes()[-1]["request_id"] == "abc-123-def-456"
    r = client.get("/health", headers={"X-Request-ID": "x\"}\n{\"event\": \"faux"})
    assert r.headers["x-request-id"] != "x" and len(r.headers["x-request-id"]) == 32
    assert all(set(x) <= observabilite.CHAMPS_AUTORISES for x in lignes())


def test_exception_interne_sans_fuite(journaux, monkeypatch):
    caplog, lignes = journaux
    import main

    app = main.create_app()

    @app.get("/boum")
    def boum():
        raise RuntimeError("secret interne : mot de passe = hunter2")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boum")
    assert r.status_code == 500 and r.json()["detail"] == "erreur_interne"
    assert r.json()["request_id"] == r.headers["x-request-id"]
    assert "hunter2" not in r.text and "hunter2" not in caplog.text and "Traceback" not in r.text
    assert lignes()[-1]["exception"] == "RuntimeError"


def test_413_journalise(client, journaux):
    _, lignes = journaux
    client.post("/api/v1/exercices/soumettre", content=b"x", headers={"content-length": str(10**9)})
    assert lignes()[-1]["status"] == 413


def test_journaliser_filtre_les_cles_non_autorisees(caplog):
    caplog.set_level(logging.INFO, logger="mikamike.http")
    observabilite.journaliser("test", request_id="r", mot_de_passe="x", jwt="y", email="z@example.com")
    assert "mot_de_passe" not in caplog.text and "z@example.com" not in caplog.text and '"request_id": "r"' in caplog.text
