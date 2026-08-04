"""
spaced_repetition.py — Moteur de Mémorisation Espacée (Ebbinghaus & Leitner) — Tâche #28.
========================================================================================
Modélise la courbe d'oubli R = exp(-t / S), gère la fragilité des notions et planifie
les rappels échelonnés à J+1, J+3, J+7, J+14.
"""

from __future__ import annotations

import datetime as _dt
import math
import os
from typing import Dict, Any, Tuple, Optional
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Secret HMAC pour la pseudonymisation
from app.core.security_config import get_pseudo_secret as _get_pseudo_secret

_PSEUDO_SECRET = _get_pseudo_secret()

# SQLAlchemy Base dédiée aux tâches de rappel mémoire
MemoryBase = declarative_base()


class TacheRappelMemoire(MemoryBase):
    """Table de suivi des rappels de mémorisation espacée."""
    __tablename__ = "mika_memory_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eleve_hmac = Column(String(32), index=True, nullable=False)
    notion_id = Column(String(64), index=True, nullable=False)
    statut_fragilite = Column(Boolean, default=False, nullable=False)
    repetition_count = Column(Integer, default=0, nullable=False)
    intervalle_jours = Column(Integer, default=1, nullable=False)
    force_memoire_s = Column(Float, default=1.0, nullable=False)  # S (Strength) dans e^(-t/S)
    derniers_succes_consecutifs = Column(Integer, default=0, nullable=False)
    prochain_rappel_date = Column(DateTime, nullable=False)
    derniere_mise_a_jour = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)


class MoteurCourbeOubliEbbinghaus:
    """Moteur algorithmique calculant la rétention et planifiant les révisions."""

    INTERVALLES_LEITNER = {
        1: 1,   # Repetition 1 -> J+1
        2: 3,   # Repetition 2 -> J+3
        3: 7,   # Repetition 3 -> J+7
        4: 14   # Repetition 4+ -> J+14
    }

    @classmethod
    def estimer_retention_ebbinghaus(cls, jours_ecoules: float, force_memoire: float) -> float:
        """
        Formule d'Ebbinghaus : R = e^(-t / S)
        R : Taux de rétention estimé (0.0 à 1.0)
        t : Temps écoulé en jours
        S : Force de la trace mnésique (Memory Strength)
        """
        if force_memoire <= 0:
            force_memoire = 1.0
        retention = math.exp(-jours_ecoules / force_memoire)
        return round(max(0.0, min(1.0, retention)), 3)

    @classmethod
    def traiter_evenement_apprentissage(
        cls,
        db: Session,
        eleve_hmac: str,
        notion_id: str,
        mastery_event: str
    ) -> Dict[str, Any]:
        """
        Calcule le prochain rappel et met à jour l'état de fragilité en DB.
        mastery_event : "SUCCESS" (Réussite) ou "FAILURE" (Échec)
        """
        now = _dt.datetime.now(_dt.timezone.utc)
        event_upper = (mastery_event or "SUCCESS").strip().upper()
        is_success = event_upper in ("SUCCESS", "REUSSITE", "CORRECT", "MAITRISE")

        # Recherche ou création de la tâche de rappel
        tache = db.execute(
            select(TacheRappelMemoire).where(
                TacheRappelMemoire.eleve_hmac == eleve_hmac,
                TacheRappelMemoire.notion_id == notion_id
            )
        ).scalars().first()

        if not tache:
            tache = TacheRappelMemoire(
                eleve_hmac=eleve_hmac,
                notion_id=notion_id,
                statut_fragilite=not is_success,
                repetition_count=1 if is_success else 0,
                intervalle_jours=1,
                force_memoire_s=1.5 if is_success else 0.5,
                derniers_succes_consecutifs=1 if is_success else 0,
                prochain_rappel_date=now + _dt.timedelta(days=1)
            )
            db.add(tache)
        else:
            if is_success:
                tache.statut_fragilite = False
                tache.repetition_count += 1
                tache.derniers_succes_consecutifs += 1
                
                # Détermination de l'intervalle J+1, J+3, J+7, J+14
                step = min(tache.repetition_count, 4)
                tache.intervalle_jours = cls.INTERVALLES_LEITNER.get(step, 14)
                
                # Augmentation exponentielle de la force mnésique S
                tache.force_memoire_s = round(tache.force_memoire_s * 1.6 + 0.5, 2)
            else:
                # ÉCHEC : Détection immédiate de fragilité !
                tache.statut_fragilite = True
                tache.repetition_count = 0
                tache.derniers_succes_consecutifs = 0
                tache.intervalle_jours = 1  # Rappel obligatoire à J+1
                tache.force_memoire_s = 0.5 # Chute de la force mnésique

            tache.prochain_rappel_date = now + _dt.timedelta(days=tache.intervalle_jours)

        db.commit()
        db.refresh(tache)

        # Calcul de la rétention estimée d'Ebbinghaus
        retention = cls.estimer_retention_ebbinghaus(
            jours_ecoules=0.0,  # Juste après le résultat
            force_memoire=tache.force_memoire_s
        )

        return {
            "notion_id": notion_id,
            "mastery_event": "SUCCESS" if is_success else "FAILURE",
            "statut_fragilite": tache.statut_fragilite,
            "repetition_count": tache.repetition_count,
            "intervalle_jours": tache.intervalle_jours,
            "prochain_rappel_date": tache.prochain_rappel_date.isoformat(),
            "courbe_ebbinghaus": {
                "force_memoire_S": tache.force_memoire_s,
                "taux_retention_estime": retention if is_success else 0.40,
                "statut_memoire": "FRAGILE" if tache.statut_fragilite else ("SOLIDE" if tache.repetition_count >= 3 else "EN_CONSOLIDATION")
            }
        }
