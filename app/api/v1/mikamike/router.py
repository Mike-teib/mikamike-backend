"""
router.py — Endpoints réels MikaMike (remplacent les mocks du Drive).

Trois routeurs, agrégés dans `mika_router` (à monter sous le préfixe /api,
cf. A_CABLER_MIKA_DANS_MAIN.md) :
  POST /exercices/soumettre        -> évaluation + remédiation via learning_engine
  GET  /parents/dashboard/{id}     -> stats agrégées SANS PII (pseudonymisation HMAC)
  GET  /parcours/prochaine-etape   -> prochaine marche réelle de l'escalier

Aucune PII ne circule : l'identifiant reçu (déjà anonyme) est re-haché en HMAC
pour l'indexation interne. Le dashboard ne renvoie jamais nom/prénom/email.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.mikamike import catalogue, crud
from app.api.v1.mikamike.learning_engine import (
    ETATS_SOLIDES,
    EtatMaitrise,
    LearningEngine,
    pseudonymiser_code,
)
from app.api.v1.mikamike.schemas import (
    DashboardOut,
    ProchaineEtapeOut,
    Remediation,
    SoumissionIn,
    SoumissionOut,
)
from app.api.v1.mikamike.store import get_db

from app.core.security_config import get_pseudo_secret as _get_pseudo_secret

_PSEUDO_SECRET = _get_pseudo_secret()


def _hmac(student_pseudo_id: str) -> str:
    """HMAC-SHA256 tronqué de l'identifiant (déjà anonyme) -> clé interne."""
    return pseudonymiser_code(student_pseudo_id, _PSEUDO_SECRET)


def _engine_charge(db: Session, eleve_hmac: str) -> LearningEngine:
    """Instancie le moteur et précharge les états connus de l'élève depuis la DB."""
    eng = LearningEngine()
    for competence, etat in crud.get_etats(db, eleve_hmac).items():
        try:
            eng.etats_eleves[(eleve_hmac, competence)] = EtatMaitrise(etat)
        except ValueError:
            continue
    return eng


# --------------------------------------------------------------------------- #
# Exercices
# --------------------------------------------------------------------------- #
exercices_router = APIRouter(prefix="/exercices", tags=["mika-exercices"])


@exercices_router.post("/soumettre", response_model=SoumissionOut)
def soumettre_exercice(payload: SoumissionIn, db: Session = Depends(get_db)):
    meta = catalogue.get_exercice(payload.exercice_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="exercice_inconnu")

    eleve_hmac = _hmac(payload.student_pseudo_id)
    competence = meta["competence"]
    correct = catalogue.est_correct(payload.exercice_id, payload.reponse)

    # 1) Journalisation de la tentative (pseudonymisée)
    crud.enregistrer_tentative(
        db,
        eleve_hmac=eleve_hmac,
        exercice_id=payload.exercice_id,
        matiere=meta["matiere"],
        niveau=meta["niveau"],
        competence=competence,
        est_correct=correct,
        avec_aide=payload.avec_aide,
    )

    # 2) Transition d'état via le moteur (préchargé avec l'historique réel)
    eng = _engine_charge(db, eleve_hmac)
    succes_consec = crud.compter_succes_consecutifs(db, eleve_hmac, competence)
    nouvel_etat = eng.evaluer_transition(
        eleve_hmac,
        competence,
        est_correct=correct,
        avec_aide=payload.avec_aide,
        nombre_succes_consecutifs=succes_consec,
    )
    crud.upsert_etat(db, eleve_hmac, competence, nouvel_etat.value)

    if correct:
        return SoumissionOut(
            est_correct=True,
            etat_maitrise=nouvel_etat.value,
            message="Bravo ! Tu montes une marche de l'escalier.",
            remediation=None,
        )

    # 3) Erreur -> diagnostic de la marche manquante (remontée des prérequis)
    lacune, _chaine = eng.diagnostiquer_marche_manquante(eleve_hmac, competence)
    competence_cible_remed = lacune or competence
    exo_prerequis = (
        catalogue.exercice_pour_competence(competence_cible_remed)
        or meta["exercice_prerequis"]
    )
    return SoumissionOut(
        est_correct=False,
        etat_maitrise=nouvel_etat.value,
        message="Ce n'est pas encore ça — on reprend la marche d'en dessous.",
        remediation=Remediation(
            explication_concept=meta["explication_concept"],
            exercice_prerequis=exo_prerequis,
            competence_lacune=competence_cible_remed,
        ),
    )


# --------------------------------------------------------------------------- #
# Parents (dashboard sans PII)
# --------------------------------------------------------------------------- #
parents_router = APIRouter(prefix="/parents", tags=["mika-parents"])


@parents_router.get("/dashboard/{student_pseudo_id}", response_model=DashboardOut)
def dashboard_parent(student_pseudo_id: str, db: Session = Depends(get_db)):
    eleve_hmac = _hmac(student_pseudo_id)
    stats = crud.agreger_dashboard(db, eleve_hmac)
    # On renvoie l'identifiant anonyme fourni (jamais de nom/prénom/email).
    return DashboardOut(pseudo_id=student_pseudo_id, statistiques_pedagogiques=stats)


# --------------------------------------------------------------------------- #
# Parcours (prochaine marche réelle)
# --------------------------------------------------------------------------- #
parcours_router = APIRouter(prefix="/parcours", tags=["mika-parcours"])


from app.api.v1.parcours.curriculum_dataset import obtenir_graphe_competences, generer_parcours_personnalise

@parcours_router.get("/prochaine-etape", response_model=ProchaineEtapeOut)
def prochaine_etape(student_pseudo_id: str, niveau: str = "5e", db: Session = Depends(get_db)):
    eleve_hmac = _hmac(student_pseudo_id)
    etats = crud.get_etats(db, eleve_hmac)

    nodes = obtenir_graphe_competences(niveau, "maths")
    personalized_path = generer_parcours_personnalise(nodes, etats)

    if personalized_path:
        cible = personalized_path[0]["notion_id"]
    else:
        # Fallback if somehow empty
        cible = nodes[0].notion_id if nodes else catalogue.toutes_les_competences()[0]

    exo_id = catalogue.exercice_pour_competence(cible)
    meta = catalogue.get_exercice(exo_id)
    return ProchaineEtapeOut(
        student_pseudo_id=student_pseudo_id,
        exercice_id=exo_id,
        niveau=meta["niveau"],
        notion_id=cible,
        competence=cible,
        consigne=meta["enonce"],
    )


# --------------------------------------------------------------------------- #
# Agrégat monté sous /api (voir A_CABLER_MIKA_DANS_MAIN.md)
# --------------------------------------------------------------------------- #
mika_router = APIRouter()
mika_router.include_router(exercices_router)
mika_router.include_router(parents_router)
mika_router.include_router(parcours_router)
