"""
Suite de tests MikaMike — vraie logique (plus de mocks), sur l'app assemblée.

Couvre, pour chaque endpoint, le cas SUCCÈS et le cas ERREUR -> remédiation :
  - POST /api/v1/exercices/soumettre    (succès + erreur->remédiation + inconnu)
  - GET  /api/v1/parents/dashboard/{id}  (agrégation sans PII)
  - GET  /api/v1/parcours/prochaine-etape (prochaine marche réelle)
"""

PII_INTERDITE = ["nom", "prenom", "email", "telephone"]


# --------------------------------------------------------------------------- #
# Exercices
# --------------------------------------------------------------------------- #
def test_soumettre_erreur_declenche_remediation(client):
    payload = {
        "exercice_id": "exo-maths-algebre-1",
        "student_pseudo_id": "anon-eleve-999",
        "reponse": "x = 42",  # faux
    }
    r = client.post("/api/v1/exercices/soumettre", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["est_correct"] is False
    assert data["remediation"] is not None, "une remédiation doit être renvoyée sur erreur"
    remed = data["remediation"]
    assert "explication_concept" in remed and remed["explication_concept"]
    assert "exercice_prerequis" in remed and remed["exercice_prerequis"]
    # La remédiation cible un prérequis (escalier pédagogique).
    assert remed["exercice_prerequis"] != payload["exercice_id"]


def test_soumettre_succes_pas_de_remediation(client):
    payload = {
        "exercice_id": "exo-maths-algebre-1",
        "student_pseudo_id": "anon-eleve-777",
        "reponse": "x = 3",  # correct (normalisation espaces)
    }
    r = client.post("/api/v1/exercices/soumettre", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["est_correct"] is True
    assert data["remediation"] is None
    assert data["etat_maitrise"], "un état de maîtrise doit être renvoyé"


def test_soumettre_exercice_inconnu_404(client):
    payload = {
        "exercice_id": "exo-inexistant",
        "student_pseudo_id": "anon-eleve-1",
        "reponse": "42",
    }
    r = client.post("/api/v1/exercices/soumettre", json=payload)
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# Dashboard parent (RGPD : aucune PII)
# --------------------------------------------------------------------------- #
def test_dashboard_agrege_sans_pii(client):
    pseudo = "anon-eleve-999"
    # Une erreur puis un succès pour peupler l'agrégat.
    client.post(
        "/api/v1/exercices/soumettre",
        json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": pseudo, "reponse": "x = 42"},
    )
    client.post(
        "/api/v1/exercices/soumettre",
        json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": pseudo, "reponse": "x = 3"},
    )

    r = client.get(f"/api/v1/parents/dashboard/{pseudo}")
    assert r.status_code == 200, r.text
    data = r.json()

    for cle in PII_INTERDITE:
        assert cle not in data, f"la clé PII '{cle}' ne doit pas être exposée"
    assert data["pseudo_id"] == pseudo
    stats = data["statistiques_pedagogiques"]
    assert stats["exercices_tentes"] == 2
    assert stats["exercices_reussis"] == 1
    assert "competences" in stats


def test_dashboard_pseudonymisation_isole_les_eleves(client):
    client.post(
        "/api/v1/exercices/soumettre",
        json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "anon-A", "reponse": "x = 3"},
    )
    # Élève B n'a rien fait : dashboard vide, indépendant de A (séparation HMAC).
    r = client.get("/api/v1/parents/dashboard/anon-B")
    assert r.status_code == 200
    assert r.json()["statistiques_pedagogiques"]["exercices_tentes"] == 0


# --------------------------------------------------------------------------- #
# Parcours (prochaine marche réelle)
# --------------------------------------------------------------------------- #
def test_parcours_prochaine_etape_reelle(client):
    r = client.get("/api/v1/parcours/prochaine-etape", params={"student_id": "anon-eleve-999"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["exercice_id"], "un exercice réel doit être proposé"
    assert data["competence"], "la compétence visée doit être précisée"
    assert data["niveau"]
    assert data["consigne"]


def test_parcours_prochaine_etape_respecte_niveau_et_matiere(client):
    r = client.get(
        "/api/v1/parcours/prochaine-etape",
        params={"student_id": "anon-eleve-999", "level": "5e", "subject": "mathematiques"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["niveau"] == "5e"
    assert data["exercice_id"] == "exo:maths:5e:priorites-01"


def test_parcours_prochaine_etape_refuse_contenu_absent(client):
    r = client.get(
        "/api/v1/parcours/prochaine-etape",
        params={"student_id": "anon-eleve-999", "level": "5e", "subject": "physique-chimie"},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "contenu_indisponible"
