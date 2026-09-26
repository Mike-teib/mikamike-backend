"""
service.py — Transitions persistées du tuteur Mika (MIKA_API_CONTRACT.md).

Garanties :
  - état EXPLICITE et versionné en base (verrou optimiste : UPDATE … WHERE version = v) ;
  - idempotence : (tutorat_id, requete_id) rejoué ⇒ même réponse, aucune transition ;
    même requete_id avec un corps différent ⇒ 409 ;
  - propriété : un tutorat n'est visible que de l'élève (HMAC) qui l'a créé (404 sinon) ;
  - la réponse attendue et les aides non encore données ne sortent jamais du serveur ;
  - `avec_aide` ne redescend jamais (monotone) ; à la fin, la tentative est versée au
    learning engine (LE-06 : une réussite aidée n'atteint jamais MAITRISE).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.learning_engine import EtatMaitrise, LearningEngine
from app.api.v1.tutorat.contenu import ContenuIndisponible, catalogue
from app.api.v1.tutorat.store import TutoratRequete, TutoratSession
from app.curriculum.pedagogie.tuteur import EtatTutorat, Reponse, TransitionInvalide, TuteurMika

CONTRACT_VERSION = "mika-tutorat/1"


def _err(code: int, detail: str, **extra) -> HTTPException:
    return HTTPException(status_code=code, detail={"code": detail, **extra} if extra else detail)


def _empreinte(operation: str, corps: Dict[str, Any]) -> str:
    canon = json.dumps({"op": operation, **corps}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def tutorat_id_pour(eleve_hmac: str, requete_id: str) -> str:
    """Identifiant déterministe du tutorat créé par une requête `start` (idempotence du start)."""
    return hashlib.sha256(f"start|{eleve_hmac}|{requete_id}".encode("utf-8")).hexdigest()[:32]


# --------------------------------------------------------------------------- #
# Sérialisation de l'état
# --------------------------------------------------------------------------- #
_CHAMPS_TUPLE = {"erreurs", "erreurs_frequentes_vues", "messages"}
_CHAMPS_ENTIERS = {"tentatives", "indices_donnes", "questions_posees", "methodes_donnees", "reformulations"}
_CHAMPS_BOOLEENS = {"avec_aide", "resolu", "termine", "attend_comprehension"}


def _type_valide(nom: str, v: Any) -> bool:
    """Types stricts de l'état persisté (revue session 3, S3-05 : un état corrompu était servi
    tel quel par GET et provoquait une 500 non maîtrisée au premier calcul)."""
    if nom in _CHAMPS_ENTIERS:
        return isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 10_000
    if nom in _CHAMPS_BOOLEENS:
        return isinstance(v, bool)
    if nom in _CHAMPS_TUPLE:
        return isinstance(v, list) and all(isinstance(x, str) for x in v)
    if nom == "comprehension_verifiee":
        return v is None or isinstance(v, bool)
    if nom == "prerequis_manquant":
        return v is None or isinstance(v, str)
    return isinstance(v, str)  # exercice_id, niveau_estime


def etat_vers_json(etat: EtatTutorat) -> str:
    return json.dumps(dataclasses.asdict(etat), ensure_ascii=False, sort_keys=True)


def etat_depuis_json(brut: str) -> EtatTutorat:
    try:
        d = json.loads(brut)
        noms = {f.name for f in dataclasses.fields(EtatTutorat)}
        if not isinstance(d, dict) or set(d) - noms or "exercice_id" not in d:
            raise ValueError
        if not all(_type_valide(k, v) for k, v in d.items()):
            raise ValueError
        return EtatTutorat(**{k: tuple(v) if k in _CHAMPS_TUPLE else v for k, v in d.items()})
    except (ValueError, TypeError):
        raise _err(status.HTTP_500_INTERNAL_SERVER_ERROR, "etat_tutorat_illisible")


def vue_publique(t: TutoratSession, etat: EtatTutorat) -> Dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "tutorat_id": t.id,
        "version": t.version,
        "exercice_id": etat.exercice_id,
        "derniere_action": t.derniere_action,
        "etat": {
            "tentatives": etat.tentatives,
            "indices_donnes": etat.indices_donnes,
            "questions_posees": etat.questions_posees,
            "methodes_donnees": etat.methodes_donnees,
            "niveau_aide": etat.niveau_aide,
            "avec_aide": etat.avec_aide,
            "resolu": etat.resolu,
            "termine": etat.termine,
            "attend_comprehension": etat.attend_comprehension,
            "comprehension_verifiee": etat.comprehension_verifiee,
            "niveau_estime": etat.niveau_estime,
            "prerequis_manquant": etat.prerequis_manquant,
            "messages": list(etat.messages),
        },
    }


def _reponse_publique(r: Reponse) -> Dict[str, Any]:
    return {"action": r.action.value, "message": r.message, "difficulte_proposee": r.difficulte_proposee,
            "exercice_id": r.exercice_id, "notion_cible": r.notion_cible}


# --------------------------------------------------------------------------- #
# Idempotence
# --------------------------------------------------------------------------- #
def _rejouer(db: Session, tutorat_id: str, requete_id: str, empreinte: str) -> Optional[Dict[str, Any]]:
    deja = db.get(TutoratRequete, (tutorat_id, requete_id))
    if deja is None:
        return None
    if deja.empreinte != empreinte:
        raise _err(status.HTTP_409_CONFLICT, "requete_id_reutilise_avec_un_autre_contenu")
    out = json.loads(deja.reponse_json)
    out["rejeu"] = True
    return out


def _journaliser(db: Session, t: TutoratSession, requete_id: str, empreinte: str, out: Dict[str, Any]) -> None:
    db.add(TutoratRequete(tutorat_id=t.id, requete_id=requete_id, eleve_hmac=t.eleve_hmac,
                          empreinte=empreinte, reponse_json=json.dumps(out, ensure_ascii=False)))


# --------------------------------------------------------------------------- #
# Opérations
# --------------------------------------------------------------------------- #
def demarrer(db: Session, eleve_hmac: str, exercice_id: str, requete_id: str) -> Tuple[int, Dict[str, Any]]:
    tid = tutorat_id_pour(eleve_hmac, requete_id)
    empreinte = _empreinte("start", {"exercice_id": exercice_id})
    rejeu = _rejouer(db, tid, requete_id, empreinte)
    if rejeu is not None:
        return 200, rejeu
    try:
        ex, plan = catalogue().obtenir(exercice_id)
    except ContenuIndisponible:
        # Raisons détaillées NON renvoyées (contenu interne) ; 404 unique.
        raise _err(status.HTTP_404_NOT_FOUND, "exercice_indisponible")
    tuteur = TuteurMika(ex, plan)
    etats = crud.get_etats(db, eleve_hmac)  # R5 : IDs de compétences à unifier avec les notions
    etat, rep = tuteur.demarrer({p: etats.get(p, "INCONNU") for p in ex.prerequis})
    t = TutoratSession(id=tid, eleve_hmac=eleve_hmac, exercice_id=ex.id, etat_json=etat_vers_json(etat),
                       derniere_action=rep.action.value, version=1, termine=etat.termine)
    out = {**vue_publique(t, etat), "reponse": _reponse_publique(rep), "rejeu": False}
    db.add(t)
    _journaliser(db, t, requete_id, empreinte, out)
    try:
        db.commit()
    except IntegrityError:  # course : la même requête vient d'être traitée
        db.rollback()
        rejeu = _rejouer(db, tid, requete_id, empreinte)
        if rejeu is None:
            raise _err(status.HTTP_409_CONFLICT, "conflit_de_creation")
        return 200, rejeu
    return 201, out


def charger(db: Session, eleve_hmac: str, tutorat_id: str) -> TutoratSession:
    t = db.get(TutoratSession, tutorat_id)
    # 404 identique pour « inexistant » et « appartient à un autre élève » (pas d'oracle).
    if t is None or t.eleve_hmac != eleve_hmac:
        raise _err(status.HTTP_404_NOT_FOUND, "tutorat_inconnu")
    return t


def transition(
    db: Session, eleve_hmac: str, tutorat_id: str, requete_id: str, version: int,
    operation: str, corps: Dict[str, Any],
    appliquer: Callable[[TuteurMika, EtatTutorat], Tuple[EtatTutorat, Reponse]],
) -> Dict[str, Any]:
    t = charger(db, eleve_hmac, tutorat_id)
    empreinte = _empreinte(operation, {"version": version, **corps})
    rejeu = _rejouer(db, t.id, requete_id, empreinte)
    if rejeu is not None:
        return rejeu
    if version != t.version:
        raise _err(status.HTTP_409_CONFLICT, "version_perimee", version_courante=t.version)
    etat = etat_depuis_json(t.etat_json)
    if etat.termine:
        raise _err(status.HTTP_409_CONFLICT, "tutorat_termine")
    try:
        ex, plan = catalogue().obtenir(t.exercice_id)
    except ContenuIndisponible:
        raise _err(status.HTTP_409_CONFLICT, "contenu_retire")
    tuteur = TuteurMika(ex, plan)
    try:
        nouvel, rep = appliquer(tuteur, etat)
    except TransitionInvalide as exc:
        raise _err(status.HTTP_409_CONFLICT, str(exc))
    if etat.avec_aide and not nouvel.avec_aide:  # garde-fou : jamais atteint (monotonie du moteur)
        raise _err(status.HTTP_500_INTERNAL_SERVER_ERROR, "invariant_avec_aide_viole")

    res = db.execute(
        update(TutoratSession)
        .where(TutoratSession.id == t.id, TutoratSession.version == version)
        .values(etat_json=etat_vers_json(nouvel), version=version + 1,
                derniere_action=rep.action.value, termine=nouvel.termine)
    )
    if res.rowcount != 1:
        db.rollback()
        # Double soumission concurrente de la MÊME requête : l'autre exécution a déjà validé
        # la transition ⇒ on rejoue sa réponse (revue session 3, S3-04 ; avant : 409).
        rejeu = _rejouer(db, tutorat_id, requete_id, empreinte)
        if rejeu is not None:
            return rejeu
        raise _err(status.HTTP_409_CONFLICT, "version_perimee")
    db.expire(t)
    t = db.get(TutoratSession, tutorat_id)
    out = {**vue_publique(t, nouvel), "reponse": _reponse_publique(rep), "rejeu": False}
    _journaliser(db, t, requete_id, empreinte, out)
    if nouvel.termine and not etat.termine and nouvel.prerequis_manquant is None:
        _verser_au_learning_engine(db, eleve_hmac, ex, nouvel)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        rejeu = _rejouer(db, tutorat_id, requete_id, empreinte)
        if rejeu is None:
            raise _err(status.HTTP_409_CONFLICT, "version_perimee")
        return rejeu
    return out


def _reussi(etat: EtatTutorat) -> bool:
    """Résolu ET compréhension non infirmée (revue session 3, S3-06 : une compréhension
    vérifiée FAUSSE comptait comme une réussite)."""
    return etat.resolu and etat.comprehension_verifiee is not False


def _verser_au_learning_engine(db: Session, eleve_hmac: str, ex, etat: EtatTutorat) -> None:
    """Fin de tutorat ⇒ une tentative journalisée + transition LE-06 (sans commit ici)."""
    from app.api.v1.mikamike.store import EtatCompetence, TentativeExercice

    db.add(TentativeExercice(eleve_hmac=eleve_hmac, exercice_id=ex.id[:64], matiere=ex.matiere.value,
                             niveau=ex.niveau.value, competence=ex.notion_id[:64],
                             est_correct=_reussi(etat), avec_aide=etat.avec_aide))
    eng = LearningEngine()
    courant = db.execute(select(EtatCompetence.etat).where(
        EtatCompetence.eleve_hmac == eleve_hmac, EtatCompetence.competence == ex.notion_id[:64])).scalar()
    try:
        eng.etats_eleves[(eleve_hmac, ex.notion_id[:64])] = EtatMaitrise(courant or "INCONNU")
    except ValueError:
        pass
    nouvel = eng.evaluer_transition(eleve_hmac, ex.notion_id[:64], est_correct=_reussi(etat),
                                    avec_aide=etat.avec_aide, nombre_succes_consecutifs=0)
    obj = db.get(EtatCompetence, (eleve_hmac, ex.notion_id[:64]))
    if obj is None:
        db.add(EtatCompetence(eleve_hmac=eleve_hmac, competence=ex.notion_id[:64], etat=nouvel.value))
    else:
        obj.etat = nouvel.value
