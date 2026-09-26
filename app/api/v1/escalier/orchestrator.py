"""
orchestrator.py — Orchestrateur Pédagogique en 8 Étapes de l'Escalier Mika.
===========================================================================
Doctrine (Cahier §4) :
1. Objectif -> 2. Analyse de l'Erreur -> 3. Remontée aux Prérequis -> 4. Explication -> 5. Micro-remédiation -> 6. Vérification PAR LE MOTEUR -> 7. Retour à l'Objectif -> 8. Mémoire
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.api.v1.mikamike import catalogue, crud
from app.api.v1.mikamike.learning_engine import (
    LearningEngine,
    EtatMaitrise,
    pseudonymiser_code
)

from app.core.security_config import get_pseudo_secret as _get_pseudo_secret

_PSEUDO_SECRET = _get_pseudo_secret()


def _hmac(student_pseudo_id: str) -> str:
    return pseudonymiser_code(student_pseudo_id, _PSEUDO_SECRET)


class OrchestrateurEscalier:
    """Moteur d'orchestration en 8 étapes pour le tuteur Mika."""

    def __init__(self, db: Session, student_pseudo_id: str):
        self.db = db
        self.student_pseudo_id = student_pseudo_id
        self.eleve_hmac = _hmac(student_pseudo_id)
        
        # Préchargement du moteur LearningEngine avec les états enregistrés en DB
        self.engine = LearningEngine()
        etats_db = crud.get_etats(self.db, self.eleve_hmac)
        for comp, etat in etats_db.items():
            try:
                self.engine.etats_eleves[(self.eleve_hmac, comp)] = EtatMaitrise(etat)
            except ValueError:
                continue

    def executer_pipeline_8_etapes(
        self,
        competence_objectif: str,
        exercice_id: str,
        reponse_eleve: Optional[str] = None,
        avec_aide: bool = False
    ) -> Dict[str, Any]:
        """Exécute la boucle séquentielle en 8 étapes et retourne l'état complet du tuteur."""

        # ---------------------------------------------------------------------
        # ÉTAPE 1 : OBJECTIF (Target & Consigne de départ)
        # ---------------------------------------------------------------------
        meta_exercice = catalogue.get_exercice(exercice_id)
        if not meta_exercice:
            exercice_id = catalogue.exercice_pour_competence(competence_objectif) or "exo-maths-algebre-1"
            meta_exercice = catalogue.get_exercice(exercice_id)

        competence_exo = meta_exercice["competence"] if meta_exercice else competence_objectif

        # ---------------------------------------------------------------------
        # ÉTAPE 2 : ANALYSE DE L'ERREUR (Évaluation déterministe)
        # ---------------------------------------------------------------------
        est_correct: Optional[bool] = None
        if reponse_eleve is not None:
            est_correct = catalogue.est_correct(exercice_id, reponse_eleve)

        # ---------------------------------------------------------------------
        # ÉTAPE 3 : REMONTÉE AUX PRÉREQUIS (Diagnostic de la marche manquante)
        # ---------------------------------------------------------------------
        lacune_identifiee, chaine_escalier = self.engine.diagnostiquer_marche_manquante(
            self.eleve_hmac, competence_objectif
        )
        
        # En cas d'erreur, la compétence active bascule sur la marche manquante
        if est_correct is False and lacune_identifiee:
            competence_active = lacune_identifiee
        else:
            competence_active = competence_exo

        # ---------------------------------------------------------------------
        # ÉTAPE 4 : EXPLICATION (Concept pédagogique pas-à-pas)
        # ---------------------------------------------------------------------
        meta_active = catalogue.get_exercice(catalogue.exercice_pour_competence(competence_active) or exercice_id)
        explication_concept = meta_active["explication_concept"] if meta_active else "Soustrayez les termes constants des deux côtés pour isoler la variable."

        # ---------------------------------------------------------------------
        # ÉTAPE 5 : MICRO-REMÉDIATION (Micro-exercice sur la marche manquante)
        # ---------------------------------------------------------------------
        exercice_remediation_id = catalogue.exercice_pour_competence(competence_active) or exercice_id

        # ---------------------------------------------------------------------
        # ÉTAPE 6 : VÉRIFICATION PAR LE MOTEUR (Strictement synchrone / Pas de LLM seul)
        # ---------------------------------------------------------------------
        nouvel_etat = EtatMaitrise.INCONNU
        if est_correct is not None:
            succes_consec = crud.compter_succes_consecutifs(self.db, self.eleve_hmac, competence_active)
            nouvel_etat = self.engine.evaluer_transition(
                eleve_pseudo=self.eleve_hmac,
                competence=competence_active,
                est_correct=est_correct,
                avec_aide=avec_aide,
                nombre_succes_consecutifs=succes_consec
            )

        # ---------------------------------------------------------------------
        # ÉTAPE 7 : RETOUR À L'OBJECTIF (Re-stabilisation de l'escalier)
        # ---------------------------------------------------------------------
        if est_correct is True:
            prochain_exo_id = catalogue.exercice_pour_competence(competence_objectif) or exercice_id
            message_tuteur = "Bravo ! La marche est consolidée. On reprend l'objectif principal."
        else:
            prochain_exo_id = exercice_remediation_id
            message_tuteur = "Ce n'est pas tout à fait ça. Reprenons la marche d'en dessous ensemble."

        # ---------------------------------------------------------------------
        # ÉTAPE 8 : MÉMOIRE (Enregistrement DB & Mise à jour des états)
        # ---------------------------------------------------------------------
        if est_correct is not None:
            crud.enregistrer_tentative(
                self.db,
                eleve_hmac=self.eleve_hmac,
                exercice_id=exercice_id,
                matiere=meta_exercice["matiere"] if meta_exercice else "maths",
                niveau=meta_exercice["niveau"] if meta_exercice else "5e",
                competence=competence_active,
                est_correct=est_correct,
                avec_aide=avec_aide
            )
            crud.upsert_etat(self.db, self.eleve_hmac, competence_active, nouvel_etat.value)

        # Numéro d'étape dans le pipeline (1 à 8)
        if est_correct is None:
            etape_num = 1
            nom_etape = "OBJECTIF"
        elif est_correct is False:
            etape_num = 5
            nom_etape = "MICRO_REMEDIATION"
        else:
            etape_num = 7
            nom_etape = "RETOUR_OBJECTIF"

        return {
            "etape_courante": etape_num,
            "nom_etape": nom_etape,
            "competence_objectif": competence_objectif,
            "competence_active": competence_active,
            "est_correct": est_correct,
            "etat_maitrise": nouvel_etat.value if est_correct is not None else "INCONNU",
            "exercice_courant_id": prochain_exo_id,
            "consigne": meta_active["enonce"] if meta_active else "Résolvez l'équation.",
            "message_tuteur": message_tuteur,
            "remediation": {
                "explication_concept": explication_concept,
                "exercice_prerequis": exercice_remediation_id,
                "competence_lacune": lacune_identifiee
            } if est_correct is False else None,
            "details_pipeline_8_etapes": {
                "1_objectif": competence_objectif,
                "2_analyse_erreur": "reponse_incorrecte" if est_correct is False else ("correcte" if est_correct is True else "non_fournie"),
                "3_remontee_prerequis": chaine_escalier,
                "4_explication": explication_concept,
                "5_micro_remediation": exercice_remediation_id,
                "6_verification_moteur": "OK_ENGINE_ONLY" if est_correct is not None else "EN_ATTENTE",
                "7_retour_objectif": prochain_exo_id,
                "8_memoire": "PERSISTE_DB" if est_correct is not None else "PRÊT"
            }
        }
