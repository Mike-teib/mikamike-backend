"""
Moteur de l'Escalier Pédagogique (Learning Engine) - MikaMike
=============================================================
Implémentation conforme aux contrats techniques V001 (LE-01 à LE-07).

Doctrine Pédagogique :
QUESTION -> VÉRIFICATION -> DIAGNOSTIC -> PRÉREQUIS -> GUIDAGE -> NOUVEL ESSAI -> AUTONOMIE -> MÉMOIRE -> RETEST
"""

import hmac
import hashlib
import time
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

# Aucune valeur par défaut de secret dans le code (fail-closed) : le sel de
# pseudonymisation est fourni par l'appelant, ou lu et validé via
# app.core.security_config.get_pseudo_secret quand il n'est pas passé.


class EtatMaitrise(str, Enum):
    """Les 7 états de maîtrise du Learning Engine (LE-03)."""
    INCONNU = "INCONNU"
    FRAGILE = "FRAGILE"
    EN_COURS = "EN_COURS"
    ACQUIS_ASSISTE = "ACQUIS_ASSISTE"
    ACQUIS_AUTONOME = "ACQUIS_AUTONOME"
    A_REVOIR = "A_REVOIR"
    MAITRISE = "MAITRISE"


# États considérés comme consolidés/solides
ETATS_SOLIDES = {EtatMaitrise.ACQUIS_AUTONOME, EtatMaitrise.MAITRISE}


class TypeEvt(str, Enum):
    """Types d'événements enregistrés dans le journal le_events (LE-01)."""
    QUESTION_POSEE = "question_posee"
    REPONSE_ELEVE = "reponse_eleve"
    VERIFICATION = "verification"
    INDICE_DONNE = "indice_donne"
    ESSAI = "essai"
    REUSSITE = "reussite"


class ResultatEvt(str, Enum):
    """Résultats d'un événement (LE-01)."""
    CORRECT = "correct"
    FAUX = "faux"
    ABSTENTION = "abstention"
    VIDE = ""


class LeEvent(BaseModel):
    """Représentation d'un événement d'apprentissage pseudonymisé (LE-01)."""
    id: Optional[int] = None
    ts: float = Field(default_factory=time.time)
    eleve_pseudo: str
    matiere: str
    niveau: str
    competence: str
    type_evt: TypeEvt
    resultat: ResultatEvt = ResultatEvt.VIDE
    avec_aide: bool = False
    exercice_ref: str = ""


# Graphe de prérequis de démonstration (LE-02) adossé aux programmes
GRAPHE_MATHS_COLLEGE: Dict[str, List[str]] = {
    "equations_1er_degre": ["calcul_litteral", "nombres_relatifs"],
    "calcul_litteral": ["expressions_algebriques", "priorites_operatoires"],
    "proportionnalite": ["fractions", "division_euclidienne"],
    "fractions": ["division_euclidienne", "multiplication"],
    "thales": ["proportionnalite", "triangles_semblables"],
    "pythagore_reciproque": ["pythagore_direct", "racine_carree"],
    "pythagore_direct": ["racine_carree", "puissances"],
}


