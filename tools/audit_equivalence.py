#!/usr/bin/env python3
"""
audit_equivalence.py — R6 : rapport d'audit symbolique du catalogue historique (LECTURE SEULE).

  python -m tools.audit_equivalence [--sortie reports/equivalence]

Écrit `equivalence.json` (détail) et `equivalence.md` (synthèse), déterministes. Code retour
1 si un FAUX POSITIF historique est trouvé (réponse non équivalente acceptée aujourd'hui).
Aucune donnée du catalogue n'est modifiée : les corrections relèvent d'une décision humaine (D5).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    from app.api.v1.mikamike import catalogue
    from app.curriculum.equivalence import Constat, auditer_catalogue, synthese

    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default="reports/equivalence")
    args = ap.parse_args(argv)
    # Référence = correcteur HISTORIQUE par chaînes (la correction symbolique D5 s'y ajoute).
    rapports = auditer_catalogue(catalogue.EXERCICES, catalogue.est_correct_chaine)
    out = Path(args.sortie)
    out.mkdir(parents=True, exist_ok=True)
    detail = [{**{k: v for k, v in dataclasses.asdict(r).items() if k != "lignes"},
               "lignes": [{**dataclasses.asdict(ligne), "decision": ligne.decision.value,
                           "constat": ligne.constat.value} for ligne in r.lignes]} for r in rapports]
    (out / "equivalence.json").write_text(json.dumps({"synthese": synthese(rapports), "exercices": detail},
                                                     ensure_ascii=False, indent=2, sort_keys=True), "utf-8")
    md = ["# Audit symbolique du catalogue historique (R6, lecture seule)", "",
          "| Clé | Nombre |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in synthese(rapports).items()]
    for r in rapports:
        md += ["", f"## {r.exercice_id} — {r.enonce}", f"Forme attendue (consigne) : `{r.forme_consigne}` · "
               f"réponses acceptées : {r.attendues} · {r.coherence_attendues}", "",
               "| Réponse | Historique | Symbolique | Décision | Constat | Raison |", "|---|---|---|---|---|---|"]
        md += [f"| `{ligne.reponse.strip()}` | {'acceptée' if ligne.historique_accepte else 'refusée'} | "
               f"{ligne.symbolique} | {ligne.decision.value} | {ligne.constat.value} | {ligne.raison} |"
               for ligne in r.lignes]
    (out / "equivalence.md").write_text("\n".join(md) + "\n", "utf-8")
    faux_positifs = sum(1 for r in rapports for ligne in r.lignes if ligne.constat == Constat.FAUX_POSITIF_HISTORIQUE)
    print(json.dumps(synthese(rapports), ensure_ascii=False))
    return 1 if faux_positifs else 0


if __name__ == "__main__":
    sys.exit(main())
