"""
Tests de sécurité complémentaires (session 3) : JWT (en-têtes hostiles, algorithmes, iat futur,
taille), IDOR croisé, CSRF/CORS, confusion de rôles, traversée, Unicode (homoglyphes, RTL),
rejeu, fixation de séance, compte supprimé. Acteurs FICTIFS (fixture `monde` de test_auth.py).
"""

import datetime as _dt

import jwt
import pytest

from app.core import auth
from paiement_comptes import crud_billing
from paiement_comptes.database import SessionLocal as BillingSession
from tests_cloud.test_auth import A, B, _cle_eleve, _eleve_claims, _h, _now, _soumettre, enforce, monde  # noqa: F401


def _jeton_eleve(**kw):
    return jwt.encode(_eleve_claims(**kw), _cle_eleve(), algorithm="HS256")


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("entete", [{"kid": "../../../../dev/null"}, {"jku": "https://attaquant.invalid/jwks"},
                                    {"x5u": "https://attaquant.invalid/cert"}, {"crit": ["exp"]}])
def test_entetes_jwt_hostiles_sans_effet(monde, entete):
    """Aucun en-tête n'oriente la vérification : clé fixe, HS256 fixe. Jeton honnête + en-tête
    exotique : soit accepté (ignoré), soit refusé — jamais une autre clé."""
    client, _ = monde
    honnete = jwt.encode(_eleve_claims(), _cle_eleve(), algorithm="HS256", headers=entete)
    assert _soumettre(client, A, honnete).status_code in (200, 401)
    forge = jwt.encode(_eleve_claims(), "cle-attaquant-0000000000000000", algorithm="HS256", headers=entete)
    assert _soumettre(client, A, forge).status_code == 401


@pytest.mark.parametrize("alg", ["HS384", "HS512"])
def test_autre_algorithme_hmac_refuse(monde, alg):
    client, _ = monde
    assert _soumettre(client, A, jwt.encode(_eleve_claims(), _cle_eleve(), algorithm=alg)).status_code == 401


def test_confusion_rs256_hs256_refusee(monde):
    """Classique : signer en HS256 avec une « clé publique » connue. Ici aucune clé publique
    n'existe et l'algorithme attendu est figé : refus."""
    import base64
    import hashlib
    import hmac
    import json

    def b64(x):
        return base64.urlsafe_b64encode(x).rstrip(b"=")

    client, _ = monde
    pem = b"-----BEGIN PUBLIC KEY-----\nMFkw\n-----END PUBLIC KEY-----"
    tete = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()) + b"." + b64(json.dumps(_eleve_claims()).encode())
    faux = (tete + b"." + b64(hmac.new(pem, tete, hashlib.sha256).digest())).decode()  # signé à la main
    assert _soumettre(client, A, faux).status_code == 401
    rs = (b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()) + b"." + tete.split(b".")[1] + b".c2ln").decode()
    assert _soumettre(client, A, rs).status_code == 401


def test_iat_dans_le_futur_refuse(monde):
    client, _ = monde
    r = _soumettre(client, A, _jeton_eleve(iat=_now() + 3600, exp=_now() + 7200))
    assert r.status_code == 401


def test_nbf_futur_refuse(monde):
    client, _ = monde
    assert _soumettre(client, A, _jeton_eleve(nbf=_now() + 3600)).status_code == 401


@pytest.mark.parametrize("modif", [{"exp": "demain"}, {"exp": None}, {"cid": "1"}, {"cid": True}, {"cid": 0},
                                   {"sub": ["eleve-a-001"]}, {"sub": ""}])
def test_types_de_claims_hostiles(monde, modif):
    client, _ = monde
    assert _soumettre(client, A, _jeton_eleve(**modif)).status_code == 401


def test_jeton_geant_refuse_sans_decodage(monde, monkeypatch):
    client, _ = monde
    appels = []
    orig = auth.jwt.get_unverified_header
    monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda t: appels.append(len(t)) or orig(t))
    assert _soumettre(client, A, "a" * 5000).status_code == 401
    assert appels == []  # refusé AVANT tout décodage (borne anti-DoS)


