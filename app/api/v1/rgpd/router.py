"""
router.py — Module RGPD pour l'export et l'effacement des données élève.
========================================================================
Conformité RGPD / Droit d'accès et Droit à l'oubli.
Endpoints :
  GET    /export/{student_pseudo_id}   -> Exporte l'ensemble des données d'apprentissage (sans PII)
  DELETE /effacer/{student_pseudo_id}  -> Purge intégrale de TOUTES les tables indexées par l'élève

Toute table portant une colonne `eleve_hmac` DOIT figurer dans `TABLES_ELEVE` :
un test de non-régression échoue sinon (droit à l'oubli complet par construction).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.v1.memory.spaced_repetition import MemoryBase, TacheRappelMemoire
from app.api.v1.mikamike.store import EtatCompetence, TentativeExercice, engine, get_db
from app.api.v1.session.session_manager import MikaSessionState, SessionBase
from app.core.pseudonymisation import hmac_eleve as _hmac
from app.core.validation import ID_PATTERN

# Registre exhaustif des tables contenant des données d'un élève.
TABLES_ELEVE = (TentativeExercice, EtatCompetence, TacheRappelMemoire, MikaSessionState)

# Les tables mémoire/session sont créées paresseusement par leurs routeurs :
# on garantit leur existence pour que l'export/effacement ne rate jamais rien.
MemoryBase.metadata.create_all(bind=engine)
SessionBase.metadata.create_all(bind=engine)


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


PseudoPath = Path(min_length=1, max_length=128, pattern=ID_PATTERN)

rgpd_router = APIRouter(prefix="/rgpd", tags=["rgpd"])


@rgpd_router.get("/export/{student_pseudo_id}")
def exporter_donnees_eleve(
    student_pseudo_id: str = PseudoPath,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Droit d'accès RGPD : Exporte l'intégralité des données d'apprentissage associées
    à un identifiant pseudonymisé, SANS aucune PII (donnée nominative).
    """
    eleve_hmac = _hmac(student_pseudo_id)

    tentatives = db.execute(
        select(TentativeExercice)
        .where(TentativeExercice.eleve_hmac == eleve_hmac)
        .order_by(TentativeExercice.ts.asc())
    ).scalars().all()
    etats = db.execute(
        select(EtatCompetence).where(EtatCompetence.eleve_hmac == eleve_hmac)
    ).scalars().all()
    rappels = db.execute(
        select(TacheRappelMemoire).where(TacheRappelMemoire.eleve_hmac == eleve_hmac)
    ).scalars().all()
    sessions = db.execute(
        select(MikaSessionState).where(MikaSessionState.eleve_hmac == eleve_hmac)
    ).scalars().all()

    if not (tentatives or etats or rappels or sessions):
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
            "date_heure": _iso(t.ts),
        }
        for t in tentatives
    ]
    export_etats = {e.competence: e.etat for e in etats}
    export_rappels: List[Dict[str, Any]] = [
        {
            "notion_id": r.notion_id,
            "statut_fragilite": r.statut_fragilite,
            "repetition_count": r.repetition_count,
            "intervalle_jours": r.intervalle_jours,
            "prochain_rappel_date": _iso(r.prochain_rappel_date),
        }
        for r in rappels
    ]
    export_sessions: List[Dict[str, Any]] = []
    for s in sessions:
        try:
            etat = json.loads(s.state_json or "{}")
        except ValueError:
            etat = {"_brut_illisible": True}
        export_sessions.append({
            "session_id": s.session_id,
            "is_active": s.is_active,
            "created_at": _iso(s.created_at),
            "last_activity_ts": _iso(s.last_activity_ts),
            "etat_seance": etat,
        })

    return {
        "contexte_rgpd": "Export complet des données d'apprentissage",
        "student_pseudo_id": student_pseudo_id,
        "anonymisation": "HMAC-SHA256 (Aucune PII stockée)",
        "total_tentatives": len(export_tentatives),
        "total_competences_suivies": len(export_etats),
        "etats_maitrise": export_etats,
        "historique_tentatives": export_tentatives,
        "rappels_memoire": export_rappels,
        "sessions": export_sessions,
    }


@rgpd_router.delete("/effacer/{student_pseudo_id}")
def effacer_donnees_eleve(
    student_pseudo_id: str = PseudoPath,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Droit à l'oubli RGPD : Efface définitivement toutes les données d'apprentissage
    associées à un identifiant élève pseudonymisé, dans TOUTES les tables élève.
    """
    eleve_hmac = _hmac(student_pseudo_id)

    compte_par_table: Dict[str, int] = {}
    for modele in TABLES_ELEVE:
        n = db.execute(
            delete(modele).where(modele.eleve_hmac == eleve_hmac)
        ).rowcount or 0
        compte_par_table[modele.__tablename__] = n
    db.commit()

    if not any(compte_par_table.values()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="aucune_donnee_a_effacer"
        )

    return {
        "statut": "effacement_effectue",
        "message": "Ensemble des données d'apprentissage purgé avec succès (Droit à l'oubli).",
        "student_pseudo_id": student_pseudo_id,
        "tentatives_supprimees": compte_par_table[TentativeExercice.__tablename__],
        "etats_supprimes": compte_par_table[EtatCompetence.__tablename__],
        "rappels_memoire_supprimes": compte_par_table[TacheRappelMemoire.__tablename__],
        "sessions_supprimees": compte_par_table[MikaSessionState.__tablename__],
    }
