"""
retention.py — Durées de conservation et purge des données (lot 20, session 4 — RGPD mineurs).

Politique PAR DÉFAUT (proposition conservatrice, à valider par le DPO — DECISION_REQUIRED) :

  donnée                               base     critère                           défaut
  -----------------------------------  -------  --------------------------------  --------
  mika_session_states (mémoire séance) mika     inactive depuis                   30 j
  mika_tutorat_requetes (idempotence)  mika     créée depuis                      30 j
  mika_tutorat_sessions (échanges)     mika     dernière activité depuis          180 j
  verifications_email (jetons)         billing  expirés ou utilisés depuis        7 j
  invitations_lien (codes)             billing  expirées non utilisées            0 j
  mika_tentatives / mika_etats         mika     NON purgées automatiquement : historique
                                                pédagogique conservé tant que le compte
                                                existe ; effacement par le droit à l'oubli.

Surcharge : MIKA_RETENTION_<CLE>_JOURS (entier 1..3650 ; hors bornes ⇒ erreur au démarrage de la
purge, jamais une purge silencieusement plus large). La purge est un OUTIL OPÉRATEUR
(`tools/purge_retention.py`), en simulation par défaut ; aucune tâche automatique en production
tant que la politique n'est pas validée.
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import Dict, Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

DEFAUTS: Dict[str, int] = {
    "SESSIONS": 30,
    "TUTORAT_REQUETES": 30,
    "TUTORAT_SESSIONS": 180,
    "VERIFICATIONS_EMAIL": 7,
}
BORNES = (1, 3650)


class PolitiqueInvalide(ValueError):
    pass


def duree_jours(cle: str) -> int:
    if cle not in DEFAUTS:
        raise PolitiqueInvalide(f"cle_inconnue:{cle}")
    brut = os.environ.get(f"MIKA_RETENTION_{cle}_JOURS", "").strip()
    if not brut:
        return DEFAUTS[cle]
    if not brut.isdigit() or not (BORNES[0] <= int(brut) <= BORNES[1]):
        raise PolitiqueInvalide(f"duree_invalide:{cle}")
    return int(brut)


def politique() -> Dict[str, int]:
    return {cle: duree_jours(cle) for cle in DEFAUTS}


def _maintenant() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


def purger_mika(db: Session, *, appliquer: bool = False, maintenant: Optional[_dt.datetime] = None) -> Dict[str, int]:
    """Renvoie {table: lignes concernées}. Simulation (comptage) si `appliquer` est faux."""
    from app.api.v1.session.session_manager import MikaSessionState
    from app.api.v1.tutorat.store import TutoratRequete, TutoratSession

    t = maintenant or _maintenant()
    p = politique()
    cibles = {
        "mika_session_states": (MikaSessionState,
                                MikaSessionState.last_activity_ts < t - _dt.timedelta(days=p["SESSIONS"])),
        "mika_tutorat_requetes": (TutoratRequete,
                                  TutoratRequete.cree_le < t - _dt.timedelta(days=p["TUTORAT_REQUETES"])),
        "mika_tutorat_sessions": (TutoratSession,
                                  TutoratSession.maj_le < t - _dt.timedelta(days=p["TUTORAT_SESSIONS"])),
    }
    return _executer(db, cibles, appliquer)


def purger_billing(db: Session, *, appliquer: bool = False, maintenant: Optional[_dt.datetime] = None) -> Dict[str, int]:
    from paiement_comptes.liens import InvitationLien
    from paiement_comptes.verification_email import VerificationEmail

    t = maintenant or _maintenant()
    limite = t - _dt.timedelta(days=duree_jours("VERIFICATIONS_EMAIL"))
    cibles = {
        "verifications_email": (VerificationEmail, or_(VerificationEmail.expire_le < limite,
                                                       VerificationEmail.utilise_le < limite)),
        # Même règle que liens.purger_invitations_expirees : les invitations UTILISÉES restent
        # (trace du rattachement, pseudo-id déjà effacé à l'acceptation).
        "invitations_lien": (InvitationLien, InvitationLien.utilise_le.is_(None) & (InvitationLien.expire_le <= t)),
    }
    return _executer(db, cibles, appliquer)


def _executer(db: Session, cibles, appliquer: bool) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for nom, (modele, condition) in cibles.items():
        if appliquer:
            out[nom] = db.execute(delete(modele).where(condition)).rowcount or 0
        else:
            out[nom] = db.execute(select(func.count()).select_from(modele).where(condition)).scalar_one()
    if appliquer:
        db.commit()
    return out
