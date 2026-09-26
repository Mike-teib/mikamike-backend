"""
Autorisation des routes élève / parent / RGPD en mode « enforce » (AUTH_CONTRACT.md).

Acteurs FICTIFS : élèves A et B (pseudo-ids), parent PA lié à A, parent PB lié à B,
compte élève EA titulaire de A. Aucun secret réel (secrets de test du conftest).
"""

import datetime as _dt
import hashlib
import hmac

import jwt
import pytest

from app.core import auth
from app.core.pseudonymisation import hmac_eleve
from app.core.security_config import get_jwt_secret
from paiement_comptes import crud_billing, liens
from paiement_comptes.database import SessionLocal as BillingSession
from paiement_comptes.router_comptes import creer_token

A, B = "eleve-a-001", "eleve-b-002"
MDP = "motdepasse-de-test-1"


@pytest.fixture()
def enforce(monkeypatch):
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")


@pytest.fixture()
def monde(client, enforce, monkeypatch):
    import bcrypt

    # Coût bcrypt minimal pour les comptes FICTIFS de test (vitesse ; le code de prod est inchangé).
    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    db = BillingSession()
    try:
        comptes = {}
        for nom, role in (("pa", "parent"), ("pb", "parent"), ("ea", "eleve"), ("seul", "parent")):
            comptes[nom] = crud_billing.creer_compte(db, email=f"{nom}@example.com", mot_de_passe=MDP, role=role)
        liens.lier(db, comptes["pa"].id, hmac_eleve(A), "parent")
        liens.lier(db, comptes["pb"].id, hmac_eleve(B), "parent")
        liens.lier(db, comptes["ea"].id, hmac_eleve(A), "eleve")
        jetons = {nom: creer_token(c) for nom, c in comptes.items()}
    finally:
        db.close()

    def jeton_eleve(pseudo, compte="pa"):
        r = client.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": pseudo},
                        headers=_h(jetons[compte]))
        assert r.status_code == 200, r.text
        return r.json()["token"]

    jetons["A"] = jeton_eleve(A, "pa")
    jetons["B"] = jeton_eleve(B, "pb")
    return client, jetons


def _h(jeton):
    return {"Authorization": f"Bearer {jeton}"}


