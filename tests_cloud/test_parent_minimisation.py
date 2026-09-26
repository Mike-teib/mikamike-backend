"""
Tableau de bord parent (lot 19) : minimisation. Le parent voit des AGRÉGATS par compétence
(tentatives, réussites, état), jamais les réponses de l'élève, ses horodatages, ni l'historique
du tuteur. Le schéma de réponse est FERMÉ : un champ ajouté par erreur ⇒ échec (fail-closed).
"""

from app.api.v1.mikamike import crud

CLES = {"exercices_tentes", "exercices_reussis", "taux_reussite", "competences", "niveau_actuel"}


def _soumettre(client, eleve, reps):
    for rep in reps:
        client.post("/api/v1/exercices/soumettre",
                    json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": eleve, "reponse": rep})


def test_dashboard_ne_contient_que_des_agregats(client):
    _soumettre(client, "mini-1", ["x=3", "réponse-très-personnelle-42", "3"])
    r = client.get("/api/v1/parents/dashboard/mini-1")
    assert r.status_code == 200
    corps = r.json()
    assert set(corps) == {"pseudo_id", "statistiques_pedagogiques"}
    stats = corps["statistiques_pedagogiques"]
    assert set(stats) == CLES
    for c in stats["competences"].values():
        assert set(c) == {"tentatives", "reussites", "etat"}
    assert "réponse-très-personnelle-42" not in r.text   # jamais les réponses saisies


def test_champ_ajoute_par_erreur_ne_fuit_pas(client, monkeypatch):
    orig = crud.agreger_dashboard

    def fuite(db, eleve_hmac):
        s = orig(db, eleve_hmac)
        s["derniere_reponse"] = "SECRET-ELEVE-XYZ"
        return s

    monkeypatch.setattr(crud, "agreger_dashboard", fuite)
    r = client.get("/api/v1/parents/dashboard/mini-2")
    assert r.status_code == 500 and "SECRET-ELEVE-XYZ" not in r.text


def test_champ_imbrique_ajoute_ne_fuit_pas(client, monkeypatch):
    orig = crud.agreger_dashboard

    def fuite(db, eleve_hmac):
        s = orig(db, eleve_hmac)
        s["competences"]["x"] = {"tentatives": 1, "reussites": 0, "etat": "FRAGILE", "reponses": ["SECRET-2"]}
        return s

    monkeypatch.setattr(crud, "agreger_dashboard", fuite)
    r = client.get("/api/v1/parents/dashboard/mini-3")
    assert r.status_code == 500 and "SECRET-2" not in r.text
