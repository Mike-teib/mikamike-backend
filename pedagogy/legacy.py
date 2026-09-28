"""
legacy.py — Correspondance des 47 notions historiques (CURRICULA_DATA) avec le registre.

Les anciens contenus sont des CANDIDATS À AUDITER, jamais des sources de vérité : ce module
ne modifie ni l'ancien fichier ni le registre ; il produit une table de correspondance
  pedagogy/data/legacy/legacy_notions_map.json
avec, pour chaque notion historique :
  MATCHED_EXACT     même titre normalisé, même matière, même niveau
  MATCHED_SIMILAR   titre proche (Jaccard > 0.5 sur les mots significatifs, sans mot discriminant
                    contradictoire) — correspondance INDICATIVE, à confirmer humainement
  UNMATCHED         aucune notion candidate correspondante
  LEVEL_AMBIGUOUS   niveau « primaire » (ni CM1 ni CM2, hors périmètre 6e → Tle)

  python -m pedagogy.legacy [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set

from pedagogy.models import Level, Notion, Subject
from pedagogy.registry import DATA_DIR, load_registry

LEVEL_MAP = {"6e": Level.SIXIEME, "5e": Level.CINQUIEME, "4e": Level.QUATRIEME, "3e": Level.TROISIEME,
             "2de": Level.SECONDE, "1re": Level.PREMIERE, "tle": Level.TERMINALE}
SUBJECT_MAP = {"maths": Subject.MATHS, "physique": Subject.PHYSIQUE_CHIMIE, "chimie": Subject.PHYSIQUE_CHIMIE,
               "svt": Subject.SVT}
_STOP = {"de", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "en", "d", "l", "un", "une"}
_SYNONYMS = {"1er": "premier", "2nd": "second", "2nde": "second", "seconde": "second"}
# Mots discriminants : deux titres qui en portent des membres différents d'un même groupe ne
# désignent pas la même notion (« réciproque de Pythagore » ≠ « réciproque de Thalès »).
_EXCLUSIVE_GROUPS = ({"pythagore", "thales"}, {"premier", "second"}, {"arithmetiques", "geometriques"},
                     {"exponentielle", "logarithme"}, {"tension", "intensite"})


def _words(t: str) -> Set[str]:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return {_SYNONYMS.get(w, w) for w in re.findall(r"[a-z0-9]+", t) if w not in _STOP}


def _incompatible(a: str, b: str) -> bool:
    sa, sb = _words(a), _words(b)
    return any((sa & g) and (sb & g) and not (sa & sb & g) for g in _EXCLUSIVE_GROUPS)


def _jaccard(a: str, b: str) -> float:
    sa, sb = _words(a), _words(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def build_map(notions: List[Notion]) -> List[Dict[str, object]]:
    from app.api.v1.parcours.curriculum_dataset import CURRICULA_DATA

    out: List[Dict[str, object]] = []
    for (lvl, sub), nodes in sorted(CURRICULA_DATA.items()):
        for node in nodes:
            entry: Dict[str, object] = {"legacy_id": node.notion_id, "legacy_title": node.titre,
                                        "legacy_level": lvl, "legacy_subject": sub}
            level, subject = LEVEL_MAP.get(lvl), SUBJECT_MAP.get(sub)
            if level is None or subject is None:
                entry.update(status="LEVEL_AMBIGUOUS", candidates=[])
                out.append(entry)
                continue
            pool = [n for n in notions if n.subject == subject and n.level == level]
            best: Optional[Notion] = None
            best_s = 0.0
            for n in sorted(pool, key=lambda x: x.notion_id):
                if _incompatible(n.title, node.titre):
                    continue
                s = 1.0 if _words(n.title) == _words(node.titre) else _jaccard(n.title, node.titre)
                if s > best_s:
                    best, best_s = n, s
            if best is not None and best_s == 1.0:
                entry.update(status="MATCHED_EXACT", candidates=[best.notion_id], score=1.0)
            elif best is not None and best_s > 0.5:
                entry.update(status="MATCHED_SIMILAR", candidates=[best.notion_id], score=round(best_s, 2))
            else:
                entry.update(status="UNMATCHED", candidates=[], score=round(best_s, 2))
            out.append(entry)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DATA_DIR / "legacy" / "legacy_notions_map.json")
    a = ap.parse_args(argv)
    reg = load_registry()
    entries = build_map(list(reg.notions.values()))
    counts: Dict[str, int] = {}
    for e in entries:
        counts[str(e["status"])] = counts.get(str(e["status"]), 0) + 1
    doc = {"schema_version": "1.0", "generated_by": "pedagogy.legacy",
           "disclaimer": "Correspondance indicative : les notions historiques n'ont aucune source ; "
                         "aucune n'est une preuve. Aucun ancien contenu n'est modifié.",
           "counts": dict(sorted(counts.items())), "entries": entries}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
