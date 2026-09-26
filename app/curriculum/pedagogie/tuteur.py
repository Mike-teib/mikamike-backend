"""
tuteur.py — Professeur virtuel Mika : machine à états pédagogique déterministe.

Démarche (dans cet ordre) :
  1. identifier ce que l'élève sait (état des prérequis) ;
  2. identifier le blocage (erreur fréquente reconnue ou non) ;
  3. poser une question intermédiaire ;
  4. donner un indice (gradué, du plus léger au plus explicite) ;
  5. laisser réessayer ;
  6. expliquer avec une AUTRE méthode ;
  7. vérifier la compréhension (après une réussite obtenue avec aide) ;
  8. proposer un exercice de consolidation.

Garanties (testées) :
  - jamais la solution d'emblée : aucun message ne contient la réponse attendue
    avant la correction commentée, proposée seulement quand toutes les aides
    sont épuisées ;
  - jamais deux fois le même message ;
  - on n'avance pas si un prérequis manque (remédiation d'abord) ;
  - monotonie : plus d'aide ⇒ difficulté proposée non croissante ;
  - LE-06 : une réussite avec aide n'est jamais « autonome ».
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, List, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from app.curriculum import dedup
from app.curriculum.exercices import Exercice
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.dispatch import verifier

ETATS_PREREQUIS_SOLIDES = frozenset({"ACQUIS_AUTONOME", "MAITRISE"})
MAX_REFORMULATIONS = 2


class Action(str, Enum):
    REMEDIER_PREREQUIS = "REMEDIER_PREREQUIS"
    PRESENTER_EXERCICE = "PRESENTER_EXERCICE"
    IDENTIFIER_BLOCAGE = "IDENTIFIER_BLOCAGE"
    QUESTION_INTERMEDIAIRE = "QUESTION_INTERMEDIAIRE"
    DONNER_INDICE = "DONNER_INDICE"
    LAISSER_REESSAYER = "LAISSER_REESSAYER"
    AUTRE_METHODE = "AUTRE_METHODE"
    VERIFIER_COMPREHENSION = "VERIFIER_COMPREHENSION"
    CONSOLIDATION = "CONSOLIDATION"
    DEMANDER_REFORMULATION = "DEMANDER_REFORMULATION"
    CORRECTION_COMMENTEE = "CORRECTION_COMMENTEE"
    REVUE_HUMAINE = "REVUE_HUMAINE"


class PlanGuidage(BaseModel):
    """Ressources pédagogiques d'un exercice (rédigées/validées en amont)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    questions_intermediaires: Tuple[str, ...] = ()
    methodes_alternatives: Tuple[str, ...] = Field(default=(), description="chaque entrée = une autre méthode")
    question_comprehension: str = ""
    correction_commentee: str = Field(min_length=1)
    exercice_consolidation_id: Optional[str] = None
    # Clé de correction de la question de compréhension (vérifiée CÔTÉ SERVEUR : on ne
    # croit jamais un « j'ai compris » déclaré par le client). Vide = non vérifiable.
    reponse_comprehension: str = Field(default="", max_length=500)
    type_verification_comprehension: Optional[str] = None


class TransitionInvalide(ValueError):
    """Action demandée incompatible avec l'état du tutorat (ex. compréhension non demandée)."""


