#!/usr/bin/env python3
"""
M01_346_COMPARISON_TOOL.py — Non-régression du lot M01 (Maths Cycle 3, 346 notions publiées).

Compare, notion par notion :
    ANCIENNE notion PUBLIÉE (corpus M01 historique)  VS  notion OFFICIELLE RÉ-EXTRAITE

et classe chacune des notions publiées :
    IDENTIQUE            texte, formules, source et affectation identiques
    TEXTE_MODIFIE        texte différent (hors formules)
    FORMULE_MODIFIEE     contenu mathématique différent (nombres, opérateurs, variables)
    NOTATION_DEGRADEE    même mathématique mais notation appauvrie (10⁻³→10-3, 1/10→0,1,
                         x²→x2, √ perdu, symbole ≤ ≥ × ÷ π perdu, LaTeX cassé)
    SOURCE_DIFFERENTE    même notion, source / page / version différente
    NOTION_REAFFECTEE    même texte mais niveau / domaine / chapitre différent
    NOTION_ABSENTE       aucune notion ré-extraite correspondante
Une notion peut porter plusieurs drapeaux ; le statut principal suit l'ordre de gravité :
NOTION_ABSENTE > FORMULE_MODIFIEE > NOTATION_DEGRADEE > NOTION_REAFFECTEE > TEXTE_MODIFIE >
SOURCE_DIFFERENTE > IDENTIQUE. Les notions ré-extraites sans correspondant sont listées
à part (NOUVELLE_DANS_REEXTRACTION).

GARANTIES
  - LECTURE SEULE : ne modifie jamais la publication ni aucun fichier d'entrée.
  - Si un des deux corpus est absent/illisible : sortie 2, message CORPUS_ABSENT, AUCUN rapport
    de comparaison (on ne prétend jamais avoir comparé).
  - Si le corpus publié ne contient pas exactement 346 notions : avertissement explicite dans
    le rapport (EFFECTIF_INATTENDU) ; la comparaison porte sur ce qui est présent.

FORMATS D'ENTRÉE (auto-détectés par extension) : .jsonl (1 objet/ligne), .json (liste ou
{"notions": [...]}) ou .csv. Correspondance des champs configurable (--map), défauts :
  id=notion_id  text=text|official_wording|title  level=level  domain=domain  chapter=chapter
  source=source_id|source  page=source_page_or_section|page

Usage :
  python M01_346_COMPARISON_TOOL.py --published M01_publie.jsonl --reextracted M01_reextrait.jsonl \\
      --out-dir reports/m01 [--expected-count 346] [--map text=libelle,id=code]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

EXPECTED_COUNT = 346
TEMPLATE = Path(__file__).resolve().parent / "M01_346_COMPARISON_REPORT_TEMPLATE.md"

PRIORITY = ("NOTION_ABSENTE", "FORMULE_MODIFIEE", "NOTATION_DEGRADEE", "NOTION_REAFFECTEE",
            "TEXTE_MODIFIE", "SOURCE_DIFFERENTE", "IDENTIQUE")

DEFAULT_MAP = {
    "id": ["notion_id", "id", "code"],
    "text": ["text", "official_wording", "libelle", "title", "titre"],
    "level": ["level", "niveau"],
    "domain": ["domain", "domaine"],
    "chapter": ["chapter", "chapitre"],
    "source": ["source_id", "source", "source_url_or_ref"],
    "page": ["source_page_or_section", "page"],
}


class CorpusError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def _records(path: Path) -> List[dict]:
    if not path.is_file():
        raise CorpusError(f"CORPUS_ABSENT:{path}")
    suffix = path.suffix.lower()
    try:
        if suffix == ".jsonl":
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return data["notions"] if isinstance(data, dict) else data
        if suffix == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))
    except (ValueError, KeyError) as exc:
        raise CorpusError(f"CORPUS_ILLISIBLE:{path.name}:{type(exc).__name__}") from exc
    raise CorpusError(f"FORMAT_NON_SUPPORTE:{path.suffix}")


def _field(rec: dict, names: Sequence[str]) -> str:
    for n in names:
        if n in rec and rec[n] not in (None, ""):
            return str(rec[n])
    return ""


def load_corpus(path: Path, mapping: Dict[str, List[str]]) -> List[Dict[str, str]]:
    out = []
    for i, rec in enumerate(_records(path)):
        if not isinstance(rec, dict):
            raise CorpusError(f"ENREGISTREMENT_INVALIDE:{path.name}:{i + 1}")
        row = {k: _field(rec, v) for k, v in mapping.items()}
        if not row["text"]:
            raise CorpusError(f"TEXTE_ABSENT:{path.name}:{i + 1}")
        row["id"] = row["id"] or f"#{i + 1}"
        out.append(row)
    ids = [r["id"] for r in out]
    dups = sorted(k for k, c in Counter(ids).items() if c > 1)
    if dups:
        raise CorpusError(f"ID_DUPLIQUE:{path.name}:{','.join(dups[:10])}")
    return out


# --------------------------------------------------------------------------- #
# Analyse du texte et des mathématiques
# --------------------------------------------------------------------------- #
_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_MATH_SYMBOLS = "≤≥≠≈×÷π√∞±∈∉⊂∪∩→↦°%"


def _nfc(t: str) -> str:
    return unicodedata.normalize("NFC", t or "")


def norm_text(t: str) -> str:
    t = _nfc(t).casefold().replace("’", "'").replace("\u00a0", " ")
    return " ".join(t.split()).rstrip(" .;:")


def text_without_math(t: str) -> str:
    t = re.sub(r"\$[^$]*\$", " ", t)
    t = re.sub(r"[\d⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺^_{}()\[\]=<>+\-*/×÷≤≥≠≈π√∞±,.]+", " ", t)
    return norm_text(t)


def math_signature(t: str) -> Tuple[str, ...]:
    """Contenu mathématique canonique : nombres (virgule→point), opérateurs, exposants."""
    t = _nfc(t).replace("\\times", "×").replace("\\div", "÷").replace("\\leq", "≤").replace("\\geq", "≥")
    t = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", t)
    t = re.sub(r"\^\{([^{}]*)\}", r"^\1", t)
    t = re.sub(r"([0-9a-zA-Z)])([⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)", lambda m: m.group(1) + "^" + m.group(2).translate(_SUP), t)
    toks = re.findall(r"\d+(?:[.,]\d+)?|[=<>+\-×÷*/^≤≥≠≈π√]|[a-zA-Z](?=\s*[=^²])", t)
    return tuple(x.replace(",", ".") for x in toks)


def notation_degradation(old: str, new: str) -> List[str]:
    """Pertes de notation entre ancienne (publiée) et nouvelle (ré-extraite) formulation."""
    flags = []
    def count(t, pat):
        return len(re.findall(pat, t))
    pairs = [
        ("EXPOSANT_PERDU", r"\^|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+"),  # une occurrence = un exposant (pas un caractère)
        ("FRACTION_PERDUE", r"\d\s*/\s*\d|\\frac"),
        ("RACINE_PERDUE", r"√|\\sqrt"),
        ("LATEX_PERDU", r"\$"),
    ]
    for code, pat in pairs:
        a, b = count(old, pat), count(new, pat)
        if a != b:
            flags.append(code)
    for sym in _MATH_SYMBOLS:
        if old.count(sym) != new.count(sym):
            flags.append(f"SYMBOLE_MODIFIE:{sym}")
    if "\ufffd" in old + new:
        flags.append("CARACTERE_CORROMPU")
    if old.count("$") % 2 or new.count("$") % 2:
        flags.append("LATEX_DESEQUILIBRE")
    return flags


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(norm_text(a).split()), set(norm_text(b).split())
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


# --------------------------------------------------------------------------- #
# Appariement et classement
# --------------------------------------------------------------------------- #
def match(published: List[Dict[str, str]], reextracted: List[Dict[str, str]], min_sim: float = 0.6):
    """
    Appariement en 3 passes GLOBALES (évite qu'une notion absente « vole » le partenaire
    d'une autre) : 1) même identifiant ; 2) même texte normalisé ; 3) similarité ≥ min_sim.
    """
    by_id = {r["id"]: r for r in reextracted}
    used: set = set()
    partner: Dict[str, Tuple[Dict[str, str], str]] = {}
    for p in published:
        r = by_id.get(p["id"])
        if r is not None and r["id"] not in used:
            partner[p["id"]] = (r, "ID")
            used.add(r["id"])
    by_text: Dict[str, List[Dict[str, str]]] = {}
    for r in reextracted:
        by_text.setdefault(norm_text(r["text"]), []).append(r)
    for p in published:
        if p["id"] in partner:
            continue
        same = [r for r in by_text.get(norm_text(p["text"]), []) if r["id"] not in used]
        if same:
            partner[p["id"]] = (same[0], "TEXTE")
            used.add(same[0]["id"])
    for p in published:
        if p["id"] in partner:
            continue
        best = max(((r, _jaccard(p["text"], r["text"])) for r in reextracted if r["id"] not in used),
                   key=lambda x: (x[1], x[0]["id"]), default=(None, 0.0))
        if best[0] is not None and best[1] >= min_sim:
            partner[p["id"]] = (best[0], f"SIMILARITE:{best[1]:.2f}")
            used.add(best[0]["id"])
    pairs = [(p, *partner.get(p["id"], (None, None))) for p in published]
    extras = [r for r in reextracted if r["id"] not in used]
    return pairs, extras


def classify(p: Dict[str, str], r: Optional[Dict[str, str]]) -> List[str]:
    if r is None:
        return ["NOTION_ABSENTE"]
    flags = []
    old_sig, new_sig = math_signature(p["text"]), math_signature(r["text"])
    degr = notation_degradation(p["text"], r["text"])
    if old_sig != new_sig:
        flags.append("FORMULE_MODIFIEE")
    if degr:
        # ex. 10⁻³ → 10-3 : sens modifié ET notation dégradée (le statut principal reste le plus grave)
        flags.append("NOTATION_DEGRADEE")
    if any(p[k] and r[k] and norm_text(p[k]) != norm_text(r[k]) for k in ("level", "domain", "chapter")):
        flags.append("NOTION_REAFFECTEE")
    if text_without_math(p["text"]) != text_without_math(r["text"]):
        flags.append("TEXTE_MODIFIE")
    if any(p[k] and r[k] and norm_text(p[k]) != norm_text(r[k]) for k in ("source", "page")):
        flags.append("SOURCE_DIFFERENTE")
    return flags or ["IDENTIQUE"]


def compare(published, reextracted, expected_count: int = EXPECTED_COUNT) -> dict:
    pairs, extras = match(published, reextracted)
    rows = []
    for p, r, how in pairs:
        flags = classify(p, r)
        primary = next(s for s in PRIORITY if s in flags)
        rows.append({
            "published_id": p["id"], "reextracted_id": r["id"] if r else None, "matched_by": how,
            "status": primary, "flags": flags,
            "notation_details": notation_degradation(p["text"], r["text"]) if r else [],
            "published_text": p["text"], "reextracted_text": r["text"] if r else None,
        })
    counts = Counter(r["status"] for r in rows)
    warnings = []
    if len(published) != expected_count:
        warnings.append(f"EFFECTIF_INATTENDU: corpus publié = {len(published)} notions (attendu {expected_count})")
    return {
        "tool": "M01_346_COMPARISON_TOOL", "expected_count": expected_count,
        "published_count": len(published), "reextracted_count": len(reextracted),
        "counts": {s: counts.get(s, 0) for s in PRIORITY},
        "new_in_reextraction": sorted(r["id"] for r in extras),
        "warnings": warnings, "rows": rows,
    }


def render(result: dict, published_path: str, reextracted_path: str) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    counts_md = "\n".join(f"| {s} | {result['counts'][s]} |" for s in PRIORITY)
    detail = "\n".join(
        f"| `{r['published_id']}` | `{r['reextracted_id'] or '—'}` | {r['status']} | {', '.join(r['flags'])} "
        f"| {', '.join(r['notation_details']) or ''} |"
        for r in result["rows"] if r["status"] != "IDENTIQUE"
    ) or "| — | — | — | — | — |"
    values = {
        "STATUT_COMPARAISON": "COMPARAISON EFFECTUÉE",
        "CORPUS_PUBLIE": published_path, "CORPUS_REEXTRAIT": reextracted_path,
        "EFFECTIF_ATTENDU": str(result["expected_count"]),
        "EFFECTIF_PUBLIE": str(result["published_count"]),
        "EFFECTIF_REEXTRAIT": str(result["reextracted_count"]),
        "AVERTISSEMENTS": "\n".join(f"- {w}" for w in result["warnings"]) or "- aucun",
        "TABLEAU_COMPTES": counts_md,
        "TABLEAU_ECARTS": detail,
        "NOUVELLES": ", ".join(f"`{x}`" for x in result["new_in_reextraction"]) or "aucune",
    }
    for k, v in values.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    return tpl


def _parse_map(spec: Optional[str]) -> Dict[str, List[str]]:
    mapping = {k: list(v) for k, v in DEFAULT_MAP.items()}
    for part in filter(None, (spec or "").split(",")):
        key, _, col = part.partition("=")
        if key not in mapping or not col:
            raise SystemExit(f"--map invalide: {part}")
        mapping[key] = [col] + mapping[key]
    return mapping


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--published", type=Path, required=True)
    ap.add_argument("--reextracted", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("reports/m01"))
    ap.add_argument("--expected-count", type=int, default=EXPECTED_COUNT)
    ap.add_argument("--map", default=None)
    a = ap.parse_args(argv)
    mapping = _parse_map(a.map)
    try:
        pub = load_corpus(a.published, mapping)
        rex = load_corpus(a.reextracted, mapping)
    except CorpusError as exc:
        print(f"{exc} — aucune comparaison effectuée.", file=sys.stderr)
        return 2
    result = compare(pub, rex, a.expected_count)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "M01_346_COMPARISON_REPORT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (a.out_dir / "M01_346_COMPARISON_REPORT.md").write_text(
        render(result, str(a.published), str(a.reextracted)), encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False))
    for w in result["warnings"]:
        print("AVERTISSEMENT", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