@pytest.mark.parametrize("entete", ["Bearer", "Bearer ", "Basic dXNlcjpwYXNz", "Token abc", "Bearer a b"])
def test_schemas_d_authentification_hostiles(monde, entete):
    client, _ = monde
    r = client.post("/api/v1/exercices/soumettre", headers={"Authorization": entete},
                    json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": A, "reponse": "3"})
    assert r.status_code == 401


def test_cle_de_compte_sans_typ_refusee_comme_eleve(monde):
    client, _ = monde
    c = {"sub": A, "exp": _now() + 600, "iat": _now(), "role": "eleve"}
    assert _soumettre(client, A, jwt.encode(c, "test-jwt-secret-not-for-prod-0123456789", algorithm="HS256")).status_code == 401


# --------------------------------------------------------------------------- #
# IDOR / confusion de rôles
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("porteur,cible,attendu", [
    ("pb", A, 403), ("pa", B, 403), ("ea", B, 403), ("seul", A, 403), ("pa", A, None), ("ea", A, None),
])
def test_lecture_croisee_dashboard_et_export(monde, porteur, cible, attendu):
    client, j = monde
    for url in (f"/api/v1/parents/dashboard/{cible}", f"/api/v1/rgpd/export/{cible}"):
        r = client.get(url, headers=_h(j[porteur]))
        if attendu is None:
            assert r.status_code in (200, 404), (url, r.status_code)  # autorisé (404 = aucune donnée)
        else:
            assert r.status_code == attendu and r.json()["detail"] == "acces_refuse"


def test_role_du_jeton_de_compte_ignore_au_profit_de_la_base(monde):
    """Jeton de compte FORGÉ (bonne clé) qui se dit « parent » pour le compte élève EA : la base
    dit « eleve » ⇒ effacement refusé."""
    client, _ = monde
    db = BillingSession()
    ea = crud_billing.get_compte_par_email(db, "ea@example.com")
    db.close()
    forge = jwt.encode({"sub": str(ea.id), "typ": "compte", "role": "parent", "iat": _now(), "exp": _now() + 600},
                       "test-jwt-secret-not-for-prod-0123456789", algorithm="HS256")
    assert client.delete(f"/api/v1/rgpd/effacer/{A}", headers=_h(forge)).status_code == 403


def test_inscription_admin_impossible(client, monkeypatch):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    r = client.post("/api/v1/comptes/inscription",
                    json={"email": "pirate@example.com", "mot_de_passe": "motdepasse-1", "role": "admin"})
    assert r.status_code == 201 and r.json()["compte"]["role"] == "parent"


def test_jeton_eleve_de_a_avec_cid_du_parent_de_b(monde):
    """Jeton élève forgé (clé connue) liant A au compte PB (non lié à A) : révoqué (S3-01)."""
    client, _ = monde
    db = BillingSession()
    pb = crud_billing.get_compte_par_email(db, "pb@example.com")
    db.close()
    assert _soumettre(client, A, _jeton_eleve(cid=pb.id)).status_code == 401


# --------------------------------------------------------------------------- #
# Rejeu / compte supprimé ou désactivé
# --------------------------------------------------------------------------- #
def test_rejeu_d_un_jeton_de_compte_apres_suppression(monde):
    client, j = monde
    db = BillingSession()
    compte = crud_billing.get_compte_par_email(db, "seul@example.com")
    db.delete(compte)
    db.commit()
    db.close()
    assert client.get("/api/v1/comptes/moi", headers=_h(j["seul"])).status_code == 401


def test_rejeu_jeton_eleve_expire_d_une_seconde(monde):
    client, _ = monde
    r = _soumettre(client, A, _jeton_eleve(iat=_now() - 7201, exp=_now() - 1))
    assert r.status_code == 401 and r.json()["detail"] == "jeton_expire"


def test_emission_jeton_eleve_pour_eleve_non_lie(monde):
    client, j = monde
    r = client.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": B}, headers=_h(j["pa"]))
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# CSRF / CORS / cookies
# --------------------------------------------------------------------------- #
def test_aucun_cookie_d_authentification(client, monkeypatch):
    """Authentification par en-tête uniquement : pas de cookie ⇒ pas de CSRF classique."""
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    r = client.post("/api/v1/comptes/inscription", json={"email": "c@example.com", "mot_de_passe": "motdepasse-1"})
    assert "set-cookie" not in r.headers
    r = client.post("/api/v1/comptes/connexion", json={"email": "c@example.com", "mot_de_passe": "motdepasse-1"})
    assert r.status_code == 200 and "set-cookie" not in r.headers


def test_jeton_dans_un_cookie_ignore(monde):
    client, j = monde
    client.cookies.set("Authorization", f"Bearer {j['A']}")
    try:
        assert _soumettre(client, A).status_code == 401
    finally:
        client.cookies.clear()


def test_cors_ferme_par_defaut(client):
    r = client.options("/api/v1/exercices/soumettre", headers={"Origin": "https://attaquant.invalid",
                                                               "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_origine_non_listee(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("CORS_ORIGINS", "https://app.mikamike.invalid")
    import main

    app = main.create_app()
    with TestClient(app) as c:
        r = c.options("/api/v1/exercices/soumettre", headers={"Origin": "https://attaquant.invalid",
                                                              "Access-Control-Request-Method": "POST"})
        assert r.headers.get("access-control-allow-origin") != "https://attaquant.invalid"
        ok = c.options("/api/v1/exercices/soumettre", headers={"Origin": "https://app.mikamike.invalid",
                                                               "Access-Control-Request-Method": "POST"})
        assert ok.headers.get("access-control-allow-origin") == "https://app.mikamike.invalid"


# --------------------------------------------------------------------------- #
# Traversée / Unicode
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("pid", ["еleve-a-001",  # « е » cyrillique (homoglyphe)
                                 "eleve‮100-a", "eleve​a", "ｅｌｅｖｅ", "eleve%2F..%2F", "..", "a/../b"])
def test_identifiants_unicode_et_traversee_refuses(client, pid):
    r = client.post("/api/v1/exercices/soumettre",
                    json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": pid, "reponse": "3"})
    assert r.status_code == 422


@pytest.mark.parametrize("chemin", ["/api/v1/rgpd/export/..%2F..%2Fetc%2Fpasswd",
                                    "/api/v1/mika/session/..%2F..%2F?student_id=a",
                                    "/api/v1/parents/dashboard/%2e%2e"])
def test_traversee_encodee(client, chemin):
    assert client.get(chemin).status_code in (404, 422)


def test_reponse_avec_caracteres_de_controle(client):
    r = client.post("/api/v1/exercices/soumettre",
                    json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "e1", "reponse": "3\u0000‮﻿"})
    assert r.status_code in (200, 422)  # jamais 500


# --------------------------------------------------------------------------- #
# Fixation de séance (S3-13) : une séance d'autrui n'est jamais reprise ni lue
# --------------------------------------------------------------------------- #
def test_fixation_de_seance_impossible_en_enforce(monde):
    """D15 : un identifiant choisi par le client ne crée plus de séance ; on ne peut donc plus
    « réserver » l'identifiant prévisible d'autrui."""
    client, j = monde
    for route, corps in (("heartbeat", {}), ("reconnect", {}), ("save-state", {"state_data": {"piege": 1}})):
        r = client.post(f"/api/v1/session/{route}", headers=_h(j["B"]),
                        json={"session_id": "partagee", "user_id": B, **corps})
        assert (r.status_code, r.json()["detail"]) == (404, "session_inconnue"), route
    assert client.get("/api/v1/session/stream?session_id=default_session", headers=_h(j["A"])).status_code == 404


def test_seance_generee_par_le_serveur_sans_prise_de_controle(monde):
    client, j = monde
    ids = set()
    for _ in range(20):
        r = client.post("/api/v1/session/nouvelle", json={"user_id": B}, headers=_h(j["B"]))
        assert r.status_code == 201
        ids.add(r.json()["session_id"])
    assert len(ids) == 20 and all(len(s) == 49 and s[0] == "s" and int(s[1:], 16) >= 0 for s in ids)
    sb = ids.pop()
    assert client.post("/api/v1/session/save-state", headers=_h(j["B"]),
                       json={"session_id": sb, "user_id": B, "state_data": {"piege": 1}}).status_code == 200
    for route, corps in (("heartbeat", {}), ("reconnect", {}), ("save-state", {"state_data": {"x": 1}})):
        r = client.post(f"/api/v1/session/{route}", headers=_h(j["A"]),
                        json={"session_id": sb, "user_id": A, **corps})
        assert r.status_code == 403, route
        assert "piege" not in r.text
    r = client.post("/api/v1/session/reconnect", headers=_h(j["B"]), json={"session_id": sb, "user_id": B})
    assert r.json()["session_state"] == {"piege": 1}
    # Création pour un autre élève refusée.
    assert client.post("/api/v1/session/nouvelle", json={"user_id": A}, headers=_h(j["B"])).status_code == 403


# --------------------------------------------------------------------------- #
# Jetons élève : durée de vie bornée même si TTL configuré au maximum
# --------------------------------------------------------------------------- #
def test_ttl_maximal_borne(monkeypatch):
    monkeypatch.setenv("MIKA_ELEVE_TOKEN_TTL_MIN", str(auth.TTL_ELEVE_MAX_MIN))
    tok, ttl = auth.emettre_jeton_eleve(A, compte_id=1)
    c = jwt.decode(tok, options={"verify_signature": False})
    assert ttl == 720 * 60 and c["exp"] - c["iat"] == ttl
    assert _dt.timedelta(seconds=ttl) <= _dt.timedelta(hours=12)
