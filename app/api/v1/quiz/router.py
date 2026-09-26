"""
router.py — API HTTP des quiz, contrat `mika-quiz/1` (session 6).

  POST /api/v1/quiz/tentatives          obtenir une question pour une notion (ou la reprendre)
  POST /api/v1/quiz/aide                demander une aide (avec_aide devient vrai, définitivement)
  POST /api/v1/quiz/repondre            soumettre la réponse (une seule fois) ⇒ résultat + progression
  GET  /api/v1/quiz/tentatives/{id}     reprendre une tentative (état public)

Action « apprentissage » (jeton de séance de l'élève en enforce). Limitation par élève.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from sqlalchemy.orm import Session

from app.api.v1.mikamike.store import get_db
from app.api.v1.quiz import service
from app.core import limitation
from app.core.auth import Action, Garde, garde as _garde
from app.core.pseudonymisation import hmac_eleve as _hmac
from app.core.validation import ID_PATTERN, Identifiant, Identifiant64

quiz_router = APIRouter(prefix="/quiz", tags=["mika-quiz"])

TentativeId = Field(pattern=r"^[0-9a-f]{32}$")
Court = Field(max_length=500)

# Réponse d'élève : types stricts et bornés (aucune structure arbitraire).
ReponseQuiz = Union[StrictBool, StrictInt, List[StrictInt], Dict[str, StrictInt], str]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_pseudo_id: Identifiant
    requete_id: Identifiant = Field(description="Clé d'idempotence choisie par le client (unique par action)")


class DemarrerIn(_Base):
    notion_id: Identifiant64
    question_id: Optional[Identifiant] = None


class _Transition(_Base):
    tentative_id: str = TentativeId
    version: int = Field(ge=1, le=100)


class AideIn(_Transition):
    pass


class RepondreIn(_Transition):
    reponse: ReponseQuiz

    def reponse_bornee(self) -> Any:
        r = self.reponse
        if isinstance(r, str) and len(r) > 500:
            raise ValueError
        if isinstance(r, (list, dict)) and len(r) > 10:
            raise ValueError
        if isinstance(r, dict) and any(len(k) > 4 for k in r):
            raise ValueError
        return r


def _limiter(eleve_hmac: str) -> None:
    paires = [(limitation.QUIZ_ELEVE, eleve_hmac)]
    limitation.exiger(*paires)
    limitation.compter(paires)


@quiz_router.post("/tentatives", status_code=status.HTTP_201_CREATED)
def demarrer(data: DemarrerIn, response: Response, db: Session = Depends(get_db),
             g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)
    h = _hmac(data.student_pseudo_id)
    _limiter(h)
    code, out = service.demarrer(db, h, data.notion_id, data.requete_id, data.question_id)
    response.status_code = code
    return out


@quiz_router.post("/aide")
def aide(data: AideIn, db: Session = Depends(get_db), g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)
    h = _hmac(data.student_pseudo_id)
    _limiter(h)
    return service.aide(db, h, data.tentative_id, data.requete_id, data.version)


@quiz_router.post("/repondre")
def repondre(data: RepondreIn, db: Session = Depends(get_db), g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)
    try:
        reponse = data.reponse_bornee()
    except ValueError:
        raise service._err(422, "reponse_hors_bornes")
    h = _hmac(data.student_pseudo_id)
    _limiter(h)
    return service.repondre(db, h, data.tentative_id, data.requete_id, data.version, reponse)


@quiz_router.get("/tentatives/{tentative_id}")
def lire(tentative_id: str = Path(pattern=r"^[0-9a-f]{32}$"),
         student_id: str = Query(max_length=128, pattern=ID_PATTERN),
         db: Session = Depends(get_db), g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(student_id, Action.APPRENTISSAGE)
    h = _hmac(student_id)
    t = service.charger(db, h, tentative_id)
    q = service._question(t.question_id)
    return service.vue_tentative(t, q)
