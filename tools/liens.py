#!/usr/bin/env python3
"""
liens.py — Outil OPÉRATEUR : premier rattachement d'un élève (décision D8).

  python -m tools.liens inviter <pseudo-id> [--relation parent|eleve]

Émet une invitation à usage unique (code affiché UNE fois, à remettre au parent par un canal
de confiance : établissement, support). Le parent valide ensuite le code depuis SON compte
(POST /api/v1/liens/accepter, `confirmation: true`). Aucun lien n'est créé par cet outil.
BILLING_DB_URL désigne la base ; aucune URL ni secret en dur.
"""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools.liens")
    sous = ap.add_subparsers(dest="cmd", required=True)
    inv = sous.add_parser("inviter")
    inv.add_argument("pseudo_id")
    inv.add_argument("--relation", choices=("parent", "eleve"), default="parent")
    args = ap.parse_args(argv)

    import re

    from app.core.pseudonymisation import hmac_eleve
    from app.core.validation import ID_PATTERN
    from paiement_comptes import liens
    from paiement_comptes.database import SessionLocal

    if not re.fullmatch(ID_PATTERN, args.pseudo_id):
        print("erreur: pseudo-id invalide", file=sys.stderr)
        return 1
    db = SessionLocal()
    try:
        code, inv_ = liens.creer_invitation(db, args.pseudo_id, hmac_eleve(args.pseudo_id),
                                            relation=args.relation, emis_par="operateur")
        relation, expire = inv_.relation, inv_.expire_le.isoformat()
    except ValueError as exc:
        print(f"erreur: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"code: {code}")
    print(f"relation: {relation} · expire le {expire}Z · usage unique")
    return 0


if __name__ == "__main__":
    sys.exit(main())
