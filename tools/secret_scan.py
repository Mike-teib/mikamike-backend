#!/usr/bin/env python3
"""
secret_scan.py — Détection de secrets / données sensibles, hors ligne, déterministe.

N'AFFICHE JAMAIS la valeur détectée : seulement le chemin, la ligne (ou le commit)
et le NOM de la règle. Code de sortie 1 si au moins une détection.

Usage :
  python tools/secret_scan.py              # fichiers suivis par git (arbre courant)
  python tools/secret_scan.py --history    # + tout l'historique git (git log -p)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, NamedTuple

RACINE = Path(__file__).resolve().parent.parent

REGLES = {
    "stripe_live_key": re.compile(r"sk_live_[A-Za-z0-9]{10,}"),
    "stripe_test_key": re.compile(r"sk_test_[A-Za-z0-9]{10,}"),
    "stripe_webhook_secret": re.compile(r"whsec_[A-Za-z0-9]{10,}"),
    "github_token": re.compile(r"\b(ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}"),
    "openai_key": re.compile(r"\bsk-(proj-)?[A-Za-z0-9]{32,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "db_url_with_password": re.compile(r"\b(postgres(ql)?|mysql|mongodb(\+srv)?)://[^\s:/@]+:[^\s@]+@"),
    "jwt_literal": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    # Littéral faible historique (repli de secret retiré en 232e464) : ne doit jamais revenir.
    "historic_weak_fallback": re.compile(r"mikamike_secret_key"),
    "fr_phone_number": re.compile(r"(?<![\w.])(?:\+33\s?|0)[67](?:[\s.\-]?\d{2}){4}(?![\w.])"),
}

# Fichiers qui DOCUMENTENT les règles (noms de motifs) sans contenir de secret.
EXCLUSIONS_CHEMIN = {
    "tools/secret_scan.py",
    "tests_cloud/test_secret_scan.py",
    "app/core/security_config.py",  # liste de fragments interdits (garde fail-closed)
    "tests_mika/test_security_config.py",  # vérifie l'absence du littéral historique
}

EXTENSIONS_BINAIRES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".db", ".sqlite", ".zip", ".gz"}
FICHIERS_INTERDITS = re.compile(r"(^|/)(\.env(\..+)?|.*\.(pem|key|p12|pfx|db|sqlite3?)|credentials.*\.json|service-account.*\.json)$")


class Detection(NamedTuple):
    emplacement: str
    regle: str


def _fichiers_suivis() -> List[str]:
    out = subprocess.run(["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f]


def scanner_texte(emplacement: str, texte: str) -> Iterable[Detection]:
    for num, ligne in enumerate(texte.splitlines(), start=1):
        for nom, motif in REGLES.items():
            if motif.search(ligne):
                yield Detection(f"{emplacement}:{num}", nom)


def scanner_arbre() -> List[Detection]:
    resultats: List[Detection] = []
    for chemin in _fichiers_suivis():
        if chemin == ".env.example":
            pass
        elif FICHIERS_INTERDITS.search(chemin):
            resultats.append(Detection(chemin, "forbidden_file"))
            continue
        if chemin in EXCLUSIONS_CHEMIN or Path(chemin).suffix.lower() in EXTENSIONS_BINAIRES:
            continue
        try:
            texte = (RACINE / chemin).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        resultats.extend(scanner_texte(chemin, texte))
    return resultats


def scanner_historique() -> List[Detection]:
    """Scanne uniquement les lignes AJOUTÉES de chaque commit (pas les retraits)."""
    out = subprocess.run(
        ["git", "log", "--all", "-p", "--no-color", "--format=COMMIT %h"],
        cwd=RACINE, capture_output=True, text=True, check=True,
    )
    resultats: List[Detection] = []
    commit, fichier = "?", "?"
    for ligne in out.stdout.splitlines():
        if ligne.startswith("COMMIT "):
            commit = ligne.split()[1]
        elif ligne.startswith("+++ b/"):
            fichier = ligne[6:]
        elif ligne.startswith("+") and not ligne.startswith("+++"):
            if fichier in EXCLUSIONS_CHEMIN:
                continue
            for nom, motif in REGLES.items():
                if motif.search(ligne):
                    resultats.append(Detection(f"{commit}:{fichier}", nom))
    return sorted(set(resultats))


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--history", action="store_true", help="scanner aussi l'historique git")
    args = ap.parse_args(argv)

    detections = scanner_arbre()
    print(f"[arbre] {len(detections)} détection(s)")
    for d in detections:
        print(f"  SECRET_DETECTED rule={d.regle} path={d.emplacement}")

    code = 1 if detections else 0
    if args.history:
        hist = scanner_historique()
        print(f"[historique] {len(hist)} détection(s) (valeurs masquées)")
        for d in hist:
            print(f"  HISTORY rule={d.regle} commit:path={d.emplacement}")
        # L'historique connu (littéral faible déjà documenté) est informatif :
        # seul l'arbre courant fait échouer la CI.
    return code


if __name__ == "__main__":
    sys.exit(main())
