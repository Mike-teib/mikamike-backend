"""
router.py — API du tuteur Mika, contrat versionné `mika-tutorat/1` (MIKA_API_CONTRACT.md).

  POST /api/v1/mika/session/start          démarre (ou rejoue) un tutorat
  POST /api/v1/mika/session/answer         réponse de l'élève à l'exercice
  POST /api/v1/mika/session/help           demande d'aide (graduée)
  POST /api/v1/mika/session/comprehension  réponse à la question de compréhension
  GET  /api/v1/mika/session/{tutorat_id}   état public du tutorat

Toutes les routes : action « apprentissage » (jeton élève du même pseudo-id en mode enforce).
Aucune dépendance LLM : moteur déterministe `app.curriculum.pedagogie.tuteur`.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.v1.mikamike.store import get_db
from app.api.v1.tutorat import service
from app.core.auth import Action, Garde, garde as _garde
from app.core.pseudonymisation import hmac_eleve as _hmac
from app.core.validation import ID_PATTERN, Identifiant, ReponseEleve
from app.curriculum.pedagogie.tuteur import TransitionInvalide

mika_tutorat_router = APIRouter(prefix="/mika/session", tags=["mika-tutorat"])

TutoratId = Field(pattern=r"^[0-9a-f]{32}$")


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_pseudo_id: Identifiant
    requete_id: Identifiant = Field(description="Clé d'idempotence choisie par le client (unique par action)")


class StartIn(_Base):
    exercice_id: Identifiant


class _Transition(_Base):
    tutorat_id: str = TutoratId
    version: int = Field(ge=1, le=10_000, description="Version courante connue du client (verrou optimiste)")


class AnswerIn(_Transition):
    reponse: ReponseEleve


class HelpIn(_Transition):
    pass


class ComprehensionIn(_Transition):
    reponse: ReponseEleve


@mika_tutorat_router.post("/start", status_code=status.HTTP_201_CREATED)
def start(data: StartIn, response: Response, db: Session = Depends(get_db),
          g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)
    code, out = service.demarrer(db, _hmac(data.student_pseudo_id), data.exercice_id, data.requete_id)
    response.status_code = code
    return out


def _answer(tuteur, etat, reponse):
    if etat.attend_comprehension:
        raise TransitionInvalide("comprehension_attendue")
    return tuteur.repondre(etat, reponse)


@mika_tutorat_router.post("/answer")
def answer(data: AnswerIn, db: Session = Depends(get_db), g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)
    return service.transition(db, _hmac(data.student_pseudo_id), data.tutorat_id, data.requete_id,
                              data.version, "answer", {"reponse": data.reponse},
                              lambda t, e: _answer(t, e, data.reponse))


@mika_tutorat_router.post("/help")
def help_(data: HelpIn, db: Session = Depends(get_db), g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)

    def appliquer(t, e):
        if e.attend_comprehension:
            raise TransitionInvalide("comprehension_attendue")
        return t.demander_aide(e)

    return service.transition(db, _hmac(data.student_pseudo_id), data.tutorat_id, data.requete_id,
                              data.version, "help", {}, appliquer)


@mika_tutorat_router.post("/comprehension")
def comprehension(data: ComprehensionIn, db: Session = Depends(get_db),
                  g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(data.student_pseudo_id, Action.APPRENTISSAGE)
    return service.transition(db, _hmac(data.student_pseudo_id), data.tutorat_id, data.requete_id,
                              data.version, "comprehension", {"reponse": data.reponse},
                              lambda t, e: t.repondre_comprehension_texte(e, data.reponse))


@mika_tutorat_router.get("/{tutorat_id}")
def lire(tutorat_id: str = Path(pattern=r"^[0-9a-f]{32}$"),
         student_id: str = Query(max_length=128, pattern=ID_PATTERN),
         db: Session = Depends(get_db), g: Garde = Depends(_garde)) -> Dict[str, Any]:
    g.exiger(student_id, Action.APPRENTISSAGE)
    t = service.charger(db, _hmac(student_id), tutorat_id)
    return service.vue_publique(t, service.etat_depuis_json(t.etat_json))
