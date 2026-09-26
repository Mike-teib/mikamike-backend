"""
service.py — Tentatives de quiz (contrat `mika-quiz/1`, session 6).

Garanties :
  - propriété : une tentative n'est visible que de l'élève (HMAC) qui l'a créée (404 sinon) ;
  - aucune clé de correction avant la soumission ; après : verdict, explication, correction ;
  - une seule soumission par tentative (verrou optimiste sur `version` + état EN_COURS) ;
  - idempotence : (tentative_id, requete_id) rejoué ⇒ même réponse ; autre contenu ⇒ 409 ;
  - `avec_aide` monotone (une aide ne s'annule jamais) ;
  - progression : tentative versée à l'historique, niveau calculé par le moteur sur historique
    (R1–R8) ; un verdict A_REVOIR (réponse indécidable) n'est PAS une preuve et n'est pas versé.
D14 (compréhension finale) : sans objet pour un quiz (pas de phase de compréhension) ; la
tentative est versée avec comprehension_finale=True.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.mikamike import crud, moteur
from app.api.v1.mikamike.store import TentativeExercice
from app.api.v1.quiz.contenu import QuestionIndisponible, catalogue, type_de
from app.api.v1.quiz.store import QuizRequete, QuizTentative
from app.curriculum import quiz_types
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.verifiers.base import Verdict

CONTRACT_VERSION = "mika-quiz/1"


def _err(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _empreinte(operation: str, corps: Dict[str, Any]) -> str:
    canon = json.dumps({"op": operation, **corps}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def tentative_id_pour(eleve_hmac: str, requete_id: str) -> str:
    return hashlib.sha256(f"quiz|{eleve_hmac}|{requete_id}".encode("utf-8")).hexdigest()[:32]


# --------------------------------------------------------------------------- #
# Vues publiques (jamais la clé de correction)
# --------------------------------------------------------------------------- #
def vue_question(q, elimine: Optional[int] = None) -> Dict[str, Any]:
    v: Dict[str, Any] = {"question_id": q.id, "notion_id": q.notion_id, "type": type_de(q), "enonce": q.enonce}
    if isinstance(q, QuestionQuiz):
        v["choix"] = list(q.choix)
        if elimine is not None:
            v["choix_elimine"] = elimine
    elif isinstance(q, quiz_types.QuestionClassement):
        v["elements"] = list(q.elements)
    elif isinstance(q, quiz_types.QuestionAssociation):
        v["gauche"], v["droite"] = list(q.gauche), list(q.droite)
    return v


def correction(q) -> Any:
    if isinstance(q, QuestionQuiz):
        return {"index_correct": q.index_correct}
    if isinstance(q, quiz_types.QuestionVraiFaux):
        return {"vrai": q.affirmation_vraie}
    if isinstance(q, quiz_types.QuestionReponseCourte):
        return {"reponse": q.reponse_reference}
    if isinstance(q, quiz_types.QuestionClassement):
        return {"ordre": list(q.ordre_correct)}
    return {"paires": [list(p) for p in q.paires]}


def _elimine(q, t: QuizTentative) -> Optional[int]:
    """Aide QCM : un distracteur éliminé, choisi de façon déterministe (jamais la bonne réponse)."""
    if not isinstance(q, QuestionQuiz) or not t.avec_aide:
        return None
    faux = [i for i in range(len(q.choix)) if i != q.index_correct]
    return faux[int(hashlib.sha256(t.id.encode()).hexdigest(), 16) % len(faux)]


def vue_tentative(t: QuizTentative, q) -> Dict[str, Any]:
    out = {"contract_version": CONTRACT_VERSION, "tentative_id": t.id, "version": t.version, "etat": t.etat,
           "avec_aide": t.avec_aide, "aides": t.aides, "question": vue_question(q, _elimine(q, t))}
    if t.etat == "TERMINEE":
        out["resultat"] = {"verdict": t.verdict, "est_correct": t.verdict == "CORRECT",
                           "explication": q.explication, "correction": correction(q)}
    return out


# --------------------------------------------------------------------------- #
# Idempotence
# --------------------------------------------------------------------------- #
def _rejouer(db: Session, tid: str, requete_id: str, empreinte: str) -> Optional[Dict[str, Any]]:
    deja = db.get(QuizRequete, (tid, requete_id))
    if deja is None:
        return None
    if deja.empreinte != empreinte:
        raise _err(status.HTTP_409_CONFLICT, "requete_id_reutilise_avec_un_autre_contenu")
    out = json.loads(deja.reponse_json)
    out["rejeu"] = True
    return out


def _journaliser(db: Session, t: QuizTentative, requete_id: str, empreinte: str, out: Dict[str, Any]) -> None:
    db.add(QuizRequete(tentative_id=t.id, requete_id=requete_id, eleve_hmac=t.eleve_hmac,
                       empreinte=empreinte, reponse_json=json.dumps(out, ensure_ascii=False)))


def _question(question_id: str):
    try:
        return catalogue().obtenir(question_id)
    except QuestionIndisponible:
        raise _err(status.HTTP_409_CONFLICT, "contenu_retire")


def charger(db: Session, eleve_hmac: str, tentative_id: str) -> QuizTentative:
    t = db.get(QuizTentative, tentative_id)
    if t is None or t.eleve_hmac != eleve_hmac:  # 404 identique : aucun oracle d'existence
        raise _err(status.HTTP_404_NOT_FOUND, "tentative_inconnue")
    return t


# --------------------------------------------------------------------------- #
# Opérations
# --------------------------------------------------------------------------- #
def demarrer(db: Session, eleve_hmac: str, notion_id: str, requete_id: str,
             question_id: Optional[str]) -> Tuple[int, Dict[str, Any]]:
    tid = tentative_id_pour(eleve_hmac, requete_id)
    empreinte = _empreinte("start", {"notion_id": notion_id, "question_id": question_id})
    rejeu = _rejouer(db, tid, requete_id, empreinte)
    if rejeu is not None:
        return 200, rejeu
    cat = catalogue()
    candidates = cat.pour_notion(notion_id)
    if question_id is not None:
        candidates = [q for q in candidates if q.id == question_id]
    if not candidates:
        raise _err(status.HTTP_404_NOT_FOUND, "quiz_indisponible")
    reussies = {r.exercice_id for r in db.query(TentativeExercice.exercice_id).filter(
        TentativeExercice.eleve_hmac == eleve_hmac, TentativeExercice.competence == notion_id[:64],
        TentativeExercice.est_correct.is_(True))}
    q = next((c for c in candidates if c.id not in reussies), candidates[0])
    t = QuizTentative(id=tid, eleve_hmac=eleve_hmac, question_id=q.id, notion_id=q.notion_id,
                      etat="EN_COURS", version=1, avec_aide=False, aides=0)
    out = {**vue_tentative(t, q), "rejeu": False}
    db.add(t)
    _journaliser(db, t, requete_id, empreinte, out)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        rejeu = _rejouer(db, tid, requete_id, empreinte)
        if rejeu is None:
            raise _err(status.HTTP_409_CONFLICT, "conflit_de_creation")
        return 200, rejeu
    return 201, out


def _transition(db: Session, t: QuizTentative, version: int, valeurs: Dict[str, Any]) -> bool:
    res = db.execute(update(QuizTentative)
                     .where(QuizTentative.id == t.id, QuizTentative.version == version,
                            QuizTentative.etat == "EN_COURS")
                     .values(version=version + 1, **valeurs))
    return res.rowcount == 1


def aide(db: Session, eleve_hmac: str, tentative_id: str, requete_id: str, version: int) -> Dict[str, Any]:
    t = charger(db, eleve_hmac, tentative_id)
    empreinte = _empreinte("aide", {"version": version})
    rejeu = _rejouer(db, t.id, requete_id, empreinte)
    if rejeu is not None:
        return rejeu
    if t.etat != "EN_COURS":
        raise _err(status.HTTP_409_CONFLICT, "tentative_terminee")
    if version != t.version:
        raise _err(status.HTTP_409_CONFLICT, "version_perimee")
    q = _question(t.question_id)
    if not _transition(db, t, version, {"avec_aide": True, "aides": t.aides + 1}):
        db.rollback()
        rejeu = _rejouer(db, t.id, requete_id, empreinte)
        if rejeu is not None:
            return rejeu
        raise _err(status.HTTP_409_CONFLICT, "version_perimee")
    db.expire(t)
    t = db.get(QuizTentative, tentative_id)
    out = {**vue_tentative(t, q), "rejeu": False}
    _journaliser(db, t, requete_id, empreinte, out)
    db.commit()
    return out


def _corriger(q, reponse: Any):
    if isinstance(q, QuestionQuiz):
        if type(reponse) is not int:
            return Verdict.NEEDS_HUMAN_REVIEW
        return Verdict.VALID if reponse == q.index_correct else Verdict.INVALID
    return quiz_types.corriger(q, reponse).verdict


VERDICTS = {Verdict.VALID: "CORRECT", Verdict.INVALID: "INCORRECT"}


def repondre(db: Session, eleve_hmac: str, tentative_id: str, requete_id: str, version: int,
             reponse: Any) -> Dict[str, Any]:
    t = charger(db, eleve_hmac, tentative_id)
    empreinte = _empreinte("repondre", {"version": version, "reponse": reponse})
    rejeu = _rejouer(db, t.id, requete_id, empreinte)
    if rejeu is not None:
        return rejeu
    if t.etat != "EN_COURS":
        raise _err(status.HTTP_409_CONFLICT, "tentative_terminee")
    if version != t.version:
        raise _err(status.HTTP_409_CONFLICT, "version_perimee")
    q = _question(t.question_id)
    verdict = VERDICTS.get(_corriger(q, reponse), "A_REVOIR")
    if not _transition(db, t, version, {"etat": "TERMINEE", "verdict": verdict}):
        db.rollback()
        rejeu = _rejouer(db, t.id, requete_id, empreinte)
        if rejeu is not None:
            return rejeu
        raise _err(status.HTTP_409_CONFLICT, "tentative_terminee")
    progression = None
    if verdict != "A_REVOIR":  # une réponse indécidable n'est pas une preuve d'apprentissage
        db.add(TentativeExercice(eleve_hmac=eleve_hmac, exercice_id=q.id[:64], matiere=q.matiere.value,
                                 niveau=q.niveau.value, competence=q.notion_id[:64],
                                 est_correct=verdict == "CORRECT", avec_aide=t.avec_aide))
    db.expire(t)
    t = db.get(QuizTentative, tentative_id)
    out = {**vue_tentative(t, q), "rejeu": False, "progression": None, "etat_maitrise": None}
    _journaliser(db, t, requete_id, empreinte, out)
    db.commit()
    if verdict != "A_REVOIR":
        etat, diag = moteur.evaluer(db, eleve_hmac, q.notion_id[:64])
        crud.upsert_etat(db, eleve_hmac, q.notion_id[:64], etat.value)
        progression = moteur.progression_json(diag)
        out["progression"], out["etat_maitrise"] = progression, etat.value
        ligne = db.get(QuizRequete, (t.id, requete_id))
        ligne.reponse_json = json.dumps(out, ensure_ascii=False)
        db.commit()
    return out
