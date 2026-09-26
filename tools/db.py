#!/usr/bin/env python3
"""
db.py — Migrations des bases MikaMike (Alembic), sans secret ni URL en dur.

  python -m tools.db status                  révision courante / head de chaque base
  python -m tools.db upgrade [mika|billing]  applique les migrations (défaut : les deux)
  python -m tools.db downgrade <cible> <rev> retour arrière (ex. base : `base`)
  python -m tools.db stamp-existant <cible>  adopte une base créée avant les migrations
  python -m tools.db sql <cible>             SQL de la migration complète (mode hors ligne,
                                             pour revue DBA avant application en production)
Les URL viennent de MIKA_DB_URL / BILLING_DB_URL. Ne touche qu'aux bases ainsi désignées.
"""

from __future__ import annotations

import sys

from alembic import command

from app.db import migrations as m


def main(argv=None) -> int:
    """Erreurs attendues (révision inconnue, base non conforme, cible inconnue) : message clair
    et code 1, jamais de trace (revue session 3 : une version incorrecte donnait une trace)."""
    from alembic.util import CommandError

    try:
        return _main(argv)
    except (CommandError, m.SchemaNonAJour, ValueError, KeyError) as exc:
        print(f"erreur: {exc}", file=sys.stderr)
        return 1


def _main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    cmd, *rest = argv
    cibles = [rest[0]] if rest else list(m.CIBLES)
    if cmd == "status":
        for c, e in m.etat().items():
            ok = "OK" if e["courante"] == e["head"] else "EN RETARD"
            print(f"{c:8} courante={e['courante']} head={e['head']} {ok}")
        return 0 if all(e["courante"] == e["head"] for e in m.etat().values()) else 1
    if cmd == "upgrade":
        for c in cibles:
            m.upgrade(c)
            print(f"{c}: {m.courante(c)}")
        return 0
    if cmd == "downgrade" and len(rest) == 2:
        m.downgrade(rest[0], rest[1])
        print(f"{rest[0]}: {m.courante(rest[0])}")
        return 0
    if cmd == "stamp-existant" and len(rest) == 1:
        print(f"{rest[0]}: adoptée à {m.adopter_base_existante(rest[0], m.BASELINE_REVISION[rest[0]])}")
        return 0
    if cmd == "sql" and len(rest) == 1:
        command.upgrade(m.config(rest[0]), "head", sql=True)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
