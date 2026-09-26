"""
retention.py — Durées de conservation et purge des données (lot 20, session 4 — RGPD mineurs).

Politique PAR DÉFAUT (proposition conservatrice, à valider par le DPO — DECISION_REQUIRED) :

  donnée                               base     critère                           défaut
  -----------------------------------  -------  --------------------------------  --------
  mika_session_states (mémoire séance) mika     inactive depuis                   30 j
  mika_tutorat_requetes (idempotence)  mika     créée depuis                      30 j
  mika_tutorat_sessions (échanges)     mika     dernière activité depuis          180 j
  verifications_email (jetons)         billing  expirés ou utilisés depuis        7 j
  invitations_lien (codes)             billing  expirées non utilisées depuis     0 j
  mika_tentatives / mika_etats         mika     NON purgées automatiquement : historique
                                                pédagogique conservé tant que le compte
                                                existe ; effacement par le droit à l'oubli.

Surcharge : MIKA_RETENTION_<CLE>_JOURS (entier 1..3650 ; hors bornes ⇒ erreur au démarrage de la
purge, jamais une purge silencieusement plus large). La purge est un OUTIL OPÉRATEUR
(`tools/purge_retention.py`), en simulation par défaut ; aucune tâche automatique en production
tant que la politique n'est pas validée.

Session 5 — exploitation (DPO_RETENTION_DECISION.md) :
  - TOUTES les durées sont configurables (y compris les invitations : INVITATIONS_EXPIREES, 0..3650) ;
    aucune n'est figée juridiquement : les valeurs ci-dessus restent une PROPOSITION ;
  - rapport daté et scellé (`rapport`) exigé avant toute application, appliqué à la MÊME date
    de référence (ce qui a été présenté est exactement ce qui est supprimé, jamais davantage) ;
  - suppression par LOTS validés un à un : une interruption laisse une base cohérente et une
    nouvelle exécution reprend là où elle s'est arrêtée ; une seconde exécution ne supprime rien ;
  - métriques par table (lignes, lots, durée) et journal d'audit chaîné (tools/purge_retention.py).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import time
from typing import Dict, Optional

from sqlalchemy import delete, func, inspect, or_, select, tuple_
from sqlalchemy.orm import Session

DEFAUTS: Dict[str, int] = {
    "SESSIONS": 30,
    "TUTORAT_REQUETES": 30,
    "TUTORAT_SESSIONS": 180,
    "VERIFICATIONS_EMAIL": 7,
    "INVITATIONS_EXPIREES": 0,
}
BORNES = (1, 3650)
# Codes d'invitation expirés et jamais utilisés : aucune valeur d'usage, purge immédiate possible.
BORNES_PAR_CLE = {"INVITATIONS_EXPIREES": (0, 3650)}
LOT_DEFAUT = 500


class PolitiqueInvalide(ValueError):
    pass


def duree_jours(cle: str) -> int:
    if cle not in DEFAUTS:
        raise PolitiqueInvalide(f"cle_inconnue:{cle}")
    brut = os.environ.get(f"MIKA_RETENTION_{cle}_JOURS", "").strip()
    if not brut:
        return DEFAUTS[cle]
    bas, haut = BORNES_PAR_CLE.get(cle, BORNES)
    if not brut.isdigit() or not (bas <= int(brut) <= haut):
        raise PolitiqueInvalide(f"duree_invalide:{cle}")
    return int(brut)


def politique() -> Dict[str, int]:
    return {cle: duree_jours(cle) for cle in DEFAUTS}


def _maintenant() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


def purger_mika(db: Session, *, appliquer: bool = False, maintenant: Optional[_dt.datetime] = None,
                lot: int = LOT_DEFAUT, metriques: Optional[dict] = None) -> Dict[str, int]:
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
    return _executer(db, cibles, appliquer, lot, metriques)


def purger_billing(db: Session, *, appliquer: bool = False, maintenant: Optional[_dt.datetime] = None,
                   lot: int = LOT_DEFAUT, metriques: Optional[dict] = None) -> Dict[str, int]:
    from paiement_comptes.liens import InvitationLien
    from paiement_comptes.verification_email import VerificationEmail

    t = maintenant or _maintenant()
    limite = t - _dt.timedelta(days=duree_jours("VERIFICATIONS_EMAIL"))
    cibles = {
        "verifications_email": (VerificationEmail, or_(VerificationEmail.expire_le < limite,
                                                       VerificationEmail.utilise_le < limite)),
        # Même règle que liens.purger_invitations_expirees : les invitations UTILISÉES restent
        # (trace du rattachement, pseudo-id déjà effacé à l'acceptation).
        "invitations_lien": (InvitationLien, InvitationLien.utilise_le.is_(None) & (
            InvitationLien.expire_le <= t - _dt.timedelta(days=duree_jours("INVITATIONS_EXPIREES")))),
    }
    return _executer(db, cibles, appliquer, lot, metriques)


def _executer(db: Session, cibles, appliquer: bool, lot: int = LOT_DEFAUT,
              metriques: Optional[dict] = None) -> Dict[str, int]:
    """Simulation : COUNT. Application : lots de `lot` clés primaires, un COMMIT par lot
    (transactions courtes ; reprise après interruption ; idempotent)."""
    if not 1 <= int(lot) <= 100_000:
        raise PolitiqueInvalide("lot_invalide")
    out: Dict[str, int] = {}
    for nom, (modele, condition) in cibles.items():
        debut = time.monotonic()
        if not appliquer:
            out[nom] = db.execute(select(func.count()).select_from(modele).where(condition)).scalar_one()
            continue
        cles = list(inspect(modele).primary_key)
        total = lots = 0
        while True:
            ids = db.execute(select(*cles).where(condition).limit(lot)).all()
            if not ids:
                break
            if len(cles) == 1:
                cible = cles[0].in_([r[0] for r in ids])
            else:
                cible = tuple_(*cles).in_([tuple(r) for r in ids])
            total += db.execute(delete(modele).where(cible)).rowcount or 0
            db.commit()
            lots += 1
        out[nom] = total
        if metriques is not None:
            metriques[nom] = {"lignes": total, "lots": lots,
                              "duree_ms": round((time.monotonic() - debut) * 1000, 1)}
    return out


# --------------------------------------------------------------------------- #
# Rapport scellé (présenté avant toute application)
# --------------------------------------------------------------------------- #
FORMAT_RAPPORT = "mika-retention-rapport/1"
AGE_MAX_RAPPORT_H = 24


class RapportInvalide(ValueError):
    pass


def _empreinte(corps: dict) -> str:
    canon = json.dumps(corps, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def rapport(db_mika: Session, db_billing: Session, *, maintenant: Optional[_dt.datetime] = None) -> dict:
    """Simulation datée : politique, date de référence, lignes concernées par table (aucune
    donnée personnelle). L'empreinte scelle l'ensemble."""
    t = maintenant or _maintenant()
    corps = {
        "format": FORMAT_RAPPORT,
        "reference": t.replace(microsecond=0).isoformat(),
        "politique_jours": politique(),
        "mika": purger_mika(db_mika, maintenant=t.replace(microsecond=0)),
        "billing": purger_billing(db_billing, maintenant=t.replace(microsecond=0)),
    }
    return {**corps, "empreinte": _empreinte(corps)}


def verifier_rapport(r: dict, *, maintenant: Optional[_dt.datetime] = None) -> _dt.datetime:
    """Refuse un rapport altéré, d'un autre format, périmé, ou établi sous une autre politique.
    Renvoie la date de référence à réutiliser pour l'application."""
    if not isinstance(r, dict) or r.get("format") != FORMAT_RAPPORT:
        raise RapportInvalide("format")
    corps = {k: v for k, v in r.items() if k != "empreinte"}
    if r.get("empreinte") != _empreinte(corps):
        raise RapportInvalide("empreinte")
    if r.get("politique_jours") != politique():
        raise RapportInvalide("politique_modifiee")
    try:
        ref = _dt.datetime.fromisoformat(r["reference"])
    except (KeyError, TypeError, ValueError):
        raise RapportInvalide("reference") from None
    t = maintenant or _maintenant()
    if not (_dt.timedelta(0) <= t - ref <= _dt.timedelta(hours=AGE_MAX_RAPPORT_H)):
        raise RapportInvalide("rapport_perime")
    return ref


def appliquer_rapport(db_mika: Session, db_billing: Session, r: dict, *, lot: int = LOT_DEFAUT,
                      maintenant: Optional[_dt.datetime] = None) -> dict:
    """Applique EXACTEMENT le périmètre présenté : même date de référence ; refus si une table
    compte désormais PLUS de lignes concernées que dans le rapport (ex. import de données
    anciennes entre-temps) — il faut alors établir un nouveau rapport."""
    ref = verifier_rapport(r, maintenant=maintenant)
    actuel = {"mika": purger_mika(db_mika, maintenant=ref), "billing": purger_billing(db_billing, maintenant=ref)}
    for base, tables in actuel.items():
        for table, n in tables.items():
            if n > int(r[base].get(table, 0)):
                raise RapportInvalide(f"perimetre_elargi:{table}")
    metriques: dict = {}
    supprimes = {"mika": purger_mika(db_mika, appliquer=True, maintenant=ref, lot=lot, metriques=metriques),
                 "billing": purger_billing(db_billing, appliquer=True, maintenant=ref, lot=lot, metriques=metriques)}
    return {"reference": r["reference"], "empreinte_rapport": r["empreinte"], "supprimes": supprimes,
            "metriques": metriques}