def _soumettre(client, pseudo, jeton=None):
    return client.post("/api/v1/exercices/soumettre", headers=_h(jeton) if jeton else {},
                       json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": pseudo, "reponse": "3"})


def _now():
    return int(_dt.datetime.now(_dt.timezone.utc).timestamp())


def _cle_eleve():
    return hmac.new(get_jwt_secret().encode(), b"mikamike/jeton-eleve/v1", hashlib.sha256).digest()


def _eleve_claims(**kw):
    c = {"iss": auth.ISSUER, "aud": auth.AUDIENCE, "typ": auth.TYP_ELEVE, "role": "eleve",
         "sub": A, "iat": _now(), "exp": _now() + 600}
    c.update(kw)
    return c


# --------------------------------------------------------------------------- #
# Toutes les routes élève/parent/RGPD sont fermées sans jeton (par construction)
# --------------------------------------------------------------------------- #
ROUTES_PUBLIQUES = {"/health", "/healthz", "/api/v1/openapi.json", "/api/v1/docs", "/api/v1/redoc",
                    "/api/v1/docs/oauth2-redirect", "/docs/oauth2-redirect"}
PREFIXES_HORS_PERIMETRE = ("/api/v1/comptes", "/api/v1/paiement", "/api/v1/auth")


def _routes_protegees(app):
    # FastAPI ≥ 0.141 encapsule les sous-routeurs : on énumère via le schéma OpenAPI.
    for chemin, ops in sorted(app.openapi()["paths"].items()):
        if chemin in ROUTES_PUBLIQUES or chemin.startswith(PREFIXES_HORS_PERIMETRE):
            continue
        for m in sorted(ops):
            yield m.upper(), chemin


def test_toutes_les_routes_eleve_exigent_un_jeton(client, enforce):
    from main import app

    vues = 0
    for methode, chemin in _routes_protegees(app):
        url = (chemin.replace("{student_pseudo_id}", A).replace("{user_id}", A)
               .replace("{level}", "5e").replace("{subject}", "maths").replace("{tutorat_id}", "x" * 32))
        r = client.request(methode, url, params={"student_id": A, "session_id": "s1"}, json={})
        assert r.status_code == 401, f"{methode} {chemin} -> {r.status_code}"
        vues += 1
    assert vues >= 14  # 14 routes historiques (+ API tutorat)


# --------------------------------------------------------------------------- #
# Jeton absent / expiré / mal signé / confusion / rôle
# --------------------------------------------------------------------------- #
def test_jeton_absent(monde):
    client, _ = monde
    assert _soumettre(client, A).status_code == 401


def test_jeton_expire(monde):
    client, _ = monde
    vieux = jwt.encode(_eleve_claims(iat=_now() - 7200, exp=_now() - 60), _cle_eleve(), algorithm="HS256")
    r = _soumettre(client, A, vieux)
    assert r.status_code == 401 and r.json()["detail"] == "jeton_expire"


@pytest.mark.parametrize("cle", [b"une-autre-cle-de-test-0000000000", "test-jwt-secret-not-for-prod-0123456789"])
def test_jeton_mal_signe(monde, cle):
    # Signé avec une autre clé, ou avec la clé BRUTE des comptes (confusion de clé).
    client, _ = monde
    assert _soumettre(client, A, jwt.encode(_eleve_claims(), cle, algorithm="HS256")).status_code == 401


def test_alg_none_refuse(monde):
    client, _ = monde
    faux = jwt.encode(_eleve_claims(), None, algorithm="none")
    assert _soumettre(client, A, faux).status_code == 401


@pytest.mark.parametrize("modif", [{"aud": "autre-api"}, {"iss": "autre"}, {"typ": "compte"},
                                   {"role": "parent"}, {"sub": 123}])
def test_claims_eleve_invalides(monde, modif):
    client, _ = monde
    assert _soumettre(client, A, jwt.encode(_eleve_claims(**modif), _cle_eleve(), algorithm="HS256")).status_code == 401


@pytest.mark.parametrize("sans", ["exp", "iat", "aud", "iss", "typ"])
def test_claim_eleve_manquant(monde, sans):
    client, _ = monde
    c = _eleve_claims()
    del c[sans]
    assert _soumettre(client, A, jwt.encode(c, _cle_eleve(), algorithm="HS256")).status_code == 401


def test_jeton_de_compte_parent_ne_vaut_pas_seance_eleve(monde):
    client, j = monde
    # Mauvais rôle : un parent lié ne peut pas SOUMETTRE à la place de l'élève.
    assert _soumettre(client, A, j["pa"]).status_code == 403


def test_jeton_eleve_refuse_sur_route_de_compte(monde):
    client, j = monde
    assert client.get("/api/v1/comptes/moi", headers=_h(j["A"])).status_code == 401


def test_entete_malforme(monde):
    client, j = monde
    for h in ("Basic abc", "Bearer", "Bearer  ", "bearer " + "x" * 5000, j["A"]):
        r = client.post("/api/v1/exercices/soumettre", headers={"Authorization": h},
                        json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": A, "reponse": "3"})
        assert r.status_code == 401, h[:20]


# --------------------------------------------------------------------------- #
# Propriété : A ne lit / ne modifie / ne supprime pas B
# --------------------------------------------------------------------------- #
def test_bon_proprietaire(monde):
    client, j = monde
    assert _soumettre(client, A, j["A"]).status_code == 200
    assert client.get(f"/api/v1/rgpd/export/{A}", headers=_h(j["A"])).status_code == 200
    assert client.get(f"/api/v1/parents/dashboard/{A}", headers=_h(j["A"])).status_code == 200


def test_a_ne_peut_pas_modifier_b(monde):
    client, j = monde
    assert _soumettre(client, B, j["A"]).status_code == 403
    for chemin, corps in [
        ("/api/v1/escalier/etape", {"student_pseudo_id": B, "competence_objectif": "fractions",
                                    "exercice_id": "exo-maths-fractions-1", "reponse_eleve": "1/2"}),
        ("/api/v1/memory/schedule", {"user_id": B, "notion_id": "n1", "mastery_event": "SUCCESS"}),
        ("/api/v1/session/save-state", {"session_id": "sb", "user_id": B, "state_data": {"x": 1}}),
        ("/api/v1/session/heartbeat", {"session_id": "sb", "user_id": B}),
        ("/api/v1/parcours", {"user_id": B}),
    ]:
        assert client.post(chemin, json=corps, headers=_h(j["A"])).status_code == 403, chemin


def test_a_ne_peut_pas_lire_b(monde):
    client, j = monde
    _soumettre(client, B, j["B"])
    for url in (f"/api/v1/rgpd/export/{B}", f"/api/v1/parents/dashboard/{B}",
                f"/api/v1/parcours/prochaine-etape?student_id={B}", f"/api/v1/parcours/{B}/5e/maths"):
        assert client.get(url, headers=_h(j["A"])).status_code == 403, url
    assert client.post("/api/v1/session/reconnect", json={"session_id": "sb", "user_id": B},
                       headers=_h(j["A"])).status_code == 403


def test_a_ne_peut_pas_supprimer_b(monde):
    client, j = monde
    _soumettre(client, B, j["B"])
    assert client.delete(f"/api/v1/rgpd/effacer/{B}", headers=_h(j["A"])).status_code == 403
    assert client.delete(f"/api/v1/rgpd/effacer/{B}", headers=_h(j["pa"])).status_code == 403
    assert client.get(f"/api/v1/rgpd/export/{B}", headers=_h(j["B"])).status_code == 200  # intact


def test_eleve_ne_peut_pas_s_effacer_lui_meme(monde):
    # Décision D9 (défaut prudent) : l'effacement est réservé au parent lié.
    client, j = monde
    _soumettre(client, A, j["A"])
    assert client.delete(f"/api/v1/rgpd/effacer/{A}", headers=_h(j["A"])).status_code == 403


def test_parent_lie_lit_et_efface_son_enfant(monde):
    client, j = monde
    _soumettre(client, A, j["A"])
    assert client.get(f"/api/v1/parents/dashboard/{A}", headers=_h(j["pa"])).status_code == 200
    assert client.get(f"/api/v1/rgpd/export/{A}", headers=_h(j["pa"])).status_code == 200
    r = client.delete(f"/api/v1/rgpd/effacer/{A}", headers=_h(j["pa"]))
    assert r.status_code == 200 and r.json()["tentatives_supprimees"] == 1
    assert r.json()["liens_compte_supprimes"] == 2  # parent + compte élève titulaire
    # Après effacement le lien n'existe plus : plus aucun accès du parent.
    assert client.get(f"/api/v1/rgpd/export/{A}", headers=_h(j["pa"])).status_code == 403


def test_parent_non_lie(monde):
    client, j = monde
    for url in (f"/api/v1/parents/dashboard/{A}", f"/api/v1/rgpd/export/{A}"):
        assert client.get(url, headers=_h(j["seul"])).status_code == 403
        assert client.get(url, headers=_h(j["pb"])).status_code == 403


def test_compte_eleve_titulaire_lecture_seule(monde):
    client, j = monde
    assert client.get(f"/api/v1/rgpd/export/{A}", headers=_h(j["ea"])).status_code in (200, 404)
    assert client.delete(f"/api/v1/rgpd/effacer/{A}", headers=_h(j["ea"])).status_code == 403
    assert _soumettre(client, A, j["ea"]).status_code == 403


def test_compte_desactive(monde):
    client, j = monde
    db = BillingSession()
    try:
        c = crud_billing.get_compte_par_email(db, "pa@example.com")
        c.actif = False
        db.commit()
    finally:
        db.close()
    assert client.get(f"/api/v1/rgpd/export/{A}", headers=_h(j["pa"])).status_code == 401


# --------------------------------------------------------------------------- #
# Émission du jeton élève
# --------------------------------------------------------------------------- #
def test_emission_exige_un_compte_lie(monde):
    client, j = monde
    url = "/api/v1/auth/eleve/jeton"
    assert client.post(url, json={"student_pseudo_id": A}).status_code == 401
    assert client.post(url, json={"student_pseudo_id": A}, headers=_h(j["pb"])).status_code == 403
    assert client.post(url, json={"student_pseudo_id": A}, headers=_h(j["A"])).status_code == 401  # pas un compte
    r = client.post(url, json={"student_pseudo_id": A}, headers=_h(j["ea"]))
    assert r.status_code == 200 and r.json()["expires_in"] == 120 * 60


def test_emission_meme_en_mode_off(client, monkeypatch):
    monkeypatch.setenv("MIKA_AUTH_MODE", "off")
    assert client.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": A}).status_code == 401


def test_jeton_emis_ne_contient_aucune_pii(monde):
    _, j = monde
    claims = jwt.decode(j["A"], options={"verify_signature": False})
    assert set(claims) == {"iss", "aud", "typ", "role", "sub", "iat", "exp", "jti"}
    assert "@" not in str(claims)


# --------------------------------------------------------------------------- #
# Configuration du mode
# --------------------------------------------------------------------------- #
def test_mode_absent_vaut_enforce(client, monkeypatch):
    monkeypatch.delenv("MIKA_AUTH_MODE", raising=False)
    assert _soumettre(client, A).status_code == 401


def test_mode_invalide_ferme(client, monkeypatch):
    monkeypatch.setenv("MIKA_AUTH_MODE", "desactive-svp")
    assert _soumettre(client, A).status_code == 500


def test_mode_off_interdit_en_production(client, monkeypatch):
    monkeypatch.setenv("MIKA_AUTH_MODE", "off")
    monkeypatch.setenv("MIKA_ENV", "production")
    assert _soumettre(client, A).status_code == 500
    with pytest.raises(auth.ConfigAuthInvalide):
        auth.mode_auth()


def test_mode_off_contrat_historique(client, monkeypatch):
    monkeypatch.setenv("MIKA_AUTH_MODE", "off")
    assert _soumettre(client, A).status_code == 200


@pytest.mark.parametrize("ttl", ["0", "721", "abc"])
def test_ttl_invalide(monkeypatch, ttl):
    monkeypatch.setenv("MIKA_ELEVE_TOKEN_TTL_MIN", ttl)
    with pytest.raises(auth.ConfigAuthInvalide):
        auth.emettre_jeton_eleve(A)


def test_session_stream_proprietaire(monde):
    client, j = monde
    client.post("/api/v1/session/heartbeat", json={"session_id": "sa", "user_id": A}, headers=_h(j["A"]))
    assert client.get("/api/v1/session/stream?session_id=sa", headers=_h(j["B"])).status_code == 403
    assert client.get("/api/v1/session/stream?session_id=sa", headers=_h(j["pa"])).status_code == 403
    assert client.get("/api/v1/session/stream?session_id=sa", headers=_h(j["A"])).status_code == 200


def test_detect_fragile_identifiant_du_porteur(monde):
    client, j = monde
    corps = {"user_id": B, "scores": [0.2, 0.3]}
    assert client.post("/api/v1/memory/detect-fragile", json=corps, headers=_h(j["A"])).status_code == 403
    corps["user_id"] = A
    assert client.post("/api/v1/memory/detect-fragile", json=corps, headers=_h(j["A"])).status_code == 200
