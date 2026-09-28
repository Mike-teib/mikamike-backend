#!/usr/bin/env python3
"""
prerequisite_graph_validator.py — Construit et valide le graphe pédagogique des prérequis.

Usage :
    python prerequisite_graph_validator.py [--data-dir DIR] [--graph-out PATH] [--check-only]

Écrit prerequisite_graph.json (racine du dépôt par défaut) sauf avec --check-only, affiche
un résumé et sort en code 1 si une anomalie BLOCKER ou ERROR est détectée.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pedagogy.graph import build_graph, validate_graph  # noqa: E402
from pedagogy.issues import Severity  # noqa: E402
from pedagogy.registry import DATA_DIR, load_registry  # noqa: E402

DEFAULT_GRAPH_OUT = REPO_ROOT / "prerequisite_graph.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validation du graphe pédagogique des prérequis MikaMike.")
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--graph-out", type=Path, default=DEFAULT_GRAPH_OUT)
    ap.add_argument("--check-only", action="store_true", help="n'écrit pas le fichier de graphe")
    args = ap.parse_args(argv)

    reg = load_registry(args.data_dir.resolve())
    graph = build_graph(reg)
    issues = validate_graph(graph)

    stats = graph["stats"]
    print(f"Graphe pédagogique — data: {args.data_dir}")
    print(f"  noeuds : {stats['node_count']}")
    print(f"  arêtes : {stats['edge_count']} " + json.dumps(stats["edges_by_type"], sort_keys=True))
    if reg.load_errors:
        print(f"  fichiers non chargés : {len(reg.load_errors)}")
        for path, reason in reg.load_errors[:20]:
            print(f"    - {path}: {reason}")

    by_sev = Counter(i.severity.value for i in issues)
    by_code = Counter((i.code, i.severity.value) for i in issues)
    print(f"  anomalies : {len(issues)} " + json.dumps(dict(sorted(by_sev.items()))))
    for (code, sev), n in sorted(by_code.items()):
        print(f"    {sev:8} {code:36} {n}")
    for i in issues:
        if i.severity in (Severity.BLOCKER, Severity.ERROR):
            print(f"  [{i.severity.value}] {i.code} {i.object_id} {i.detail}")

    if not args.check_only:
        out = args.graph_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"  graphe écrit : {out}")

    failing = any(i.severity in (Severity.BLOCKER, Severity.ERROR) for i in issues)
    print("RESULTAT : " + ("ECHEC" if failing else "OK"))
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
