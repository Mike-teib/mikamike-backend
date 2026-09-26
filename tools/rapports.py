#!/usr/bin/env python3
"""
rapports.py — Génère les rapports reproductibles (backlog canonique + audit de
déduplication) à partir des données du dépôt, ou d'un dossier d'artefacts importé.

Usage :
  python -m tools.rapports                       # existant (notions migrées + catalogue)
  python -m tools.rapports --artefacts <dossier> [--sha-manifest <sha256>] [--rentree 2026]
                                                 # import strict (manifest v2 : --sha-manifest obligatoire)
  python -m tools.rapports --depot <racine>      # lot ACTIF du dépôt de contenu (revalidé)
  Options : --sortie reports/  (défaut)

Écrit : <sortie>/backlog.json, backlog.md, audit_dedup.json
Deux exécutions sur les mêmes données produisent des fichiers identiques.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Revue session 2 (R2-21) : plus de secret littéral de repli posé ici ; la chaîne de
# contenu (app.curriculum) n'importe aucun module qui lit les secrets applicatifs.
from app.curriculum.audit import auditer  # noqa: E402
from app.curriculum.backlog import calculer_backlog, en_markdown  # noqa: E402
from app.curriculum.importers import importer  # noqa: E402
from app.curriculum.legacy import migrer_existant  # noqa: E402
from app.curriculum.model import Referentiel  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artefacts", type=Path)
    ap.add_argument("--sortie", type=Path, default=Path("reports"))
    ap.add_argument("--sha-manifest", dest="sha_manifest")
    ap.add_argument("--rentree", type=int)
    ap.add_argument("--depot", type=Path)
    args = ap.parse_args(argv)

    if args.depot:
        from app.curriculum.depot import DepotContenu

        res = DepotContenu(args.depot).charger_actif()
        if res is None:
            print("[depot] aucun lot actif")
            return 1
        ref, exos, quiz, titre = res.referentiel, res.exercices, res.quiz, "Backlog canonique (lot actif)"
    elif args.artefacts:
        res = importer(args.artefacts, checkpoint=args.sortie / "import_checkpoint.json",
                       sha256_manifest=args.sha_manifest, rentree=args.rentree)
        print(f"[import] statut={res.statut} fichiers={len(res.fichiers)} anomalies={len(res.anomalies)}")
        if res.statut != "VALIDATED":
            for k, v in sorted(res.fichiers.items()):
                print(f"  {k}: {v}")
            for a in res.anomalies[:50]:
                print(f"  {a.code} {a.objet_id} {a.detail}")
            return 1
        ref, exos, quiz, titre = res.referentiel, res.exercices, res.quiz, "Backlog canonique (artefacts importés)"
    else:
        ref = Referentiel(notions=migrer_existant().notions)
        exos, quiz, titre = [], [], "Backlog canonique (existant du dépôt)"

    args.sortie.mkdir(parents=True, exist_ok=True)
    bl = calculer_backlog(ref, exos, quiz)
    (args.sortie / "backlog.json").write_text(json.dumps(bl, indent=2, sort_keys=True, ensure_ascii=False), "utf-8")
    (args.sortie / "backlog.md").write_text(en_markdown(bl, titre), "utf-8")
    au = auditer(ref, exos, quiz)
    (args.sortie / "audit_dedup.json").write_text(json.dumps(au, indent=2, sort_keys=True, ensure_ascii=False), "utf-8")
    print(json.dumps(bl["total"], ensure_ascii=False))
    print(json.dumps(au["totaux"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
