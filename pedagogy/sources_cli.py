"""
sources_cli.py — Outils en ligne de commande pour les sources officielles locales.

  python -m pedagogy.sources_cli status
      état de chaque source attendue (EXPECTED / RETRIEVED / VERIFIED, fichier présent ?)
  python -m pedagogy.sources_cli register SOURCE_ID CHEMIN_LOCAL [--reference-verified]
      calcule le SHA-256 du PDF déposé et met à jour official_sources.json
  python -m pedagogy.sources_cli propose
      pour chaque notion candidate UNPROVEN, pages où son titre apparaît dans une source
      récupérée (propositions à confirmer : aucune promotion automatique)
  python -m pedagogy.sources_cli verify
      recalcule le statut de preuve de toutes les notions ; code 1 si une notion déclarée
      PROVEN_OFFICIAL n'est pas vérifiable

Aucun téléchargement : les PDF doivent être déposés manuellement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from pedagogy.models import OfficialSource, ProofStatus, SourceRetrieval
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import (
    ExtractionError,
    SourceText,
    load_source_text,
    propose_promotions,
    recompute_statuses,
    register_source,
)

SOURCES_FILE = DATA_DIR / "sources" / "official_sources.json"


def _loaded_texts(sources: Dict[str, OfficialSource], root: Path) -> Dict[str, SourceText]:
    texts: Dict[str, SourceText] = {}
    for sid, s in sorted(sources.items()):
        if s.retrieval == SourceRetrieval.EXPECTED:
            continue
        try:
            texts[sid] = load_source_text(s, root)
        except ExtractionError as exc:
            print(f"  ! {sid}: {exc}", file=sys.stderr)
    return texts


def cmd_status(data_dir: Path, root: Path) -> int:
    reg = load_registry(data_dir)
    for sid, s in sorted(reg.sources.items()):
        present = bool(s.local_path) and (root / s.local_path).is_file()
        print(f"{sid:24} {s.retrieval.value:9} fichier={'oui' if present else 'non':3} ref_verifiee={s.reference_verified}")
    return 0


def cmd_register(data_dir: Path, root: Path, source_id: str, local_path: str, verified: bool) -> int:
    path = data_dir / "sources" / "official_sources.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    for i, s in enumerate(raw["sources"]):
        if s["source_id"] == source_id:
            src = OfficialSource.model_validate({**s, "local_path": local_path, "reference_verified": verified})
            src = register_source(src, root)
            raw["sources"][i] = src.model_dump(mode="json")
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{source_id}: {src.retrieval.value} sha256={src.sha256}")
            return 0
    print(f"source inconnue: {source_id}", file=sys.stderr)
    return 2


def cmd_propose(data_dir: Path, root: Path) -> int:
    reg = load_registry(data_dir)
    texts = _loaded_texts(reg.sources, root)
    props = propose_promotions(reg.notions.values(), texts)
    for p in props:
        print(f"{p.notion_id}\t{p.source_id}\tpages={p.pages}")
    print(f"{len(props)} proposition(s) ; {len(texts)} source(s) lisible(s)")
    return 0


def cmd_verify(data_dir: Path, root: Path) -> int:
    reg = load_registry(data_dir)
    texts = _loaded_texts(reg.sources, root)
    results = recompute_statuses(list(reg.notions.values()), texts)
    bad: List[str] = []
    counts: Dict[str, int] = {}
    for nid, res in sorted(results.items()):
        counts[res.status.value] = counts.get(res.status.value, 0) + 1
        declared = reg.notions[nid].proof_status
        if declared == ProofStatus.PROVEN_OFFICIAL and res.status != ProofStatus.PROVEN_OFFICIAL:
            bad.append(f"{nid}: {','.join(res.reasons)}")
    print(json.dumps(counts, sort_keys=True))
    for b in bad:
        print("NON VERIFIABLE", b)
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--root", type=Path, default=REPO_ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    r = sub.add_parser("register")
    r.add_argument("source_id")
    r.add_argument("local_path")
    r.add_argument("--reference-verified", action="store_true")
    sub.add_parser("propose")
    sub.add_parser("verify")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        return cmd_status(a.data_dir, a.root)
    if a.cmd == "register":
        return cmd_register(a.data_dir, a.root, a.source_id, a.local_path, a.reference_verified)
    if a.cmd == "propose":
        return cmd_propose(a.data_dir, a.root)
    return cmd_verify(a.data_dir, a.root)


if __name__ == "__main__":
    sys.exit(main())
