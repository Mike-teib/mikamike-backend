"""
moteur.py — Pont entre l'API historique et le moteur de progression sur historique (session 5).

Les routes `/exercices/soumettre`, `/escalier/etape` et la fin d'un tutorat Mika utilisaient
le moteur historique simpliste (`LearningEngine.evaluer_transition`) : un diagnostic dès la
première réponse, et MAITRISE après deux succès le même jour. Elles délèguent désormais la
décision à `app.curriculum.pedagogie.progression.diagnostiquer` (règles R1–R8) :

  - jamais de diagnostic sur une seule réponse (R1) ;
  - une réussite aidée n'est jamais autonome, et déclarer l'aide ne fait jamais monter le
    niveau (R2, R8) ;
  - D14 : compréhension finale ratée ⇒ pas de réussite (R3) ;
  - MAITRISE exige des réussites autonomes réparties sur ≥ 2 jours (R4) ;
  - au plus un cran de variation par réponse (R7).

Compatibilité : le champ `etat_maitrise` garde le vocabulaire historique (7 états) ; il est
DÉRIVÉ du diagnostic (voir `etat_compatible`) et ne peut donc jamais dépasser ce que le
nouveau moteur démontre. Le diagnostic complet est exposé à part (`progression`).

Retour arrière : `MIKA_PROGRESSION_MOTEUR=legacy` rétablit l'ancien calcul sans migration
(aucune donnée n'est écrite différemment : même table de tentatives, même table d'états).
"""

from __future__ import annotations

import datetime as _dt
import os
import time
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.mikamike.learning_engine import EtatMaitrise
from app.api.v1.mikamike.store import TentativeExercice
from app.curriculum.pedagogie.progression import (
    FENETRE,
    HISTORIQUE_MAX,
    Diagnostic,
    Niveau,
    Tentative,
    diagnostiquer,
)

MOTEURS = ("historique", "legacy")
MOTEUR_DEFAUT = "historique"


class MoteurConfigError(RuntimeError):
    """Valeur de MIKA_PROGRESSION_MOTEUR inconnue (fail-closed : jamais de repli silencieux)."""


def moteur_actif() -> str:
    brut = (os.getenv("MIKA_PROGRESSION_MOTEUR") or MOTEUR_DEFAUT).strip().lower()
    if brut not in MOTEURS:
        raise MoteurConfigError(f"MIKA_PROGRESSION_MOTEUR invalide (attendu : {'|'.join(MOTEURS)})")
    return brut


def _secondes(ts: _dt.datetime) -> float:
    # SQLite rend des datetimes naïfs : ils sont écrits en UTC (store._utcnow).
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_dt.timezone.utc)
    return ts.timestamp()


def historique(db: Session, eleve_hmac: str, competence: str) -> List[Tentative]:
    """Tentatives récentes (au plus HISTORIQUE_MAX, lecture bornée par l'index
    (eleve_hmac, competence, ts)), de la plus ancienne à la plus récente."""
    lignes = db.execute(
        select(TentativeExercice.est_correct, TentativeExercice.avec_aide, TentativeExercice.ts)
        .where(TentativeExercice.eleve_hmac == eleve_hmac, TentativeExercice.competence == competence)
        .order_by(TentativeExercice.ts.desc(), TentativeExercice.id.desc())
        .limit(HISTORIQUE_MAX)
    ).all()
    return [Tentative(bool(ok), bool(aide), _secondes(ts)) for ok, aide, ts in reversed(lignes)]


def etat_compatible(diag: Diagnostic, h: Sequence[Tentative]) -> EtatMaitrise:
    """Libellé historique dérivé du diagnostic (jamais plus favorable que lui).

    NON_EVALUEE donne un libellé PROVISOIRE (INCONNU / EN_COURS / ACQUIS_ASSISTE) : aucun
    n'est « solide » (ETATS_SOLIDES) ni « fragile », donc aucune décision (prérequis,
    prochaine étape, tableau parent) ne repose sur une seule réponse.
    """
    if diag.niveau == Niveau.MAITRISEE:
        return EtatMaitrise.MAITRISE
    if diag.niveau == Niveau.NON_ACQUISE:
        return EtatMaitrise.A_REVOIR
    if diag.niveau == Niveau.FRAGILE:
        return EtatMaitrise.FRAGILE
    reussies = [t for t in list(h)[-FENETRE:] if t.correcte and t.comprehension_finale]
    autonomes = [t for t in reussies if not t.avec_aide]
    if diag.niveau == Niveau.EN_COURS:
        if "R4_retest_espace_requis" in diag.raisons:
            return EtatMaitrise.ACQUIS_AUTONOME
        return EtatMaitrise.EN_COURS if autonomes else EtatMaitrise.ACQUIS_ASSISTE
    if autonomes:
        return EtatMaitrise.EN_COURS
    return EtatMaitrise.ACQUIS_ASSISTE if reussies else EtatMaitrise.INCONNU


def evaluer(
    db: Session,
    eleve_hmac: str,
    competence: str,
    *,
    courante: Optional[Tentative] = None,
) -> Tuple[EtatMaitrise, Diagnostic]:
    """Diagnostic sur l'historique en base (+ la tentative `courante` si elle n'est pas
    encore visible par la requête : écriture non validée, ou journalisée après)."""
    h = historique(db, eleve_hmac, competence)
    if courante is not None:
        h = (h + [courante])[-HISTORIQUE_MAX:]
    diag = diagnostiquer(h)
    return etat_compatible(diag, h), diag


def tentative_courante(correcte: bool, avec_aide: bool, comprehension_finale: bool = True) -> Tentative:
    return Tentative(bool(correcte), bool(avec_aide), time.time(), bool(comprehension_finale))


def progression_json(diag: Diagnostic) -> dict:
    """Vue publique du diagnostic (aucune donnée personnelle : niveau, codes de règles, compte)."""
    return {
        "moteur": "historique",
        "niveau": diag.niveau.value,
        "prochaine_action": diag.prochaine_action,
        "observations": diag.observations,
        "raisons": list(diag.raisons),
    }
