"""Serveur E2E jetable pour tester le vrai frontend contre le vrai backend MikaMike.

Données fictives uniquement. Ne doit jamais être utilisé en production.
"""
from __future__ import annotations

import os
import tempfile

_tmp = tempfile.gettempdir()
os.environ["MIKA_DB_URL"] = "sqlite:///" + os.path.join(_tmp, "mika_front_e2e.db")
os.environ["BILLING_DB_URL"] = "sqlite:///" + os.path.join(_tmp, "billing_front_e2e.db")
os.environ["MIKA_JWT_SECRET"] = "e2e-jwt-secret-not-for-prod-0123456789"
os.environ["MIKA_PSEUDO_SECRET"] = "e2e-pseudo-secret-not-for-prod-0123456789"
os.environ["MIKA_DB_INIT"] = "none"
os.environ["MIKA_AUTH_MODE"] = "enforce"
os.environ["MIKA_RATE_LIMIT"] = "on"
os.environ["MIKA_ENV"] = "test"
os.environ["MIKA_EMAIL_TRANSPORT"] = "faux"
os.environ["MIKA_EMAIL_VERIFICATION"] = "off"
os.environ["CORS_ORIGINS"] = "http://127.0.0.1:4173"

from app.db.registre import creer_tables_pour_tests

creer_tables_pour_tests(reinitialiser=True)

from app.api.v1.tutorat import contenu
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.exercices import Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.pedagogie.tuteur import PlanGuidage
from paiement_comptes import crud_billing, liens
from paiement_comptes.database import SessionLocal

STUDENT = "Test26Mika"
EMAIL = "parent.e2e@example.com"
PASSWORD = "motdepasse-e2e-0001"

db = SessionLocal()
try:
    compte = crud_billing.creer_compte(
        db,
        email=EMAIL,
        mot_de_passe=PASSWORD,
        prenom="Parent E2E",
        role="parent",
    )
    compte.email_verifie = True
    db.commit()
    db.refresh(compte)
    liens.lier(db, compte.id, hmac_eleve(STUDENT), "parent")
finally:
    db.close()

ref = referentiel_fictif()
notion = ref.index().notions["notion:fictif:fractions-decimales"]
exercise = Exercice(
    id="exo-maths-algebre-1",
    notion_id=notion.id,
    matiere=notion.matiere,
    niveau=notion.niveau,
    programme_id=notion.programme_id,
    chapitre_id=notion.chapitre_id,
    difficulte=2,
    objectif_pedagogique="[E2E] résoudre une équation simple",
    prerequis=(),
    enonce="Résous : x + 4 = 7",
    reponse_attendue="3",
    type_verification="maths_symbolique",
    indices=("Quel nombre faut-il retirer des deux côtés ?",),
    erreurs_frequentes={"11": "addition au lieu de soustraction"},
    source_sha256_extrait=notion.preuve.sha256_extrait,
)
plan = PlanGuidage(
    questions_intermediaires=("Que faut-il faire pour isoler x ?",),
    methodes_alternatives=("Imagine une balance : retire 4 des deux côtés.",),
    question_comprehension="Si x + 2 = 5, combien vaut x ?",
    reponse_comprehension="3",
    correction_commentee="On retire 4 des deux côtés : x = 3.",
    exercice_consolidation_id="exo-maths-algebre-1",
)
contenu.definir_catalogue(
    contenu.CatalogueTutorat(ref, [exercise], {exercise.id: plan}, autoriser_fictif=True)
)

from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
