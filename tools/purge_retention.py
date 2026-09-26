"""
purge_retention.py — Purge des données au-delà des durées de conservation (lot 20 S4, session 5).

    python -m tools.purge_retention                              # SIMULATION (défaut) : rapport scellé
    python -m tools.purge_retention --sortie rapport.json        # idem, rapport écrit dans un fichier
    MIKA_OPERATEUR=<id> python -m tools.purge_retention --appliquer --rapport rapport.json [--lot 500]
    python -m tools.purge_retention --verifier-audit             # contrôle du journal d'audit

Règles (session 5) :
  - aucune application sans rapport préalable : le rapport (≤ 24 h, même politique) fixe la date de
    référence et le nombre maximal de lignes par table ; tout élargissement est refusé ;
  - suppression par lots validés un à un : relancer après interruption reprend et termine ;
    relancer après succès ne supprime rien (idempotent) ;
  - journal d'audit JSONL chaîné (SHA-256 de la ligne précédente) : DEBUT puis FIN/ECHEC, avec
    l'opérateur, l'empreinte du rapport, la politique, les métriques ; jamais de donnée d'élève.
    Emplacement : MIKA_RETENTION_AUDIT (défaut var/retention_audit.jsonl) — à conserver hors du
    serveur applicatif en production.

Politique : app/core/retention.py (surcharges MIKA_RETENTION_<CLE>_JOURS), non validée par le DPO
(DPO_RETENTION_DECISION.md).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

ZERO = "0" * 64
USAGE = ("usage : python -m tools.purge_retention [--sortie F] | --appliquer --rapport F [--lot N]"
         " | --verifier-audit")


def chemin_audit() -> Path:
    return Path(os.getenv("MIKA_RETENTION_AUDIT") or "var/retention_audit.jsonl")


def _derniere_empreinte(p: Path) -> str:
    if not p.exists():
        return ZERO
    lignes = p.read_bytes().splitlines()
    return hashlib.sha256(lignes[-1]).hexdigest() if lignes else ZERO


def ecrire_audit(entree: dict, p: Optional[Path] = None) -> None:
    p = p or chemin_audit()
    p.parent.mkdir(parents=True, exist_ok=True)
    ligne = json.dumps({**entree, "precedent": _derniere_empreinte(p)}, sort_keys=True, ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(ligne + "\n")
        f.flush()
        os.fsync(f.fileno())


def verifier_audit(p: Optional[Path] = None) -> List[str]:
    """Anomalies : chaîne rompue (ligne modifiée/supprimée), exécution sans FIN (interrompue)."""
    p = p or chemin_audit()
    if not p.exists():
        return []
    anomalies, precedent, ouverts = [], ZERO, {}
    for i, brut in enumerate(p.read_bytes().splitlines(), 1):
        try:
            e = json.loads(brut)
        except ValueError:
            anomalies.append(f"ligne {i} : JSON invalide")
            precedent = hashlib.sha256(brut).hexdigest()
            continue
        if e.get("precedent") != precedent:
            anomalies.append(f"ligne {i} : chaîne rompue")
        precedent = hashlib.sha256(brut).hexdigest()
        if e.get("etape") == "DEBUT":
            ouverts[e.get("execution")] = i
        elif e.get("etape") in ("FIN", "ECHEC"):
            ouverts.pop(e.get("execution"), None)
    anomalies += [f"ligne {i} : exécution {x} sans FIN (interrompue : relancer pour reprendre)"
                  for x, i in ouverts.items()]
    return anomalies


def _maintenant_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _lire_args(argv: List[str]):
    opts = {"appliquer": False, "rapport": None, "sortie": None, "lot": None, "verifier_audit": False}
    it = iter(argv)
    for a in it:
        if a == "--appliquer":
            opts["appliquer"] = True
        elif a == "--verifier-audit":
            opts["verifier_audit"] = True
        elif a in ("--rapport", "--sortie", "--lot"):
            v = next(it, None)
            if v is None:
                return None
            opts[a[2:]] = v
        else:
            return None
    if opts["verifier_audit"] and len(argv) != 1:
        return None
    if opts["appliquer"] != bool(opts["rapport"]) or (opts["lot"] and not opts["appliquer"]):
        return None
    if opts["lot"] is not None and not opts["lot"].isdigit():
        return None
    return opts


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = _lire_args(argv)
    if opts is None:
        print(USAGE, file=sys.stderr)
        return 2
    if opts["verifier_audit"]:
        anomalies = verifier_audit()
        print(json.dumps({"journal": str(chemin_audit()), "anomalies": anomalies}, indent=2, ensure_ascii=False))
        return 1 if anomalies else 0

    from app.api.v1.mikamike.store import SessionLocal as MikaSession
    from app.core import retention
    from paiement_comptes.database import SessionLocal as BillingSession

    try:
        retention.politique()
    except retention.PolitiqueInvalide as exc:
        print(f"politique invalide : {exc}", file=sys.stderr)
        return 2

    if not opts["appliquer"]:
        with MikaSession() as m, BillingSession() as b:
            r = retention.rapport(m, b)
        if opts["sortie"]:
            Path(opts["sortie"]).write_text(json.dumps(r, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"mode": "SIMULATION", **r}, indent=2, sort_keys=True))
        return 0

    operateur = (os.getenv("MIKA_OPERATEUR") or "").strip()
    if not operateur:
        print("MIKA_OPERATEUR requis pour appliquer (identifiant d'opérateur, tracé dans l'audit)", file=sys.stderr)
        return 2
    try:
        r = json.loads(Path(opts["rapport"]).read_text(encoding="utf-8"))
        retention.verifier_rapport(r)
    except (OSError, ValueError) as exc:
        print(f"rapport refusé : {exc}", file=sys.stderr)
        return 3
    execution = hashlib.sha256(f"{r['empreinte']}|{_maintenant_iso()}".encode()).hexdigest()[:16]
    commun = {"execution": execution, "operateur": operateur, "empreinte_rapport": r["empreinte"],
              "reference": r["reference"], "politique_jours": r["politique_jours"]}
    ecrire_audit({**commun, "etape": "DEBUT", "horodatage": _maintenant_iso(),
                  "prevu": {"mika": r["mika"], "billing": r["billing"]}})
    try:
        with MikaSession() as m, BillingSession() as b:
            res = retention.appliquer_rapport(m, b, r, lot=int(opts["lot"] or retention.LOT_DEFAUT))
    except retention.RapportInvalide as exc:
        ecrire_audit({**commun, "etape": "ECHEC", "horodatage": _maintenant_iso(), "motif": str(exc)})
        print(f"rapport refusé : {exc}", file=sys.stderr)
        return 3
    ecrire_audit({**commun, "etape": "FIN", "horodatage": _maintenant_iso(),
                  "supprimes": res["supprimes"], "metriques": res["metriques"]})
    print(json.dumps({"mode": "APPLIQUE", "execution": execution, **res}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
