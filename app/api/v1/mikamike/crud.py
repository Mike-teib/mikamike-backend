"""
crud.py — Accès données MikaMike (ORM synchrone).

Réécriture cohérente de `crud_student.py` (qui était en psycopg async,
incompatible avec la session sync). Toutes les fonctions travaillent sur des
identifiants HMAC ; aucune PII n'entre ni ne sort d'ici.
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.mikamike.store import EtatCompetence, TentativeExercice


def enregistrer_tentative(
    db: Session,
    *,
    eleve_hmac: str,
    exercice_id: str,
    matiere: str,
    niveau: str,
    competence: str,
    est_correct: bool,
    avec_aide: bool = False,
) -> TentativeExercice:
    evt = TentativeExercice(
        eleve_hmac=eleve_hmac,
        exercice_id=exercice_id,
        matiere=matiere,
        niveau=niveau,
        competence=competence,
        est_correct=est_correct,
        avec_aide=avec_aide,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def compter_succes_consecutifs(
    db: Session, eleve_hmac: str, competence: str, *, autonomes_seulement: bool = False
) -> int:
    """
    Nombre de tentatives correctes consécutives (les plus récentes).

    `autonomes_seulement=True` : un succès obtenu AVEC aide interrompt la série
    (règle LE-06 : l'aide ne doit jamais contribuer à atteindre MAITRISE).
    """
    lignes = db.execute(
        select(TentativeExercice)
        .where(
            TentativeExercice.eleve_hmac == eleve_hmac,
            TentativeExercice.competence == competence,
        )
        .order_by(TentativeExercice.ts.desc())
    ).scalars().all()
    n = 0
    for t in lignes:
        if t.est_correct and not (autonomes_seulement and t.avec_aide):
            n += 1
        else:
            break
    return n


def upsert_etat(
    db: Session, eleve_hmac: str, competence: str, etat: str
) -> EtatCompetence:
    obj = db.get(EtatCompetence, (eleve_hmac, competence))
    if obj is None:
        obj = EtatCompetence(
            eleve_hmac=eleve_hmac, competence=competence, etat=etat
        )
        db.add(obj)
    else:
        obj.etat = etat
    db.commit()
    return obj


def get_etats(db: Session, eleve_hmac: str) -> Dict[str, str]:
    lignes = db.execute(
        select(EtatCompetence).where(EtatCompetence.eleve_hmac == eleve_hmac)
    ).scalars().all()
    return {e.competence: e.etat for e in lignes}


def get_tentatives(db: Session, eleve_hmac: str) -> List[TentativeExercice]:
    return db.execute(
        select(TentativeExercice)
        .where(TentativeExercice.eleve_hmac == eleve_hmac)
        .order_by(TentativeExercice.ts.desc())
    ).scalars().all()


def agreger_dashboard(db: Session, eleve_hmac: str) -> dict:
    """Statistiques pédagogiques agrégées, SANS aucune PII."""
    tentatives = get_tentatives(db, eleve_hmac)
    total = len(tentatives)
    reussis = sum(1 for t in tentatives if t.est_correct)
    etats = get_etats(db, eleve_hmac)

    par_competence: Dict[str, dict] = {}
    for t in tentatives:
        c = par_competence.setdefault(
            t.competence, {"tentatives": 0, "reussites": 0, "etat": etats.get(t.competence, "INCONNU")}
        )
        c["tentatives"] += 1
        if t.est_correct:
            c["reussites"] += 1

    return {
        "exercices_tentes": total,
        "exercices_reussis": reussis,
        "taux_reussite": round(reussis / total, 3) if total else 0.0,
        "competences": par_competence,
        "niveau_actuel": _niveau_courant(par_competence),
    }


def _niveau_courant(par_competence: Dict[str, dict]) -> str:
    """Résumé lisible de l'avancement (aucune donnée nominative)."""
    if not par_competence:
        return "demarrage"
    solides = sum(
        1 for c in par_competence.values() if c["etat"] in ("ACQUIS_AUTONOME", "MAITRISE")
    )
    return f"{solides}/{len(par_competence)} competences consolidees"
