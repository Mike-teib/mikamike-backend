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

from app.api.v1.memory.spaced_repetition import TacheRappelMemoire
from app.api.v1.mikamike.store import EtatCompetence, TentativeExercice, get_db
from app.api.v1.session.session_manager import MikaSessionState
from app.api.v1.tutorat.store import TutoratRequete, TutoratSession
from app.core.pseudonymisation import hmac_eleve as _hmac
from app.core.auth import Action, Garde, garde as _garde
from app.core.validation import ID_PATTERN

# Registre exhaustif des tables contenant des données d'un élève.
TABLES_ELEVE = (TentativeExercice, EtatCompetence, TacheRappelMemoire, MikaSessionState,
                TutoratSession, TutoratRequete)


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


PseudoPath = Path(min_length=1, max_length=128, pattern=ID_PATTERN)

rgpd_router = APIRouter(prefix="/rgpd", tags=["rgpd"])


@rgpd_router.get("/export/{student_pseudo_id}")
def exporter_donnees_eleve(
    student_pseudo_id: str = PseudoPath,
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
) -> Dict[str, Any]:
    """
    Droit d'accès RGPD : Exporte l'intégralité des données d'apprentissage associées
    à un identifiant pseudonymisé, SANS aucune PII (donnée nominative).
    """
    g.exiger(student_pseudo_id, Action.LECTURE)
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

    tutorats = db.execute(
        select(TutoratSession).where(TutoratSession.eleve_hmac == eleve_hmac)
        .order_by(TutoratSession.cree_le.asc(), TutoratSession.id.asc())
    ).scalars().all()

    requetes = db.execute(
        select(TutoratRequete).where(TutoratRequete.eleve_hmac == eleve_hmac)
        .order_by(TutoratRequete.cree_le.asc(), TutoratRequete.tutorat_id.asc(),
                  TutoratRequete.requete_id.asc())
    ).scalars().all()
    # Liens compte ↔ élève (base billing) : relation et date, jamais l'e-mail du compte.
    from paiement_comptes.liens import LienCompteEleve

    liens = g.db.execute(
        select(LienCompteEleve).where(LienCompteEleve.eleve_hmac == eleve_hmac)
        .order_by(LienCompteEleve.id.asc())
    ).scalars().all()

    if not (tentatives or etats or rappels or sessions or tutorats or requetes):
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

    export_tutorats: List[Dict[str, Any]] = []
    for t in tutorats:
        try:
            etat_t = json.loads(t.etat_json or "{}")
        except ValueError:
            etat_t = {"_brut_illisible": True}
        export_tutorats.append({
            "tutorat_id": t.id,
            "exercice_id": t.exercice_id,
            "derniere_action": t.derniere_action,
            "termine": t.termine,
            "cree_le": _iso(t.cree_le),
            "maj_le": _iso(t.maj_le),
            "etat": etat_t,
        })

    # Journal d'idempotence du tuteur : il figure dans TABLES_ELEVE (effacé) mais n'était
    # pas exporté (revue session 3, S3-09 : droit d'accès incomplet).
    export_requetes: List[Dict[str, Any]] = []
    for q in requetes:
        try:
            rep = json.loads(q.reponse_json or "{}")
        except ValueError:
            rep = {"_brut_illisible": True}
        export_requetes.append({"tutorat_id": q.tutorat_id, "requete_id": q.requete_id,
                                "cree_le": _iso(q.cree_le), "reponse": rep})
    export_liens = [{"relation": lien.relation, "cree_le": _iso(lien.cree_le)} for lien in liens]
    # Invitations (D8) : ni code (seule son empreinte existe) ni compte, seulement l'historique.
    from paiement_comptes.liens import invitations_eleve

    export_invitations = [{"relation": i.relation, "emis_par": i.emis_par.split(":")[0], "cree_le": _iso(i.cree_le),
                           "expire_le": _iso(i.expire_le), "utilisee": i.utilise_le is not None}
                          for i in invitations_eleve(g.db, eleve_hmac)]

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
        "tutorats_mika": export_tutorats,
        "requetes_tutorat_mika": export_requetes,
        "liens_comptes": export_liens,
        "invitations_liens": export_invitations,
    }


# Table élève → clé de l'export (un test exige que TOUTE table de TABLES_ELEVE soit exportée).
CLES_EXPORT = {
    "mika_tentatives": "historique_tentatives",
    "mika_etats": "etats_maitrise",
    "mika_memory_schedules": "rappels_memoire",
    "mika_session_states": "sessions",
    "mika_tutorat_sessions": "tutorats_mika",
    "mika_tutorat_requetes": "requetes_tutorat_mika",
}


@rgpd_router.delete("/effacer/{student_pseudo_id}")
def effacer_donnees_eleve(
    student_pseudo_id: str = PseudoPath,
    db: Session = Depends(get_db),
    g: Garde = Depends(_garde),
) -> Dict[str, Any]:
    """
    Droit à l'oubli RGPD : Efface définitivement toutes les données d'apprentissage
    associées à un identifiant élève pseudonymisé, dans TOUTES les tables élève.
    """
    g.exiger(student_pseudo_id, Action.EFFACEMENT)
    eleve_hmac = _hmac(student_pseudo_id)

    compte_par_table: Dict[str, int] = {}
    for modele in TABLES_ELEVE:
        n = db.execute(
            delete(modele).where(modele.eleve_hmac == eleve_hmac)
        ).rowcount or 0
        compte_par_table[modele.__tablename__] = n
    db.commit()
    # Liens compte ↔ élève (base billing) : donnée relative à l'élève, effacée aussi.
    from paiement_comptes.liens import supprimer_invitations_eleve, supprimer_liens_eleve

    compte_par_table["liens_compte_eleve"] = supprimer_liens_eleve(g.db, eleve_hmac)
    compte_par_table["invitations_lien"] = supprimer_invitations_eleve(g.db, eleve_hmac)

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
        "tutorats_supprimes": compte_par_table[TutoratSession.__tablename__],
        "requetes_tutorat_supprimees": compte_par_table[TutoratRequete.__tablename__],
        "liens_compte_supprimes": compte_par_table["liens_compte_eleve"],
        "invitations_supprimees": compte_par_table["invitations_lien"],
    }
