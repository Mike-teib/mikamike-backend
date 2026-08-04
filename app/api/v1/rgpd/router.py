"""
router.py — Module RGPD pour l'export et l'effacement des données élève.
========================================================================
Conformité RGPD / Droit d'accès et Droit à l'oubli.
Endpoints :
  GET    /export/{student_pseudo_id}   -> Exporte l'ensemble des données d'apprentissage (sans PII)
  DELETE /effacer/{student_pseudo_id}  -> Purge intégrale des tentatives et états d'une clé pseudonymisée
"""

from __future__ import annotations

import os
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.api.v1.mikamike.learning_engine import pseudonymiser_code
from app.api.v1.mikamike.store import EtatCompetence, TentativeExercice, get_db

_PSEUDO_SECRET = os.getenv("MIKA_PSEUDO_SECRET", "mikamike_secret_key_2026")


def _hmac(student_pseudo_id: str) -> str:
    """Calcul du hash HMAC déterministe pour la clé interne."""
    return pseudonymiser_code(student_pseudo_id, _PSEUDO_SECRET)


rgpd_router = APIRouter(prefix="/rgpd", tags=["rgpd"])


@rgpd_router.get("/export/{student_pseudo_id}")
def exporter_donnees_eleve(
    student_pseudo_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Droit d'accès RGPD : Exporte l'intégralité des données d'apprentissage associées
    à un identifiant pseudonymisé, SANS aucune PII (donnée nominative).
    """
    eleve_hmac = _hmac(student_pseudo_id)

    # Récupération des tentatives
    tentatives = db.execute(
        select(TentativeExercice)
        .where(TentativeExercice.eleve_hmac == eleve_hmac)
        .order_by(TentativeExercice.ts.asc())
    ).scalars().all()

    # Récupération des états de maîtrise
    etats = db.execute(
        select(EtatCompetence)
        .where(EtatCompetence.eleve_hmac == eleve_hmac)
    ).scalars().all()

    if not tentatives and not etats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aucune_donnee_trouvee_pour_cet_identifiant"
        )

    export_tentatives = [
        {
            "id": t.id,
            "exercice_id": t.exercice_id,
            "matiere": t.matiere,
            "niveau": t.niveau,
            "competence": t.competence,
            "est_correct": t.est_correct,
            "avec_aide": t.avec_aide,
            "date_heure": t.ts.isoformat() if t.ts else None,
        }
        for t in tentatives
    ]

    export_etats = {e.competence: e.etat for e in etats}

    return {
        "contexte_rgpd": "Export complet des données d'apprentissage",
        "student_pseudo_id": student_pseudo_id,
        "anonymisation": "HMAC-SHA256 (Aucune PII stockée)",
        "total_tentatives": len(export_tentatives),
        "total_competences_suivies": len(export_etats),
        "etats_maitrise": export_etats,
        "historique_tentatives": export_tentatives,
    }


@rgpd_router.delete("/effacer/{student_pseudo_id}")
def effacer_donnees_eleve(
    student_pseudo_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Droit à l'oubli RGPD : Efface définitivement toutes les données d'apprentissage
    associées à un identifiant élève pseudonymisé sur la base de données.
    """
    eleve_hmac = _hmac(student_pseudo_id)

    # 1. Compter et supprimer les tentatives
    tentatives_a_supprimer = db.execute(
        select(TentativeExercice).where(TentativeExercice.eleve_hmac == eleve_hmac)
    ).scalars().all()
    count_tentatives = len(tentatives_a_supprimer)

    if count_tentatives > 0:
        db.execute(
            delete(TentativeExercice).where(TentativeExercice.eleve_hmac == eleve_hmac)
        )

    # 2. Compter et supprimer les états
    etats_a_supprimer = db.execute(
        select(EtatCompetence).where(EtatCompetence.eleve_hmac == eleve_hmac)
    ).scalars().all()
    count_etats = len(etats_a_supprimer)

    if count_etats > 0:
        db.execute(
            delete(EtatCompetence).where(EtatCompetence.eleve_hmac == eleve_hmac)
        )

    db.commit()

    if count_tentatives == 0 and count_etats == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aucune_donnee_a_effacer"
        )

    return {
        "statut": "effacement_effectue",
        "message": "Ensemble des données d'apprentissage purgé avec succès (Droit à l'oubli).",
        "student_pseudo_id": student_pseudo_id,
        "tentatives_supprimees": count_tentatives,
        "etats_supprimes": count_etats,
    }
