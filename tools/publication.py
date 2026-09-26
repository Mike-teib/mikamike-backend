#!/usr/bin/env python3
"""
publication.py — Outil opérateur de la garde de publication (app/curriculum/publication.py).

  python -m tools.publication etat    --depot <racine>
  python -m tools.publication publier <contenu_id> --depot <racine> --operateur <nom>
  python -m tools.publication retirer <contenu_id> --depot <racine> --operateur <nom>

Le lot ACTIF du dépôt est revalidé à chaque commande (empreinte épinglée). Aucune publication
n'est possible pour un contenu qui n'est pas READY_FOR_PUBLICATION.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    from app.curriculum.depot import DepotContenu, DepotInvalide
    from app.curriculum.publication import PublicationRefusee, RegistrePublication, evaluer

    ap = argparse.ArgumentParser(prog="tools.publication")
    ap.add_argument("commande", choices=("etat", "publier", "retirer"))
    ap.add_argument("contenu_id", nargs="?")
    ap.add_argument("--depot", required=True)
    ap.add_argument("--operateur")
    args = ap.parse_args(argv)
    try:
        res = DepotContenu(Path(args.depot)).charger_actif()
    except DepotInvalide as exc:
        print(f"erreur: {exc}", file=sys.stderr)
        return 1
    if res is None:
        print("erreur: aucun lot actif", file=sys.stderr)
        return 1
    reg = RegistrePublication(Path(args.depot))
    try:
        if args.commande == "etat":
            for cid, ev in sorted(evaluer(res, reg.publies()).items()):
                print(json.dumps({"contenu_id": cid, "etat": ev.etat.value, "raisons": list(ev.raisons)},
                                 ensure_ascii=False))
            return 0
        if not args.contenu_id or not args.operateur:
            print("erreur: contenu_id et --operateur requis", file=sys.stderr)
            return 2
        if args.commande == "publier":
            print(reg.publier(res, args.contenu_id, args.operateur).etat.value)
        else:
            reg.retirer(args.contenu_id, args.operateur)
            print("retire")
        return 0
    except PublicationRefusee as exc:
        print(f"refus: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
