"""
router.py — Endpoints réels MikaMike (remplacent les mocks du Drive).

Trois routeurs, agrégés dans `mika_router` (à monter sous le préfixe /api,
cf. A_CABLER_MIKA_DANS_MAIN.md) :
  POST /exercices/soumettre        -> évaluation + remédiation via learning_engine
  GET  /parents/dashboard/{id}     -> stats agrégées SANS PII (pseudonymisation HMAC)
  GET  /parcours/prochaine-etape   -> prochaine marche réelle de l'escalier

Aucune PII ne circule : l'identifiant reçu (déjà anonyme) est re-haché en HMAC
pour l'indexation interne. Le dashboard ne renvoie jamais nom/prénom/email.
"""

from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.api.v1.mikamike import catalogue, crud, moteur
from app.api.v1.mikamike.learning_engine import (
    ETATS_SOLIDES,
    EtatMaitrise,
    LearningEngine,
)
from app.api.v1.mikamike.schemas import (
    DashboardOut,
    ProchaineEtapeOut,
    Remediation,
    SoumissionIn,
    SoumissionOut,
)
from app.api.v1.mikamike.store import get_db
from app.core.validation import ID_PATTERN
from app.core.auth import Action, Garde, garde as _garde

from app.core.pseudonymisation import hmac_eleve as _hmac

def _engine_charge(db: Session, eleve_hmac: str) -> LearningEngine:
    """Instancie le moteur et précharge les états connus de l'élève depuis la DB."""
    eng = LearningEngine()
    for competence, etat in crud.get_etats(db, eleve_hmac).items():
        try:
            eng.etats_eleves[(eleve_hmac, competence)] = EtatMaitrise(etat)
        except ValueError:
            continue
    return eng


# --------------------------------------------------------------------------- #
# Exercices
# --------------------------------------------------------------------------- #
exercices_router = APIRouter(prefix="/exercices", tags=["mika-exercices"])


@exercices_router.post("/soumettre", response_model=SoumissionOut)
def soumettre_exercice(payload: SoumissionIn, db: Session = Depends(get_db), g: Garde = Depends(_garde)):
    g.exiger(payload.student_pseudo_id, Action.APPRENTISSAGE)
    meta = catalogue.get_exercice(payload.exercice_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="exercice_inconnu")

    eleve_hmac = _hmac(payload.student_pseudo_id)
    competence = meta["competence"]
    correct = catalogue.est_correct(payload.exercice_id, payload.reponse)

    # 1) Journalisation de la tentative (pseudonymisée)
    crud.enregistrer_tentative(
        db,
        eleve_hmac=eleve_hmac,
        exercice_id=payload.exercice_id,
        matiere=meta["matiere"],
        niveau=meta["niveau"],
        competence=competence,
        est_correct=correct,
        avec_aide=payload.avec_aide,
    )

    # 2) Transition d'état. Session 5 : décision par le moteur sur HISTORIQUE (moteur.py) ;
    #    `MIKA_PROGRESSION_MOTEUR=legacy` rétablit l'ancien calcul (retour arrière).
    eng = _engine_charge(db, eleve_hmac)
    progression = None
    if moteur.moteur_actif() == "legacy":
        succes_consec = crud.compter_succes_consecutifs(
            db, eleve_hmac, competence, autonomes_seulement=True
        )
        nouvel_etat = eng.evaluer_transition(
            eleve_hmac,
            competence,
            est_correct=correct,
            avec_aide=payload.avec_aide,
            nombre_succes_consecutifs=succes_consec,
        )
    else:
        # La tentative vient d'être validée en base : elle fait partie de l'historique lu.
        nouvel_etat, diag = moteur.evaluer(db, eleve_hmac, competence)
        eng.etats_eleves[(eleve_hmac, competence)] = nouvel_etat
        progression = moteur.progression_json(diag)
    crud.upsert_etat(db, eleve_hmac, competence, nouvel_etat.value)

    if correct:
        return SoumissionOut(
            est_correct=True,
            etat_maitrise=nouvel_etat.value,
            message="Bravo ! Tu montes une marche de l'escalier.",
            remediation=None,
            progression=progression,
        )

    # 3) Erreur -> diagnostic de la marche manquante (remontée des prérequis)
    lacune, _chaine = eng.diagnostiquer_marche_manquante(eleve_hmac, competence)
    competence_cible_remed = lacune or competence
    exo_prerequis = (
        catalogue.exercice_pour_competence(competence_cible_remed)
        or meta["exercice_prerequis"]
    )
    return SoumissionOut(
        est_correct=False,
        etat_maitrise=nouvel_etat.value,
        message="Ce n'est pas encore ça — on reprend la marche d'en dessous.",
        remediation=Remediation(
            explication_concept=meta["explication_concept"],
            exercice_prerequis=exo_prerequis,
            competence_lacune=competence_cible_remed,
        ),
        progression=progression,
    )