def pseudonymiser_code(code_eleve: str, secret: Optional[str] = None) -> str:
    """
    Génère un pseudonyme sécurisé HMAC_SHA256 (LE-01).
    Jamais le prénom ni le code en clair dans les logs/événements.
    Si `secret` n'est pas fourni, il est lu et validé (fail-closed) via
    app.core.security_config.get_pseudo_secret — aucun repli faible.
    """
    if secret is None:
        from app.core.security_config import get_pseudo_secret
        secret = get_pseudo_secret()
    return hmac.new(secret.encode("utf-8"), code_eleve.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


class LearningEngine:
    """Moteur gérant les états de maîtrise, les prérequis et le diagnostic d'escalier."""

    def __init__(self, graphe_prerequis: Optional[Dict[str, List[str]]] = None):
        self.graphe = graphe_prerequis or GRAPHE_MATHS_COLLEGE
        # Stockage en mémoire (simulant la persistance base de données)
        self.etats_eleves: Dict[Tuple[str, str], EtatMaitrise] = {}  # (eleve_pseudo, competence) -> EtatMaitrise
        self.historique_events: List[LeEvent] = []

    def get_etat(self, eleve_pseudo: str, competence: str) -> EtatMaitrise:
        """Retourne l'état de maîtrise actuel d'un élève sur une compétence."""
        return self.etats_eleves.get((eleve_pseudo, competence), EtatMaitrise.INCONNU)

    def evaluer_transition(
        self,
        eleve_pseudo: str,
        competence: str,
        est_correct: bool,
        avec_aide: bool = False,
        nombre_succes_consecutifs: int = 1
    ) -> EtatMaitrise:
        """
        Détermine le nouvel état de maîtrise d'une notion selon l'évaluation et l'historique.

        RÈGLE ABSOLUE (LE-06) :
        Une réponse correcte OBTENUE AVEC AIDE ne fait JAMAIS passer une notion à MAITRISE.
        Au mieux ACQUIS_ASSISTE.
        """
        etat_actuel = self.get_etat(eleve_pseudo, competence)

        if est_correct:
            if avec_aide:
                # Avec aide -> Plafonnement strict à ACQUIS_ASSISTE (LE-06)
                nouvel_etat = EtatMaitrise.ACQUIS_ASSISTE
            else:
                # Sans aide (Autonome)
                if etat_actuel in {EtatMaitrise.INCONNU, EtatMaitrise.FRAGILE, EtatMaitrise.A_REVOIR}:
                    nouvel_etat = EtatMaitrise.EN_COURS
                elif etat_actuel == EtatMaitrise.EN_COURS:
                    nouvel_etat = EtatMaitrise.ACQUIS_AUTONOME
                elif etat_actuel in {EtatMaitrise.ACQUIS_ASSISTE, EtatMaitrise.ACQUIS_AUTONOME}:
                    if nombre_succes_consecutifs >= 2:
                        nouvel_etat = EtatMaitrise.MAITRISE
                    else:
                        nouvel_etat = EtatMaitrise.ACQUIS_AUTONOME
                else:
                    nouvel_etat = EtatMaitrise.MAITRISE
        else:
            # En cas d'échec
            if etat_actuel in {EtatMaitrise.MAITRISE, EtatMaitrise.ACQUIS_AUTONOME}:
                nouvel_etat = EtatMaitrise.A_REVOIR
            elif etat_actuel in {EtatMaitrise.ACQUIS_ASSISTE, EtatMaitrise.EN_COURS}:
                nouvel_etat = EtatMaitrise.FRAGILE
            else:
                nouvel_etat = EtatMaitrise.FRAGILE

        self.etats_eleves[(eleve_pseudo, competence)] = nouvel_etat
        return nouvel_etat

    def enregistrer_evenement(
        self,
        eleve_pseudo: str,
        matiere: str,
        niveau: str,
        competence: str,
        type_evt: TypeEvt,
        resultat: ResultatEvt = ResultatEvt.VIDE,
        avec_aide: bool = False,
        exercice_ref: str = ""
    ) -> LeEvent:
        """Enregistre un événement conforme au schéma LE-01."""
        evt = LeEvent(
            id=len(self.historique_events) + 1,
            ts=time.time(),
            eleve_pseudo=eleve_pseudo,
            matiere=matiere,
            niveau=niveau,
            competence=competence,
            type_evt=type_evt,
            resultat=resultat,
            avec_aide=avec_aide,
            exercice_ref=exercice_ref
        )
        self.historique_events.append(evt)
        return evt

    def diagnostiquer_marche_manquante(
        self,
        eleve_pseudo: str,
        competence_cible: str
    ) -> Tuple[Optional[str], List[str]]:
        """
        Remonte le graphe de prérequis (l'Escalier de Mika) pour identifier
        le premier prérequis non maîtrisé (la 'marche manquante').

        Retourne : (premiere_lacune, chaine_remontee)
        """
        visites: Set[str] = set()
        chaine_remontee: List[str] = []

        def explorer(comp: str) -> Optional[str]:
            if comp in visites:
                return None
            visites.add(comp)
            chaine_remontee.append(comp)

            prerequis_list = self.graphe.get(comp, [])
            for pre in prerequis_list:
                etat_pre = self.get_etat(eleve_pseudo, pre)
                # Si le prérequis n'est pas solide (non autonome / non maîtrisé)
                if etat_pre not in ETATS_SOLIDES:
                    lacune_sous_jacente = explorer(pre)
                    return lacune_sous_jacente or pre

            return None

        lacune = explorer(competence_cible)
        return lacune, chaine_remontee