def valider_plan(plan: PlanGuidage, ex: Exercice, *, exiger_cle_comprehension: bool = False) -> List[str]:
    """Le plan ne doit ni divulguer la réponse avant la correction, ni se répéter."""
    raisons: List[str] = []
    rep = dedup.normaliser(ex.reponse_attendue)
    aides = list(ex.indices) + list(plan.questions_intermediaires) + list(plan.methodes_alternatives)
    if plan.question_comprehension:
        aides.append(plan.question_comprehension)
    # Les diagnostics d'erreurs fréquentes sont affichés AVANT la correction : ils ne
    # doivent pas non plus divulguer la réponse (revue session 2, finding R2-09).
    diagnostics = list(ex.erreurs_frequentes.values())
    for texte in aides + diagnostics:
        if len(rep) >= 1 and _contient_reponse(texte, rep):
            raisons.append("aide_divulgue_la_reponse")
            break
    normes = [dedup.normaliser(t) for t in aides]
    if len(set(normes)) != len(normes):
        raisons.append("aides_repetees")
    if not ex.indices and not plan.questions_intermediaires and not plan.methodes_alternatives:
        raisons.append("aucune_aide_disponible")
    if plan.question_comprehension and plan.reponse_comprehension:
        cle = dedup.normaliser(plan.reponse_comprehension)
        if cle and _contient_reponse(plan.question_comprehension, cle):
            raisons.append("question_comprehension_divulgue_sa_reponse")
    if exiger_cle_comprehension and plan.question_comprehension and not plan.reponse_comprehension:
        raisons.append("comprehension_non_verifiable")
    return raisons


def _contient_reponse(texte: str, reponse_norm: str) -> bool:
    """La réponse apparaît comme jeton isolé (évite « 7 » trouvé dans « 7/10 »)."""
    t = dedup.normaliser(texte)
    i = t.find(reponse_norm)
    n = len(reponse_norm)
    while i >= 0:
        avant = t[i - 2:i] if i >= 2 else (" " + t[:i])[-2:]
        apres = t[i + n:i + n + 2] + "  "
        # Frontière : pas de caractère alphanumérique collé, ni de décimale/fraction qui
        # prolonge le nombre (« 0,7 » est dans « 0,75 » ou « 10,7 » mais pas dans « 0,7, »).
        colle_avant = avant[-1].isalnum() or (avant[-1] in ",./" and avant[0].isdigit())
        colle_apres = apres[0].isalnum() or (apres[0] in ",./" and apres[1].isdigit())
        if not colle_avant and not colle_apres:
            return True
        i = t.find(reponse_norm, i + 1)
    return False


@dataclass(frozen=True)
class EtatTutorat:
    exercice_id: str
    tentatives: int = 0
    erreurs: Tuple[str, ...] = ()
    erreurs_frequentes_vues: Tuple[str, ...] = ()
    indices_donnes: int = 0
    questions_posees: int = 0
    methodes_donnees: int = 0
    reformulations: int = 0
    avec_aide: bool = False
    resolu: bool = False
    comprehension_verifiee: Optional[bool] = None
    prerequis_manquant: Optional[str] = None
    niveau_estime: str = "INCONNU"
    messages: Tuple[str, ...] = ()
    termine: bool = False
    attend_comprehension: bool = False

    @property
    def niveau_aide(self) -> int:
        return self.indices_donnes + self.questions_posees + 2 * self.methodes_donnees


@dataclass(frozen=True)
class Reponse:
    action: Action
    message: str
    difficulte_proposee: int
    exercice_id: Optional[str] = None
    notion_cible: Optional[str] = None
    donnees: Dict[str, object] = field(default_factory=dict)