# --------------------------------------------------------------------------- #
# Parents (dashboard sans PII)
# --------------------------------------------------------------------------- #
parents_router = APIRouter(prefix="/parents", tags=["mika-parents"])


@parents_router.get("/dashboard/{student_pseudo_id}", response_model=DashboardOut)
def dashboard_parent(
    student_pseudo_id: str = Path(max_length=128, pattern=ID_PATTERN),
    db: Session = Depends(get_db), g: Garde = Depends(_garde)):
    g.exiger(student_pseudo_id, Action.LECTURE)
    eleve_hmac = _hmac(student_pseudo_id)
    stats = crud.agreger_dashboard(db, eleve_hmac)
    # On renvoie l'identifiant anonyme fourni (jamais de nom/prénom/email).
    return DashboardOut(pseudo_id=student_pseudo_id, statistiques_pedagogiques=stats)


# --------------------------------------------------------------------------- #
# Parcours (prochaine marche réelle)
# --------------------------------------------------------------------------- #
parcours_router = APIRouter(prefix="/parcours", tags=["mika-parcours"])


@parcours_router.get("/prochaine-etape", response_model=ProchaineEtapeOut)
def prochaine_etape(
    student_id: str = Query(max_length=128, pattern=ID_PATTERN),
    level: str | None = Query(default=None, max_length=32),
    subject: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db), g: Garde = Depends(_garde)):
    g.exiger(student_id, Action.APPRENTISSAGE)
    eleve_hmac = _hmac(student_id)
    etats = crud.get_etats(db, eleve_hmac)

    # Première compétence du catalogue non encore consolidée, dans le niveau/matière demandé.
    filtres_actifs = bool((level or "").strip() or (subject or "").strip())
    candidats = catalogue.exercices_disponibles(niveau=level, matiere=subject) if filtres_actifs else list(catalogue.EXERCICES)
    if not candidats:
        raise HTTPException(status_code=404, detail="contenu_indisponible")

    cible = None
    exo_id = None
    for candidat_id in candidats:
        candidat = catalogue.get_exercice(candidat_id)
        if candidat is None:
            continue
        comp = candidat["competence"]
        try:
            etat = EtatMaitrise(etats.get(comp, "INCONNU"))
        except ValueError:
            etat = EtatMaitrise.INCONNU
        if etat not in ETATS_SOLIDES:
            cible = comp
            exo_id = candidat_id
            break

    if exo_id is None:
        # Tout est consolidé pour ce filtre : révision du premier exercice disponible.
        exo_id = candidats[0]
        meta_revision = catalogue.get_exercice(exo_id)
        cible = meta_revision["competence"]

    meta = catalogue.get_exercice(exo_id)
    return ProchaineEtapeOut(
        exercice_id=exo_id,
        niveau=meta["niveau"],
        competence=cible,
        consigne=meta["enonce"],
    )


# --------------------------------------------------------------------------- #
# Agrégat monté sous /api (voir A_CABLER_MIKA_DANS_MAIN.md)
# --------------------------------------------------------------------------- #
mika_router = APIRouter()
mika_router.include_router(exercices_router)
mika_router.include_router(parents_router)
mika_router.include_router(parcours_router)
