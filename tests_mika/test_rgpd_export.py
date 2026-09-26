"""
Tests d'intégration et unitaires du module RGPD (Export & Droit à l'oubli).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import MikaBase, engine, get_db
from app.api.v1.rgpd.router import rgpd_router, _hmac

# Application d'essai dédiée aux tests RGPD
app_rgpd_test = FastAPI()
app_rgpd_test.include_router(rgpd_router, prefix="/api/v1")

client = TestClient(app_rgpd_test)


@pytest.fixture(autouse=True)
def init_tables():
    """Garantit que les tables SQLite sont prêtes avant chaque test."""
    MikaBase.metadata.create_all(bind=engine)
    yield


def test_rgpd_export_et_effacement_complet():
    """
    Test complet du cycle RGPD :
    1. Création de tentatives et d'états pour un élève
    2. Export des données et vérification de l'absence de PII
    3. Effacement RGPD (Droit à l'oubli) et vérification de la purge en DB
    4. Vérification du retour 404 après effacement
    """
    pseudo_id = "eleve_rgpd_test_999"
    eleve_hmac = _hmac(pseudo_id)

    # Obtenir une session DB
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        # 1. Pré-remplissage de données
        crud.enregistrer_tentative(
            db,
            eleve_hmac=eleve_hmac,
            exercice_id="exo-maths-algebre-1",
            matiere="maths",
            niveau="5e",
            competence="equations_1er_degre",
            est_correct=True,
            avec_aide=False
        )

        crud.upsert_etat(
            db,
            eleve_hmac=eleve_hmac,
            competence="equations_1er_degre",
            etat="ACQUIS_AUTONOME"
        )

        # 2. Test Export RGPD (GET /api/v1/rgpd/export/{student_pseudo_id})
        res_export = client.get(f"/api/v1/rgpd/export/{pseudo_id}")
        assert res_export.status_code == 200
        data_export = res_export.json()

        assert data_export["student_pseudo_id"] == pseudo_id
        assert data_export["total_tentatives"] == 1
        assert data_export["total_competences_suivies"] == 1
        assert data_export["etats_maitrise"]["equations_1er_degre"] == "ACQUIS_AUTONOME"
        assert len(data_export["historique_tentatives"]) == 1

        # Vérification stricte : Zéro PII nominative dans l'export
        for cle_interdite in ["nom", "prenom", "email", "telephone", "adresse", "ip"]:
            assert cle_interdite not in data_export

        # 3. Test Effacement RGPD (DELETE /api/v1/rgpd/effacer/{student_pseudo_id})
        res_effacement = client.delete(f"/api/v1/rgpd/effacer/{pseudo_id}")
        assert res_effacement.status_code == 200
        data_effacement = res_effacement.json()

        assert data_effacement["statut"] == "effacement_effectue"
        assert data_effacement["tentatives_supprimees"] == 1
        assert data_effacement["etats_supprimes"] == 1

        # 4. Vérification après purge : l'export doit renvoyer 404 (aucune donnée)
        res_apres_purge = client.get(f"/api/v1/rgpd/export/{pseudo_id}")
        assert res_apres_purge.status_code == 404

    finally:
        db.close()


def test_rgpd_export_eleve_inconnu_renvoie_404():
    """Vérifie qu'une demande d'export pour un élève sans historique renvoie 404."""
    res = client.get("/api/v1/rgpd/export/eleve_inconnu_000")
    assert res.status_code == 404
    assert res.json()["detail"] == "aucune_donnee_trouvee_pour_cet_identifiant"


def test_rgpd_effacement_eleve_inconnu_renvoie_404():
    """Vérifie qu'une demande d'effacement pour un élève sans données renvoie 404."""
    res = client.delete("/api/v1/rgpd/effacer/eleve_inconnu_000")
    assert res.status_code == 404
    assert res.json()["detail"] == "aucune_donnee_a_effacer"