class TuteurMika:
    def __init__(self, exercice: Exercice, plan: PlanGuidage):
        problemes = valider_plan(plan, exercice)
        if problemes:
            raise ValueError(f"plan_de_guidage_invalide:{','.join(problemes)}")
        self.ex = exercice
        self.plan = plan

    # ------------------------------------------------------------------ utils
    def _difficulte(self, etat: EtatTutorat) -> int:
        """Monotone : plus d'aide ⇒ difficulté non croissante (plancher 1)."""
        return max(1, self.ex.difficulte - etat.niveau_aide // 2)

    def _emettre(self, etat: EtatTutorat, action: Action, message: str, **kw) -> Tuple[EtatTutorat, Reponse]:
        # Anti-répétition : un message déjà donné n'est jamais redonné tel quel.
        if message in etat.messages:
            message = f"{message} (reformulons autrement : décris-moi ton raisonnement étape par étape.)"
            if message in etat.messages:
                action, message = Action.REVUE_HUMAINE, "Je préviens ton professeur pour qu'il t'aide directement."
                etat = replace(etat, termine=True)
        etat = replace(etat, messages=etat.messages + (message,))
        return etat, Reponse(action, message, self._difficulte(etat), **kw)

    # -------------------------------------------------------------- démarrage
    def demarrer(self, maitrise_prerequis: Mapping[str, str]) -> Tuple[EtatTutorat, Reponse]:
        """Étape 1 : ce que l'élève sait. Un prérequis non solide bloque l'avancée."""
        etat = EtatTutorat(exercice_id=self.ex.id)
        for pre in self.ex.prerequis:
            if maitrise_prerequis.get(pre, "INCONNU") not in ETATS_PREREQUIS_SOLIDES:
                etat = replace(etat, prerequis_manquant=pre, termine=True)
                return self._emettre(
                    etat, Action.REMEDIER_PREREQUIS,
                    "Avant cet exercice, on consolide une notion dont il a besoin.",
                    notion_cible=pre,
                )
        acquis = [p for p in self.ex.prerequis if maitrise_prerequis.get(p) in ETATS_PREREQUIS_SOLIDES]
        return self._emettre(etat, Action.PRESENTER_EXERCICE, self.ex.enonce,
                             exercice_id=self.ex.id, donnees={"prerequis_acquis": acquis})

    # ------------------------------------------------------------- réponses
    def repondre(self, etat: EtatTutorat, reponse: str) -> Tuple[EtatTutorat, Reponse]:
        if etat.termine:
            return etat, Reponse(Action.REVUE_HUMAINE, "Séance déjà terminée.", self._difficulte(etat))
        if not (reponse or "").strip():
            invitation = "Écris ta proposition, même si tu n'es pas sûr : on part de là."
            if invitation in etat.messages:
                # Deuxième réponse vide : l'élève est bloqué, on l'aide (sans compter d'erreur).
                return self._escalader(replace(etat, avec_aide=True))
            return self._emettre(etat, Action.LAISSER_REESSAYER, invitation)

        res = verifier(self.ex.type_verification, self.ex.reponse_attendue, reponse,
                       self.ex.parametres_verification)
        if res.verdict == Verdict.VALID:
            return self._succes(etat)
        if res.verdict in (Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW):
            etat = replace(etat, reformulations=etat.reformulations + 1)
            if etat.reformulations > MAX_REFORMULATIONS:
                return self._emettre(replace(etat, termine=True), Action.REVUE_HUMAINE,
                                     "Je n'arrive pas à lire ta réponse ; ton professeur va regarder avec toi.")
            return self._emettre(etat, Action.DEMANDER_REFORMULATION,
                                 "Je ne suis pas sûr de bien lire ta réponse : peux-tu l'écrire autrement ?")
        return self._erreur(etat, reponse)

    def demander_aide(self, etat: EtatTutorat) -> Tuple[EtatTutorat, Reponse]:
        if etat.termine:
            return etat, Reponse(Action.REVUE_HUMAINE, "Séance déjà terminée.", self._difficulte(etat))
        return self._escalader(replace(etat, avec_aide=True))

    def repondre_comprehension(self, etat: EtatTutorat, correcte: bool) -> Tuple[EtatTutorat, Reponse]:
        # Seulement en réponse à VERIFIER_COMPREHENSION : sinon « j'ai compris » permettait
        # de clore un exercice jamais résolu (revue session 2, finding R2-08).
        if etat.termine or not etat.attend_comprehension:
            raise TransitionInvalide("comprehension_non_demandee")
        etat = replace(etat, comprehension_verifiee=correcte, attend_comprehension=False)
        if correcte:
            return self._consolider(etat)
        if etat.methodes_donnees < len(self.plan.methodes_alternatives):
            return self._autre_methode(etat)
        return self._consolider(etat)

    def repondre_comprehension_texte(self, etat: EtatTutorat, reponse: str) -> Tuple[EtatTutorat, Reponse]:
        """Vérifie la réponse à la question de compréhension avec la clé du plan."""
        if not self.plan.reponse_comprehension:
            raise TransitionInvalide("comprehension_non_verifiable")
        type_v = self.plan.type_verification_comprehension or self.ex.type_verification
        res = verifier(type_v, self.plan.reponse_comprehension, reponse, self.ex.parametres_verification)
        return self.repondre_comprehension(etat, res.verdict == Verdict.VALID)

    # -------------------------------------------------------------- interne
    def _succes(self, etat: EtatTutorat) -> Tuple[EtatTutorat, Reponse]:
        etat = replace(etat, resolu=True,
                       niveau_estime="ACQUIS_ASSISTE" if etat.avec_aide else "ACQUIS_AUTONOME")
        if etat.avec_aide and self.plan.question_comprehension:
            return self._emettre(replace(etat, attend_comprehension=True),
                                 Action.VERIFIER_COMPREHENSION, self.plan.question_comprehension)
        return self._consolider(etat)

    def _consolider(self, etat: EtatTutorat) -> Tuple[EtatTutorat, Reponse]:
        etat = replace(etat, termine=True)
        msg = "Bravo ! Un exercice de consolidation pour ancrer la méthode." if etat.resolu else \
            "On consolide avec un exercice proche, un peu plus guidé."
        return self._emettre(etat, Action.CONSOLIDATION, msg,
                             exercice_id=self.plan.exercice_consolidation_id)

    def _erreur(self, etat: EtatTutorat, reponse: str) -> Tuple[EtatTutorat, Reponse]:
        cle = dedup.normaliser(reponse)
        diag = next((d for r, d in self.ex.erreurs_frequentes.items() if dedup.normaliser(r) == cle), None)
        etat = replace(etat, tentatives=etat.tentatives + 1, erreurs=etat.erreurs + (cle,))
        if diag and diag not in etat.erreurs_frequentes_vues:
            etat = replace(etat, erreurs_frequentes_vues=etat.erreurs_frequentes_vues + (diag,))
            return self._emettre(etat, Action.IDENTIFIER_BLOCAGE, f"Je crois voir le blocage : {diag}.",
                                 donnees={"erreur_frequente": diag})
        if etat.tentatives == 1 and not diag:
            return self._emettre(etat, Action.IDENTIFIER_BLOCAGE,
                                 "Ce n'est pas encore ça. Qu'as-tu fait en premier ?")
        return self._escalader(replace(etat, avec_aide=True))

    def _escalader(self, etat: EtatTutorat) -> Tuple[EtatTutorat, Reponse]:
        """Question intermédiaire → indices gradués → autre méthode → correction commentée."""
        if etat.questions_posees < len(self.plan.questions_intermediaires):
            q = self.plan.questions_intermediaires[etat.questions_posees]
            return self._emettre(replace(etat, questions_posees=etat.questions_posees + 1, avec_aide=True),
                                 Action.QUESTION_INTERMEDIAIRE, q)
        if etat.indices_donnes < len(self.ex.indices):
            ind = self.ex.indices[etat.indices_donnes]
            return self._emettre(replace(etat, indices_donnes=etat.indices_donnes + 1, avec_aide=True),
                                 Action.DONNER_INDICE, f"Indice : {ind} Réessaie.")
        if etat.methodes_donnees < len(self.plan.methodes_alternatives):
            return self._autre_methode(etat)
        etat = replace(etat, avec_aide=True, termine=True, niveau_estime="FRAGILE")
        return self._emettre(etat, Action.CORRECTION_COMMENTEE, self.plan.correction_commentee,
                             exercice_id=self.plan.exercice_consolidation_id)

    def _autre_methode(self, etat: EtatTutorat) -> Tuple[EtatTutorat, Reponse]:
        m = self.plan.methodes_alternatives[etat.methodes_donnees]
        return self._emettre(replace(etat, methodes_donnees=etat.methodes_donnees + 1, avec_aide=True),
                             Action.AUTRE_METHODE, f"Essayons une autre méthode : {m}")
