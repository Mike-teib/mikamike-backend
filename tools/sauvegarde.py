"""
sauvegarde.py — Sauvegarde / restauration cohérentes des deux bases SQLite (session 5, runbooks).

    python -m tools.sauvegarde sauvegarder --dest <dossier>
    python -m tools.sauvegarde verifier   --source <dossier>
    python -m tools.sauvegarde restaurer  --source <dossier> --confirmer   # APPLICATION ARRÊTÉE

Lit MIKA_DB_URL et BILLING_DB_URL (aucun secret). Sauvegarde EN LIGNE via l'API `backup` de
sqlite3 (copie cohérente même pendant des écritures), puis écrit SAUVEGARDE.json : révision
Alembic de chaque base, taille, SHA-256, date. `restaurer` revérifie les empreintes puis remplace
chaque base de façon atomique (copie temporaire + os.replace) ; l'ancienne base est conservée
à côté (`<base>.avant-restauration-<date>`). Bases non SQLite : refus explicite (utiliser l'outil
natif du moteur, ex. pg_dump). Codes : 0 ok · 1 erreur · 2 usage / refus.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Dict

FORMAT = "mika-sauvegarde/1"
BASES = {"mika": "MIKA_DB_URL", "billing": "BILLING_DB_URL"}


class Refus(RuntimeError):
    pass


def _chemin_sqlite(var: str) -> Path:
    url = os.getenv(var, "")
    if not url.startswith("sqlite:///"):
        raise Refus(f"{var} : base non SQLite (utiliser l'outil natif du moteur)")
    chemin = url[len("sqlite:///"):]
    if not chemin or chemin == ":memory:":
        raise Refus(f"{var} : chemin SQLite invalide")
    return Path(chemin)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _revision(p: Path) -> str | None:
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        return con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        con.close()


def sauvegarder(dest: Path) -> Dict:
    dest.mkdir(parents=True, exist_ok=False)
    bases = {}
    for nom, var in BASES.items():
        src = _chemin_sqlite(var)
        if not src.is_file():
            raise Refus(f"{var} : fichier absent")
        cible = dest / f"{nom}.db"
        s, d = sqlite3.connect(str(src)), sqlite3.connect(str(cible))
        try:
            s.backup(d)
        finally:
            d.close()
            s.close()
        bases[nom] = {"fichier": cible.name, "sha256": _sha(cible), "taille": cible.stat().st_size,
                      "revision": _revision(cible)}
    meta = {"format": FORMAT, "date": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
            "bases": bases}
    (dest / "SAUVEGARDE.json").write_text(json.dumps(meta, indent=2, sort_keys=True), "utf-8")
    return meta


def verifier(source: Path) -> Dict:
    meta = json.loads((source / "SAUVEGARDE.json").read_text("utf-8"))
    if meta.get("format") != FORMAT or set(meta.get("bases", {})) != set(BASES):
        raise Refus("sauvegarde : format invalide")
    for nom, b in meta["bases"].items():
        f = source / b["fichier"]
        if not f.is_file() or f.stat().st_size != b["taille"] or _sha(f) != b["sha256"]:
            raise Refus(f"sauvegarde altérée : {nom}")
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise Refus(f"sauvegarde corrompue : {nom}")
        finally:
            con.close()
    return meta


def restaurer(source: Path) -> Dict:
    meta = verifier(source)
    horodatage = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for nom, var in BASES.items():
        cible = _chemin_sqlite(var)
        cible.parent.mkdir(parents=True, exist_ok=True)
        tmp = cible.with_name(cible.name + ".restauration-en-cours")
        shutil.copyfile(source / meta["bases"][nom]["fichier"], tmp)
        if cible.exists():
            shutil.copyfile(cible, cible.with_name(f"{cible.name}.avant-restauration-{horodatage}"))
        os.replace(tmp, cible)
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools.sauvegarde")
    ap.add_argument("commande", choices=("sauvegarder", "verifier", "restaurer"))
    ap.add_argument("--dest")
    ap.add_argument("--source")
    ap.add_argument("--confirmer", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    try:
        if a.commande == "sauvegarder":
            if not a.dest:
                return 2
            meta = sauvegarder(Path(a.dest))
        elif a.commande == "verifier":
            if not a.source:
                return 2
            meta = verifier(Path(a.source))
        else:
            if not a.source or not a.confirmer:
                print("restaurer exige --source et --confirmer (application ARRÊTÉE)", file=sys.stderr)
                return 2
            meta = restaurer(Path(a.source))
    except (Refus, FileExistsError) as e:
        print(f"refus : {e}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, sqlite3.Error) as e:
        print(f"erreur : {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"commande": a.commande, **meta}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
