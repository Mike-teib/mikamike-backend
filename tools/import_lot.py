#!/usr/bin/env python3
"""
import_lot.py — Import d'un lot d'artefacts RÉELS en deux temps (IMPORT_CONTRACT.md §7).

  python -m tools.import_lot simuler --dossier <lot> --sha <sha-épinglé> [--depot <racine>]
                                     [--rentree 2026] [--sortie <dir>]
  python -m tools.import_lot publier --dossier <lot> --sha <sha-épinglé> --depot <racine> --confirmer

`simuler` n'écrit que le rapport (JSON + Markdown) ; code 0 si VALIDATED, 1 sinon.
`publier` refait la simulation et n'active le lot que s'il est VALIDATED et que `--confirmer`
est donné. Rollback : `DepotContenu(<racine>).rollback()`. Les artefacts ne sont jamais commités.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    from app.curriculum.depot import DepotContenu, DepotInvalide
    from app.curriculum.rapport_import import en_markdown, simuler

    ap = argparse.ArgumentParser(prog="tools.import_lot")
    ap.add_argument("commande", choices=("simuler", "publier"))
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--depot")
    ap.add_argument("--rentree", type=int)
    ap.add_argument("--sortie")
    ap.add_argument("--confirmer", action="store_true")
    ap.add_argument("--autoriser-fictif", action="store_true", help="TESTS UNIQUEMENT (lots synthétiques)")
    a = ap.parse_args(argv)
    rapport = simuler(Path(a.dossier), a.sha, depot=Path(a.depot) if a.depot else None, rentree=a.rentree,
                      autoriser_fictif=a.autoriser_fictif)
    if a.sortie:
        out = Path(a.sortie)
        out.mkdir(parents=True, exist_ok=True)
        (out / "rapport_import.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2, sort_keys=True),
                                                 "utf-8")
        (out / "rapport_import.md").write_text(en_markdown(rapport), "utf-8")
    print(json.dumps({"statut": rapport["statut"], "publiable": rapport["publiable"],
                      "metriques": rapport.get("metriques", {})}, ensure_ascii=False))
    if a.commande == "simuler":
        return 0 if rapport["publiable"] else 1
    if not a.depot or not a.confirmer:
        print("erreur: publier exige --depot et --confirmer", file=sys.stderr)
        return 2
    if not rapport["publiable"]:
        print("refus: lot non VALIDATED (voir le rapport)", file=sys.stderr)
        return 1
    try:
        DepotContenu(Path(a.depot), autoriser_fictif=a.autoriser_fictif).publier(Path(a.dossier), a.sha)
    except DepotInvalide as exc:
        print(f"refus: {exc}", file=sys.stderr)
        return 1
    print("lot activé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
