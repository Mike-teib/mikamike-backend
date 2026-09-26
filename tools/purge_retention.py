"""
purge_retention.py — Purge des données au-delà des durées de conservation (lot 20, S4).

    python -m tools.purge_retention              # SIMULATION : compte les lignes concernées
    python -m tools.purge_retention --appliquer  # supprime (opérateur, après validation DPO)

Politique : app/core/retention.py (surcharges MIKA_RETENTION_<CLE>_JOURS). N'affiche que des
comptes par table (aucune donnée d'élève).
"""

from __future__ import annotations

import json
import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--appliquer"]):
        print("usage : python -m tools.purge_retention [--appliquer]", file=sys.stderr)
        return 2
    appliquer = argv == ["--appliquer"]
    from app.api.v1.mikamike.store import SessionLocal as MikaSession
    from app.core.retention import PolitiqueInvalide, politique, purger_billing, purger_mika
    from paiement_comptes.database import SessionLocal as BillingSession

    try:
        pol = politique()
    except PolitiqueInvalide as exc:
        print(f"politique invalide : {exc}", file=sys.stderr)
        return 2
    with MikaSession() as m, BillingSession() as b:
        res = {"mode": "APPLIQUE" if appliquer else "SIMULATION", "politique_jours": pol,
               "mika": purger_mika(m, appliquer=appliquer), "billing": purger_billing(b, appliquer=appliquer)}
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
