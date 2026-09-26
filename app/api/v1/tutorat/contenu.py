"""
contenu.py — Fournisseur de contenus du tuteur (exercice validé + plan de guidage validé).

Fail-closed : un exercice n'est servi que s'il franchit `valider_exercice` (notion PROVEN,
texte recalculé utilisable, cohérences, vérificateur) ET si son plan franchit
`valider_plan(..., exiger_cle_comprehension=True)`. Sinon : ContenuIndisponible.

Aujourd'hui aucun contenu réel PROVEN n'existe dans le dépôt (artefacts absents) :
le catalogue par défaut est VIDE ⇒ `/mika/session/start` répond 404. Les tests
installent un catalogue FICTIF (`autoriser_fictif=True`), interdit en production.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

from app.curriculum.exercices import Exercice, valider_exercice
from app.curriculum.model import IndexReferentiel, Referentiel
from app.curriculum.pedagogie.tuteur import PlanGuidage, valider_plan


class ContenuIndisponible(LookupError):
    def __init__(self, raisons: List[str]):
        super().__init__(";".join(raisons))
        self.raisons = raisons


class CatalogueTutorat:
    def __init__(self, referentiel: Referentiel, exercices: List[Exercice],
                 plans: Dict[str, PlanGuidage], *, autoriser_fictif: bool = False):
        if autoriser_fictif and os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod"):
            raise ValueError("contenu_fictif_interdit_en_production")
        self.idx: IndexReferentiel = referentiel.index()
        self.autoriser_fictif = autoriser_fictif
        self.exercices = {e.id: e for e in exercices}
        self.plans = dict(plans)

    def obtenir(self, exercice_id: str) -> Tuple[Exercice, PlanGuidage]:
        ex = self.exercices.get(exercice_id)
        plan = self.plans.get(exercice_id)
        if ex is None or plan is None:
            raise ContenuIndisponible(["exercice_inconnu"])
        autres = [e for e in self.exercices.values() if e.id != ex.id]
        raisons = valider_exercice(ex, self.idx, autres, autoriser_fictif=self.autoriser_fictif)
        raisons += valider_plan(plan, ex, exiger_cle_comprehension=True)
        if raisons:
            raise ContenuIndisponible(raisons)
        return ex, plan


_CATALOGUE: Optional[CatalogueTutorat] = None


def definir_catalogue(catalogue: Optional[CatalogueTutorat]) -> None:
    global _CATALOGUE
    _CATALOGUE = catalogue


def catalogue() -> CatalogueTutorat:
    return _CATALOGUE if _CATALOGUE is not None else CatalogueTutorat(Referentiel(), [], {})
