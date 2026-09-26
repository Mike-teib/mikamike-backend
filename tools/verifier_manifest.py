#!/usr/bin/env python3
"""
verifier_manifest.py — Vérifie un manifeste SHA-256 (« HASH  chemin » par ligne) contre
l'arbre courant. Accepte le format historique Windows (BOM, hash majuscule, « \\ »).

Statuts par fichier :
  MATCH        empreinte identique
  MATCH_CRLF   identique une fois les fins de ligne converties en CRLF (checkout Windows)
  CHANGED      contenu modifié depuis le manifeste
  MISSING      fichier absent
  OUTSIDE      chemin hors du dépôt (refusé)
Code retour : 0 si tout correspond, 1 sinon.
Usage : python -m tools.verifier_manifest SHA256_DEPOT_PREPARE.txt
"""

from __future__ import annotations

import hashlib
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

RACINE = Path(__file__).resolve().parent.parent


def lire(manifest: Path) -> List[Tuple[str, str]]:
    lignes = manifest.read_text(encoding="utf-8-sig").splitlines()
    out = []
    for ligne in lignes:
        if not ligne.strip():
            continue
        h, _, chemin = ligne.strip().partition("  ")
        out.append((h.lower(), chemin.replace("\\", "/").strip()))
    return out


def verifier(manifest: Path) -> Dict[str, str]:
    res = {}
    racine = RACINE.resolve()
    for h, chemin in lire(manifest):
        f = (RACINE / chemin).resolve()
        # Revue session 2 (R2-13) : « ../ » ou chemin absolu lisaient hors du dépôt.
        if racine not in f.parents:
            res[chemin] = "OUTSIDE"
            continue
        if not f.is_file():
            res[chemin] = "MISSING"
            continue
        data = f.read_bytes()
        if hashlib.sha256(data).hexdigest() == h:
            res[chemin] = "MATCH"
        elif hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest() == h:
            res[chemin] = "MATCH_CRLF"
        else:
            res[chemin] = "CHANGED"
    return res


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        return 2
    res = verifier(Path(argv[0]))
    for chemin, statut in sorted(res.items()):
        print(f"{statut:10} {chemin}")
    print(dict(Counter(res.values())))
    # Code retour non nul si une empreinte ne correspond pas (utilisable en CI).
    return 0 if all(v in ("MATCH", "MATCH_CRLF") for v in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
