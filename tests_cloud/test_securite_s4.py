"""
Sécurité (lot 21, session 4) : affectation de masse, écho des saisies dans les erreurs,
en-têtes HTTP, fuite d'erreurs internes. Données FICTIVES.
"""

import pytest

from main import app


def test_tous_les_corps_de_requete_refusent_les_champs_inconnus():
    s = app.openapi()
    comps = s["components"]["schemas"]
    ouverts = []
    for chemin, ops in s["paths"].items():
        for methode, op in ops.items():
            corps = op.get("requestBody")
            if not corps:
                continue
            ref = corps["content"]["application/json"]["schema"].get("$ref", "")
            nom = ref.rsplit("/", 1)[-1]
            if comps.get(nom, {}).get("additionalProperties") is not False:
                ouverts.append(f"{methode.upper()} {chemin} ({nom})")
    assert ouverts == []


@pytest.mark.parametrize("chemin,corps", [
    ("/api/v1/comptes/inscription", {"email": "x@example.com", "mot_de_passe": "motdepasse-1234", "actif": False}),
    ("/api/v1/comptes/inscription", {"email": "x@example.com", "mot_de_passe": "motdepasse-1234",
                                     "email_verifie": True}),
    ("/api/v1/comptes/connexion", {"email": "x@example.com", "mot_de_passe": "m", "role": "admin"}),
    ("/api/v1/exercices/soumettre", {"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "e1",
                                     "reponse": "3", "est_correct": True}),
    ("/api/v1/session/nouvelle", {"user_id": "e1", "session_id": "choisi-par-le-client"}),
])
def test_affectation_de_masse_refusee(client, chemin, corps):
    r = client.post(chemin, json=corps)
    assert r.status_code == 422
    assert any(e["type"] == "extra_forbidden" for e in r.json()["detail"])


def test_role_admin_jamais_auto_attribue(client):
    r = client.post("/api/v1/comptes/inscription",
                    json={"email": "adm@example.com", "mot_de_passe": "motdepasse-1234", "role": "admin"})
    assert r.status_code == 201 and r.json()["compte"]["role"] == "parent"


def test_erreur_422_sans_echo_de_la_saisie(client):
    secret = "court1!"
    r = client.post("/api/v1/comptes/inscription", json={"email": "e@example.com", "mot_de_passe": secret})
    assert r.status_code == 422 and secret not in r.text
    assert set(r.json()["detail"][0]) == {"type", "loc", "msg"}
    r = client.post("/api/v1/comptes/connexion", json={"email": "<script>alert(1)</script>", "mot_de_passe": "x"})
    assert r.status_code == 422 and "<script>" not in r.text


def test_entetes_de_securite(client):
    for r in (client.get("/healthz"), client.post("/api/v1/comptes/connexion", json={})):
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "no-referrer"
        assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert r.headers["cache-control"] == "no-store"
    doc = client.get("/api/v1/docs")
    assert doc.headers["x-content-type-options"] == "nosniff" and "content-security-policy" not in doc.headers


def test_erreur_interne_sans_details_et_avec_entetes(client, monkeypatch):
    from app.api.v1.mikamike import crud

    def boum(*a, **k):
        raise RuntimeError("chemin=/srv/secret mot_de_passe=xyz")

    monkeypatch.setattr(crud, "agreger_dashboard", boum)
    r = client.get("/api/v1/parents/dashboard/e1")
    assert r.status_code == 500 and r.json()["detail"] == "erreur_interne"
    assert "secret" not in r.text and "Traceback" not in r.text
    assert r.headers["x-content-type-options"] == "nosniff"
