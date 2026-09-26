"""
Suite de tests paiement/comptes — sur l'app assemblée.

Chemins publics :
  - POST /api/v1/comptes/inscription | /connexion, GET /moi (JWT via PyJWT)
  - GET  /api/v1/paiement/statut, POST /api/v1/paiement/checkout (garde Stripe)

Couvre succès + erreur par endpoint. Stripe n'est PAS requis (checkout est testé
sur sa garde de configuration, sans réseau).
"""

EMAIL = "parent@example.com"
MDP = "MotDePasse#2026"


def _inscrire(client, email=EMAIL, mdp=MDP):
    return client.post(
        "/api/v1/comptes/inscription",
        json={"email": email, "mot_de_passe": mdp, "prenom": "Test", "role": "parent"},
    )


# --------------------------------------------------------------------------- #
# Comptes
# --------------------------------------------------------------------------- #
def test_inscription_connexion_et_moi(client):
    r = _inscrire(client)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["token"]
    assert data["compte"]["email"] == EMAIL
    assert data["compte"]["statut_abonnement"] == "aucun"

    # Connexion
    r2 = client.post(
        "/api/v1/comptes/connexion", json={"email": EMAIL, "mot_de_passe": MDP}
    )
    assert r2.status_code == 200, r2.text
    token = r2.json()["token"]

    # /moi avec Bearer
    r3 = client.get(
        "/api/v1/comptes/moi", headers={"Authorization": f"Bearer {token}"}
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["email"] == EMAIL


def test_inscription_email_duplique_400(client):
    assert _inscrire(client).status_code == 201
    r = _inscrire(client)  # même email
    assert r.status_code == 400
    assert r.json()["detail"] == "email_deja_utilise"


def test_connexion_mauvais_mot_de_passe_401(client):
    _inscrire(client)
    r = client.post(
        "/api/v1/comptes/connexion",
        json={"email": EMAIL, "mot_de_passe": "MauvaisMdp#9999"},
    )
    assert r.status_code == 401


def test_moi_sans_token_401(client):
    r = client.get("/api/v1/comptes/moi")
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# Paiement (abonnement)
# --------------------------------------------------------------------------- #
def _token(client):
    return _inscrire(client).json()["token"]


def test_statut_abonnement_authentifie(client):
    token = _token(client)
    r = client.get(
        "/api/v1/paiement/statut", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["statut"] == "aucun"
    assert data["acces_autorise"] is False


def test_statut_sans_token_401(client):
    r = client.get("/api/v1/paiement/statut")
    assert r.status_code == 401


def test_checkout_garde_configuration(client):
    """Sans Stripe installé/configuré, checkout renvoie 500 explicite (pas de crash)."""
    token = _token(client)
    r = client.post(
        "/api/v1/paiement/checkout", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 500
    assert r.json()["detail"] in (
        "stripe_non_installe",
        "STRIPE_SECRET_KEY_absent",
        "STRIPE_PRICE_ID_absent",
    )
