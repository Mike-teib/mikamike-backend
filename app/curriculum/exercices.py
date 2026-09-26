"""
exercices.py — Schéma canonique d'un exercice et verrou de création.

Un exercice est TOUJOURS relié à : matière, niveau, programme, chapitre, notion
canonique, difficulté, objectif pédagogique, prérequis, source (preuve de la notion).

`creer_exercice` refuse (RefusCreation) si :
  - la notion n'existe pas ou ne franchit pas `autorisation_generation`
    (non prouvée, texte quarantiné/suspect, chapitre ambigu…) ;
  - matière / niveau / programme / chapitre incohérents avec la notion ;
  - un prérequis n'existe pas ;
  - énoncé ou réponse vide ; la réponse fuit dans l'énoncé ;
  - la réponse attendue n'est pas VALID pour son propre vérificateur ;
  - un exercice équivalent existe déjà (même empreinte exacte, ou même gabarit
    sur la même notion avec une réponse équivalente).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from app.curriculum import dedup
from app.curriculum.model import ID_CANONIQUE, IndexReferentiel, Matiere, Niveau
from app.curriculum.provenance import autorisation_generation
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.dispatch import TYPES_VERIFICATION, verifier


class Exercice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_CANONIQUE)
    notion_id: str = Field(pattern=ID_CANONIQUE)
    matiere: Matiere
    niveau: Niveau
    programme_id: str = Field(pattern=ID_CANONIQUE)
    chapitre_id: str = Field(pattern=ID_CANONIQUE)
    difficulte: int = Field(ge=1, le=5)
    objectif_pedagogique: str = Field(min_length=5, max_length=500)
    prerequis: Tuple[str, ...] = ()
    enonce: str = Field(min_length=3, max_length=3000)
    reponse_attendue: str = Field(min_length=1, max_length=500)
    type_verification: str
    parametres_verification: Dict[str, Any] = Field(default_factory=dict)
    indices: Tuple[str, ...] = Field(default=(), max_length=6, description="du plus léger au plus explicite")
    erreurs_frequentes: Dict[str, str] = Field(default_factory=dict, description="réponse fausse → diagnostic")
    source_sha256_extrait: str = Field(pattern=r"^[0-9a-f]{64}$")

    def empreinte(self) -> str:
        return dedup.empreinte_exacte(self.enonce, self.reponse_attendue)


class RefusCreation(ValueError):
    def __init__(self, raisons: List[str]):
        super().__init__(";".join(raisons))
        self.raisons = raisons


def valider_exercice(
    ex: Exercice,
    idx: IndexReferentiel,
    banque: Iterable[Exercice] = (),
    *,
    autoriser_fictif: bool = False,
) -> List[str]:
    raisons: List[str] = []
    notion = idx.notions.get(ex.notion_id)
    if notion is None:
        return ["notion_inconnue"]

    auto = autorisation_generation(notion, idx, autoriser_fictif=autoriser_fictif)
    if not auto.autorise:
        raisons.extend(f"notion_non_autorisee:{r}" for r in auto.raisons)

    if ex.matiere != notion.matiere:
        raisons.append("matiere_incoherente")
    if ex.niveau != notion.niveau:
        raisons.append("niveau_incoherent")
    if ex.programme_id != notion.programme_id:
        raisons.append("programme_incoherent")
    if ex.chapitre_id != notion.chapitre_id:
        raisons.append("chapitre_incoherent")
    if notion.preuve is None or ex.source_sha256_extrait != notion.preuve.sha256_extrait:
        raisons.append("source_incoherente")
    for pre in ex.prerequis:
        if pre not in idx.notions:
            raisons.append(f"prerequis_inconnu:{pre}")
    manquants = set(notion.prerequis) - set(ex.prerequis)
    if manquants:
        raisons.append("prerequis_de_la_notion_non_declares")

    if not ex.enonce.strip():
        raisons.append("enonce_vide")
    if not ex.reponse_attendue.strip():
        raisons.append("reponse_vide")
    elif len(dedup.normaliser(ex.reponse_attendue)) >= 2 and \
            dedup.normaliser(ex.reponse_attendue) in dedup.normaliser(ex.enonce):
        raisons.append("reponse_fuite_dans_enonce")

    if ex.type_verification not in TYPES_VERIFICATION:
        raisons.append("type_verification_inconnu")
    else:
        auto_check = verifier(ex.type_verification, ex.reponse_attendue, ex.reponse_attendue,
                              ex.parametres_verification)
        if auto_check.verdict != Verdict.VALID:
            raisons.append(f"reponse_attendue_non_verifiable:{auto_check.verdict.value}")
        for fausse in ex.erreurs_frequentes:
            r = verifier(ex.type_verification, ex.reponse_attendue, fausse, ex.parametres_verification)
            if r.verdict == Verdict.VALID:
                raisons.append("erreur_frequente_en_fait_correcte")

    for autre in banque:
        if autre.id == ex.id:
            raisons.append("id_deja_utilise")
        elif autre.empreinte() == ex.empreinte():
            raisons.append(f"doublon_exact:{autre.id}")
        elif autre.notion_id == ex.notion_id and \
                dedup.empreinte_gabarit(autre.enonce) == dedup.empreinte_gabarit(ex.enonce) and \
                autre.type_verification == ex.type_verification and \
                verifier(ex.type_verification, autre.reponse_attendue, ex.reponse_attendue,
                         ex.parametres_verification).verdict == Verdict.VALID:
            raisons.append(f"doublon_equivalent:{autre.id}")
    return raisons


def creer_exercice(
    ex: Exercice,
    idx: IndexReferentiel,
    banque: Optional[List[Exercice]] = None,
    *,
    autoriser_fictif: bool = False,
) -> Exercice:
    """Valide puis ajoute à la banque (liste mutable) ; lève RefusCreation sinon."""
    raisons = valider_exercice(ex, idx, banque or (), autoriser_fictif=autoriser_fictif)
    if raisons:
        raise RefusCreation(raisons)
    if banque is not None:
        banque.append(ex)
    return ex
