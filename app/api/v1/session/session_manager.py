"""
session_manager.py — Gestionnaire de Session & Restauration d'État (Tâche #37).
===============================================================================
1. Détection de Timeout d'inactivité à 5 minutes (300 secondes).
2. Reconnexion gracieuse en < 2.0 secondes.
3. Sauvegarde et restauration partielle de la mémoire de séance (ardoise, exercice, étape).
"""

from __future__ import annotations

import datetime as _dt
import json
import time
from typing import Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import Column, String, Boolean, DateTime, Text, select
from sqlalchemy.orm import declarative_base, Session

from app.core.security_config import get_pseudo_secret as _get_pseudo_secret

_PSEUDO_SECRET = _get_pseudo_secret()
INACTIVITY_TIMEOUT_SECONDS = 300  # 5 minutes d'inactivité

SessionBase = declarative_base()


def _utcnow_naive() -> _dt.datetime:
    """UTC naïf (SQLite ne stocke pas le fuseau) — remplace datetime.utcnow déprécié."""
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)


def _verifier_proprietaire(session_obj: "MikaSessionState", eleve_hmac: str) -> None:
    """
    Une session n'est accessible qu'à l'élève qui l'a créée (anti-IDOR, RGPD).
    Sans ce contrôle, connaître un session_id suffisait pour lire (reconnect) ou
    écrire (save-state) la mémoire de séance d'un autre élève.
    """
    if session_obj.eleve_hmac != eleve_hmac:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="session_non_autorisee")


class MikaSessionState(SessionBase):
    """Table de suivi des sessions actives et mémoire de séance."""
    __tablename__ = "mika_session_states"

    session_id = Column(String(64), primary_key=True)
    eleve_hmac = Column(String(32), index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity_ts = Column(DateTime, nullable=False, default=_utcnow_naive)
    created_at = Column(DateTime, nullable=False, default=_utcnow_naive)
    state_json = Column(Text, nullable=True, default="{}")


class GestionnaireSession:
    """Moteur de gestion des sessions et de reconnexion < 2s."""

    @classmethod
    def heartbeat(cls, db: Session, session_id: str, eleve_hmac: str) -> Dict[str, Any]:
        """
        Met à jour le timestamp de dernière activité (heartbeat 5 min).
        Renvoie 401 si la session est expirée depuis plus de 5 minutes.
        """
        now = _dt.datetime.now(_dt.timezone.utc)
        session_obj = db.execute(
            select(MikaSessionState).where(MikaSessionState.session_id == session_id)
        ).scalars().first()

        if not session_obj:
            session_obj = MikaSessionState(
                session_id=session_id,
                eleve_hmac=eleve_hmac,
                is_active=True,
                last_activity_ts=now,
                state_json=json.dumps({"exercice_courant_id": "exo-01", "ardoise_draft": ""})
            )
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)
            return {"statut": "session_creee", "session_id": session_id, "is_active": True}

        # Vérification du timeout d'inactivité de 5 minutes (300 s)
        elapsed_seconds = (now.replace(tzinfo=None) - session_obj.last_activity_ts).total_seconds()
        if elapsed_seconds > INACTIVITY_TIMEOUT_SECONDS:
            session_obj.is_active = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="session_inactivite_5min"
            )

        _verifier_proprietaire(session_obj, eleve_hmac)
        session_obj.last_activity_ts = now
        session_obj.is_active = True
        db.commit()
        return {"statut": "heartbeat_ok", "session_id": session_id, "is_active": True}

    @classmethod
    def sauvegarder_etat_partiel(
        cls,
        db: Session,
        session_id: str,
        eleve_hmac: str,
        state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sauvegarde la mémoire de séance (ardoise, étape escalier, exercice courant)."""
        now = _dt.datetime.now(_dt.timezone.utc)
        session_obj = db.execute(
            select(MikaSessionState).where(MikaSessionState.session_id == session_id)
        ).scalars().first()

        if not session_obj:
            session_obj = MikaSessionState(
                session_id=session_id,
                eleve_hmac=eleve_hmac,
                is_active=True,
                last_activity_ts=now,
                state_json=json.dumps(state_data)
            )
            db.add(session_obj)
        else:
            _verifier_proprietaire(session_obj, eleve_hmac)
            # Fusion de l'état existant avec les nouvelles données
            existing_state = json.loads(session_obj.state_json or "{}")
            existing_state.update(state_data)
            session_obj.state_json = json.dumps(existing_state)
            session_obj.last_activity_ts = now
            session_obj.is_active = True

        db.commit()
        return {"statut": "etat_sauvegarde", "session_id": session_id}

    @classmethod
    def reconnecter_et_restaurer(
        cls,
        db: Session,
        session_id: str,
        eleve_hmac: str
    ) -> Dict[str, Any]:
        """
        Reconnexion gracieuse < 2.0 secondes :
        Restaure la mémoire de séance partielle (ardoise, exercice, étape).
        """
        start_time = time.time()
        now = _dt.datetime.now(_dt.timezone.utc)

        session_obj = db.execute(
            select(MikaSessionState).where(MikaSessionState.session_id == session_id)
        ).scalars().first()

        if not session_obj:
            # Création automatique de session par défaut si inconnue
            session_obj = MikaSessionState(
                session_id=session_id,
                eleve_hmac=eleve_hmac,
                is_active=True,
                last_activity_ts=now,
                state_json=json.dumps({"exercice_courant_id": "exo-01", "ardoise_draft": ""})
            )
            db.add(session_obj)
            db.commit()

        _verifier_proprietaire(session_obj, eleve_hmac)

        # Restauration d'état
        state_data = json.loads(session_obj.state_json or "{}")
        session_obj.is_active = True
        session_obj.last_activity_ts = now
        db.commit()

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "statut": "reconnexion_reussie",
            "session_id": session_id,
            "duree_reconnexion_ms": elapsed_ms,
            "reconnexion_inf_2s": elapsed_ms < 2000.0,
            "session_state": state_data
        }
