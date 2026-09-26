#!/usr/bin/env python3
"""
content_check.py — Garde-fou de contenu exécuté en CI (hors ligne, déterministe).

1. Le référentiel FICTIF de démonstration est structurellement valide.
2. Hors mode test, aucune notion adossée à une source fictive n'est autorisée
   à la génération (les fixtures ne peuvent pas passer pour du réel).
3. L'existant (parcours/curriculum_dataset.py) est migré sans rien inventer et
   son backlog est calculé (toutes les notions attendent une source).
4. Cohérence du catalogue historique d'exercices : les réponses acceptées d'un
   même exercice sont mathématiquement équivalentes entre elles.

Sortie 0 si tout est conforme ; 1 sinon.
Usage : python -m tools.content_check
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("MIKA_PSEUDO_SECRET", "content-check-only-not-a-secret-000")

from app.api.v1.mikamike.catalogue import EXERCICES  # noqa: E402
from app.curriculum.backlog import calculer_backlog  # noqa: E402
from app.curriculum.fixtures import referentiel_fictif  # noqa: E402
from app.curriculum.legacy import migrer_existant  # noqa: E402
from app.curriculum.model import Referentiel  # noqa: E402
from app.curriculum.provenance import autorisation_generation  # noqa: E402
from app.curriculum.structure import valider_referentiel  # noqa: E402
from app.curriculum.verifiers.base import Verdict  # noqa: E402
from app.curriculum.verifiers.maths import equivalents  # noqa: E402


def main() -> int:
    echecs = []

    ref = referentiel_fictif()
    anomalies = valider_referentiel(ref)
    print(f"[fixtures] anomalies structurelles : {len(anomalies)}")
    if anomalies:
        echecs.append("fixtures_invalides")

    idx = ref.index()
    fuites = [n.id for n in ref.notions if autorisation_generation(n, idx).autorise]
    print(f"[fixtures] notions fictives autorisées hors mode test : {len(fuites)}")
    if fuites:
        echecs.append("fixture_prouvable_en_production")

    mig = migrer_existant()
    legacy = Referentiel(notions=mig.notions)
    bl = calculer_backlog(legacy)
    t = bl["total"]
    print(f"[existant] notions migrées : {len(mig.notions)} ; non migrables : {len(mig.non_migrables)}")
    print(f"[existant] PROVEN={t['PROVEN']} WAITING_SOURCE={t['WAITING_SOURCE']} "
          f"NEED_EXERCISE={t['NEED_EXERCISE']}")
    if t["PROVEN"] != 0:
        echecs.append("notion_existante_prouvee_sans_source")

    incoherents = []
    for exo_id, meta in sorted(EXERCICES.items()):
        reps = [r.split("=")[-1] for r in meta["reponses_acceptees"]]
        for r in reps[1:]:
            if equivalents(reps[0], r).verdict != Verdict.VALID:
                incoherents.append(f"{exo_id}:{reps[0]}≠{r}")
        if meta.get("exercice_prerequis") == exo_id:
            print(f"[catalogue] info : {exo_id} est son propre prérequis (marche de base)")
    print(f"[catalogue] réponses acceptées incohérentes : {len(incoherents)}")
    if incoherents:
        echecs.append("catalogue_incoherent:" + ";".join(incoherents))

    if echecs:
        print("ÉCHEC :", ", ".join(echecs))
        return 1
    print("OK — contenu conforme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
