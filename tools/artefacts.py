"""
artefacts.py — Présence des artefacts réels attendus (session 5, ARTIFACTS_REQUIRED_MANIFEST.json).

    python -m tools.artefacts verifier [--dossier <lot>] [--requis ARTIFACTS_REQUIRED_MANIFEST.json]

Lit le IMPORT_MANIFEST.json du lot (sans rien importer) et indique, pour chaque artefact requis :
PRESENT, WAITING_FOR_ARTIFACT, ou SHA_DIFFERENT (empreinte épinglée connue et différente).
Codes retour : 0 tout présent · 4 au moins un WAITING_FOR_ARTIFACT · 3 empreinte différente ·
2 usage. Ce contrôle ne remplace pas l'import (tools.import_lot simuler), qui revérifie tout.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

RACINE = Path(__file__).resolve().parent.parent
REQUIS = RACINE / "ARTIFACTS_REQUIRED_MANIFEST.json"


def _roles(a: dict) -> List[str]:
    r = a["role_manifest"]
    return [r] if isinstance(r, str) else list(r)


def etat(requis: dict, dossier: Path | None) -> Dict[str, dict]:
    fichiers: List[dict] = []
    if dossier is not None and (dossier / "IMPORT_MANIFEST.json").is_file():
        m = json.loads((dossier / "IMPORT_MANIFEST.json").read_text("utf-8"))
        fichiers = [f for f in m.get("fichiers", []) if isinstance(f, dict)]
    out: Dict[str, dict] = {}
    for a in requis["artefacts"] + requis.get("complements_attendus", []):
        trouves = [f for f in fichiers if f.get("role") in _roles(a)]
        attendu = a.get("sha256_attendu")
        if not trouves:
            statut = "WAITING_FOR_ARTIFACT"
        elif attendu and all(f.get("sha256") != attendu for f in trouves):
            statut = "SHA_DIFFERENT"
        else:
            statut = "PRESENT"
        out[a["id"]] = {"statut": statut, "fichiers": sorted(f.get("chemin", "") for f in trouves),
                        "obligatoire": a in requis["artefacts"]}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools.artefacts")
    ap.add_argument("commande", choices=("verifier",))
    ap.add_argument("--dossier")
    ap.add_argument("--requis", default=str(REQUIS))
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2
    requis = json.loads(Path(args.requis).read_text("utf-8"))
    dossier = args.dossier or os.getenv("MIKA_ARTEFACTS_DIR")
    res = etat(requis, Path(dossier) if dossier else None)
    print(json.dumps({"dossier": dossier, "artefacts": res}, indent=2, ensure_ascii=False, sort_keys=True))
    obligatoires = [v["statut"] for v in res.values() if v["obligatoire"]]
    if "SHA_DIFFERENT" in obligatoires:
        return 3
    return 4 if "WAITING_FOR_ARTIFACT" in obligatoires else 0


if __name__ == "__main__":
    raise SystemExit(main())
